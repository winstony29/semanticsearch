"""
Semantic comparison engine using embeddings and Hungarian alignment.

This is Nickolas's domain - the ML pipeline for semantic diff.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment
import os
from typing import Optional

# Configuration constants
THRESHOLD_GREEN = 0.85
THRESHOLD_YELLOW = 0.60
EMBEDDING_MODEL = "text-embedding-3-small"
PADDING_PENALTY = 1.0


def compare_sentences(v1_sentences: list[str], v2_sentences: list[str]) -> dict:
    """
    Main pipeline: align and score sentence pairs.

    Steps:
    1. Embed all sentences in one batch
    2. Compute similarity matrix
    3. Run Hungarian algorithm for optimal alignment
    4. Classify pairs by severity
    5. Detect additions and deletions
    6. Compute summary statistics

    Returns:
        Dict with 'pairs' and 'summary' matching MLResult schema
    """
    # Handle edge cases
    if not v1_sentences and not v2_sentences:
        return _empty_result()

    if not v1_sentences:
        return _all_additions(v2_sentences)

    if not v2_sentences:
        return _all_deletions(v1_sentences)

    # Step 1: Get embeddings
    embeddings = _get_embeddings(v1_sentences + v2_sentences)
    emb_v1 = embeddings[:len(v1_sentences)]
    emb_v2 = embeddings[len(v1_sentences):]

    # Step 2: Compute similarity matrix
    sim_matrix = cosine_similarity(emb_v1, emb_v2)

    # Step 3: Hungarian algorithm for alignment
    pairs = _align_with_hungarian(sim_matrix, v1_sentences, v2_sentences)

    # Step 4: Compute summary statistics
    summary = _compute_summary(pairs)

    return {
        "pairs": pairs,
        "summary": summary
    }


def _get_embeddings(sentences: list[str]) -> np.ndarray:
    """
    Get embeddings for all sentences in a single batch.

    TODO: Implement actual embedding call
    - Option 1: OpenAI text-embedding-3-small
    - Option 2: sentence-transformers locally (all-MiniLM-L6-v2)
    """
    # Mock implementation - returns random embeddings
    # Replace with actual embedding API call
    return np.random.rand(len(sentences), 384)  # 384-dim for all-MiniLM


def _align_with_hungarian(
    sim_matrix: np.ndarray,
    v1_sentences: list[str],
    v2_sentences: list[str]
) -> list[dict]:
    """
    Use Hungarian algorithm to find optimal 1:1 sentence alignment.

    Returns list of aligned pairs plus additions/deletions.
    """
    n, m = sim_matrix.shape
    cost_matrix = 1 - sim_matrix

    # Pad to square matrix
    max_dim = max(n, m)
    padded_cost = np.full((max_dim, max_dim), PADDING_PENALTY)
    padded_cost[:n, :m] = cost_matrix

    # Run Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(padded_cost)

    pairs = []
    pair_id = 0

    # Process matched pairs
    for i, j in zip(row_ind, col_ind):
        if i < n and j < m:
            # Valid match
            score = sim_matrix[i, j]
            severity = _classify_severity(score)

            pairs.append({
                "pair_id": f"pair_{pair_id:03d}",
                "v1_sentence": v1_sentences[i],
                "v2_sentence": v2_sentences[j],
                "v1_index": i,
                "v2_index": j,
                "similarity_score": float(score),
                "status": "matched",
                "severity": severity
            })
            pair_id += 1

        elif i >= n:
            # Addition (v2-only)
            pairs.append({
                "pair_id": f"pair_add_{pair_id:03d}",
                "v1_sentence": None,
                "v2_sentence": v2_sentences[j],
                "v1_index": None,
                "v2_index": j,
                "similarity_score": 0.0,
                "status": "added",
                "severity": "added"
            })
            pair_id += 1

        elif j >= m:
            # Deletion (v1-only)
            pairs.append({
                "pair_id": f"pair_del_{pair_id:03d}",
                "v1_sentence": v1_sentences[i],
                "v2_sentence": None,
                "v1_index": i,
                "v2_index": None,
                "similarity_score": 0.0,
                "status": "deleted",
                "severity": "deleted"
            })
            pair_id += 1

    return pairs


def _classify_severity(score: float) -> str:
    """Classify similarity score into severity level."""
    if score >= THRESHOLD_GREEN:
        return "green"
    elif score >= THRESHOLD_YELLOW:
        return "yellow"
    else:
        return "red"


def _compute_summary(pairs: list[dict]) -> dict:
    """Compute document-level summary statistics."""
    matched = [p for p in pairs if p["status"] == "matched"]
    green = sum(1 for p in matched if p["severity"] == "green")
    yellow = sum(1 for p in matched if p["severity"] == "yellow")
    red = sum(1 for p in matched if p["severity"] == "red")
    added = sum(1 for p in pairs if p["status"] == "added")
    deleted = sum(1 for p in pairs if p["status"] == "deleted")

    overall_score = (
        sum(p["similarity_score"] for p in matched) / len(matched)
        if matched else 0.0
    )

    return {
        "overall_score": overall_score,
        "total_pairs": len(matched),
        "green_count": green,
        "yellow_count": yellow,
        "red_count": red,
        "added_count": added,
        "deleted_count": deleted
    }


def _empty_result() -> dict:
    """Return empty result when both inputs are empty."""
    return {
        "pairs": [],
        "summary": {
            "overall_score": 0.0,
            "total_pairs": 0,
            "green_count": 0,
            "yellow_count": 0,
            "red_count": 0,
            "added_count": 0,
            "deleted_count": 0
        }
    }


def _all_additions(v2_sentences: list[str]) -> dict:
    """Handle case where v1 is empty (all additions)."""
    pairs = [
        {
            "pair_id": f"pair_add_{i:03d}",
            "v1_sentence": None,
            "v2_sentence": sent,
            "v1_index": None,
            "v2_index": i,
            "similarity_score": 0.0,
            "status": "added",
            "severity": "added"
        }
        for i, sent in enumerate(v2_sentences)
    ]

    return {
        "pairs": pairs,
        "summary": {
            "overall_score": 0.0,
            "total_pairs": 0,
            "green_count": 0,
            "yellow_count": 0,
            "red_count": 0,
            "added_count": len(v2_sentences),
            "deleted_count": 0
        }
    }


def _all_deletions(v1_sentences: list[str]) -> dict:
    """Handle case where v2 is empty (all deletions)."""
    pairs = [
        {
            "pair_id": f"pair_del_{i:03d}",
            "v1_sentence": sent,
            "v2_sentence": None,
            "v1_index": i,
            "v2_index": None,
            "similarity_score": 0.0,
            "status": "deleted",
            "severity": "deleted"
        }
        for i, sent in enumerate(v1_sentences)
    ]

    return {
        "pairs": pairs,
        "summary": {
            "overall_score": 0.0,
            "total_pairs": 0,
            "green_count": 0,
            "yellow_count": 0,
            "red_count": 0,
            "added_count": 0,
            "deleted_count": len(v1_sentences)
        }
    }


# Test function
if __name__ == "__main__":
    v1 = ["I love dogs.", "They are great pets."]
    v2 = ["I really love dogs.", "Cats are also nice."]

    result = compare_sentences(v1, v2)
    print("Pairs:", len(result["pairs"]))
    print("Summary:", result["summary"])
