"""Step 2 — Scoring.

Owner: Agent 2 (embed/score/classify).

Pair-wise cosine similarity (dot product on normalised vectors) and the
cosine_to_drift remap (clamped, 0–100 scale).
"""

import numpy as np

from backend.models.schemas import AlignedPair
from ml.thresholds import DRIFT_CEIL, DRIFT_FLOOR


def score_pair(before_emb: np.ndarray, after_emb: np.ndarray) -> float:
    """Cosine similarity (dot product on unit-normalized vectors), clamped to [-1, 1]."""
    sim = float(np.dot(before_emb, after_emb))
    return max(-1.0, min(1.0, sim))


def cosine_to_drift(similarity: float) -> float:
    """Remap cosine similarity to a 0-100 drift score, clamped per thresholds.py."""
    sim = max(DRIFT_FLOOR, min(DRIFT_CEIL, similarity))
    return round((1.0 - sim) / (DRIFT_CEIL - DRIFT_FLOOR) * 100.0, 2)


def score_pairs(
    pairs: list[AlignedPair],
    embeddings: dict[str, np.ndarray],
) -> list[tuple[AlignedPair, float, float]]:
    """Score every aligned pair and return ``(pair, similarity, drift)`` tuples.

    Pure / sync — no I/O.
    """
    result: list[tuple[AlignedPair, float, float]] = []
    for pair in pairs:
        before_emb = embeddings[pair.before.id]
        after_emb = embeddings[pair.after.id]
        sim = score_pair(before_emb, after_emb)
        drift = cosine_to_drift(sim)
        result.append((pair, sim, drift))
    return result


# Backwards-compat alias. Prefer score_pairs in new code; this exists so
# any pre-rename caller keeps working until next sweep.
score_alignment = score_pairs
