"""
Client for calling the ML layer.

For hackathon simplicity, this directly imports and calls the ML module.
In production, this could be an HTTP client to a separate ML service.
"""

import sys
sys.path.insert(0, 'ml')

from models.schemas import MLResult, SentencePair, DocumentSummary
from ml.semantic_engine import compare_sentences


def compare_sentences_ml(v1_sentences: list[str], v2_sentences: list[str]) -> MLResult:
    """
    Call ML layer to align and score sentence pairs using adaptive Hungarian.

    Uses adaptive_hungarian which:
    - Primary: semantic_hungarian (handles reordering, simple edits)
    - Fallback: greedy_with_merges if quality < 0.5 (handles merges/splits)
    - Normalizes output (converts merged/split to matched with raw_status)
    - Adds quality warning if overall_score < 0.3

    Args:
        v1_sentences: List of sentences from original version
        v2_sentences: List of sentences from revised version

    Returns:
        MLResult with aligned pairs and summary statistics
    """
    # Call the actual ML pipeline
    result = compare_sentences(v1_sentences, v2_sentences)

    # Convert dict result to MLResult schema
    pairs = [SentencePair(**pair) for pair in result["pairs"]]
    summary = DocumentSummary(**result["summary"])

    return MLResult(pairs=pairs, summary=summary)
