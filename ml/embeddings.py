"""Step 1 — Embeddings.

Owner: Agent 2 (embed/score/classify).

Embed all clauses (from pairs and unmatched lists) via OpenAI's text-embedding-3-small,
with batching, L2 normalisation, empty-string protection, and tenacity retry.
"""

import os

import numpy as np
from openai import AsyncOpenAI, RateLimitError, APIConnectionError, APIStatusError
from tenacity import retry, wait_random_exponential, stop_after_attempt

from backend.models.schemas import AlignmentResult
from ml.thresholds import EMBEDDING_MODEL


@retry(
    retry=lambda exc: isinstance(exc, (RateLimitError, APIConnectionError, APIStatusError)),
    wait=wait_random_exponential(min=1, max=30),
    stop=stop_after_attempt(6),
)
async def embed_clauses(alignment: AlignmentResult) -> dict[str, np.ndarray]:
    """Embed every clause in alignment and return id -> normalized vector."""
    # Collect all unique clause ids and texts.
    clause_map: dict[str, str] = {}

    # From pairs.
    for pair in alignment.pairs:
        clause_map[pair.before.id] = pair.before.text
        clause_map[pair.after.id] = pair.after.text

    # From unmatched.
    for clause in alignment.unmatched_before:
        clause_map[clause.id] = clause.text
    for clause in alignment.unmatched_after:
        clause_map[clause.id] = clause.text

    # Replace empty/whitespace-only strings with a single space.
    for cid in clause_map:
        if not clause_map[cid].strip():
            clause_map[cid] = " "

    # Batch embed via AsyncOpenAI.
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    clause_ids = list(clause_map.keys())
    texts = [clause_map[cid] for cid in clause_ids]

    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    # Defensively L2-normalize all vectors.
    embeddings: dict[str, np.ndarray] = {}
    for i, cid in enumerate(clause_ids):
        vec = np.array(response.data[i].embedding, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        embeddings[cid] = vec

    return embeddings
