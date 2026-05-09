"""
FIX #2: Replace compare_sentences_ml() in backend/services/ml_client.py

COPY-PASTE READY
"""

def compare_sentences_ml(v1_sentences: list[str], v2_sentences: list[str]) -> MLResult:
    """
    Call ML layer to align and score sentence pairs.

    This imports the real ML pipeline and returns actual results.
    """
    import sys
    from pathlib import Path

    # Add ml directory to path
    ml_path = Path(__file__).parent.parent.parent / 'ml'
    sys.path.insert(0, str(ml_path))

    # Import ML function
    from semantic_engine import compare_sentences

    # Call real ML pipeline
    result_dict = compare_sentences(v1_sentences, v2_sentences)

    # Convert dict to Pydantic models
    pairs = [SentencePair(**p) for p in result_dict["pairs"]]
    summary = DocumentSummary(**result_dict["summary"])

    return MLResult(pairs=pairs, summary=summary)


# DELETE EVERYTHING BELOW THIS (the entire _mock_ml_result function)
# Lines 30-107 can be deleted
