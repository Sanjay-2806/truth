"""Unit and integration tests for Phase 2: Generator and Claim Extractor."""

import pytest
from app.core.config import settings
from app.schemas.records import (
    RetrievalRecord,
    PassageRecord,
    PassageLocation,
    DraftRecord,
)
from app.agents.retriever import RetrieverAgent
from app.agents.generator import GeneratorAgent
from app.agents.extractor import ClaimExtractorAgent


@pytest.fixture(scope="module")
def generator() -> GeneratorAgent:
    return GeneratorAgent()


@pytest.fixture(scope="module")
def extractor() -> ClaimExtractorAgent:
    return ClaimExtractorAgent()


def test_generator_grounded_answer(generator: GeneratorAgent):
    """Verifies that the Generator agent answers policy questions grounded in retrieved passages."""
    retriever = RetrieverAgent(top_k=5)
    retrieval_record = retriever.retrieve("What happens if a student has 45 or more credits as backlog arrears?")

    assert len(retrieval_record.passages) > 0
    draft = generator.generate(retrieval_record)

    assert isinstance(draft, DraftRecord)
    assert draft.is_unanswerable is False
    assert len(draft.answer) > 20
    assert "45" in draft.answer
    assert any(term in draft.answer.lower() for term in ["not permitted", "arrear", "register", "subsequent semester"])


def test_generator_unanswerable_handling(generator: GeneratorAgent):
    """Verifies that the Generator explicitly reports INSUFFICIENT_INFORMATION when no evidence exists."""
    empty_record = RetrievalRecord(
        query="What is the policy for students operating commercial spacecraft?",
        passages=[],
        retrieval_mode="hybrid_rrf",
    )
    draft = generator.generate(empty_record)

    assert draft.is_unanswerable is True
    assert "INSUFFICIENT_INFORMATION" in draft.answer


def test_claim_extractor_typology_and_critical_weighting(extractor: ClaimExtractorAgent):
    """Verifies that the Claim Extractor decomposes answers into atomic claims with proper types and weights."""
    sample_answer = (
        "Students must secure a minimum of 80% overall attendance to appear for the end semester examination. "
        "However, a student securing between 65% and 80% attendance due to medical reasons may be granted permission by Dean-Academics. "
        "Course registration must be confirmed within five working days after the commencement of the semester. "
        "Students having a total of 45 and above credits as backlog arrear courses are not permitted to register for the subsequent semester."
    )
    draft = DraftRecord(
        query="Explain attendance, registration deadlines, and arrear limits.",
        answer=sample_answer,
        used_passage_ids=["chunk_1"],
        is_unanswerable=False,
    )

    record = extractor.extract_claims(draft)

    assert len(record.claims) >= 3
    claim_types = {c.type for c in record.claims}

    # At least some of the expected types should be detected
    expected_categories = {"condition", "exception", "deadline", "penalty", "authority"}
    assert len(claim_types.intersection(expected_categories)) >= 2

    # Verify critical weighting rules
    for claim in record.claims:
        assert isinstance(claim.text, str)
        assert len(claim.text) > 5
        if claim.critical:
            assert claim.weight == settings.WEIGHT_CRITICAL
        else:
            assert claim.weight == settings.WEIGHT_NON_CRITICAL


def test_claim_extractor_unanswerable_returns_empty(extractor: ClaimExtractorAgent):
    """Verifies that unanswerable drafts return empty claims."""
    unanswerable_draft = DraftRecord(
        query="Irrelevant query",
        answer="INSUFFICIENT_INFORMATION: No passages provided.",
        used_passage_ids=[],
        is_unanswerable=True,
    )
    record = extractor.extract_claims(unanswerable_draft)
    assert len(record.claims) == 0


def test_claim_extractor_json_resilience(extractor: ClaimExtractorAgent):
    """Tests the parsing and weighting logic on raw mock JSON payloads."""
    mock_json = """
    ```json
    {
      "claims": [
        {
          "claim_id": "c_01",
          "text": "A candidate must secure at least 80% attendance to write the exam.",
          "type": "condition",
          "critical": true
        },
        {
          "claim_id": "c_02",
          "text": "The College was founded in Chennai.",
          "type": "other",
          "critical": false
        }
      ]
    }
    ```
    """
    claims = extractor._parse_and_validate_json(mock_json)
    assert len(claims) == 2
    assert claims[0].critical is True
    assert claims[0].weight == 2.0
    assert claims[0].type == "condition"

    assert claims[1].critical is False
    assert claims[1].weight == 1.0
    assert claims[1].type == "other"
