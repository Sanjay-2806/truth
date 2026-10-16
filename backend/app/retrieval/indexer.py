"""Hybrid Retrieval Engine combining ChromaDB (dense) and BM25 (sparse) with RRF.

Implements Reciprocal Rank Fusion (RRF) to merge semantic embeddings with exact
keyword matching over academic regulations.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import re
import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.device import get_device
from app.core.logging import get_logger
from app.schemas.records import PassageRecord, PassageLocation, RetrievalRecord

logger = get_logger("truthguard.indexer")


def _tokenize_text(text: str) -> List[str]:
    """Simple alphanumeric tokenizer for BM25."""
    return re.findall(r"\b\w+\b", text.lower())


class HybridRetriever:
    """Manages ChromaDB vector store and BM25 index with Reciprocal Rank Fusion."""

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        embedding_model_name: Optional[str] = None,
        collection_name: str = "regulations_clauses",
    ):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name or settings.EMBEDDING_MODEL_NAME

        self.device = get_device()
        logger.info(f"Initializing HybridRetriever on device: {self.device}")

        # Lazy model loader
        self._embedding_model: Optional[SentenceTransformer] = None

        # ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # In-memory storage for passages and BM25
        self.passages_map: Dict[str, PassageRecord] = {}
        self.bm25: Optional[BM25Okapi] = None
        self.passage_ids_order: List[str] = []

        # Try to load existing indexed passages from disk if present
        self._load_cached_passages()

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            logger.info(f"Loading dense embedding model: {self.embedding_model_name} on {self.device}")
            self._embedding_model = SentenceTransformer(
                self.embedding_model_name,
                device=str(self.device),
            )
        return self._embedding_model

    def index_passages(self, passages: List[PassageRecord]) -> int:
        """Indexes passage records into both ChromaDB and BM25."""
        if not passages:
            logger.warning("No passages provided for indexing.")
            return 0

        logger.info(f"Indexing {len(passages)} passages into ChromaDB and BM25...")

        # 1. Prepare data structures
        ids = [p.passage_id for p in passages]
        texts = [p.text for p in passages]
        metadatas = [
            {
                "doc_id": p.location.doc_id,
                "doc_title": p.location.doc_title,
                "section_heading": p.location.section_heading,
                "page": p.location.page,
                "chunk_index": p.location.chunk_index,
                "neighbour_context": p.neighbour_context or "",
            }
            for p in passages
        ]

        # 2. Compute Dense Embeddings & Upsert to ChromaDB
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()

        # Chroma upsert in batches of 100
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[i : i + batch_size],
                embeddings=embeddings[i : i + batch_size],
                documents=texts[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

        # 3. Build Sparse BM25 Index
        tokenized_corpus = [_tokenize_text(t) for t in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.passage_ids_order = list(ids)

        # 4. Populate in-memory map
        self.passages_map = {p.passage_id: p for p in passages}

        # 5. Save passages to disk for warm restart
        self._save_cached_passages(passages)
        logger.info(f"Successfully indexed {len(passages)} passages.")
        return len(passages)

    def search(
        self,
        query: str,
        top_k: int = 5,
        rrf_k: int = 60,
    ) -> RetrievalRecord:
        """Performs hybrid retrieval using Reciprocal Rank Fusion (RRF)."""
        if not self.passages_map or self.bm25 is None:
            self._load_cached_passages()

        if not self.passages_map:
            logger.warning("Search called on empty retriever index.")
            return RetrievalRecord(query=query, passages=[], retrieval_mode="hybrid_rrf")

        candidate_k = min(max(top_k * 3, 20), len(self.passages_map))

        # --- A. Dense Retrieval via ChromaDB ---
        query_embedding = self.embedding_model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()

        chroma_res = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=candidate_k,
            include=["documents", "metadatas", "distances"],
        )

        dense_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}
        if chroma_res["ids"] and chroma_res["ids"][0]:
            for rank, (p_id, dist) in enumerate(zip(chroma_res["ids"][0], chroma_res["distances"][0])):
                # Cosine distance in Chroma: sim = 1 - distance
                dense_ranks[p_id] = rank + 1
                dense_scores[p_id] = max(0.0, 1.0 - float(dist))

        # --- B. Sparse Retrieval via BM25 ---
        query_tokens = _tokenize_text(query)
        bm25_scores_raw = self.bm25.get_scores(query_tokens)
        bm25_sorted_indices = sorted(
            range(len(bm25_scores_raw)),
            key=lambda idx: bm25_scores_raw[idx],
            reverse=True,
        )[:candidate_k]

        sparse_ranks: Dict[str, int] = {}
        sparse_scores: Dict[str, float] = {}
        for rank, idx in enumerate(bm25_sorted_indices):
            p_id = self.passage_ids_order[idx]
            score_val = float(bm25_scores_raw[idx])
            if score_val > 0.0:
                sparse_ranks[p_id] = rank + 1
                sparse_scores[p_id] = score_val

        # --- C. Reciprocal Rank Fusion (RRF) ---
        all_candidates = set(dense_ranks.keys()).union(set(sparse_ranks.keys()))
        rrf_scores: Dict[str, float] = {}

        for p_id in all_candidates:
            score = 0.0
            if p_id in dense_ranks:
                score += 1.0 / (rrf_k + dense_ranks[p_id])
            if p_id in sparse_ranks:
                score += 1.0 / (rrf_k + sparse_ranks[p_id])
            rrf_scores[p_id] = score

        # Rank candidates by final RRF score
        sorted_candidates = sorted(all_candidates, key=lambda pid: rrf_scores[pid], reverse=True)[:top_k]

        # Max possible RRF score for normalisation: (1/(60+1) + 1/(60+1)) = 2 / 61 = 0.03278
        max_theoretical_rrf = 2.0 / (rrf_k + 1)

        ranked_passages: List[PassageRecord] = []
        for p_id in sorted_candidates:
            original = self.passages_map[p_id]
            norm_score = min(1.0, rrf_scores[p_id] / max_theoretical_rrf)

            record = PassageRecord(
                passage_id=original.passage_id,
                text=original.text,
                score=round(norm_score, 4),
                location=original.location,
                dense_score=round(dense_scores.get(p_id, 0.0), 4),
                bm25_score=round(sparse_scores.get(p_id, 0.0), 4),
                neighbour_context=original.neighbour_context,
            )
            ranked_passages.append(record)

        return RetrievalRecord(
            query=query,
            passages=ranked_passages,
            retrieval_mode="hybrid_rrf",
        )

    def _save_cached_passages(self, passages: List[PassageRecord]) -> None:
        cache_file = self.persist_dir / "passages_cache.json"
        data = [p.model_dump() for p in passages]
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_cached_passages(self) -> None:
        cache_file = self.persist_dir / "passages_cache.json"
        if not cache_file.exists():
            return
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            passages = [PassageRecord(**d) for d in data]
            self.passages_map = {p.passage_id: p for p in passages}
            self.passage_ids_order = [p.passage_id for p in passages]
            tokenized = [_tokenize_text(p.text) for p in passages]
            self.bm25 = BM25Okapi(tokenized)
            logger.info(f"Loaded {len(passages)} passages from cache into BM25.")
        except Exception as e:
            logger.warning(f"Failed to load cached passages: {e}")
