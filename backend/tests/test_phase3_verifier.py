"""Unit and integration tests for Phase 3: Claim Verifier (DeBERTa-v3 NLI)."""

import pytest
from app.core.config import settings
from app.schemas.records import (
    AtomicClaim,
    PassageRecord,
    PassageLocation,
    VerificationRecord,
)
from app.verification.verifier import ClaimVerifierAgent, get_nli_engine


@pytest.fixture(scope="module")
def verifier() -> ClaimVerifierAgent:
    engine = get_nli_engine()
    return ClaimVerifierAgent(engine=engine, theta_e=0.70, theta_c=0.60)


def _make_passage(passage_id: str, text: str, page: int = 1) -> PassageRecord:
    return PassageRecord(
        passage_id=passage_id,
        text=text,
        score=0.9,
        location=PassageLocation(
            doc_id="reg_2024",
            doc_title="Academic Regulations 2024",
            section_heading="Rules",
            page=page,
            chunk_index=0,
        ),
    )


def test_verifier_entailed_claim(verifier: ClaimVerifierAgent):
    """Verifies that an entailed claim is labelled 'Verified' with evidence pointer."""
    passages = [
        _make_passage(
            "p_01",
            "Candidates seeking admission to the first semester should have passed the Higher Secondary Examinations of (10+2) Curriculum.",
        )
    ]
    claims = [
        AtomicClaim(
            claim_id="c_01",
            text="Admission to the first semester requires passing the (10+2) Higher Secondary Examinations.",
            type="condition",
            critical=True,
            weight=2.0,
        )
    ]

    record = verifier.verify(claims, passages, query="What is the admission qualification?")
    res = record.results[0]

    assert res.label == "Verified"
    assert res.E_i >= 0.70
    assert res.E_i > res.K_i
    assert res.evidence_passage_id == "p_01"


def test_verifier_contradicted_claim(verifier: ClaimVerifierAgent):
    """Verifies that a directly conflicting claim is labelled 'Contradicted'."""
    passages = [
        _make_passage(
            "p_02",
            "Students having a total of 45 and above credits as their (backlog) arrear courses are not permitted to register for the subsequent semester.",
        )
    ]
    claims = [
        AtomicClaim(
            claim_id="c_02",
            text="A student with 48 arrear credits is permitted to register for the subsequent semester.",
            type="penalty",
            critical=True,
            weight=2.0,
        )
    ]

    record = verifier.verify(claims, passages, query="Can a student with 48 arrear credits register?")
    res = record.results[0]

    assert res.label == "Contradicted"
    assert res.K_i >= 0.60
    assert res.K_i >= res.E_i
    assert res.evidence_passage_id == "p_02"


def test_verifier_negation_flip(verifier: ClaimVerifierAgent):
    """Verifies that asserting the opposite of a negative rule is labelled 'Contradicted'."""
    passages = [
        _make_passage(
            "p_03",
            "Withdrawal from examination will not be considered as an appearance for the eligibility of a candidate for First Class with Distinction.",
        )
    ]
    claims = [
        AtomicClaim(
            claim_id="c_03",
            text="Withdrawal from an examination counts as an appearance for First Class with Distinction.",
            type="condition",
            critical=True,
            weight=2.0,
        )
    ]

    record = verifier.verify(claims, passages)
    res = record.results[0]

    assert res.label == "Contradicted"
    assert res.K_i >= 0.60


def test_verifier_numeric_mismatch(verifier: ClaimVerifierAgent):
    """Verifies that numeric requirements that conflict or fail support are not Verified."""
    passages = [
        _make_passage(
            "p_04",
            "Ideally every student is expected to attend all classes. However, he/she shall secure not less than 80% of overall attendance.",
        )
    ]
    claims = [
        AtomicClaim(
            claim_id="c_04",
            text="A student only needs 50% overall attendance to satisfy semester completion.",
            type="condition",
            critical=True,
            weight=2.0,
        )
    ]

    record = verifier.verify(claims, passages)
    res = record.results[0]

    assert res.label in ["Contradicted", "Unsupported"]
    assert res.label != "Verified"


