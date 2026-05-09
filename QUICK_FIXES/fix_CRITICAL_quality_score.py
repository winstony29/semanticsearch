"""
CRITICAL FIX: Add Overall Quality Score and Warnings

ISSUE: No validation of alignment quality. System matches everything
       even if all matches are terrible.

FILE: backend/routes/compare.py
LINE: Add at the end of compare_documents function (before return)
PRIORITY: HIGH - Warns users about poor alignments

TIME: 5 minutes
"""

# ADD THIS CODE BEFORE THE RETURN STATEMENT (line 61):
# -----------------------------------------------------------------------------

    # VALIDATION: Check alignment quality
    matched_pairs = [p for p in ml_result.pairs if p.status == "matched"]

    if matched_pairs:
        overall_quality = sum(p.similarity_score for p in matched_pairs) / len(matched_pairs)

        # Add quality metrics to summary
        ml_result.summary.overall_quality = overall_quality

        # Determine confidence level
        if overall_quality >= 0.75:
            confidence = "high"
        elif overall_quality >= 0.50:
            confidence = "medium"
        elif overall_quality >= 0.30:
            confidence = "low"
        else:
            confidence = "very_low"

        # Log warning for poor alignments
        if overall_quality < 0.30:
            import logging
            logging.warning(
                f"Very poor alignment quality ({overall_quality:.2f}). "
                f"Documents may be completely unrelated."
            )

    else:
        # No matches at all
        overall_quality = 0.0
        confidence = "none"
        import logging
        logging.warning("No sentence matches found. Documents appear completely different.")

    # Add to response (you'll need to update CompareResponse schema)
    # For now, just log it

    return CompareResponse(
        comparison_id=comparison_id,
        pairs=pairs_out,
        summary=ml_result.summary
        # TODO: Add overall_quality and confidence to response
    )

# -----------------------------------------------------------------------------

# ALSO UPDATE THE SCHEMA (models/schemas.py):
# Add to DocumentSummary class:

class DocumentSummary(BaseModel):
    overall_score: float
    total_pairs: int
    green_count: int
    yellow_count: int
    red_count: int
    added_count: int
    deleted_count: int
    # ADD THESE:
    overall_quality: float = 0.0  # NEW: mean of all match scores
    confidence: str = "unknown"    # NEW: high/medium/low/very_low/none
