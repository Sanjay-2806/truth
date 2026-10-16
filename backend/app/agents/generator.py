"""Generator Agent for TruthGuard AI.

Generates draft answers grounded strictly in retrieved regulation passages.
Outputs DraftRecord.
"""

from pathlib import Path
from typing import List, Optional
import json
import re
import time
from google import genai
from google.genai import errors

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.records import RetrievalRecord, DraftRecord

logger = get_logger("truthguard.agent.generator")


class GeneratorAgent:
    """Agent that produces grounded answers solely from retrieved regulation passages."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        prompt_path: Optional[Path] = None,
        max_retries: int = 3,
        initial_backoff: float = 2.0,
    ):
        self.model_name = model_name or settings.GEMINI_MODEL
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

        prompt_file = prompt_path or (settings.PROJECT_ROOT / settings.PROMPTS_DIR / "generator_v1.txt")
        if not prompt_file.exists():
            # Fallback path relative to cwd
            prompt_file = Path("prompts/generator_v1.txt")
        self.prompt_template = prompt_file.read_text(encoding="utf-8")

        # Lazy Gemini client
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is not configured in settings or .env")
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def generate(self, retrieval_record: RetrievalRecord) -> DraftRecord:
        """Generates a grounded draft answer given a query and its retrieved passages."""
        query = retrieval_record.query
        passages = retrieval_record.passages

        # If no passages were retrieved, return unanswerable draft immediately
        if not passages:
            logger.warning(f"No passages provided to generator for query: '{query}'")
            return DraftRecord(
                query=query,
                answer="INSUFFICIENT_INFORMATION: No relevant regulation passages were retrieved.",
                used_passage_ids=[],
                is_unanswerable=True,
            )

        # Format passages block with ID, heading, page, and text
        passages_text_blocks = []
        for p in passages:
            block = (
                f"[Passage ID: {p.passage_id}]\n"
                f"Source: {p.location.doc_title} | Section: {p.location.section_heading} | Page: {p.location.page}\n"
                f"Content: {p.text}\n"
            )
            if p.neighbour_context:
                block += f"Context: {p.neighbour_context}\n"
            passages_text_blocks.append(block)

        passages_formatted = "\n---\n".join(passages_text_blocks)
        prompt_content = (
            self.prompt_template
            .replace("{passages_text}", passages_formatted)
            .replace("{query}", query)
        )

        raw_response = self._call_gemini_with_backoff(prompt_content)
        return self._parse_draft_response(query, raw_response, [p.passage_id for p in passages])

    def _call_gemini_with_backoff(self, prompt: str) -> str:
        """Invokes Gemini API with exponential backoff on rate limits and errors."""
        backoff = self.initial_backoff

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text.strip()
                raise ValueError("Empty response received from Gemini.")
            except (errors.APIError, errors.ClientError, Exception) as e:
                err_msg = str(e)
                logger.warning(
                    f"Gemini API attempt {attempt}/{self.max_retries} failed: {type(e).__name__} ({err_msg[:120]})"
                )
                if attempt == self.max_retries:
                    logger.error("Exceeded maximum retries for GeneratorAgent.")
                    raise
                time.sleep(backoff)
                backoff *= 2.0

        return ""

    def _parse_draft_response(
        self,
        query: str,
        raw_text: str,
        available_passage_ids: List[str],
    ) -> DraftRecord:
        """Separates the natural text answer from the JSON block of used passage IDs."""
        used_ids: List[str] = []
        clean_answer = raw_text

        # Search for JSON block ```json ... ```
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if json_match:
            try:
                meta = json.loads(json_match.group(1))
                used_ids = meta.get("used_passage_ids", [])
                clean_answer = raw_text[: json_match.start()].strip()
            except Exception as e:
                logger.warning(f"Could not parse used_passage_ids metadata block: {e}")

        # If no explicit block parsed, fall back to matching IDs mentioned in raw text
        if not used_ids:
            for pid in available_passage_ids:
                if pid in raw_text:
                    used_ids.append(pid)

        # Detect unanswerable indicators
        is_unanswerable = (
            clean_answer.startswith("INSUFFICIENT_INFORMATION")
            or "do not contain sufficient" in clean_answer.lower()
            or "cannot be answered" in clean_answer.lower()
        )

        return DraftRecord(
            query=query,
            answer=clean_answer,
            used_passage_ids=used_ids,
            is_unanswerable=is_unanswerable,
        )
