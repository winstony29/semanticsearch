"""
Semantic comparison engine using embeddings and adaptive Hungarian alignment.

This is Nickolas's domain - the ML pipeline for semantic diff.
"""

import numpy as np
import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import alignment methods
from alignment_methods import adaptive_hungarian


def compare_sentences(v1_sentences: list[str], v2_sentences: list[str]) -> dict:
    """
    Main pipeline: align and score sentence pairs using adaptive Hungarian.

    Uses adaptive_hungarian which:
    - Tries semantic_hungarian first (handles reordering, simple edits)
    - Falls back to greedy_with_merges if quality < 0.5 (handles merges/splits)
    - Normalizes output (converts merged/split to matched with raw_status)
    - Adds quality warning if overall_score < 0.3

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

    # Get embeddings for all sentences
    embeddings = _get_embeddings(v1_sentences + v2_sentences)

    # Use adaptive Hungarian alignment
    result = adaptive_hungarian(v1_sentences, v2_sentences, embeddings, quality_threshold=0.5)

    # Return just pairs and summary (remove internal fields)
    return {
        "pairs": result["pairs"],
        "summary": result["summary"],
        "warning": result.get("warning")  # Include warning if present
    }


def _get_embeddings(sentences: list[str]) -> np.ndarray:
    """
    Get embeddings for all sentences using OpenAI text-embedding-3-small.

    Requires: OPENAI_API_KEY in environment
    Cost: ~$0.00002 per 1000 tokens (very cheap)
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=sentences
    )

    embeddings = np.array([d.embedding for d in response.data])
    return embeddings


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
