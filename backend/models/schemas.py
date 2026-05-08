from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

# ============================================================================
# REQUEST MODELS
# ============================================================================

class CompareRequest(BaseModel):
    """Request model for comparing two text versions."""
    v1_text: str = Field(..., description="Original version, plaintext")
    v2_text: str = Field(..., description="Revised version, plaintext")


# ============================================================================
# INTERNAL MODELS (BE ↔ ML)
# ============================================================================

class TokenizedInput(BaseModel):
    """Tokenized sentences sent from BE to ML layer."""
    v1_sentences: list[str]
    v2_sentences: list[str]


class SentencePair(BaseModel):
    """Individual sentence pair with alignment and scoring."""
    pair_id: str
    v1_sentence: Optional[str] = None  # None if addition (v2-only)
    v2_sentence: Optional[str] = None  # None if deletion (v1-only)
    v1_index: Optional[int] = None
    v2_index: Optional[int] = None
    similarity_score: float  # 0.0 to 1.0
    status: str  # "matched" | "added" | "deleted"
    severity: str  # "green" | "yellow" | "red" | "added" | "deleted"


class DocumentSummary(BaseModel):
    """Summary statistics for the entire document comparison."""
    overall_score: float
    total_pairs: int
    green_count: int
    yellow_count: int
    red_count: int
    added_count: int
    deleted_count: int


class MLResult(BaseModel):
    """Complete result from ML layer."""
    pairs: list[SentencePair]
    summary: DocumentSummary


# ============================================================================
# RESPONSE MODELS (BE → FE)
# ============================================================================

class SentencePairOut(BaseModel):
    """Sentence pair output sent to frontend."""
    pair_id: str
    v1_sentence: Optional[str] = None
    v2_sentence: Optional[str] = None
    v1_index: Optional[int] = None
    v2_index: Optional[int] = None
    similarity_score: float
    status: str  # "matched" | "added" | "deleted"
    severity: str  # "green" | "yellow" | "red" | "added" | "deleted"
    explanation: Optional[str] = None  # null initially, populated via async polling


class CompareResponse(BaseModel):
    """Response model for compare endpoint."""
    comparison_id: str
    pairs: list[SentencePairOut]
    summary: DocumentSummary


class ExplanationResponse(BaseModel):
    """Response model for explanation polling endpoint."""
    comparison_id: str
    status: str  # "pending" | "partial" | "complete"
    explanations: dict[str, Optional[str]]  # pair_id → explanation string or null
