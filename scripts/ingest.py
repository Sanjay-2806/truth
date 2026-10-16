#!/usr/bin/env python3
"""Ingestion script for TruthGuard AI.

Parses regulation PDFs from data/raw_pdfs, extracts clauses,
generates chunks with metadata & neighbour links, and indexes into ChromaDB + BM25.
"""

import sys
from pathlib import Path
from app.core.config import settings
from app.core.logging import get_logger
from app.retrieval.parser import PDFParser, ScannedPDFException
from app.retrieval.chunker import ClauseChunker
from app.retrieval.indexer import HybridRetriever

logger = get_logger("truthguard.ingest")


def run_ingestion() -> int:
    logger.info("=== Starting Regulation Ingestion Pipeline ===")
    raw_dir = settings.PROJECT_ROOT / settings.RAW_PDFS_DIR
    if not raw_dir.exists():
        logger.error(f"Raw PDFs directory '{raw_dir}' does not exist.")
        return 1

    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDF files found in '{raw_dir}'. Please provide regulation PDFs.")
        return 1

    logger.info(f"Found {len(pdf_files)} PDF file(s) to process.")

    parser = PDFParser()
    chunker = ClauseChunker()
    retriever = HybridRetriever()

    total_chunks_indexed = 0

    for pdf_path in pdf_files:
        logger.info(f"Processing: {pdf_path.name}")
        doc_id = pdf_path.stem.lower().replace(" ", "_").replace("-", "_")
        doc_title = pdf_path.stem.replace("_", " ").replace("-", " ")

        try:
            pages = parser.parse(pdf_path)
        except ScannedPDFException as e:
            logger.error(f"Aborting ingestion for {pdf_path.name}: {e}")
            logger.error("Please provide OCR-processed searchable PDF.")
            return 2

        passages = chunker.chunk_document(doc_id=doc_id, doc_title=doc_title, pages=pages)
        indexed_count = retriever.index_passages(passages)
        total_chunks_indexed += indexed_count

        logger.info(f"Indexed {indexed_count} passages from '{pdf_path.name}'.")

    logger.info(f"=== Ingestion Complete! Total indexed passages: {total_chunks_indexed} ===")
    return 0


if __name__ == "__main__":
    sys.exit(run_ingestion())
