"""Unit tests for Phase 0 setup in TruthGuard AI."""

import os
from pathlib import Path
import pytest
import torch
import yaml

from app.core.config import Settings
from app.core.device import get_device, get_device_info
from app.core.logging import SensitiveDataFilter


def test_settings_defaults():
    s = Settings()
    assert s.TOP_K == 5
    assert s.ALPHA == 0.50
    assert s.TAU == 0.25
    assert s.THETA_E == 0.70
    assert s.THETA_C == 0.60
    assert s.RELEVANCE_FLOOR == 0.30
    assert s.WEIGHT_CRITICAL == 2.0
    assert s.WEIGHT_NON_CRITICAL == 1.0
    assert s.EMBEDDING_MODEL_NAME == "BAAI/bge-small-en-v1.5"
    assert s.NLI_MODEL_NAME == "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"


def test_secret_masking():
    s = Settings(GEMINI_API_KEY="AIzaSyA1234567890abcdefGhIjKlMnOpQrStU")
    masked = s.get_masked_gemini_key()
    assert masked.startswith("AIza...")
    assert "1234567890abcdefGhIjKlMn" not in masked

    s_empty = Settings(GEMINI_API_KEY="")
    assert s_empty.get_masked_gemini_key() == "<UNSET>"


def test_logging_secret_scrubbing():
    filter_obj = SensitiveDataFilter(secrets=["super_secret_token_123"])
    import logging
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Connecting using super_secret_token_123 to database",
        args=(),
        exc_info=None,
    )
    filter_obj.filter(record)
    assert "super_secret_token_123" not in record.msg
    assert "[REDACTED_SECRET]" in record.msg


def test_hardware_device_detection():
    info = get_device_info()
    assert "selected_device" in info
    assert "pytorch_version" in info
    device = get_device()
    assert isinstance(device, torch.device)
    assert device.type in ["mps", "cuda", "cpu"]


def test_docker_compose_and_makefile_exist():
    root = Path(__file__).resolve().parent.parent.parent
    docker_compose = root / "docker-compose.yml"
    makefile = root / "Makefile"
    env_example = root / ".env.example"

    assert docker_compose.exists(), "docker-compose.yml must exist"
    assert makefile.exists(), "Makefile must exist"
    assert env_example.exists(), ".env.example must exist"

    # Verify Makefile has required targets
    makefile_content = makefile.read_text()
    for target in ["up", "ingest", "run", "test", "eval"]:
        assert f"{target}:" in makefile_content, f"Makefile missing target {target}"


def test_embedding_model_device_smoke():
    from sentence_transformers import SentenceTransformer
    s = Settings()
    device = get_device()
    model = SentenceTransformer(s.EMBEDDING_MODEL_NAME, device=str(device))
    embedding = model.encode(["Regulations 2024 clause"], convert_to_tensor=True, device=str(device))
    assert embedding.shape[0] == 1
    assert embedding.shape[1] == 384

