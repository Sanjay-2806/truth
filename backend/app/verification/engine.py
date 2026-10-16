"""Batch NLI Inference Engine using DeBERTa-v3 for TruthGuard AI.

Calculates entailment, contradiction, and neutral probabilities for premise-hypothesis pairs
with GPU/MPS acceleration.
"""

from typing import List, Tuple, Dict, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from app.core.config import settings
from app.core.device import get_device
from app.core.logging import get_logger

logger = get_logger("truthguard.verification.engine")


class NLIEngine:
    """Manages DeBERTa-v3 cross-encoder model for high-throughput NLI inference."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[torch.device] = None,
        max_seq_length: int = 512,
    ):
        self.model_name = model_name or settings.NLI_MODEL_NAME
        self.device = device or get_device()
        self.max_seq_length = max_seq_length

        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForSequenceClassification] = None
        self.label_map: Dict[str, int] = {}

    def load_model(self) -> None:
        """Loads tokenizer and sequence classification model if not already loaded."""
        if self.model is not None and self.tokenizer is not None:
            return

        logger.info(f"Loading NLI model '{self.model_name}' on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

        # Identify label indices dynamically
        id2label = self.model.config.id2label
        label2id = {v.lower(): k for k, v in id2label.items()}

        # Verify entailment, contradiction, neutral exist
        for key in ["entailment", "contradiction", "neutral"]:
            if key in label2id:
                self.label_map[key] = label2id[key]
            else:
                # Handle potential abbreviated keys like "ent", "con", "neu"
                matched = [idx for k, idx in label2id.items() if key.startswith(k[:3])]
                if matched:
                    self.label_map[key] = matched[0]
                else:
                    raise ValueError(f"Label '{key}' could not be identified in model config: {id2label}")

        logger.info(f"NLI Engine initialized successfully with label mapping: {self.label_map}")

    def predict_pairs_batch(
        self,
        pairs: List[Tuple[str, str]],
        batch_size: int = 16,
    ) -> List[Dict[str, float]]:
        """Predicts NLI probabilities for a list of (premise, hypothesis) pairs.

        Returns:
            List of dicts: [{'entailment': p_ent, 'contradiction': p_con, 'neutral': p_neu}, ...]
        """
        if not pairs:
            return []

        self.load_model()
        results: List[Dict[str, float]] = []

        ent_idx = self.label_map["entailment"]
        con_idx = self.label_map["contradiction"]
        neu_idx = self.label_map["neutral"]

        total_pairs = len(pairs)
        for i in range(0, total_pairs, batch_size):
            batch_pairs = pairs[i : i + batch_size]
            premises = [p[0] for p in batch_pairs]
            hypotheses = [p[1] for p in batch_pairs]

            inputs = self.tokenizer(
                premises,
                hypotheses,
                padding=True,
                truncation=True,
                max_length=self.max_seq_length,
                return_tensors="pt",
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)

            for row in probs:
                p_ent = float(row[ent_idx].cpu().item())
                p_con = float(row[con_idx].cpu().item())
                p_neu = float(row[neu_idx].cpu().item())

                results.append({
                    "entailment": p_ent,
                    "contradiction": p_con,
                    "neutral": p_neu,
                })

        return results
