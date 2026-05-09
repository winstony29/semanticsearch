"""Step 1 — Embeddings.

Owner: Agent 2 (embed/score/classify).

Embed all clauses (from pairs and unmatched lists) via OpenAI's text-embedding-3-small,
with batching, L2 normalisation, empty-string protection, and tenacity retry.
"""

import os

import numpy as np
from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from backend.models.schemas import AlignmentResult
from ml.thresholds import EMBEDDING_MODEL

_RETRYABLE_OPENAI_ERRORS = (RateLimitError, APIConnectionError, APIStatusError)


@retry(
    retry=retry_if_exception_type(_RETRYABLE_OPENAI_ERRORS),
    wait=wait_random_exponential(min=1, max=30),
    stop=stop_after_attempt(6),
    reraise=True,
)
async def _embed_batch_normalized(texts: list[str]) -> list[np.ndarray]:
    """Embed a list of texts in one API call, return L2-normalized vectors.

    Internal helper shared by ``embed_clauses`` (clause-keyed dict) and
    ``embed_texts`` (ordered ndarray). Centralising the OpenAI call keeps
    retry config in one place.

    Empty / whitespace-only inputs are replaced with a single space so the
    API does not 400 on a zero-token request.
    """
    safe_texts = [t if t.strip() else " " for t in texts]

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=safe_texts,
    )

    out: list[np.ndarray] = []
    for i in range(len(safe_texts)):
        vec = np.array(response.data[i].embedding, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        out.append(vec)
    return out


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

    clause_ids = list(clause_map.keys())
    texts = [clause_map[cid] for cid in clause_ids]

    vectors = await _embed_batch_normalized(texts)

    return {cid: vec for cid, vec in zip(clause_ids, vectors)}


async def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a flat list of texts; return an ``(N, d)`` L2-normalized array.

    Used by the alignment-time embedding path (``backend/services/align.py``)
    where Winston's ``semantic_hungarian`` consumes embeddings as a single
    ndarray sliced by index, not a clause-id dict.

    For an empty input list returns a ``(0, 0)`` ndarray.
    """
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    vectors = await _embed_batch_normalized(texts)
    return np.stack(vectors)
