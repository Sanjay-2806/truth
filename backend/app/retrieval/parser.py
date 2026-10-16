"""PDF Parser module for TruthGuard AI.

Extracts text and tables per page from regulation documents,
filters running headers/footers, and detects scanned/image-only PDFs.
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import re
import pymupdf
import pdfplumber

from app.core.logging import get_logger

logger = get_logger("truthguard.parser")


class ScannedPDFException(Exception):
    """Raised when an uploaded PDF is determined to be a scanned image document without searchable text."""
    pass


class PDFParser:
    """Extracts clean text and structural tables from regulation PDFs."""

    def __init__(
        self,
        min_avg_chars_per_page: float = 60.0,
        empty_page_threshold_ratio: float = 0.50,
    ):
        self.min_avg_chars_per_page = min_avg_chars_per_page
        self.empty_page_threshold_ratio = empty_page_threshold_ratio

    def detect_scanned(self, pdf_path: Path) -> Tuple[bool, float, int]:
        """Inspects text density to identify whether a PDF is scanned.

        Returns:
            Tuple of (is_scanned: bool, avg_chars_per_page: float, total_pages: int)
        """
        doc = pymupdf.open(str(pdf_path))
        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            return True, 0.0, 0

        total_chars = 0
        empty_pages = 0

        for page in doc:
            text = page.get_text().strip()
            total_chars += len(text)
            if len(text) < 15:
                empty_pages += 1

        doc.close()
        avg_chars = total_chars / total_pages
        empty_ratio = empty_pages / total_pages

        is_scanned = (
            avg_chars < self.min_avg_chars_per_page
            or empty_ratio >= self.empty_page_threshold_ratio
        )
        return is_scanned, avg_chars, total_pages

    def parse(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Parses a regulation PDF into structured page records.

        Raises:
            ScannedPDFException: If the PDF is scanned and lacks text streams.
        """
        is_scanned, avg_chars, total_pages = self.detect_scanned(pdf_path)
        if is_scanned:
            msg = (
                f"PDF '{pdf_path.name}' appears to be scanned or contains insufficient text "
                f"(avg chars/page: {avg_chars:.1f}, total pages: {total_pages}). "
                "Optical Character Recognition (OCR) is required."
            )
            logger.error(msg)
            raise ScannedPDFException(msg)

        logger.info(
            f"Parsing '{pdf_path.name}' ({total_pages} pages, avg {avg_chars:.1f} chars/page)..."
        )

        # Extract table structures using pdfplumber
        tables_per_page: Dict[int, List[str]] = {}
        try:
            with pdfplumber.open(str(pdf_path)) as plumber_pdf:
                for idx, page in enumerate(plumber_pdf.pages, start=1):
                    tables = page.extract_tables()
                    formatted_tables = []
                    for table in tables:
                        if not table:
                            continue
                        # Format table into markdown
                        headers = table[0]
                        clean_headers = [str(c or "").strip().replace("\n", " ") for c in headers]
                        rows = table[1:]
                        if not any(clean_headers):
                            continue
                        tbl_md = ["| " + " | ".join(clean_headers) + " |"]
                        tbl_md.append("| " + " | ".join(["---"] * len(clean_headers)) + " |")
                        for row in rows:
                            clean_row = [str(c or "").strip().replace("\n", " ") for c in row]
                            tbl_md.append("| " + " | ".join(clean_row) + " |")
                        formatted_tables.append("\n".join(tbl_md))
                    if formatted_tables:
                        tables_per_page[idx] = formatted_tables
        except Exception as e:
            logger.warning(f"Optional table extraction via pdfplumber failed: {e}")

        # Extract textual stream per page using pymupdf
        doc = pymupdf.open(str(pdf_path))
        page_records: List[Dict[str, Any]] = []

        for page_idx, page in enumerate(doc, start=1):
            raw_text = page.get_text()
            cleaned_text = self._clean_page_text(raw_text, page_idx)

            # Append structured table representations if present
            if page_idx in tables_per_page:
                cleaned_text += "\n\n[Structured Tables from Page]\n" + "\n\n".join(
                    tables_per_page[page_idx]
                )

            page_records.append({
                "page": page_idx,
                "text": cleaned_text.strip(),
                "raw_char_count": len(raw_text),
            })

        doc.close()
        logger.info(f"Successfully extracted {len(page_records)} pages from '{pdf_path.name}'.")
        return page_records

    def _clean_page_text(self, text: str, page_number: int) -> str:
        """Removes headers, footers, and page numbers."""
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            # Remove recurring headers
            if stripped in ["Autonomous Regulations 2024", "REGULATIONS 2024"]:
                continue
            # Remove standalone page numbers or | 21 |
            if re.match(r"^\|\s*\d+\s*\|$", stripped) or stripped == str(page_number):
                continue
            # Remove footer signatures
            if "SRI SAIRAM ENGINEERING COLLEGE" in stripped and "West Tambaram" in stripped:
                continue
            if stripped in ["Principal", "Prinerpal"]:
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)
