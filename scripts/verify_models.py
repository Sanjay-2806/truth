#!/usr/bin/env python3
"""Verification script for Phase 0.

Verifies:
1. PyTorch device (Apple M4 MPS or CPU)
2. Downloading and running BGE embedding model (BAAI/bge-small-en-v1.5)
3. Downloading and running DeBERTa-v3 NLI model (MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli)
4. Model forward pass on sample Premise-Hypothesis pair
"""

import sys
import time
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.device import get_device, get_device_info
from app.core.logging import get_logger

logger = get_logger("truthguard.verify_models")


def main() -> int:
    logger.info("=== Phase 0 Model & Hardware Verification ===")
    device_info = get_device_info()
    device = get_device()
    logger.info(f"PyTorch Version: {device_info['pytorch_version']}")
    logger.info(f"MPS Available: {device_info['mps_available']} (Built: {device_info['mps_built']})")
    logger.info(f"CUDA Available: {device_info['cuda_available']}")
    logger.info(f"Active Device Selected: {device}")

    # 1. Test Embedding Model
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME} on {device}...")
    t0 = time.time()
    embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME, device=str(device))
    t_emb_load = time.time() - t0
    logger.info(f"Embedding model loaded successfully in {t_emb_load:.2f}s")

    test_sentences = [
        "Candidates seeking admission to the first semester must have passed 10+2.",
        "Students having 45 and above credits as arrear backlog cannot register.",
    ]
    emb = embedding_model.encode(test_sentences, convert_to_tensor=True, device=str(device))
    logger.info(f"Embedding forward pass succeeded. Shape: {emb.shape}")

    # 2. Test DeBERTa-v3 NLI Model
    logger.info(f"Loading NLI model: {settings.NLI_MODEL_NAME} on {device}...")
    t1 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(settings.NLI_MODEL_NAME)
    nli_model = AutoModelForSequenceClassification.from_pretrained(settings.NLI_MODEL_NAME)
    nli_model.to(device)
    nli_model.eval()
    t_nli_load = time.time() - t1
    logger.info(f"NLI model loaded successfully in {t_nli_load:.2f}s")

    # Sample pair test
    premise = "Students having a total of 45 and above credits as their backlog arrear courses are not permitted to register for the subsequent semester."
    hypothesis = "A student with 46 arrear credits cannot register for the next semester."

    inputs = tokenizer(premise, hypothesis, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = nli_model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)[0]

    # Map label probabilities
    id2label = nli_model.config.id2label
    prob_dict = {id2label[i].lower(): float(probs[i].cpu().item()) for i in range(len(probs))}

    logger.info(f"Premise: '{premise}'")
    logger.info(f"Hypothesis: '{hypothesis}'")
    logger.info(f"NLI Probabilities: {prob_dict}")

    logger.info("=== Phase 0 Verification Complete: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
