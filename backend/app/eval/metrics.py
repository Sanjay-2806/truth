"""Evaluation metrics module for TruthGuard AI.

Calculates:
- Claim-Level Verification Metrics: Precision, Recall, F1 for Verified, Unsupported, Contradicted
- Contradiction Detection F1
- Selective QA Decision Metrics: Abstention Precision, Recall, Coverage, and Risk
- Expected Calibration Error (ECE) for NLI probabilities
- Risk-Coverage curve data
"""

from typing import List, Dict, Any, Tuple
import math
from collections import defaultdict


def compute_claim_verification_metrics(
    gold_labels: List[str],
    pred_labels: List[str],
) -> Dict[str, Any]:
    """Calculates macro and per-class Precision, Recall, and F1 for verification classifications.

    Classes: Verified, Unsupported, Contradicted (excluding Not Applicable if absent).
    """
    labels = ["Verified", "Unsupported", "Contradicted"]
    metrics: Dict[str, Any] = {}

    total_correct = 0
    total_count = len(gold_labels)

    for cls in labels:
        tp = sum(1 for g, p in zip(gold_labels, pred_labels) if g == cls and p == cls)
        fp = sum(1 for g, p in zip(gold_labels, pred_labels) if g != cls and p == cls)
        fn = sum(1 for g, p in zip(gold_labels, pred_labels) if g == cls and p != cls)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        metrics[f"{cls}_precision"] = round(prec, 4)
        metrics[f"{cls}_recall"] = round(rec, 4)
        metrics[f"{cls}_f1"] = round(f1, 4)
        metrics[f"{cls}_support"] = sum(1 for g in gold_labels if g == cls)

    # Accuracy
    total_correct = sum(1 for g, p in zip(gold_labels, pred_labels) if g == p)
    metrics["accuracy"] = round(total_correct / total_count, 4) if total_count > 0 else 0.0

    # Contradiction F1 is a key hallucination penalty indicator
    metrics["contradiction_f1"] = metrics["Contradicted_f1"]

    # Macro F1
    metrics["macro_f1"] = round(
        (metrics["Verified_f1"] + metrics["Unsupported_f1"] + metrics["Contradicted_f1"]) / 3.0,
        4,
    )
    return metrics


def compute_abstention_metrics(
    ground_truth_answerable: List[bool],
    system_abstained: List[bool],
) -> Dict[str, float]:
    """Calculates Selective Answering / Abstention metrics.

    Ground Truth:
      - Answerable = False -> System SHOULD abstain (Positive for Abstention)
      - Answerable = True  -> System should release (Negative for Abstention)
    """
    assert len(ground_truth_answerable) == len(system_abstained)
    n = len(ground_truth_answerable)
    if n == 0:
        return {"abstention_precision": 0.0, "abstention_recall": 0.0, "coverage": 0.0, "effective_accuracy": 0.0}

    # True positives: Unanswerable and system abstained
    tp = sum(1 for ans, abs_ in zip(ground_truth_answerable, system_abstained) if not ans and abs_)
    # False positives: Answerable but system abstained
    fp = sum(1 for ans, abs_ in zip(ground_truth_answerable, system_abstained) if ans and abs_)
    # False negatives: Unanswerable but system released (hallucination leak!)
    fn = sum(1 for ans, abs_ in zip(ground_truth_answerable, system_abstained) if not ans and not abs_)
    # True negatives: Answerable and system released
    tn = sum(1 for ans, abs_ in zip(ground_truth_answerable, system_abstained) if ans and not abs_)

    abstention_prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    abstention_rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    coverage = (tn + fn) / n  # Fraction of queries where system answered
    leakage_rate = fn / (tn + fn) if (tn + fn) > 0 else 0.0  # Fraction of answered questions that were unanswerable

    return {
        "abstention_precision": round(abstention_prec, 4),
        "abstention_recall": round(abstention_rec, 4),
        "coverage": round(coverage, 4),
        "leakage_rate": round(leakage_rate, 4),
        "total_queries": n,
        "abstained_count": tp + fp,
        "released_count": tn + fn,
    }


def compute_expected_calibration_error(
    confidences: List[float],
    accuracies: List[int],
    n_bins: int = 10,
) -> float:
    """Computes Expected Calibration Error (ECE) for verification confidence.

    ECE = sum(|acc(B_m) - conf(B_m)| * |B_m| / N)
    """
    assert len(confidences) == len(accuracies)
    n = len(confidences)
    if n == 0:
        return 0.0

    bins = defaultdict(list)
    for conf, acc in zip(confidences, accuracies):
        # Clip to [0, 1]
        c = max(0.0, min(1.0, conf))
        bin_idx = min(int(c * n_bins), n_bins - 1)
        bins[bin_idx].append((c, acc))

    ece = 0.0
    for b_idx in range(n_bins):
        items = bins[b_idx]
        if not items:
            continue
        bin_size = len(items)
        avg_conf = sum(c for c, _ in items) / bin_size
        avg_acc = sum(a for _, a in items) / bin_size
        ece += abs(avg_acc - avg_conf) * (bin_size / n)

    return round(ece, 4)


def compute_risk_coverage_curve(
    risk_scores: List[float],
    ground_truth_answerable: List[bool],
    tau_steps: int = 20,
) -> List[Dict[str, float]]:
    """Calculates coverage and error rates across varied risk tolerance tau in [0.0, 1.0]."""
    points = []
    n = len(risk_scores)
    if n == 0:
        return points

    for i in range(tau_steps + 1):
        tau = i / float(tau_steps)
        # Abstained if risk > tau
        released = [ans for r, ans in zip(risk_scores, ground_truth_answerable) if r <= tau]
        coverage = len(released) / float(n)
        # Risk on covered: proportion of covered items that were unanswerable
        errors = sum(1 for ans in released if not ans)
        risk = errors / float(len(released)) if len(released) > 0 else 0.0

        points.append({
            "tau": round(tau, 3),
            "coverage": round(coverage, 4),
            "risk": round(risk, 4),
        })

    return points
