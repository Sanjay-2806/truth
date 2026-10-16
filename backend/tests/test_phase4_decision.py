"""Unit tests for Phase 4: Risk and Decision Agent."""

import pytest
from app.schemas.records import (
    ClaimVerificationResult,
    VerificationRecord,
    DraftRecord,
    PassageRecord,
    PassageLocation,
    DecisionRecord,
)
from app.agents.decision import RiskDecisionAgent


def _make_sample_passage(passage_id: str, score: float = 0.85) -> PassageRecord:
    return PassageRecord(
        passage_id=passage_id,
        text="Sample regulation clause text.",
        score=score,
        location=PassageLocation(
            doc_id="sec_reg_2024",
            doc_title="Regulations 2024",
            section_heading="Clause 6",
            page=18,
            chunk_index=1,
        ),
    )


def test_risk_calculation_exact_prompt_case():
    """Verifies that weights 2,2,1 with labels V,V,U and alpha=0.5 gives R=0.10 exactly."""
    agent = RiskDecisionAgent(alpha=0.50, tau=0.25, relevance_floor=0.30)

    claims = [
        ClaimVerificationResult(
            claim_id="c_01",
            claim_text="First condition is required.",
            label="Verified",
            E_i=0.95,
            K_i=0.01,
            critical=True,
            weight=2.0,
        ),
        ClaimVerificationResult(
            claim_id="c_02",
            claim_text="Second condition is required.",
            label="Verified",
            E_i=0.92,
            K_i=0.02,
            critical=True,
            weight=2.0,
        ),
        ClaimVerificationResult(
            claim_id="c_03",
            claim_text="Additional peripheral detail.",
            label="Unsupported",
            E_i=0.30,
            K_i=0.05,
            critical=False,
            weight=1.0,
        ),
    ]

    risk, count = agent.compute_risk(claims)
    assert risk == 0.10
    assert count == 3

    # Ensure this decision results in safe release since R=0.10 <= tau=0.25
    draft = DraftRecord(query="Test query", answer="Released answer text.", is_unanswerable=False)
    verification = VerificationRecord(query="Test query", results=claims)
    passages = [_make_sample_passage("p_01", score=0.85)]

    dec = agent.decide(query="Test query", draft=draft, verification=verification, passages=passages)
    assert dec.abstained is False
    assert dec.reason_code == "NONE"
    assert dec.answer == "Released answer text."
    assert "Verified answer within risk tolerance" in dec.reason_explanation


def test_decision_branch_no_evidence_empty():
    """Verifies abstention with reason NO_EVIDENCE when no passages are retrieved."""
    agent = RiskDecisionAgent(alpha=0.50, tau=0.25, relevance_floor=0.30)
    draft = DraftRecord(query="Alien policy", answer="Some draft answer.", is_unanswerable=False)
    verification = VerificationRecord(query="Alien policy", results=[])

    dec = agent.decide(query="Alien policy", draft=draft, verification=verification, passages=[])
    assert dec.abstained is True
    assert dec.reason_code == "NO_EVIDENCE"
    assert dec.answer is None
    assert "Insufficient policy evidence" in dec.reason_explanation


def test_decision_branch_no_evidence_below_floor():
    """Verifies abstention with reason NO_EVIDENCE when all passages fall below relevance floor."""
    agent = RiskDecisionAgent(alpha=0.50, tau=0.25, relevance_floor=0.30)
    draft = DraftRecord(query="Obscure query", answer="Low confidence draft.", is_unanswerable=False)
    claims = [
        ClaimVerificationResult(
            claim_id="c_01",
            claim_text="Some statement.",
            label="Verified",
            E_i=0.80,
            K_i=0.01,
            critical=False,
            weight=1.0,
        )
    ]
    verification = VerificationRecord(query="Obscure query", results=claims)
    # Both passages have low scores < relevance_floor (0.30)
    passages = [
        _make_sample_passage("p_low1", score=0.18),
        _make_sample_passage("p_low2", score=0.24),
    ]

    dec = agent.decide(query="Obscure query", draft=draft, verification=verification, passages=passages)
    assert dec.abstained is True
    assert dec.reason_code == "NO_EVIDENCE"
    assert dec.answer is None
    assert "falls below the relevance floor" in dec.reason_explanation