def test_verifier_unrelated_unsupported_claim(verifier: ClaimVerifierAgent):
    """Verifies that assertions completely absent from evidence are labelled 'Unsupported'."""
    passages = [
        _make_passage(
            "p_05",
            "Each semester shall normally consist of 90 working days or 630 periods of 50 minutes each.",
        )
    ]
    claims = [
        AtomicClaim(
            claim_id="c_05",
            text="Every student receives a free MacBook Pro upon enrolment.",
            type="other",
            critical=False,
            weight=1.0,
        )
    ]

    record = verifier.verify(claims, passages)
    res = record.results[0]

    assert res.label == "Unsupported"
    assert res.E_i < 0.70
    assert res.K_i < 0.60


def test_verifier_real_world_truth_absent_from_text(verifier: ClaimVerifierAgent):
    """Verifies that real-world truths absent from the policy passages are marked Unsupported (grounding test)."""
    passages = [
        _make_passage(
            "p_06",
            "The Controller of Examinations is responsible for all activities of the Examinations.",
        )
    ]
    claims = [
        AtomicClaim(
            claim_id="c_06",
            text="Water boils at 100 degrees Celsius at standard atmospheric pressure.",
            type="other",
            critical=False,
            weight=1.0,
        )
    ]

    record = verifier.verify(claims, passages)
    res = record.results[0]

    # Grounding semantics: Even if true in physics, absent from retrieved text -> Unsupported!
    assert res.label == "Unsupported"
    assert res.E_i < 0.70


def test_verifier_not_applicable_claim(verifier: ClaimVerifierAgent):
    """Verifies that conversational filler or non-factual statements are labelled 'Not Applicable'."""
    passages = [_make_passage("p_07", "Sample regulations text content.")]
    claims = [
        AtomicClaim(
            claim_id="c_07",
            text="Thank you for your question regarding academic rules.",
            type="other",
            critical=False,
            weight=1.0,
        )
    ]

    record = verifier.verify(claims, passages)
    res = record.results[0]

    assert res.label == "Not Applicable"
    assert res.E_i == 0.0
    assert res.K_i == 0.0


def test_verifier_evidence_pointer_resolution(verifier: ClaimVerifierAgent):
    """Verifies that the evidence pointer correctly identifies the specific passage out of multiple candidates."""
    passages = [
        _make_passage("pass_irrelevant", "The campus provides bus facilities across Chennai city."),
        _make_passage(
            "pass_target",
            "A candidate who secures not less than 50% of total marks prescribed for the course shall be declared to have passed the course.",
        ),
        _make_passage("pass_other", "Students may participate in National Cadet Corps (NCC)."),
    ]
    claims = [
        AtomicClaim(
            claim_id="c_08",
            text="A candidate must secure at least 50% of total marks to pass the course.",
            type="condition",
            critical=True,
            weight=2.0,
        )
    ]

    record = verifier.verify(claims, passages)
    res = record.results[0]

    assert res.label == "Verified"
    assert res.evidence_passage_id == "pass_target"


def test_verifier_contradiction_precedence():
    """Verifies that Contradiction takes precedence when both signals are strong."""
    class MockEngine:
        def predict_pairs_batch(self, pairs):
            # Simulate conflicting passages: one entails (0.85), one contradicts (0.88)
            return [
                {"entailment": 0.85, "contradiction": 0.10, "neutral": 0.05},
                {"entailment": 0.10, "contradiction": 0.88, "neutral": 0.02},
            ]

    agent = ClaimVerifierAgent(engine=MockEngine(), theta_e=0.70, theta_c=0.60)
    passages = [
        _make_passage("circular_a", "Rule states X is permitted."),
        _make_passage("circular_b", "Rule states X is prohibited."),
    ]
    claims = [
        AtomicClaim(
            claim_id="c_conflict",
            text="Action X is permitted.",
            type="condition",
            critical=True,
            weight=2.0,
        )
    ]
    rec = agent.verify(claims, passages)
    res = rec.results[0]

    # Contradiction MUST take precedence so conflicting circulars are flagged
    assert res.label == "Contradicted"
    assert res.evidence_passage_id == "circular_b"

