"""Integration tests for Phase 5: FastAPI Endpoints and Orchestrator."""

import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_api_health():
    """Verifies that the /health endpoint reports healthy status and hardware info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "device" in data
    assert "models" in data


def test_ask_truthguard_mode():
    """Verifies full TruthGuard claim verification pipeline via POST /ask."""
    payload = {
        "question": "What is the consequence if a student has 45 or more credits in arrear backlog courses?",
        "mode": "truthguard",
        "top_k": 5,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "run_id" in data
    assert data["mode"] == "truthguard"
    assert "risk_score" in data
    assert "reason_code" in data
    assert "reason_explanation" in data

    # Claims must be populated with labels and E/K scores
    assert isinstance(data["claims"], list)
    assert len(data["claims"]) > 0
    for claim in data["claims"]:
        assert "claim_id" in claim
        assert "label" in claim
        assert "E_i" in claim
        assert "K_i" in claim

    # Passages must have locations
    assert isinstance(data["passages"], list)
    assert len(data["passages"]) > 0
    for passage in data["passages"]:
        assert "location" in passage
        assert passage["location"]["page"] >= 1
        assert passage["location"]["section_heading"] != ""

    # Timings per stage
    timings = data["timings_ms"]
    assert "retrieve_ms" in timings
    assert "generate_ms" in timings
    assert "extract_ms" in timings
    assert "verify_ms" in timings
    assert "decision_ms" in timings



def test_ask_plain_rag_baseline():
    """Verifies plain RAG baseline mode (no claim verification)."""
    payload = {
        "question": "What is the minimum overall attendance percentage required to appear for end semester examinations?",
        "mode": "plain_rag",
        "top_k": 3,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["mode"] == "plain_rag"
    assert data["abstained"] is False
    assert data["answer"] is not None
    assert len(data["claims"]) == 0  # No claim extraction or verification in plain RAG
    assert data["risk_score"] == 0.0


def test_ask_answer_level_check_baseline():
    """Verifies single answer-level LLM check baseline mode."""
    payload = {
        "question": "What are the passing marks for a theory course?",
        "mode": "answer_level_check",
        "top_k": 3,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["mode"] == "answer_level_check"
    assert "reason_explanation" in data
    assert len(data["claims"]) == 0


def test_run_persistence_and_retrieval():
    """Verifies that every run is persisted to the database and retrievable via GET /runs/{id}."""
    # First, make a run
    payload = {
        "question": "What is the requirement for First Class with Distinction?",
        "mode": "truthguard",
        "top_k": 4,
    }
    post_res = client.post("/ask", json=payload)
    assert post_res.status_code == 200
    run_id = post_res.json()["run_id"]

    # Now retrieve the persisted run audit trail
    get_res = client.get(f"/runs/{run_id}")
    assert get_res.status_code == 200
    run_data = get_res.json()

    assert run_data["run_id"] == run_id
    assert run_data["question"] == payload["question"]
    assert run_data["mode"] == "truthguard"
    assert "created_at" in run_data
    assert "claims" in run_data
    assert "passages" in run_data
    assert "timings_ms" in run_data


def test_list_runs_endpoint():
    """Verifies GET /runs returns recent audit runs."""
    response = client.get("/runs?limit=10")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1
    assert "run_id" in runs[0]
