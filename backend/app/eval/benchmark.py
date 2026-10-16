"""Evaluation harness runner for evaluating TruthGuard and comparative baselines.

Executes:
1. Full TruthGuard pipeline
2. Plain RAG baseline
3. Answer-Level LLM Check baseline
Over gold test/dev splits, computing accuracy, hallucination leakage, and timings.
"""

from typing import List, Dict, Any, Optional
import time
import pandas as pd
from app.core.config import settings
from app.core.logging import get_logger
from app.agents.orchestrator import TruthGuardOrchestrator
from app.eval.metrics import compute_abstention_metrics

logger = get_logger("truthguard.eval.benchmark")


class BenchmarkEvaluator:
    """Evaluates question answering pipelines against gold benchmark datasets."""

    def __init__(self, orchestrator: Optional[TruthGuardOrchestrator] = None):
        self.orchestrator = orchestrator or TruthGuardOrchestrator()

    def load_dataset(self, split: Optional[str] = None) -> pd.DataFrame:
        """Loads and filters gold dataset by split (dev/test)."""
        csv_path = settings.PROJECT_ROOT / settings.GOLD_DATA_PATH
        df = pd.read_csv(csv_path)
        if split:
            df = df[df["split"] == split].copy()
        return df

    def evaluate_split(
        self,
        split: str = "test",
        modes: Optional[List[str]] = None,
        max_samples: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Runs evaluation over requested modes on a designated dataset split."""
        if modes is None:
            modes = ["plain_rag", "answer_level_check", "truthguard"]

        df = self.load_dataset(split)
        if max_samples:
            df = df.head(max_samples)

        logger.info(f"Starting evaluation on split '{split}' with {len(df)} samples across modes: {modes}")
        summary_results: Dict[str, Any] = {}

        for mode in modes:
            logger.info(f"Evaluating mode: {mode}")
            mode_records = []
            start_t = time.time()

            for _, row in df.iterrows():
                q = str(row["question"])
                is_answerable = bool(row["is_answerable"])

                t0 = time.time()
                result = self.orchestrator.run(query=q, mode=mode, top_k=settings.TOP_K)
                latency_s = round(time.time() - t0, 3)

                decision = result["decision"]
                mode_records.append({
                    "question_id": row["question_id"],
                    "question": q,
                    "is_answerable": is_answerable,
                    "abstained": decision.abstained,
                    "reason_code": decision.reason_code,
                    "risk_score": decision.risk_score,
                    "latency_s": latency_s,
                    "claims_count": len(decision.claims),
                })

            total_elapsed = round(time.time() - start_t, 2)
            gt_answerable = [r["is_answerable"] for r in mode_records]
            sys_abstained = [r["abstained"] for r in mode_records]

            abstention_stats = compute_abstention_metrics(gt_answerable, sys_abstained)
            avg_latency = round(sum(r["latency_s"] for r in mode_records) / len(mode_records), 3)

            summary_results[mode] = {
                "metrics": abstention_stats,
                "avg_latency_s": avg_latency,
                "total_elapsed_s": total_elapsed,
                "records": mode_records,
            }

        return summary_results
