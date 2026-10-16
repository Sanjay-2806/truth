"""Unit and integration tests for Phase 1: Ingestion and Hybrid Retrieval."""

from pathlib import Path
import pytest
import pymupdf

from app.core.config import settings
from app.retrieval.parser import PDFParser, ScannedPDFException
from app.retrieval.chunker import ClauseChunker
from app.retrieval.indexer import HybridRetriever
from app.agents.retriever import RetrieverAgent


@pytest.fixture(scope="module")
def pdf_path() -> Path:
    raw_pdf = settings.PROJECT_ROOT / "data/raw_pdfs/2024-SEC-UG-REGULATIONS-1.pdf"
    assert raw_pdf.exists(), f"Raw regulation PDF not found at {raw_pdf}"
    return raw_pdf


@pytest.fixture(scope="module")
def retriever_instance() -> HybridRetriever:
    retriever = HybridRetriever()
    assert len(retriever.passages_map) > 0, "Retriever passages map should be populated"
    return retriever


def test_scanned_pdf_detection_on_digital_pdf(pdf_path: Path):
    """Verifies that the digital regulation PDF is not flagged as scanned."""
    parser = PDFParser()
    is_scanned, avg_chars, total_pages = parser.detect_scanned(pdf_path)
    assert is_scanned is False
    assert total_pages == 48
    assert avg_chars > 500


def test_scanned_pdf_detection_on_empty_dummy(tmp_path: Path):
    """Verifies that a mock scanned (empty text) PDF raises ScannedPDFException."""
    dummy_pdf = tmp_path / "scanned_doc.pdf"
    doc = pymupdf.open()
    # Create empty blank pages without text
    for _ in range(3):
        page = doc.new_page()
    doc.save(str(dummy_pdf))
    doc.close()

    parser = PDFParser()
    is_scanned, avg_chars, total_pages = parser.detect_scanned(dummy_pdf)
    assert is_scanned is True
    assert avg_chars == 0.0

    with pytest.raises(ScannedPDFException):
        parser.parse(dummy_pdf)


def test_chunker_metadata_and_neighbour_linking(pdf_path: Path):
    """Verifies that chunks have non-empty text, complete metadata, and neighbour links."""
    parser = PDFParser()
    chunker = ClauseChunker()

    pages = parser.parse(pdf_path)
    passages = chunker.chunk_document(
        doc_id="test_reg_2024",
        doc_title="Test Regulations 2024",
        pages=pages,
    )

    assert len(passages) >= 50
    for p in passages:
        assert p.passage_id.startswith("test_reg_2024::chunk_")
        assert len(p.text.strip()) > 20
        assert p.location.doc_id == "test_reg_2024"
        assert p.location.doc_title == "Test Regulations 2024"
        assert p.location.page >= 1
        assert p.location.section_heading != ""

    # Test neighbour context linking on middle chunks
    has_neighbour_context = any(p.neighbour_context is not None for p in passages)
    assert has_neighbour_context is True

    # Check a chunk around the middle
    mid_chunk = passages[len(passages) // 2]
    assert mid_chunk.neighbour_context is not None
    assert "Context:" in mid_chunk.neighbour_context


def test_retrieval_backlog_arrear_limit(retriever_instance: HybridRetriever):
    """Verifies retrieval for 45 credits arrear limit (Clause 6.4.4)."""
    agent = RetrieverAgent(retriever=retriever_instance, top_k=5)
    record = agent.retrieve("What happens if a student has 45 or more credits as backlog arrears?")

    assert len(record.passages) > 0
    top_texts = " ".join([p.text for p in record.passages])
    assert "45" in top_texts
    assert "arrear" in top_texts.lower() or "backlog" in top_texts.lower()


def test_retrieval_attendance_requirement(retriever_instance: HybridRetriever):
    """Verifies retrieval for 80% attendance rule (Clause 7.1)."""
    agent = RetrieverAgent(retriever=retriever_instance, top_k=5)
    record = agent.retrieve("What is the minimum overall attendance percentage required to write end semester examinations?")

    assert len(record.passages) > 0
    top_texts = " ".join([p.text for p in record.passages])
    assert "80%" in top_texts or "80" in top_texts
    assert "attendance" in top_texts.lower()


def test_retrieval_medical_concession(retriever_instance: HybridRetriever):
    """Verifies retrieval for 65% to 80% medical concession (Clause 7.2)."""
    agent = RetrieverAgent(retriever=retriever_instance, top_k=5)
    record = agent.retrieve("What is the attendance concession for medical reasons or hospitalisation?")

    assert len(record.passages) > 0
    top_texts = " ".join([p.text for p in record.passages])
    assert "65%" in top_texts or "medical" in top_texts.lower()


def test_retrieval_first_class_distinction(retriever_instance: HybridRetriever):
    """Verifies retrieval for First Class with Distinction (Clause 16.1.2)."""
    agent = RetrieverAgent(retriever=retriever_instance, top_k=5)
    record = agent.retrieve("What are the requirements and minimum CGPA for First Class with Distinction?")

    assert len(record.passages) > 0
    top_texts = " ".join([p.text for p in record.passages])
    assert "8.50" in top_texts or "8.5" in top_texts
    assert "distinction" in top_texts.lower()


def test_retrieval_theory_passing_marks(retriever_instance: HybridRetriever):
    """Verifies retrieval for theory passing minimum marks (Clause 14.1)."""
    agent = RetrieverAgent(retriever=retriever_instance, top_k=5)
    record = agent.retrieve("What is the minimum mark required in the End Semester Examination for theory courses?")

    assert len(record.passages) > 0
    top_texts = " ".join([p.text for p in record.passages])
    assert "45%" in top_texts or "27" in top_texts or "50%" in top_texts

