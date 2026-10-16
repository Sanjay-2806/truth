"""Tests for Phase 6: Evaluation Metrics and Benchmark Harness."""

import pytest
from app.eval.metrics import (
    compute_claim_verification_metrics,
    compute_abstention_metrics,
    compute_expected_calibration_error,
    compute_risk_coverage_curve,
)
from app.eval.benchmark import BenchmarkEvaluator


def test_claim_verification_metrics_calculation():
    """Verifies precision, recall, F1, and contradiction F1 calculations."""
    gold = ["Verified", "Verified", "Unsupported", "Contradicted", "Contradicted"]
    pred = ["Verified", "Unsupported", "Unsupported", "Contradicted", "Verified"]

    metrics = compute_claim_verification_metrics(gold, pred)

    assert "accuracy" in metrics
    assert "macro_f1" in metrics
    assert "contradiction_f1" in metrics
    assert metrics["Contradicted_support"] == 2
    assert metrics["Contradicted_precision"] == 1.0  # 1 true positive, 0 false positive
    assert metrics["Contradicted_recall"] == 0.5     # 1 detected out of 2 gold


def test_abstention_metrics_calculation():
    """Verifies selective QA metrics: coverage, leakage rate, and abstention precision/recall."""
    # 4 questions: 3 answerable (True), 1 unanswerable (False)
    ground_truth = [True, True, True, False]
    # System released the 3 answerable, and correctly abstained on the unanswerable
    system_abstained = [False, False, False, True]

    stats = compute_abstention_metrics(ground_truth, system_abstained)

    assert stats["abstention_precision"] == 1.0
    assert stats["abstention_recall"] == 1.0
    assert stats["coverage"] == 0.75
    assert stats["leakage_rate"] == 0.0  # Zero unanswerable questions were answered!


def test_abstention_metrics_with_leakage():
    """Verifies leakage rate calculation when system answers an unanswerable question."""
    ground_truth = [True, False]
    system_abstained = [False, False]  # System failed to abstain on the unanswerable query

    stats = compute_abstention_metrics(ground_truth, system_abstained)

    assert stats["abstention_recall"] == 0.0
    assert stats["coverage"] == 1.0
    assert stats["leakage_rate"] == 0.5  # 1 out of 2 answered queries was unanswerable


def test_expected_calibration_error():
    """Verifies ECE computation across confidence bins."""
    confidences = [0.9, 0.85, 0.8, 0.4, 0.2]
    accuracies = [1, 1, 1, 0, 0]

    ece = compute_expected_calibration_error(confidences, accuracies, n_bins=5)
    assert 0.0 <= ece <= 1.0


def test_risk_coverage_curve():
    """Verifies Risk-Coverage curve generation over tau thresholds."""
    risks = [0.0, 0.1, 0.4, 0.8]
    answerable = [True, True, True, False]

    curve = compute_risk_coverage_curve(risks, answerable, tau_steps=10)
    assert len(curve) == 11
    assert curve[0]["tau"] == 0.0
    assert curve[-1]["tau"] == 1.0
    # As tau increases, coverage should be monotonically non-decreasing
    coverages = [pt["coverage"] for pt in curve]
    assert all(x <= y for x, y in zip(coverages, coverages[1:]))


def test_benchmark_evaluator_dataset_loading():
    """Verifies benchmark evaluator properly parses dev and test splits from CSV."""
    evaluator = BenchmarkEvaluator()
    dev_df = evaluator.load_dataset(split="dev")
    test_df = evaluator.load_dataset(split="test")

    assert len(dev_df) == 15
    assert len(test_df) == 15
    assert "question" in dev_df.columns
    assert "is_answerable" in dev_df.columns
    assert "expected_decision" in dev_df.columns
