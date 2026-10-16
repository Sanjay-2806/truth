#!/usr/bin/env python3
"""Run evaluation benchmark comparing Plain RAG, Answer-Level Check, and TruthGuard AI.

Reads questions from data/gold/questions.csv, runs comparative inference across all 3 modes,
and prints comparative evaluation metrics (Coverage, Hallucination Leakage, Abstention, Latency).
Saves BOTH aggregate metrics AND per-query records to data/processed/benchmark_results.json.
"""

import sys
from pathlib import Path
import json

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.eval.benchmark import BenchmarkEvaluator


def main():
    print("\n==========================================================================")
    print(" TruthGuard AI — Comparative Benchmark Evaluation on TEST Split")
    print("==========================================================================\n")

    evaluator = BenchmarkEvaluator()
    # Run evaluation on test split (subset for benchmark report)
    results = evaluator.evaluate_split(split="test", modes=["plain_rag", "answer_level_check", "truthguard"], max_samples=6)

    print("\n" + "=" * 80)
    print(f"{'Method / Mode':<22} | {'Coverage':<10} | {'Abstain P':<10} | {'Abstain R':<10} | {'Leakage':<9} | {'Avg Latency'}")
    print("-" * 80)

    for mode, data in results.items():
        m = data["metrics"]
        lat = f"{data['avg_latency_s']:.2f}s"
        print(f"{mode:<22} | {m['coverage']:<10.2f} | {m['abstention_precision']:<10.2f} | {m['abstention_recall']:<10.2f} | {m['leakage_rate']:<9.2f} | {lat}")

    print("=" * 80)

    # Per-query detail table
    print("\n\n" + "=" * 120)
    print(f"{'QID':<6} | {'Mode':<22} | {'Answerable':<11} | {'Abstained':<10} | {'Correct':<8} | {'Risk Score':<11} | {'Claims':<7} | {'Reason Code':<28} | {'Latency'}")
    print("-" * 120)
    for mode, data in results.items():
        for r in data["records"]:
            expected_abstain = not r["is_answerable"]
            correct = (r["abstained"] == expected_abstain)
            print(f"{r['question_id']:<6} | {mode:<22} | {'Yes' if r['is_answerable'] else 'No':<11} | {'Yes' if r['abstained'] else 'No':<10} | {'✓' if correct else '✗':<8} | {r['risk_score']:<11.4f} | {r['claims_count']:<7} | {r['reason_code']:<28} | {r['latency_s']:.2f}s")
    print("=" * 120)

    # Export benchmark report with BOTH aggregate and per-query records
    report_path = PROJECT_ROOT / "data/processed/benchmark_results.json"
    export = {}
    for mode, data in results.items():
        per_query = []
        for r in data["records"]:
            expected_abstain = not r["is_answerable"]
            correct = (r["abstained"] == expected_abstain)
            per_query.append({
                "question_id": r["question_id"],
                "question": r["question"],
                "is_answerable": r["is_answerable"],
                "abstained": r["abstained"],
                "correct_decision": correct,
                "reason_code": r["reason_code"],
                "risk_score": round(r["risk_score"], 4),
                "claims_count": r["claims_count"],
                "latency_s": r["latency_s"],
            })
        export[mode] = {
            "metrics": data["metrics"],
            "avg_latency_s": data["avg_latency_s"],
            "per_query": per_query,
        }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2)
    print(f"\nSaved benchmark metrics + per-query records to {report_path}\n")


if __name__ == "__main__":
    main()
