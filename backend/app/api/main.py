"""FastAPI application endpoints for TruthGuard AI.

Provides:
- POST /ask : Multi-mode question answering with claim-level verification and audit logs
- GET /runs/{id} : Historical run detail by UUID
- GET /runs : Recent run history list
- GET /health : System and accelerator health
"""

from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Literal
import uuid
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.device import get_device_info
from app.core.logging import get_logger
from app.db.session import init_db, get_db
from app.db.models import RunRecordModel
from app.schemas.records import (
    ClaimVerificationResult,
    PassageRecord,
    DecisionReason,
)
from app.agents.orchestrator import TruthGuardOrchestrator
from app.api.eval import eval_router

logger = get_logger("truthguard.api")

orchestrator: Optional[TruthGuardOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook initializing database tables and singleton orchestrator."""
    global orchestrator
    logger.info("Initializing TruthGuard AI API server...")
    init_db()
    orchestrator = TruthGuardOrchestrator()
    yield
    logger.info("Shutting down TruthGuard AI API server...")


app = FastAPI(
    title="TruthGuard AI API",
    description="Claim-Level Evidence Verification Framework for Hallucination Mitigation in Academic Regulations",
    version="1.0.0",
    lifespan=lifespan,
)

# Initialize database tables on import
init_db()

# Enable CORS for Next.js frontend (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include read-only evaluation routes
app.include_router(eval_router, prefix="/eval", tags=["evaluation"])


# --- Request and Response Schemas ---

class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description="User question about academic regulations")
    mode: Literal["truthguard", "plain_rag", "answer_level_check"] = Field(
        default="truthguard",
        description="Pipeline mode: full truthguard verification, plain_rag baseline, or answer_level_check baseline",
    )
    top_k: Optional[int] = Field(default=None, description="Number of passages to retrieve")


class AskResponse(BaseModel):
    run_id: str
    question: str
    mode: str
    answer: Optional[str]
    abstained: bool
    reason_code: DecisionReason
    reason_explanation: str
    risk_score: float
    claims: List[ClaimVerificationResult]
    passages: List[PassageRecord]
    timings_ms: Dict[str, float]
    token_usage: Dict[str, int]
    model_versions: Dict[str, str]
    parameters: Dict[str, Any]


# --- Endpoints ---

@app.get("/health")
def health_check():
    """Health check endpoint providing hardware and system diagnostics."""
    dev_info = get_device_info()
    return {
        "status": "healthy",
        "service": "TruthGuard AI",
        "device": dev_info,
        "models": {
            "embedding_model": settings.EMBEDDING_MODEL_NAME,
            "nli_model": settings.NLI_MODEL_NAME,
            "gemini_model": settings.GEMINI_MODEL,
        },
    }


@app.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest, db: Session = Depends(get_db)):
    """Executes the verification pipeline and persists the run audit trail."""
    global orchestrator
    if orchestrator is None:
        orchestrator = TruthGuardOrchestrator()

    logger.info(f"Received question: '{req.question}' (mode={req.mode})")
    run_id = str(uuid.uuid4())

    # Execute LangGraph pipeline
    state = orchestrator.run(query=req.question, mode=req.mode, top_k=req.top_k)
    decision = state["decision"]
    draft = state.get("draft")
    verification = state.get("verification")
    passages = state.get("passages", [])
    claims_results = verification.results if verification else []

    # Model and parameter metadata
    model_versions = {
        "gemini_model": settings.GEMINI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "nli_model": settings.NLI_MODEL_NAME,
    }
    parameters = {
        "alpha": settings.ALPHA,
        "tau": settings.TAU,
        "theta_e": settings.THETA_E,
        "theta_c": settings.THETA_C,
        "relevance_floor": settings.RELEVANCE_FLOOR,
        "top_k": req.top_k or settings.TOP_K,
        "prompt_versions": {
            "generator": "v1",
            "claim_extractor": "v1",
            "answer_check": "v1",
        },
    }

    # Persist to database
    db_record = RunRecordModel(
        id=run_id,
        question=req.question,
        mode=req.mode,
        answer=decision.answer,
        abstained=decision.abstained,
        reason_code=decision.reason_code,
        reason_explanation=decision.reason_explanation,
        risk_score=decision.risk_score,
        draft_answer=draft.answer if draft else None,
        claims_json=[c.model_dump() for c in claims_results],
        passages_json=[p.model_dump() for p in passages],
        timings_json=state.get("timings", {}),
        token_usage_json=state.get("token_usage", {}),
        parameters_json=parameters,
    )
    db.add(db_record)
    db.commit()

    logger.info(f"Run {run_id} persisted. Abstained: {decision.abstained}, Reason: {decision.reason_code}")

    return AskResponse(
        run_id=run_id,
        question=req.question,
        mode=req.mode,
        answer=decision.answer,
        abstained=decision.abstained,
        reason_code=decision.reason_code,
        reason_explanation=decision.reason_explanation,
        risk_score=decision.risk_score,
        claims=claims_results,
        passages=passages,
        timings_ms=state.get("timings", {}),
        token_usage=state.get("token_usage", {}),
        model_versions=model_versions,
        parameters=parameters,
    )


@app.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Retrieves full historical audit trail for a specific run ID."""
    record = db.query(RunRecordModel).filter(RunRecordModel.id == run_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Run with ID '{run_id}' not found.")

    return {
        "run_id": record.id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "question": record.question,
        "mode": record.mode,
        "answer": record.answer,
        "abstained": record.abstained,
        "reason_code": record.reason_code,
        "reason_explanation": record.reason_explanation,
        "risk_score": record.risk_score,
        "draft_answer": record.draft_answer,
        "claims": record.claims_json or [],
        "passages": record.passages_json or [],
        "timings_ms": record.timings_json or {},
        "token_usage": record.token_usage_json or {},
        "parameters": record.parameters_json or {},
    }


@app.get("/runs")
def list_runs(limit: int = Query(default=20, le=100), db: Session = Depends(get_db)):
    """Returns a list of recent query answering runs."""
    records = (
        db.query(RunRecordModel)
        .order_by(RunRecordModel.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "run_id": r.id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "question": r.question,
            "mode": r.mode,
            "abstained": r.abstained,
            "reason_code": r.reason_code,
            "risk_score": r.risk_score,
            "answer_preview": (r.answer[:100] + "...") if r.answer else None,
        }
        for r in records
    ]
