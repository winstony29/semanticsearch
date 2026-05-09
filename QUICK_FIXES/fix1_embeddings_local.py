"""
FIX #1: Replace this function in ml/semantic_engine.py at line 65

COPY-PASTE READY - Local Version (FREE, but slower first time)
"""

# Add this at the top of semantic_engine.py
_model = None

def _get_embeddings(sentences: list[str]) -> np.ndarray:
    """
    Get embeddings for all sentences using local sentence-transformers.

    Requires: pip install sentence-transformers
    First run: Downloads ~90MB model (one-time)
    Speed: ~100 sentences/second on CPU
    """
    from sentence_transformers import SentenceTransformer

    global _model
    if _model is None:
        # Load model once (first call takes ~5 seconds)
        _model = SentenceTransformer('all-MiniLM-L6-v2')

    embeddings = _model.encode(sentences)
    return np.array(embeddings)
