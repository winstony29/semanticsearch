"""
Pydantic schemas — single source of truth for all data flowing between
Frontend, Backend, and ML.

Two contracts coexist on this branch:

1. Legacy `/compare` contract (CompareRequest, SentencePair, etc.) — kept so the
   existing FE keeps working until it's rebuilt.
2. New `/api/diff` contract from ML_ARCHITECTURE.md (DiffRequest, ClauseUnit,
   AlignmentResult, DiffResponse, etc.) — the doc-aligned pipeline.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# LEGACY /compare CONTRACT
# ============================================================================

class CompareRequest(BaseModel):
    """Request model for comparing two text versions."""
    v1_text: str = Field(..., description="Original version, plaintext")
    v2_text: str = Field(..., description="Revised version, plaintext")


class TokenizedInput(BaseModel):
    """Tokenized sentences sent from BE to ML layer."""
    v1_sentences: list[str]
    v2_sentences: list[str]


class SentencePair(BaseModel):
    """Individual sentence pair with alignment and scoring."""
    pair_id: str
    v1_sentence: Optional[str] = None
    v2_sentence: Optional[str] = None
    v1_index: Optional[int] = None
    v2_index: Optional[int] = None
    similarity_score: float
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
    """Complete result from legacy ML layer."""
    pairs: list[SentencePair]
    summary: DocumentSummary


class SentencePairOut(BaseModel):
    """Sentence pair output sent to frontend on /compare."""
    pair_id: str
    v1_sentence: Optional[str] = None
    v2_sentence: Optional[str] = None
    v1_index: Optional[int] = None
    v2_index: Optional[int] = None
    similarity_score: float
    status: str
    severity: str
    explanation: Optional[str] = None


class CompareResponse(BaseModel):
    """Response model for /compare."""
    comparison_id: str
    pairs: list[SentencePairOut]
    summary: DocumentSummary


class ExplanationResponse(BaseModel):
    """Response model for /explanation/{id} polling."""
    comparison_id: str
    status: str  # "pending" | "partial" | "complete"
    explanations: dict[str, Optional[str]]


# ============================================================================
# NEW /api/diff CONTRACT  (per ML_ARCHITECTURE.md)
# ============================================================================

Classification = Literal["unchanged", "modified", "added", "removed"]
ConceptStatus = Literal["new", "weakened", "strengthened", "unchanged"]
# DiffRequest enforces min_length=1 on both sides, so concept extraction
# always sees real input — there is no "skipped" path from the public API.
ConceptExtractionStatus = Literal["ok", "failed"]


# ----- Request -----

class DiffRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    before: str = Field(..., min_length=1, max_length=20_000)
    after: str = Field(..., min_length=1, max_length=20_000)


# ----- Backend lead → ML slice (alignment contract, locked in §1) -----

class ClauseUnit(BaseModel):
    """A clause as defined by align(). May span multiple original sentences."""
    id: str = Field(..., description='"b0", "b1", ... or "a0", "a1", ...')
    text: str


class AlignedPair(BaseModel):
    """A clause from the before side paired with a clause from the after side."""
    before: ClauseUnit
    after: ClauseUnit


class AlignmentResult(BaseModel):
    """Output of align(before_text, after_text). Input to the ML slice."""
    pairs: list[AlignedPair]
    unmatched_before: list[ClauseUnit]
    unmatched_after: list[ClauseUnit]
    original_before: str
    original_after: str


# ----- ML slice → Frontend (the response, per §6) -----

class ClauseRendering(BaseModel):
    """A clause as rendered in either the before or after column."""
    id: str
    text: str
    classification: Classification
    drift_score: float = Field(..., ge=0, le=100)
    paired_with: Optional[str | list[str]] = Field(
        None,
        description=(
            "id of partner on the other side. "
            "None ⇒ unmatched / split-off / unpaired. "
            "str ⇒ standard 1:1 pairing (the common case). "
            "list[str] ⇒ N:1 merge or 1:N split — this clause maps to "
            "multiple partners on the other side. Frontend should "
            "Array.isArray() check before using."
        ),
    )


class PairRendering(BaseModel):
    """A clause pair, used for hover-connector rendering on the frontend."""
    before_id: str
    after_id: str
    similarity: float = Field(..., ge=-1.0, le=1.0)
    drift_score: float = Field(..., ge=0, le=100)
    classification: Classification


class DiffSummary(BaseModel):
    before_count: int
    after_count: int
    unchanged: int
    modified: int
    added: int
    removed: int
    overall_drift: float = Field(..., ge=0, le=100)
    pct_text_edited: float = Field(..., ge=0, le=100)
    pct_meaning_edited: float = Field(..., ge=0, le=100)
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    alignment: str = "hungarian"
    elapsed_ms: int


class Concept(BaseModel):
    name: str = Field(
        ...,
        description="Short noun phrase (3-8 words) naming the idea, obligation, "
                    "right, or theme.",
    )
    status: ConceptStatus
    evidence: str = Field(
        ...,
        description="Verbatim quote (≤240 chars) supporting the classification.",
    )
    evidence_before_ids: list[str] = Field(default_factory=list)
    evidence_after_ids: list[str] = Field(default_factory=list)


class ConceptDiff(BaseModel):
    """Wrapper used as the schema for OpenAI structured output in concepts.py."""
    summary: str
    concepts: list[Concept]


class DiffResponse(BaseModel):
    before_clauses: list[ClauseRendering]
    after_clauses: list[ClauseRendering]
    pairs: list[PairRendering]
    summary: DiffSummary
    concepts: list[Concept]
    concept_extraction: ConceptExtractionStatus = "ok"
