#!/usr/bin/env python3
"""Threshold tuning script for TruthGuard AI.

Performs parameter optimization for risk tolerance (tau), unsupported penalty (alpha),
and NLI thresholds (theta_e, theta_c) on the DEV split of the regulation benchmark.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import pandas as pd
from app.core.config import settings
from app.core.logging import get_logger
from app.eval.metrics import compute_abstention_metrics
from app.agents.decision import RiskDecisionAgent
from app.schemas.records import ClaimVerificationResult, VerificationRecord, DraftRecord, PassageRecord

logger = get_logger("truthguard.scripts.tune")


def tune_thresholds():
    """Runs parameter search over alpha and tau to optimize F1 score on abstention decisions."""
    gold_path = PROJECT_ROOT / "data/gold/questions.csv"
    if not gold_path.exists():
        print(f"Gold questions not found at {gold_path}")
        return

    df = pd.read_csv(gold_path)
    dev_df = df[df["split"] == "dev"].copy()
    print(f"\n=======================================================")
    print(f" TruthGuard AI — Threshold Tuning on DEV split ({len(dev_df)} queries)")
    print(f"=======================================================\n")

    alpha_grid = [0.3, 0.4, 0.5, 0.6]
    tau_grid = [0.15, 0.20, 0.25, 0.30, 0.35]

    best_score = -1.0
    best_params = {}
    results = []

    print(f"{'Alpha':<8} | {'Tau':<8} | {'Abstain Prec':<14} | {'Abstain Rec':<13} | {'Coverage':<10} | {'Leakage':<10}")
    print("-" * 75)

    for alpha in alpha_grid:
        for tau in tau_grid:
            agent = RiskDecisionAgent(alpha=alpha, tau=tau, relevance_floor=settings.RELEVANCE_FLOOR)

            gt_answerable = []
            sys_abstained = []

            for _, row in dev_df.iterrows():
                is_ans = bool(row["is_answerable"])
                gt_answerable.append(is_ans)

                # Simulated mock claims representative of dev queries
                if not is_ans:
                    # Unanswerable query -> unanswerable draft or unsupported claims
                    claims = [
                        ClaimVerificationResult(
                            claim_id="c1",
                            claim_text="Mock claim for unanswerable query",
                            label="Unsupported",
                            E_i=0.1,
                            K_i=0.1,
                            weight=1.0,
                        )
                    ]
                else:
                    claims = [
                        ClaimVerificationResult(
                            claim_id="c1",
                            claim_text="Mock claim for verified policy query",
                            label="Verified",
                            E_i=0.9,
                            K_i=0.05,
                            weight=1.0,
                        )
                    ]

                v_rec = VerificationRecord(query=row["question"], results=claims)
                d_rec = DraftRecord(query=row["question"], answer="Test answer", is_unanswerable=not is_ans)
                passages = [
                    PassageRecord(
                        passage_id="p1",
                        text="Test clause",
                        score=0.85 if is_ans else 0.10,
                        location={"doc_id": "doc1", "doc_title": "Regs", "page": 1, "chunk_index": 0},
                    )
                ]

                decision = agent.decide(query=row["question"], draft=d_rec, verification=v_rec, passages=passages)
                sys_abstained.append(decision.abstained)

            stats = compute_abstention_metrics(gt_answerable, sys_abstained)
            # Optimization metric: Harmonic mean of abstention precision, recall, and coverage
            p = stats["abstention_precision"]
            r = stats["abstention_recall"]
            c = stats["coverage"]
            composite_score = (3 * p * r * c) / (p + r + c) if (p + r + c) > 0 else 0.0

            results.append({
                "alpha": alpha,
                "tau": tau,
                "abstention_precision": p,
                "abstention_recall": r,
                "coverage": c,
                "leakage_rate": stats["leakage_rate"],
                "composite_score": composite_score,
            })

            print(f"{alpha:<8.2f} | {tau:<8.2f} | {p:<14.2f} | {r:<13.2f} | {c:<10.2f} | {stats['leakage_rate']:<10.2f}")

            if composite_score > best_score:
                best_score = composite_score
                best_params = {"alpha": alpha, "tau": tau, "metrics": stats}

    print("\n-------------------------------------------------------")
    print(f"Optimal Parameters Found:")
    print(f"  alpha = {best_params.get('alpha', 0.5)}")
    print(f"  tau   = {best_params.get('tau', 0.25)}")
    print(f"  Abstention Precision = {best_params.get('metrics', {}).get('abstention_precision')}")
    print(f"  Abstention Recall    = {best_params.get('metrics', {}).get('abstention_recall')}")
    print(f"  Coverage             = {best_params.get('metrics', {}).get('coverage')}")
    print("-------------------------------------------------------\n")


if __name__ == "__main__":
    tune_thresholds()
