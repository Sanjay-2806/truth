"""Retriever Agent module for TruthGuard AI.

Provides the standalone retrieval interface for the multi-agent pipeline.
"""

from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.records import RetrievalRecord
from app.retrieval.indexer import HybridRetriever

logger = get_logger("truthguard.agent.retriever")

# Global singleton instance for retriever
_retriever_instance: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """Returns singleton instance of HybridRetriever."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HybridRetriever()
    return _retriever_instance


class RetrieverAgent:
    """Agent responsible for querying hybrid vector store and returning ranked passages."""

    def __init__(self, retriever: Optional[HybridRetriever] = None, top_k: Optional[int] = None):
        self.retriever = retriever or get_retriever()
        self.top_k = top_k or settings.TOP_K

    def retrieve(self, query: str, top_k: Optional[int] = None) -> RetrievalRecord:
        """Executes hybrid retrieval over indexed regulation clauses."""
        k = top_k or self.top_k
        logger.info(f"RetrieverAgent querying: '{query}' (top_k={k})")
        record = self.retriever.search(query=query, top_k=k)
        logger.info(
            f"RetrieverAgent found {len(record.passages)} passages. "
            f"Top score: {record.passages[0].score if record.passages else 0.0}"
        )
        return record
