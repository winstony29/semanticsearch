"""
FIX #1: Replace this function in ml/semantic_engine.py at line 65

COPY-PASTE READY - OpenAI Version
"""

def _get_embeddings(sentences: list[str]) -> np.ndarray:
    """
    Get embeddings for all sentences in a single batch using OpenAI.

    Requires: OPENAI_API_KEY in environment
    Cost: ~$0.00002 per 1000 tokens (very cheap)
    """
    from openai import OpenAI
    import os

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=sentences
    )

    embeddings = np.array([d.embedding for d in response.data])
    return embeddings
