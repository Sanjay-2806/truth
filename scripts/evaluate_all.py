#!/usr/bin/env python3
"""TruthGuard AI Comprehensive Benchmark Evaluation Runner.

Evaluates all 30 gold benchmark questions across all 3 modes:
1. Plain RAG (standard unverified generation)
2. Answer-Level Check (LLM checking its own output)
3. TruthGuard AI (atomic claim extraction + NLI cross-encoder verification)

Saves both comprehensive per-query metrics and aggregate metrics to:
data/processed/benchmark_results.json
"""

import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.config import settings
from app.core.logging import get_logger
from app.agents.orchestrator import TruthGuardOrchestrator
from app.eval.metrics import compute_abstention_metrics

logger = get_logger("truthguard.eval.runner")

OUTPUT_PATH = PROJECT_ROOT / "data/processed/benchmark_results.json"
GOLD_PATH = PROJECT_ROOT / "data/gold/questions.csv"


def load_existing_results() -> Dict[str, Any]:
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read existing benchmark results: {e}")
    return {}


def save_results(results_data: Dict[str, Any]):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Run TruthGuard AI Benchmark Evaluation")
    parser.add_argument("--split", choices=["all", "test", "dev"], default="all", help="Dataset split to evaluate")
    parser.add_argument("--max-samples", type=int, default=None, help="Max queries to evaluate")
    parser.add_argument("--modes", nargs="+", default=["plain_rag", "answer_level_check", "truthguard"], help="Modes to run")
    parser.add_argument("--force", action="store_true", help="Re-evaluate all queries, ignoring cache")
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("TruthGuard AI — Gold Benchmark Evaluation Runner")
    print(f"Split: {args.split} | Modes: {args.modes} | Max Samples: {args.max_samples}")
    print("=" * 80 + "\n")

    df = pd.read_csv(GOLD_PATH)
    if args.split != "all":
        df = df[df["split"] == args.split].copy()
    if args.max_samples:
        df = df.head(args.max_samples)

    total_queries = len(df)
    print(f"Loaded {total_queries} queries from {GOLD_PATH}\n")

    orchestrator = TruthGuardOrchestrator()

    # Load existing benchmark results
    existing_data = load_existing_results() if not args.force else {}

    # Initialize mode containers if missing
    for m in args.modes:
        if m not in existing_data:
            existing_data[m] = {
                "metrics": {},
                "avg_latency_s": 0.0,
                "per_query": [],
            }

    # Evaluate query by query across modes
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        qid = str(row["question_id"])
        q_text = str(row["question"])
        split = str(row["split"])
        category = str(row["category"])
        is_ans = bool(row["is_answerable"])
        expected_decision = str(row.get("expected_decision", "RELEASE"))
        relevant_clause = str(row.get("relevant_clause", "N/A"))
        expected_claims_count = int(row.get("expected_claims_count", 0))

        print(f"[{idx}/{total_queries}] Evaluating {qid} ({split.upper()} - {category}): \"{q_text[:60]}...\"")

        for mode in args.modes:
            mode_per_query = existing_data[mode].get("per_query", [])
            # Check if query already evaluated
            existing_rec = next((r for r in mode_per_query if r.get("question_id") == qid), None)
            if existing_rec and not args.force and existing_rec.get("claims") is not None:
                print(f"  -> {mode:<18}: CACHED (Decision={existing_rec.get('abstained')})")
                continue

            t0 = time.time()
            try:
                result = orchestrator.run(query=q_text, mode=mode, top_k=settings.TOP_K)
                latency_s = round(time.time() - t0, 3)
                decision = result["decision"]

                # Extract claims
                claims_detail = []
                if decision.claims:
                    for c in decision.claims:
                        lbl = c.label.value if hasattr(c.label, "value") else str(c.label)
                        claims_detail.append({
                            "claim_id": c.claim_id,
                            "claim_text": c.claim_text,
                            "label": lbl,
                            "E_i": round(float(c.E_i), 4),
                            "K_i": round(float(c.K_i), 4),
                            "evidence_text": c.evidence_text[:300] if c.evidence_text else "",
                            "critical": bool(c.critical),
                        })

                expected_abstain = not is_ans
                correct_decision = (decision.abstained == expected_abstain)

                record = {
                    "question_id": qid,
                    "split": split,
                    "category": category,
                    "question": q_text,
                    "is_answerable": is_ans,
                    "relevant_clause": relevant_clause,
                    "expected_decision": expected_decision,
                    "expected_claims_count": expected_claims_count,
                    "abstained": decision.abstained,
                    "correct_decision": correct_decision,
                    "reason_code": decision.reason_code,
                    "reason_explanation": decision.reason_explanation or "",
                    "answer": decision.answer or "",
                    "risk_score": round(float(decision.risk_score), 4),
                    "claims_count": len(decision.claims),
                    "claims": claims_detail,
                    "latency_s": latency_s,
                }

                # Update or append in existing_data
                if existing_rec:
                    existing_rec.update(record)
                else:
                    mode_per_query.append(record)
                existing_data[mode]["per_query"] = mode_per_query

                status_mark = "✓" if correct_decision else "✗"
                print(f"  -> {mode:<18}: {status_mark} Abstained={decision.abstained} (Risk={decision.risk_score:.2f}, Latency={latency_s}s)")

            except Exception as e:
                logger.error(f"Error evaluating {qid} with mode {mode}: {e}")
                print(f"  -> {mode:<18}: ERROR: {e}")

        # Compute running aggregate metrics for each mode
        for mode in args.modes:
            records = existing_data[mode]["per_query"]
            if records:
                gt_answerable = [r["is_answerable"] for r in records]
                sys_abstained = [r["abstained"] for r in records]
                abstention_stats = compute_abstention_metrics(gt_answerable, sys_abstained)
                avg_latency = round(sum(r.get("latency_s", 0) for r in records) / len(records), 3)

                existing_data[mode]["metrics"] = abstention_stats
                existing_data[mode]["avg_latency_s"] = avg_latency

        # Save checkpoint after each query
        save_results(existing_data)
        print(f"  Saved progress checkpoint ({idx}/{total_queries} queries)\n")

    print("\n" + "=" * 80)
    print("Benchmark Evaluation Completed Successfully!")
    print(f"Results saved to: {OUTPUT_PATH}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