def test_decision_branch_critical_contradiction():
    """Verifies abstention with CRITICAL_CONTRADICTION if any critical claim is Contradicted."""
    agent = RiskDecisionAgent(alpha=0.50, tau=0.25, relevance_floor=0.30)
    draft = DraftRecord(query="Arrear registration", answer="Hallucinated answer.", is_unanswerable=False)
    claims = [
        ClaimVerificationResult(
            claim_id="c_critical_failed",
            claim_text="Students with 50 arrear credits can register without restriction.",
            label="Contradicted",
            E_i=0.05,
            K_i=0.96,
            evidence_passage_id="clause_6_4_4",
            critical=True,
            weight=2.0,
        ),
        ClaimVerificationResult(
            claim_id="c_02",
            claim_text="The semester fee is standard.",
            label="Verified",
            E_i=0.88,
            K_i=0.02,
            critical=False,
            weight=1.0,
        ),
    ]
    verification = VerificationRecord(query="Arrear registration", results=claims)
    passages = [_make_sample_passage("clause_6_4_4", score=0.95)]

    dec = agent.decide(query="Arrear registration", draft=draft, verification=verification, passages=passages)
    assert dec.abstained is True
    assert dec.reason_code == "CRITICAL_CONTRADICTION"
    assert dec.answer is None
    # Explanation must name the failing claim and evidence
    assert "c_critical_failed" in dec.reason_explanation
    assert "clause_6_4_4" in dec.reason_explanation


def test_decision_branch_risk_above_threshold():
    """Verifies abstention with RISK_ABOVE_THRESHOLD when R exceeds tau without critical contradiction."""
    agent = RiskDecisionAgent(alpha=0.50, tau=0.25, relevance_floor=0.30)
    draft = DraftRecord(query="Course details", answer="Partially unsupported draft.", is_unanswerable=False)
    claims = [
        ClaimVerificationResult(
            claim_id="c_unsupp_1",
            claim_text="Course provides industry certifications.",
            label="Unsupported",
            E_i=0.40,
            K_i=0.02,
            critical=False,
            weight=1.0,
        ),
        ClaimVerificationResult(
            claim_id="c_unsupp_2",
            claim_text="All exams are open book.",
            label="Unsupported",
            E_i=0.35,
            K_i=0.05,
            critical=False,
            weight=1.0,
        ),
    ]
    # R = (1.0 * 0.5 + 1.0 * 0.5) / 2.0 = 0.50 > tau (0.25)
    verification = VerificationRecord(query="Course details", results=claims)
    passages = [_make_sample_passage("p_valid", score=0.80)]

    dec = agent.decide(query="Course details", draft=draft, verification=verification, passages=passages)
    assert dec.abstained is True
    assert dec.reason_code == "RISK_ABOVE_THRESHOLD"
    assert dec.answer is None
    assert dec.risk_score == 0.50
    assert "exceeds permissible threshold tau" in dec.reason_explanation
    assert "c_unsupp_1" in dec.reason_explanation


def test_not_applicable_claims_excluded_from_risk():
    """Verifies that Not Applicable claims (greetings/filler) are excluded from the risk denominator."""
    agent = RiskDecisionAgent(alpha=0.50, tau=0.25, relevance_floor=0.30)
    claims = [
        ClaimVerificationResult(
            claim_id="c_01",
            claim_text="The minimum pass mark is 50%.",
            label="Verified",
            E_i=0.98,
            K_i=0.01,
            critical=True,
            weight=2.0,
        ),
        ClaimVerificationResult(
            claim_id="c_filler",
            claim_text="Thank you for asking.",
            label="Not Applicable",
            E_i=0.0,
            K_i=0.0,
            critical=False,
            weight=1.0,
        ),
    ]

    risk, count = agent.compute_risk(claims)
    assert risk == 0.0
    assert count == 1  # Filler excluded from count
