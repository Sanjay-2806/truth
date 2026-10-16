"""Pydantic v2 schemas for TruthGuard AI inter-agent records."""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# -------------------------------------------------------------------------
# Phase 1: Retrieval Schemas
# -------------------------------------------------------------------------

class PassageLocation(BaseModel):
    """Metadata detailing the location of a retrieved passage."""
    doc_id: str = Field(..., description="Unique identifier of source document")
    doc_title: str = Field(..., description="Human-readable title or filename")
    section_heading: str = Field(default="", description="Section or clause heading (e.g., Clause 6.4.4)")
    page: int = Field(..., description="1-indexed page number in the original PDF")
    chunk_index: int = Field(..., description="Zero-indexed chunk offset within the document")


class PassageRecord(BaseModel):
    """Individual retrieved text passage with hybrid retrieval scores."""
    passage_id: str = Field(..., description="Unique chunk identifier (e.g. doc_id::chunk_001)")
    text: str = Field(..., description="Clean passage text content")
    score: float = Field(..., description="Final hybrid reciprocal rank fusion score (or similarity score)")
    location: PassageLocation = Field(..., description="Physical and semantic location of the text")
    dense_score: Optional[float] = Field(default=None, description="Dense vector similarity score")
    bm25_score: Optional[float] = Field(default=None, description="Sparse BM25 score")
    neighbour_context: Optional[str] = Field(
        default=None,
        description="Surrounding clause or paragraph context for resolving exceptions",
    )


class RetrievalRecord(BaseModel):
    """Output of the Retriever Agent provided to downstream components."""
    query: str = Field(..., description="User query submitted to the system")
    passages: List[PassageRecord] = Field(default_factory=list, description="Ranked list of top-k passages")
    retrieval_mode: str = Field(default="hybrid_rrf", description="Retrieval strategy used")


# -------------------------------------------------------------------------
# Phase 2: Generation and Claim Extraction Schemas
# -------------------------------------------------------------------------

class DraftRecord(BaseModel):
    """Output of the Generator Agent."""
    query: str = Field(..., description="User query")
    answer: str = Field(..., description="Generated answer grounded solely in retrieved passages")
    used_passage_ids: List[str] = Field(default_factory=list, description="IDs of passages referenced")
    is_unanswerable: bool = Field(default=False, description="True if retrieved passages do not answer the query")


ClaimType = Literal[
    "condition",
    "exception",
    "deadline",
    "penalty",
    "authority",
    "effective_date",
    "other",
]


class AtomicClaim(BaseModel):
    """Atomic claim extracted from a generated answer."""
    claim_id: str = Field(..., description="Unique claim identifier, e.g. c_01")
    text: str = Field(..., description="Self-contained statement asserting a single factual proposition")
    type: ClaimType = Field(default="other", description="Typological category of the claim")
    critical: bool = Field(
        default=False,
        description="True for claims governing eligibility, deadlines, or penalties",
    )
    weight: float = Field(default=1.0, description="Risk calculation weight (default 2 for critical, 1 for other)")


class ClaimExtractionRecord(BaseModel):
    """Output of the Claim Extractor Agent."""
    query: str = Field(..., description="User query")
    claims: List[AtomicClaim] = Field(default_factory=list, description="List of extracted atomic claims")


# -------------------------------------------------------------------------
# Phase 3: Claim Verification (NLI) Schemas
# -------------------------------------------------------------------------

VerificationLabel = Literal["Verified", "Unsupported", "Contradicted", "Not Applicable"]


class ClaimVerificationResult(BaseModel):
    """Verification decision and evidence pointer for a single atomic claim."""
    claim_id: str = Field(..., description="Claim identifier")
    claim_text: str = Field(..., description="Claim text evaluated")
    label: VerificationLabel = Field(..., description="Verification classification")
    E_i: float = Field(..., description="Maximum entailment probability across all retrieved passages")
    K_i: float = Field(..., description="Maximum contradiction probability across all retrieved passages")
    evidence_passage_id: Optional[str] = Field(
        default=None,
        description="Passage ID providing the maximum entailment (or contradiction) score",
    )
    evidence_text: Optional[str] = Field(default=None, description="Text snippet of the primary evidence passage")
    critical: bool = Field(default=False, description="Whether claim was flagged as critical")
    weight: float = Field(default=1.0, description="Weight used in risk aggregation")


class VerificationRecord(BaseModel):
    """Output of the Claim Verifier Agent."""
    query: str = Field(..., description="User query")
    results: List[ClaimVerificationResult] = Field(default_factory=list, description="Per-claim verification results")


# -------------------------------------------------------------------------
# Phase 4: Risk and Decision Schemas
# -------------------------------------------------------------------------

DecisionReason = Literal[
    "NONE",
    "NO_EVIDENCE",
    "CRITICAL_CONTRADICTION",
    "RISK_ABOVE_THRESHOLD",
]


class DecisionRecord(BaseModel):
    """Output of the Risk & Decision Agent."""
    query: str = Field(..., description="User query")
    answer: Optional[str] = Field(default=None, description="Released answer or None if abstained")
    abstained: bool = Field(..., description="Whether the system chose to abstain from answering")
    reason_code: DecisionReason = Field(default="NONE", description="Machine-readable abstention code")
    reason_explanation: str = Field(default="", description="Human-readable explanation of decision")
    risk_score: float = Field(..., description="Calibrated risk score R in range [0, 1]")
    claims: List[ClaimVerificationResult] = Field(default_factory=list, description="Full per-claim verification detail")
    passages: List[PassageRecord] = Field(default_factory=list, description="Retrieved evidence passages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution telemetry and timings")
