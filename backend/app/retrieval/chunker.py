"""Clause-aware chunker for academic regulations in TruthGuard AI.

Splits documents by clause/section headings, attaches hierarchical metadata,
maintains NLI token constraints with sliding-window support, and links
neighbouring context for exception handling.
"""

from typing import List, Dict, Any, Optional
import re
from app.schemas.records import PassageRecord, PassageLocation
from app.core.logging import get_logger

logger = get_logger("truthguard.chunker")


class ClauseChunker:
    """Extracts clause-level passages with metadata and neighbour links."""

    def __init__(
        self,
        max_chunk_words: int = 260,
        min_chunk_words: int = 25,
        window_overlap_words: int = 50,
    ):
        self.max_chunk_words = max_chunk_words
        self.min_chunk_words = min_chunk_words
        self.window_overlap_words = window_overlap_words

        # Regex matching clause numbers like "1.", "2.1", "6.4.4", "TABLE 14.1:"
        self.heading_regex = re.compile(
            r"^(?:(?:TABLE\s+\d+(\.\d+)?[:\s]+[^\n]+)|(?:\d+(\.\d+)*\.?\s+[A-Z][^\n]+))",
            re.MULTILINE,
        )

    def chunk_document(
        self,
        doc_id: str,
        doc_title: str,
        pages: List[Dict[str, Any]],
    ) -> List[PassageRecord]:
        """Processes page records into an ordered list of PassageRecords with metadata."""
        raw_sections = self._extract_raw_sections(pages)
        raw_chunks: List[Dict[str, Any]] = []

        # Split long sections into sliding windows adhering to token limits
        for sec in raw_sections:
            heading = sec["heading"]
            text = sec["text"].strip()
            page = sec["page"]

            words = text.split()
            if len(words) <= self.max_chunk_words:
                if len(words) >= self.min_chunk_words or not raw_chunks:
                    raw_chunks.append({
                        "heading": heading,
                        "text": text,
                        "page": page,
                    })
                elif raw_chunks:
                    # Append small fragments to previous chunk
                    raw_chunks[-1]["text"] += "\n\n" + text
            else:
                # Apply sliding window
                step = self.max_chunk_words - self.window_overlap_words
                start = 0
                part_idx = 1
                while start < len(words):
                    sub_words = words[start : start + self.max_chunk_words]
                    sub_text = " ".join(sub_words)
                    sub_heading = f"{heading} (Part {part_idx})" if part_idx > 1 else heading
                    raw_chunks.append({
                        "heading": sub_heading,
                        "text": sub_text,
                        "page": page,
                    })
                    start += step
                    part_idx += 1

        # Build PassageRecord objects and attach neighbouring context
        passage_records: List[PassageRecord] = []
        total_chunks = len(raw_chunks)

        for i, chunk_data in enumerate(raw_chunks):
            passage_id = f"{doc_id}::chunk_{i:04d}"
            text = chunk_data["text"]

            # Construct neighbouring context (previous tail + next head)
            prev_ctx = ""
            if i > 0:
                prev_words = raw_chunks[i - 1]["text"].split()[-40:]
                prev_ctx = "Previous Clause Context: ... " + " ".join(prev_words)

            next_ctx = ""
            if i < total_chunks - 1:
                next_words = raw_chunks[i + 1]["text"].split()[:40]
                next_ctx = "Following Clause Context: " + " ".join(next_words) + " ..."

            neighbour_parts = [p for p in [prev_ctx, next_ctx] if p]
            neighbour_context = "\n---\n".join(neighbour_parts) if neighbour_parts else None

            location = PassageLocation(
                doc_id=doc_id,
                doc_title=doc_title,
                section_heading=chunk_data["heading"],
                page=chunk_data["page"],
                chunk_index=i,
            )

            record = PassageRecord(
                passage_id=passage_id,
                text=text,
                score=0.0,
                location=location,
                neighbour_context=neighbour_context,
            )
            passage_records.append(record)

        logger.info(f"Chunked document '{doc_id}' into {len(passage_records)} clause passages.")
        return passage_records

    def _extract_raw_sections(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifies clause boundaries across consecutive pages."""
        sections: List[Dict[str, Any]] = []
        current_heading = "Preamble / General Introduction"
        current_lines: List[str] = []
        current_page = 1

        for p_data in pages:
            page_num = p_data["page"]
            text = p_data["text"]
            lines = text.split("\n")

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                if self.heading_regex.match(stripped):
                    # Save accumulated section if it contains content
                    accumulated = "\n".join(current_lines).strip()
                    if accumulated:
                        sections.append({
                            "heading": current_heading,
                            "text": accumulated,
                            "page": current_page,
                        })
                        current_lines = []

                    current_heading = stripped
                    current_page = page_num
                    current_lines.append(stripped)
                else:
                    current_lines.append(line)

        # Append final section
        final_text = "\n".join(current_lines).strip()
        if final_text:
            sections.append({
                "heading": current_heading,
                "text": final_text,
                "page": current_page,
            })

        return sections
