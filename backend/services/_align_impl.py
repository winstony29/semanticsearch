"""
Vendored alignment implementation — minimal subset.

Source: ``origin/main:ml/alignment_methods.py`` (Winston). Only
``semantic_hungarian`` and its private helpers are pulled in. The other
methods on origin (lexical, hybrid, greedy, adaptive) are intentionally
omitted — we only need one path for the staged adapter, and a smaller
surface keeps the eventual upstream merge clean.

This file is staging only. It is reachable from ``backend/services/align.py``
solely behind the ``USE_REAL_ALIGN`` feature flag, which defaults to off.
When Winston pushes his finished algorithm, replace the body of this file
with whatever he ships and leave ``align.py`` alone.

Imports mirror the upstream file so a future ``git diff`` against
``origin/main:ml/alignment_methods.py`` stays small.
"""

from typing import Dict, List

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.metrics.pairwise import cosine_similarity


def semantic_hungarian(
    v1_sentences: List[str],
    v2_sentences: List[str],
    embeddings: np.ndarray,
    threshold: float = 0.6,
) -> Dict:
    """Hungarian alignment using semantic embeddings.

    Args:
        v1_sentences: Original-side sentences (length n).
        v2_sentences: Revised-side sentences (length m).
        embeddings: Pre-computed (n+m, d) array — first n rows are v1,
            remaining m rows are v2.
        threshold: Similarity below which a Hungarian pairing is rejected
            and split into ``deleted`` + ``added``.

    Returns:
        Dict with ``method``, ``pairs`` (flat list of dicts mixing
        ``matched`` / ``added`` / ``deleted``), and ``similarity_matrix``.
    """
    if not v1_sentences or not v2_sentences:
        return _handle_empty_case(v1_sentences, v2_sentences)

    emb_v1 = embeddings[: len(v1_sentences)]
    emb_v2 = embeddings[len(v1_sentences):]

    sim_matrix = cosine_similarity(emb_v1, emb_v2)

    pairs = _run_hungarian_with_threshold(
        sim_matrix, v1_sentences, v2_sentences, threshold, method="semantic"
    )

    return {
        "method": "semantic_hungarian",
        "pairs": pairs,
        "similarity_matrix": sim_matrix,
    }


def _run_hungarian_with_threshold(
    sim_matrix: np.ndarray,
    v1_sentences: List[str],
    v2_sentences: List[str],
    threshold: float,
    method: str,
) -> List[Dict]:
    """Hungarian with square padding and threshold-based pruning."""
    n, m = sim_matrix.shape
    cost_matrix = 1 - sim_matrix

    max_dim = max(n, m)
    padded_cost = np.full((max_dim, max_dim), 1.0)
    padded_cost[:n, :m] = cost_matrix

    row_ind, col_ind = linear_sum_assignment(padded_cost)

    pairs: List[Dict] = []
    pair_id = 0

    for i, j in zip(row_ind, col_ind):
        if i < n and j < m:
            score = sim_matrix[i, j]
            if score >= threshold:
                pairs.append({
                    "pair_id": f"pair_{pair_id:03d}",
                    "v1_sentence": v1_sentences[i],
                    "v2_sentence": v2_sentences[j],
                    "v1_index": int(i),
                    "v2_index": int(j),
                    "similarity_score": float(score),
                    "status": "matched",
                })
                pair_id += 1
            else:
                pairs.append({
                    "pair_id": f"del_{pair_id:03d}",
                    "v1_sentence": v1_sentences[i],
                    "v2_sentence": None,
                    "v1_index": int(i),
                    "v2_index": None,
                    "similarity_score": 0.0,
                    "status": "deleted",
                })
                pairs.append({
                    "pair_id": f"add_{pair_id:03d}",
                    "v1_sentence": None,
                    "v2_sentence": v2_sentences[j],
                    "v1_index": None,
                    "v2_index": int(j),
                    "similarity_score": 0.0,
                    "status": "added",
                })
                pair_id += 1
        elif i >= n:
            pairs.append({
                "pair_id": f"add_{pair_id:03d}",
                "v1_sentence": None,
                "v2_sentence": v2_sentences[j],
                "v1_index": None,
                "v2_index": int(j),
                "similarity_score": 0.0,
                "status": "added",
            })
            pair_id += 1
        elif j >= m:
            pairs.append({
                "pair_id": f"del_{pair_id:03d}",
                "v1_sentence": v1_sentences[i],
                "v2_sentence": None,
                "v1_index": int(i),
                "v2_index": None,
                "similarity_score": 0.0,
                "status": "deleted",
            })
            pair_id += 1

    return pairs


def _handle_empty_case(
    v1_sentences: List[str], v2_sentences: List[str]
) -> Dict:
    """Empty-side handling — symmetric with the full method."""
    pairs: List[Dict] = []

    if not v1_sentences and not v2_sentences:
        return {"pairs": [], "similarity_matrix": np.array([])}

    if not v1_sentences:
        pairs = [{
            "pair_id": f"add_{i:03d}",
            "v1_sentence": None,
            "v2_sentence": sent,
            "v1_index": None,
            "v2_index": i,
            "similarity_score": 0.0,
            "status": "added",
        } for i, sent in enumerate(v2_sentences)]

    if not v2_sentences:
        pairs = [{
            "pair_id": f"del_{i:03d}",
            "v1_sentence": sent,
            "v2_sentence": None,
            "v1_index": i,
            "v2_index": None,
            "similarity_score": 0.0,
            "status": "deleted",
        } for i, sent in enumerate(v1_sentences)]

    return {"pairs": pairs, "similarity_matrix": np.array([])}
