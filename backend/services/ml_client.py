"""
Client for calling the ML layer.

For hackathon simplicity, this directly imports and calls the ML module.
In production, this could be an HTTP client to a separate ML service.
"""

from models.schemas import MLResult, SentencePair, DocumentSummary


def compare_sentences_ml(v1_sentences: list[str], v2_sentences: list[str]) -> MLResult:
    """
    Call ML layer to align and score sentence pairs.

    Args:
        v1_sentences: List of sentences from original version
        v2_sentences: List of sentences from revised version

    Returns:
        MLResult with aligned pairs and summary statistics
    """
    # TODO: Import and call the actual ML pipeline
    # from ml.semantic_engine import compare_sentences
    # return compare_sentences(v1_sentences, v2_sentences)

    # For now, return mock data to test the API flow
    return _mock_ml_result(v1_sentences, v2_sentences)


def _mock_ml_result(v1_sentences: list[str], v2_sentences: list[str]) -> MLResult:
    """
    Generate mock ML results for testing the API.
    Remove this once the real ML pipeline is implemented.
    """
    pairs = []

    # Create mock matched pairs
    for i in range(min(len(v1_sentences), len(v2_sentences))):
        # Mock similarity scores
        if i == 0:
            score, severity = 0.92, "green"
        elif i == 1:
            score, severity = 0.75, "yellow"
        else:
            score, severity = 0.55, "red"

        pairs.append(SentencePair(
            pair_id=f"pair_{i:03d}",
            v1_sentence=v1_sentences[i],
            v2_sentence=v2_sentences[i],
            v1_index=i,
            v2_index=i,
            similarity_score=score,
            status="matched",
            severity=severity
        ))

    # Mock additions (v2 has more sentences)
    for i in range(len(v1_sentences), len(v2_sentences)):
        pairs.append(SentencePair(
            pair_id=f"pair_add_{i:03d}",
            v1_sentence=None,
            v2_sentence=v2_sentences[i],
            v1_index=None,
            v2_index=i,
            similarity_score=0.0,
            status="added",
            severity="added"
        ))

    # Mock deletions (v1 has more sentences)
    for i in range(len(v2_sentences), len(v1_sentences)):
        pairs.append(SentencePair(
            pair_id=f"pair_del_{i:03d}",
            v1_sentence=v1_sentences[i],
            v2_sentence=None,
            v1_index=i,
            v2_index=None,
            similarity_score=0.0,
            status="deleted",
            severity="deleted"
        ))

    # Calculate mock summary
    matched_pairs = [p for p in pairs if p.status == "matched"]
    green_count = sum(1 for p in matched_pairs if p.severity == "green")
    yellow_count = sum(1 for p in matched_pairs if p.severity == "yellow")
    red_count = sum(1 for p in matched_pairs if p.severity == "red")
    added_count = sum(1 for p in pairs if p.status == "added")
    deleted_count = sum(1 for p in pairs if p.status == "deleted")

    overall_score = (
        sum(p.similarity_score for p in matched_pairs) / len(matched_pairs)
        if matched_pairs else 0.0
    )

    summary = DocumentSummary(
        overall_score=overall_score,
        total_pairs=len(matched_pairs),
        green_count=green_count,
        yellow_count=yellow_count,
        red_count=red_count,
        added_count=added_count,
        deleted_count=deleted_count
    )

    return MLResult(pairs=pairs, summary=summary)
