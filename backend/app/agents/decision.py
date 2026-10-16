"""Risk & Decision Agent for TruthGuard AI.

Calculates calibrated risk R, evaluates abstention triggers, and produces structured decisions
with explicit explanations and evidence linkages.
"""

from typing import List, Optional, Tuple
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.records import (
    ClaimVerificationResult,
    VerificationRecord,
    DraftRecord,
    PassageRecord,
    DecisionRecord,
    DecisionReason,
)

logger = get_logger("truthguard.agent.decision")


class RiskDecisionAgent:
    """Agent responsible for calculating factual risk and deciding whether to release or abstain."""

    def __init__(
        self,
        alpha: Optional[float] = None,
        tau: Optional[float] = None,
        relevance_floor: Optional[float] = None,
    ):
        self.alpha = alpha if alpha is not None else settings.ALPHA
        self.tau = tau if tau is not None else settings.TAU
        self.relevance_floor = relevance_floor if relevance_floor is not None else settings.RELEVANCE_FLOOR

    def compute_risk(self, claims: List[ClaimVerificationResult]) -> Tuple[float, int]:
        """Calculates risk score R = sum(w_i * s(label_i)) / sum(w_i), excluding 'Not Applicable'.

        s(Verified) = 0
        s(Unsupported) = alpha
        s(Contradicted) = 1

        Returns:
            Tuple of (risk_score: float in [0.0, 1.0], checkable_claims_count: int)
        """
        checkable = [c for c in claims if c.label != "Not Applicable"]
        if not checkable:
            return 0.0, 0

        total_weight = sum(c.weight for c in checkable)
        if total_weight <= 0.0:
            return 0.0, len(checkable)

        total_penalty = 0.0
        for c in checkable:
            if c.label == "Verified":
                score = 0.0
            elif c.label == "Unsupported":
                score = self.alpha
            elif c.label == "Contradicted":
                score = 1.0
            else:
                score = self.alpha

            total_penalty += c.weight * score

        risk = total_penalty / total_weight
        return round(risk, 4), len(checkable)

    def decide(
        self,
        query: str,
        draft: DraftRecord,
        verification: VerificationRecord,
        passages: List[PassageRecord],
    ) -> DecisionRecord:
        """Determines whether to release the draft answer or abstain with an explicit reason.

        Abstention Triggers:
        1. NO_EVIDENCE: Passages list is empty or all passages fall below relevance floor.
        2. CRITICAL_CONTRADICTION: Any critical claim is Contradicted by retrieved evidence.
        3. RISK_ABOVE_THRESHOLD: Aggregated risk R exceeds risk threshold tau.
        """
        claims = verification.results
        risk, checkable_count = self.compute_risk(claims)

        # -------------------------------------------------------------
        # 1. Trigger: NO_EVIDENCE
        # -------------------------------------------------------------
        max_passage_score = max([p.score for p in passages], default=0.0)
        if not passages or max_passage_score < self.relevance_floor or draft.is_unanswerable:
            reason_code: DecisionReason = "NO_EVIDENCE"
            explanation = (
                f"Abstained: Insufficient policy evidence. The maximum passage relevance score was "
                f"{max_passage_score:.4f}, which falls below the relevance floor of {self.relevance_floor:.4f}."
            )
            logger.info(f"Decision for '{query}': ABSTAIN ({reason_code})")
            return DecisionRecord(
                query=query,
                answer=None,
                abstained=True,
                reason_code=reason_code,
                reason_explanation=explanation,
                risk_score=risk,
                claims=claims,
                passages=passages,
                metadata={"max_passage_score": max_passage_score, "relevance_floor": self.relevance_floor},
            )

        # -------------------------------------------------------------
        # 2. Trigger: CRITICAL_CONTRADICTION
        # -------------------------------------------------------------
        critical_contradictions = [c for c in claims if c.critical and c.label == "Contradicted"]
        if critical_contradictions:
            reason_code = "CRITICAL_CONTRADICTION"
            failing_details = []
            for c in critical_contradictions:
                evidence_info = f" (Conflicting passage: {c.evidence_passage_id})" if c.evidence_passage_id else ""
                failing_details.append(f"• [Claim {c.claim_id}] '{c.claim_text}' with K_i={c.K_i:.4f}{evidence_info}")

            explanation = (
                f"Abstained: One or more critical claims directly contradict university regulations:\n"
                + "\n".join(failing_details)
            )
            logger.info(f"Decision for '{query}': ABSTAIN ({reason_code})")
            return DecisionRecord(
                query=query,
                answer=None,
                abstained=True,
                reason_code=reason_code,
                reason_explanation=explanation,
                risk_score=risk,
                claims=claims,
                passages=passages,
                metadata={"critical_contradictions_count": len(critical_contradictions)},
            )

        # -------------------------------------------------------------
        # 3. Trigger: RISK_ABOVE_THRESHOLD
        # -------------------------------------------------------------
        if risk > self.tau:
            reason_code = "RISK_ABOVE_THRESHOLD"
            unsupported_claims = [c for c in claims if c.label in ["Unsupported", "Contradicted"]]
            failing_list = [f"• [Claim {c.claim_id}: {c.label}] '{c.claim_text}'" for c in unsupported_claims]
            explanation = (
                f"Abstained: Risk score R={risk:.4f} exceeds permissible threshold tau={self.tau:.4f}.\n"
                f"Failing claims ({len(unsupported_claims)}):\n"
                + "\n".join(failing_list)
            )
            logger.info(f"Decision for '{query}': ABSTAIN ({reason_code}) - Risk: {risk} > {self.tau}")
            return DecisionRecord(
                query=query,
                answer=None,
                abstained=True,
                reason_code=reason_code,
                reason_explanation=explanation,
                risk_score=risk,
                claims=claims,
                passages=passages,
                metadata={"risk": risk, "tau": self.tau},
            )

        # -------------------------------------------------------------
        # 4. Safe Release: NONE (All checks passed)
        # -------------------------------------------------------------
        reason_code = "NONE"
        explanation = (
            f"Released: Verified answer within risk tolerance (R={risk:.4f} <= tau={self.tau:.4f}). "
            f"{len(claims)} claim(s) audited."
        )
        logger.info(f"Decision for '{query}': RELEASE (Risk: {risk} <= {self.tau})")
        return DecisionRecord(
            query=query,
            answer=draft.answer,
            abstained=False,
            reason_code=reason_code,
            reason_explanation=explanation,
            risk_score=risk,
            claims=claims,
            passages=passages,
            metadata={"risk": risk, "tau": self.tau},
        )
