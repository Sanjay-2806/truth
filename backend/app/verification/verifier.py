"""Claim Verifier Agent for TruthGuard AI.

Executes claim-level NLI verification using DeBERTa-v3 across retrieved regulation passages.
Enforces decision thresholds, contradiction precedence, and evidence linkage.
"""

from typing import List, Optional, Tuple, Dict, Any
import re
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.records import (
    AtomicClaim,
    PassageRecord,
    ClaimVerificationResult,
    VerificationRecord,
    VerificationLabel,
)
from app.verification.engine import NLIEngine

logger = get_logger("truthguard.verification.verifier")

_nli_engine_instance: Optional[NLIEngine] = None


def get_nli_engine() -> NLIEngine:
    """Returns singleton instance of NLIEngine."""
    global _nli_engine_instance
    if _nli_engine_instance is None:
        _nli_engine_instance = NLIEngine()
        _nli_engine_instance.load_model()
    return _nli_engine_instance


class ClaimVerifierAgent:
    """Independent verifier evaluating atomic claims against retrieved evidence passages."""

    def __init__(
        self,
        engine: Optional[NLIEngine] = None,
        theta_e: Optional[float] = None,
        theta_c: Optional[float] = None,
    ):
        self.engine = engine or get_nli_engine()
        self.theta_e = theta_e if theta_e is not None else settings.THETA_E
        self.theta_c = theta_c if theta_c is not None else settings.THETA_C

    def is_non_checkable(self, claim_text: str) -> bool:
        """Determines if a claim asserts nothing factually checkable (greetings, restated questions)."""
        text = claim_text.strip().lower()
        if not text:
            return True

        non_checkable_patterns = [
            r"^(hello|hi|hey|greetings|thank you|thanks)\b",
            r"^(the question asks|the user is asking|regarding the question)\b",
            r"^here is (the answer|the information|a summary)\b",
            r"^in summary\b",
        ]
        return any(re.search(pat, text) for pat in non_checkable_patterns)

    def verify(
        self,
        claims: List[AtomicClaim],
        passages: List[PassageRecord],
        query: str = "",
    ) -> VerificationRecord:
        """Verifies each atomic claim against all retrieved passages.

        Returns VerificationRecord containing per-claim labels, E_i, K_i, and evidence pointers.
        """
        if not claims:
            logger.info("No claims provided for verification.")
            return VerificationRecord(query=query, results=[])

        results: List[ClaimVerificationResult] = []

        # If no passages exist, all checkable claims are Unsupported by definition
        if not passages:
            logger.warning("No evidence passages provided to verifier; all claims marked Unsupported.")
            for c in claims:
                label: VerificationLabel = "Not Applicable" if self.is_non_checkable(c.text) else "Unsupported"
                results.append(
                    ClaimVerificationResult(
                        claim_id=c.claim_id,
                        claim_text=c.text,
                        label=label,
                        E_i=0.0,
                        K_i=0.0,
                        evidence_passage_id=None,
                        evidence_text=None,
                        critical=c.critical,
                        weight=c.weight,
                    )
                )
            return VerificationRecord(query=query, results=results)

        # Separate checkable from non-checkable claims
        checkable_claims: List[AtomicClaim] = []
        for c in claims:
            if self.is_non_checkable(c.text):
                results.append(
                    ClaimVerificationResult(
                        claim_id=c.claim_id,
                        claim_text=c.text,
                        label="Not Applicable",
                        E_i=0.0,
                        K_i=0.0,
                        evidence_passage_id=None,
                        evidence_text=None,
                        critical=c.critical,
                        weight=c.weight,
                    )
                )
            else:
                checkable_claims.append(c)

        if not checkable_claims:
            return VerificationRecord(query=query, results=results)

        # Build Cartesian product batch: (passage_j.text, claim_i.text)
        pairs: List[Tuple[str, str]] = []
        pair_mapping: List[Tuple[int, int]] = []  # (claim_index, passage_index)

        for c_idx, claim in enumerate(checkable_claims):
            for p_idx, passage in enumerate(passages):
                pairs.append((passage.text, claim.text))
                pair_mapping.append((c_idx, p_idx))

        # Run batch NLI inference
        logger.info(
            f"Evaluating {len(pairs)} (passage, claim) pairs across {len(checkable_claims)} claims and {len(passages)} passages..."
        )
        nli_outputs = self.engine.predict_pairs_batch(pairs)

        # Aggregate scores per claim: E_i = max_j p_ent_ij, K_i = max_j p_con_ij
        claim_scores: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(len(checkable_claims))}

        for (c_idx, p_idx), out in zip(pair_mapping, nli_outputs):
            claim_scores[c_idx].append({
                "passage": passages[p_idx],
                "p_ent": out["entailment"],
                "p_con": out["contradiction"],
                "p_neu": out["neutral"],
            })

        for c_idx, claim in enumerate(checkable_claims):
            evals = claim_scores[c_idx]

            # Find best entailment and contradiction passage candidates
            best_ent_eval = max(evals, key=lambda x: x["p_ent"])
            best_con_eval = max(evals, key=lambda x: x["p_con"])

            E_i = best_ent_eval["p_ent"]
            K_i = best_con_eval["p_con"]

            # Decision logic with contradiction precedence:
            # 1. Contradicted if K_i >= theta_c and K_i >= E_i
            # 2. Verified if E_i >= theta_e and E_i > K_i
            # 3. Otherwise Unsupported
            if K_i >= self.theta_c and K_i >= E_i:
                label: VerificationLabel = "Contradicted"
                evidence_passage = best_con_eval["passage"]
            elif E_i >= self.theta_e and E_i > K_i:
                label = "Verified"
                evidence_passage = best_ent_eval["passage"]
            else:
                label = "Unsupported"
                # Point to candidate with highest entailment if any non-trivial signal
                evidence_passage = best_ent_eval["passage"] if E_i >= 0.25 else None

            results.append(
                ClaimVerificationResult(
                    claim_id=claim.claim_id,
                    claim_text=claim.text,
                    label=label,
                    E_i=round(E_i, 4),
                    K_i=round(K_i, 4),
                    evidence_passage_id=evidence_passage.passage_id if evidence_passage else None,
                    evidence_text=evidence_passage.text if evidence_passage else None,
                    critical=claim.critical,
                    weight=claim.weight,
                )
            )

        # Restore original claim ordering
        id_order = {c.claim_id: idx for idx, c in enumerate(claims)}
        results.sort(key=lambda r: id_order.get(r.claim_id, 0))

        return VerificationRecord(query=query, results=results)
