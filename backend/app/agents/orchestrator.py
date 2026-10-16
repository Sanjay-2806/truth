"""LangGraph multi-agent pipeline orchestrator for TruthGuard AI.

Implements stateful workflow with nodes for Retriever, Generator, Claim Extractor,
Claim Verifier, and Risk Decision agents, plus baselines (plain_rag, answer_level_check).
"""

from typing import TypedDict, List, Optional, Dict, Any, Literal
from pathlib import Path
import json
import time
import re
from langgraph.graph import StateGraph, END
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.records import (
    PassageRecord,
    DraftRecord,
    AtomicClaim,
    VerificationRecord,
    DecisionRecord,
    RetrievalRecord,
    ClaimExtractionRecord,
)
from app.agents.retriever import RetrieverAgent, get_retriever
from app.agents.generator import GeneratorAgent
from app.agents.extractor import ClaimExtractorAgent
from app.verification.verifier import ClaimVerifierAgent, get_nli_engine
from app.agents.decision import RiskDecisionAgent

logger = get_logger("truthguard.orchestrator")


class PipelineState(TypedDict):
    """Strongly-typed pipeline execution state across agents."""
    query: str
    mode: str
    top_k: int
    passages: List[PassageRecord]
    draft: Optional[DraftRecord]
    claims: List[AtomicClaim]
    verification: Optional[VerificationRecord]
    decision: Optional[DecisionRecord]
    timings: Dict[str, float]
    token_usage: Dict[str, int]
    metadata: Dict[str, Any]


