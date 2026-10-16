"""Claim Extractor Agent for TruthGuard AI.

Decomposes candidate answers into typed atomic claims using Gemini structured output,
validates with Pydantic v2, and enforces risk weights.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import re
import time
from google import genai
from google.genai import errors
from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.records import (
    DraftRecord,
    AtomicClaim,
    ClaimExtractionRecord,
    ClaimType,
)

logger = get_logger("truthguard.agent.extractor")


class ClaimExtractorAgent:
    """Agent that decomposes answers into typed atomic claims."""

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

        prompt_file = prompt_path or (settings.PROJECT_ROOT / settings.PROMPTS_DIR / "claim_extractor_v1.txt")
        if not prompt_file.exists():
            prompt_file = Path("prompts/claim_extractor_v1.txt")
        self.prompt_template = prompt_file.read_text(encoding="utf-8")

        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is not configured in settings or .env")
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def extract_claims(self, draft_record: DraftRecord) -> ClaimExtractionRecord:
        """Extracts atomic claims from a candidate answer."""
        query = draft_record.query
        answer = draft_record.answer

        # If answer is marked unanswerable, do not extract spurious claims
        if draft_record.is_unanswerable or not answer.strip():
            logger.info("Draft is marked unanswerable; returning empty claim record.")
            return ClaimExtractionRecord(query=query, claims=[])

        prompt_content = (
            self.prompt_template
            .replace("{query}", query)
            .replace("{answer}", answer)
        )

        claims = self._extract_with_retry(prompt_content)
        return ClaimExtractionRecord(query=query, claims=claims)

    def _extract_with_retry(self, prompt: str) -> List[AtomicClaim]:
        """Calls Gemini to produce structured JSON and validates claims with backoff."""
        backoff = self.initial_backoff

        for attempt in range(1, self.max_retries + 1):
            try:
                # Request JSON output from Gemini
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )

                if not response or not response.text:
                    raise ValueError("Empty response received from Gemini for claim extraction.")

                raw_json = response.text.strip()
                claims = self._parse_and_validate_json(raw_json)
                return claims

            except (json.JSONDecodeError, ValueError, errors.APIError, Exception) as e:
                logger.warning(
                    f"Claim extraction attempt {attempt}/{self.max_retries} failed: {type(e).__name__} ({str(e)[:120]})"
                )
                if attempt == self.max_retries:
                    logger.error("Exceeded maximum retries for ClaimExtractorAgent.")
                    raise
                time.sleep(backoff)
                backoff *= 2.0

        return []

    def _parse_and_validate_json(self, raw_json_text: str) -> List[AtomicClaim]:
        """Parses JSON text, validates each claim, and assigns weights."""
        # Clean potential markdown wrapping ```json ... ```
        cleaned = raw_json_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        data = json.loads(cleaned)
        raw_claims = data.get("claims", [])
        if not isinstance(raw_claims, list):
            raise ValueError("Expected 'claims' field to be a list in JSON output.")

        valid_types = {
            "condition",
            "exception",
            "deadline",
            "penalty",
            "authority",
            "effective_date",
            "other",
        }

        atomic_claims: List[AtomicClaim] = []
        for i, c in enumerate(raw_claims):
            cid = c.get("claim_id") or f"c_{i+1:02d}"
            text = (c.get("text") or "").strip()
            if not text:
                continue

            raw_type = str(c.get("type", "other")).lower()
            claim_type: ClaimType = raw_type if raw_type in valid_types else "other"

            # Criticality rule: eligibility (conditions), deadlines, penalties MUST be critical
            is_critical = bool(
                c.get("critical", False)
                or claim_type in ["condition", "deadline", "penalty"]
            )

            # Assign weights: critical=2.0, else=1.0 (configurable via settings)
            weight = settings.WEIGHT_CRITICAL if is_critical else settings.WEIGHT_NON_CRITICAL

            atomic_claims.append(
                AtomicClaim(
                    claim_id=cid,
                    text=text,
                    type=claim_type,
                    critical=is_critical,
                    weight=weight,
                )
            )

        logger.info(f"Extracted and validated {len(atomic_claims)} atomic claims.")
        return atomic_claims