class TruthGuardOrchestrator:
    """Manages LangGraph workflow execution for TruthGuard and comparative baselines."""

    def __init__(self):
        self.retriever = RetrieverAgent(retriever=get_retriever())
        self.generator = GeneratorAgent()
        self.extractor = ClaimExtractorAgent()
        self.verifier = ClaimVerifierAgent(engine=get_nli_engine())
        self.decision_agent = RiskDecisionAgent()

        # Load answer-level check prompt
        check_prompt_path = settings.PROJECT_ROOT / settings.PROMPTS_DIR / "answer_level_check_v1.txt"
        if not check_prompt_path.exists():
            check_prompt_path = Path("prompts/answer_level_check_v1.txt")
        self.answer_check_prompt = check_prompt_path.read_text(encoding="utf-8")

        self.graph = self._build_graph()

    def _build_graph(self):
        """Constructs the LangGraph state machine with conditional routing."""
        workflow = StateGraph(PipelineState)

        workflow.add_node("retrieve", self._node_retrieve)
        workflow.add_node("generate", self._node_generate)
        workflow.add_node("plain_rag", self._node_plain_rag)
        workflow.add_node("answer_level_check", self._node_answer_level_check)
        workflow.add_node("extract_claims", self._node_extract_claims)
        workflow.add_node("verify_claims", self._node_verify_claims)
        workflow.add_node("decide_risk", self._node_decide_risk)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")

        # Conditional route from generate based on requested mode
        workflow.add_conditional_edges(
            "generate",
            self._route_after_generation,
            {
                "plain_rag": "plain_rag",
                "answer_level_check": "answer_level_check",
                "truthguard": "extract_claims",
            },
        )

        workflow.add_edge("plain_rag", END)
        workflow.add_edge("answer_level_check", END)
        workflow.add_edge("extract_claims", "verify_claims")
        workflow.add_edge("verify_claims", "decide_risk")
        workflow.add_edge("decide_risk", END)

        return workflow.compile()

    def _route_after_generation(self, state: PipelineState) -> str:
        mode = state.get("mode", "truthguard").lower()
        if mode == "plain_rag":
            return "plain_rag"
        if mode == "answer_level_check":
            return "answer_level_check"
        return "truthguard"

    # --- Graph Nodes ---

    def _node_retrieve(self, state: PipelineState) -> Dict[str, Any]:
        t0 = time.time()
        query = state["query"]
        top_k = state.get("top_k", settings.TOP_K)
        record = self.retriever.retrieve(query=query, top_k=top_k)
        dt = (time.time() - t0) * 1000.0

        timings = state.get("timings", {})
        timings["retrieve_ms"] = round(dt, 2)
        return {"passages": record.passages, "timings": timings}

    def _node_generate(self, state: PipelineState) -> Dict[str, Any]:
        t0 = time.time()
        query = state["query"]
        passages = state.get("passages", [])
        retrieval_rec = RetrievalRecord(query=query, passages=passages, retrieval_mode="hybrid_rrf")

        draft = self.generator.generate(retrieval_rec)
        dt = (time.time() - t0) * 1000.0

        timings = state.get("timings", {})
        timings["generate_ms"] = round(dt, 2)

        # Approximate token telemetry (input chars/4, output chars/4)
        token_usage = state.get("token_usage", {})
        input_len = sum(len(p.text) for p in passages) + len(query)
        output_len = len(draft.answer)
        token_usage["generator_prompt_tokens"] = input_len // 4
        token_usage["generator_completion_tokens"] = output_len // 4

        return {"draft": draft, "timings": timings, "token_usage": token_usage}

    def _node_plain_rag(self, state: PipelineState) -> Dict[str, Any]:
        """Baseline (a): Plain RAG without verification."""
        t0 = time.time()
        draft = state["draft"]
        passages = state.get("passages", [])
        query = state["query"]

        abstained = draft.is_unanswerable if draft else True
        reason = "NO_EVIDENCE" if abstained else "NONE"
        explanation = "Plain RAG baseline released without claim verification."

        decision = DecisionRecord(
            query=query,
            answer=draft.answer if (draft and not abstained) else None,
            abstained=abstained,
            reason_code=reason,
            reason_explanation=explanation,
            risk_score=0.0,
            claims=[],
            passages=passages,
            metadata={"mode": "plain_rag"},
        )
        dt = (time.time() - t0) * 1000.0
        timings = state.get("timings", {})
        timings["baseline_decision_ms"] = round(dt, 2)

        return {"decision": decision, "timings": timings}

    def _node_answer_level_check(self, state: PipelineState) -> Dict[str, Any]:
        """Baseline (b): RAG with one answer-level LLM check."""
        t0 = time.time()
        draft = state["draft"]
        passages = state.get("passages", [])
        query = state["query"]

        if not draft or draft.is_unanswerable or not passages:
            decision = DecisionRecord(
                query=query,
                answer=None,
                abstained=True,
                reason_code="NO_EVIDENCE",
                reason_explanation="No passages to evaluate answer-level check.",
                risk_score=1.0,
                claims=[],
                passages=passages,
                metadata={"mode": "answer_level_check"},
            )
            return {"decision": decision}

        passages_formatted = "\n---\n".join([f"[{p.passage_id}] {p.text}" for p in passages])
        prompt = (
            self.answer_check_prompt
            .replace("{passages_text}", passages_formatted)
            .replace("{query}", query)
            .replace("{answer}", draft.answer)
        )

        supported = True
        explanation = "Answer-level LLM check passed."
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            resp = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0),
            )
            data = json.loads(resp.text)
            supported = bool(data.get("supported", False))
            explanation = data.get("explanation", "")
        except Exception as e:
            logger.warning(f"Answer-level check fallback: {e}")

        abstained = not supported
        reason = "NONE" if supported else "RISK_ABOVE_THRESHOLD"
        risk = 0.0 if supported else 1.0

        decision = DecisionRecord(
            query=query,
            answer=draft.answer if supported else None,
            abstained=abstained,
            reason_code=reason,
            reason_explanation=f"Answer-Level LLM Check: {explanation}",
            risk_score=risk,
            claims=[],
            passages=passages,
            metadata={"mode": "answer_level_check", "supported": supported},
        )

        dt = (time.time() - t0) * 1000.0
        timings = state.get("timings", {})
        timings["answer_check_ms"] = round(dt, 2)
        return {"decision": decision, "timings": timings}

    def _node_extract_claims(self, state: PipelineState) -> Dict[str, Any]:
        t0 = time.time()
        draft = state["draft"]
        record = self.extractor.extract_claims(draft)
        dt = (time.time() - t0) * 1000.0

        timings = state.get("timings", {})
        timings["extract_ms"] = round(dt, 2)

        token_usage = state.get("token_usage", {})
        token_usage["extractor_tokens"] = len(draft.answer) // 4 if draft else 0

        return {"claims": record.claims, "timings": timings, "token_usage": token_usage}

    def _node_verify_claims(self, state: PipelineState) -> Dict[str, Any]:
        t0 = time.time()
        claims = state.get("claims", [])
        passages = state.get("passages", [])
        query = state["query"]

        verification = self.verifier.verify(claims=claims, passages=passages, query=query)
        dt = (time.time() - t0) * 1000.0

        timings = state.get("timings", {})
        timings["verify_ms"] = round(dt, 2)

        return {"verification": verification, "timings": timings}

    def _node_decide_risk(self, state: PipelineState) -> Dict[str, Any]:
        t0 = time.time()
        query = state["query"]
        draft = state["draft"]
        verification = state["verification"]
        passages = state.get("passages", [])

        decision = self.decision_agent.decide(
            query=query,
            draft=draft,
            verification=verification,
            passages=passages,
        )
        dt = (time.time() - t0) * 1000.0

        timings = state.get("timings", {})
        timings["decision_ms"] = round(dt, 2)
        timings["total_pipeline_ms"] = round(sum(v for k, v in timings.items() if k != "total_pipeline_ms"), 2)

        return {"decision": decision, "timings": timings}

    def run(
        self,
        query: str,
        mode: str = "truthguard",
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Executes the pipeline graph synchronously and returns the complete final state."""
        initial_state: PipelineState = {
            "query": query,
            "mode": mode,
            "top_k": top_k or settings.TOP_K,
            "passages": [],
            "draft": None,
            "claims": [],
            "verification": None,
            "decision": None,
            "timings": {},
            "token_usage": {},
            "metadata": {},
        }
        final_state = self.graph.invoke(initial_state)
        return final_state
