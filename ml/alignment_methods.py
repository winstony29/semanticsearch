"""
Multiple alignment approaches for semantic diff experiments.

Nickolas's concerns:
1. Lexical vs semantic similarity for Hungarian
2. Handling sentence merging (2→1) and splitting (1→2)
3. Re-evaluation when alignment quality is poor
4. Padding strategy for unequal counts
"""

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Tuple, Dict, Optional
import warnings


# ============================================================================
# METHOD 1: LEXICAL HUNGARIAN (TF-IDF)
# ============================================================================

def lexical_hungarian(v1_sentences: List[str], v2_sentences: List[str],
                      threshold: float = 0.3) -> Dict:
    """
    Hungarian alignment using TF-IDF lexical similarity.

    Pros: Fast, no API calls, works well for light edits
    Cons: Fails on heavy paraphrasing where words change but meaning stays same

    Args:
        threshold: Minimum similarity to consider a valid match
    """
    if not v1_sentences or not v2_sentences:
        return _handle_empty_case(v1_sentences, v2_sentences)

    # Compute TF-IDF vectors
    vectorizer = TfidfVectorizer()
    all_sents = v1_sentences + v2_sentences
    tfidf_matrix = vectorizer.fit_transform(all_sents)

    # Split back
    v1_vectors = tfidf_matrix[:len(v1_sentences)]
    v2_vectors = tfidf_matrix[len(v1_sentences):]

    # Compute similarity
    sim_matrix = cosine_similarity(v1_vectors, v2_vectors)

    # Run Hungarian
    pairs = _run_hungarian_with_threshold(
        sim_matrix, v1_sentences, v2_sentences, threshold, method="lexical"
    )

    return {
        "method": "lexical_hungarian",
        "pairs": pairs,
        "similarity_matrix": sim_matrix
    }


# ============================================================================
# METHOD 2: SEMANTIC HUNGARIAN (EMBEDDINGS)
# ============================================================================

def semantic_hungarian(v1_sentences: List[str], v2_sentences: List[str],
                       embeddings: np.ndarray, threshold: float = 0.6) -> Dict:
    """
    Hungarian alignment using semantic embeddings.

    Pros: Handles paraphrasing well, meaning-based matching
    Cons: Requires API call or local model, slower

    Args:
        embeddings: Pre-computed embeddings for v1_sentences + v2_sentences
        threshold: Minimum similarity to consider a valid match
    """
    if not v1_sentences or not v2_sentences:
        return _handle_empty_case(v1_sentences, v2_sentences)

    # Split embeddings
    emb_v1 = embeddings[:len(v1_sentences)]
    emb_v2 = embeddings[len(v1_sentences):]

    # Compute cosine similarity
    sim_matrix = cosine_similarity(emb_v1, emb_v2)

    # Run Hungarian
    pairs = _run_hungarian_with_threshold(
        sim_matrix, v1_sentences, v2_sentences, threshold, method="semantic"
    )

    return {
        "method": "semantic_hungarian",
        "pairs": pairs,
        "similarity_matrix": sim_matrix
    }


# ============================================================================
# METHOD 3: HYBRID (LEXICAL PRE-FILTER + SEMANTIC REFINEMENT)
# ============================================================================

def hybrid_hungarian(v1_sentences: List[str], v2_sentences: List[str],
                     embeddings: np.ndarray,
                     lexical_threshold: float = 0.2,
                     semantic_threshold: float = 0.6) -> Dict:
    """
    Two-stage approach:
    1. Fast lexical pre-filter to eliminate obviously unrelated pairs
    2. Semantic refinement on remaining candidates

    Pros: Faster than pure semantic, more accurate than pure lexical
    Cons: More complex, two thresholds to tune
    """
    if not v1_sentences or not v2_sentences:
        return _handle_empty_case(v1_sentences, v2_sentences)

    # Stage 1: Lexical pre-filter
    vectorizer = TfidfVectorizer()
    all_sents = v1_sentences + v2_sentences
    tfidf_matrix = vectorizer.fit_transform(all_sents)
    v1_tfidf = tfidf_matrix[:len(v1_sentences)]
    v2_tfidf = tfidf_matrix[len(v1_sentences):]
    lexical_sim = cosine_similarity(v1_tfidf, v2_tfidf)

    # Stage 2: Semantic similarity on candidates
    emb_v1 = embeddings[:len(v1_sentences)]
    emb_v2 = embeddings[len(v1_sentences):]
    semantic_sim = cosine_similarity(emb_v1, emb_v2)

    # Combine: use semantic similarity only where lexical similarity > threshold
    # Otherwise set to 0 to eliminate from consideration
    combined_sim = np.where(
        lexical_sim > lexical_threshold,
        semantic_sim,
        0.0
    )

    pairs = _run_hungarian_with_threshold(
        combined_sim, v1_sentences, v2_sentences, semantic_threshold, method="hybrid"
    )

    return {
        "method": "hybrid_hungarian",
        "pairs": pairs,
        "similarity_matrix": combined_sim,
        "lexical_matrix": lexical_sim,
        "semantic_matrix": semantic_sim
    }


# ============================================================================
# METHOD 4: GREEDY WITH MERGE DETECTION (HANDLES 2→1, 1→2)
# ============================================================================

def greedy_with_merges(v1_sentences: List[str], v2_sentences: List[str],
                       embeddings: np.ndarray,
                       match_threshold: float = 0.6,
                       merge_threshold: float = 0.5) -> Dict:
    """
    Greedy matching that allows many-to-one relationships.

    Algorithm:
    1. Find best match for each v2 sentence
    2. If multiple v2 sentences map to same v1 → potential merge
    3. If v1 sentence has low similarity to all v2 → potential split

    Pros: Handles merging and splitting
    Cons: Not optimal like Hungarian, order-dependent
    """
    if not v1_sentences or not v2_sentences:
        return _handle_empty_case(v1_sentences, v2_sentences)

    emb_v1 = embeddings[:len(v1_sentences)]
    emb_v2 = embeddings[len(v1_sentences):]
    sim_matrix = cosine_similarity(emb_v1, emb_v2)

    pairs = []
    v1_matched = set()
    v2_matched = set()

    # Phase 1: Greedy matching (highest similarities first)
    flat_indices = np.argsort(sim_matrix.ravel())[::-1]  # Descending

    for flat_idx in flat_indices:
        i = flat_idx // sim_matrix.shape[1]  # v1 index
        j = flat_idx % sim_matrix.shape[1]   # v2 index
        score = sim_matrix[i, j]

        if score < match_threshold:
            break  # Rest are below threshold

        # Check if this could be a merge (multiple v2 → same v1)
        if i in v1_matched and j not in v2_matched:
            # This v1 sentence already matched, but this v2 is unmatched
            # Check if it's a merge candidate
            if score >= merge_threshold:
                pairs.append({
                    "pair_id": f"merge_{len(pairs)}",
                    "v1_sentence": v1_sentences[i],
                    "v2_sentence": v2_sentences[j],
                    "v1_index": i,
                    "v2_index": j,
                    "similarity_score": float(score),
                    "status": "merged",
                    "note": "Multiple v2 sentences merged with same v1"
                })
                v2_matched.add(j)
            continue

        # Check if this could be a split (same v2 ← multiple v1)
        if j in v2_matched and i not in v1_matched:
            if score >= merge_threshold:
                pairs.append({
                    "pair_id": f"split_{len(pairs)}",
                    "v1_sentence": v1_sentences[i],
                    "v2_sentence": v2_sentences[j],
                    "v1_index": i,
                    "v2_index": j,
                    "similarity_score": float(score),
                    "status": "split",
                    "note": "v1 sentence split across multiple v2 sentences"
                })
                v1_matched.add(i)
            continue

        # Normal 1:1 match
        if i not in v1_matched and j not in v2_matched:
            pairs.append({
                "pair_id": f"pair_{len(pairs)}",
                "v1_sentence": v1_sentences[i],
                "v2_sentence": v2_sentences[j],
                "v1_index": i,
                "v2_index": j,
                "similarity_score": float(score),
                "status": "matched"
            })
            v1_matched.add(i)
            v2_matched.add(j)

    # Phase 2: Handle unmatched (additions/deletions)
    for j in range(len(v2_sentences)):
        if j not in v2_matched:
            pairs.append({
                "pair_id": f"add_{len(pairs)}",
                "v1_sentence": None,
                "v2_sentence": v2_sentences[j],
                "v1_index": None,
                "v2_index": j,
                "similarity_score": 0.0,
                "status": "added"
            })

    for i in range(len(v1_sentences)):
        if i not in v1_matched:
            pairs.append({
                "pair_id": f"del_{len(pairs)}",
                "v1_sentence": v1_sentences[i],
                "v2_sentence": None,
                "v1_index": i,
                "v2_index": None,
                "similarity_score": 0.0,
                "status": "deleted"
            })

    return {
        "method": "greedy_with_merges",
        "pairs": pairs,
        "similarity_matrix": sim_matrix
    }


# ============================================================================
# METHOD 5: ADAPTIVE (RE-EVALUATION WHEN QUALITY IS LOW)
# ============================================================================

def adaptive_hungarian(v1_sentences: List[str], v2_sentences: List[str],
                       embeddings: np.ndarray,
                       quality_threshold: float = 0.5) -> Dict:
    """
    Tries semantic Hungarian first, but if overall quality is low,
    falls back to greedy with merges (assumes heavy restructuring).

    Quality metric: mean of top-k matched pairs
    """
    # Try semantic Hungarian first
    result = semantic_hungarian(v1_sentences, v2_sentences, embeddings)

    # Evaluate quality
    matched_scores = [p["similarity_score"] for p in result["pairs"]
                     if p["status"] == "matched"]

    if not matched_scores:
        overall_quality = 0.0
    else:
        overall_quality = np.mean(matched_scores)

    # If quality is poor, try greedy with merges
    if overall_quality < quality_threshold:
        warnings.warn(
            f"Semantic Hungarian quality low ({overall_quality:.2f}). "
            f"Switching to greedy with merge detection."
        )
        result = greedy_with_merges(v1_sentences, v2_sentences, embeddings)
        result["fallback_used"] = True
        result["initial_quality"] = overall_quality
    else:
        result["fallback_used"] = False
        result["quality"] = overall_quality

    result["method"] = "adaptive_hungarian"
    return result


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _run_hungarian_with_threshold(sim_matrix: np.ndarray,
                                   v1_sentences: List[str],
                                   v2_sentences: List[str],
                                   threshold: float,
                                   method: str) -> List[Dict]:
    """
    Run Hungarian algorithm with padding and threshold filtering.
    """
    n, m = sim_matrix.shape
    cost_matrix = 1 - sim_matrix

    # Pad to square
    max_dim = max(n, m)
    padded_cost = np.full((max_dim, max_dim), 1.0)  # High cost for dummy matches
    padded_cost[:n, :m] = cost_matrix

    # Run Hungarian
    row_ind, col_ind = linear_sum_assignment(padded_cost)

    pairs = []
    pair_id = 0

    for i, j in zip(row_ind, col_ind):
        if i < n and j < m:
            # Real match
            score = sim_matrix[i, j]
            if score >= threshold:
                pairs.append({
                    "pair_id": f"pair_{pair_id:03d}",
                    "v1_sentence": v1_sentences[i],
                    "v2_sentence": v2_sentences[j],
                    "v1_index": i,
                    "v2_index": j,
                    "similarity_score": float(score),
                    "status": "matched"
                })
                pair_id += 1
            else:
                # Below threshold - treat as deletion + addition
                pairs.append({
                    "pair_id": f"del_{pair_id:03d}",
                    "v1_sentence": v1_sentences[i],
                    "v2_sentence": None,
                    "v1_index": i,
                    "v2_index": None,
                    "similarity_score": 0.0,
                    "status": "deleted"
                })
                pairs.append({
                    "pair_id": f"add_{pair_id:03d}",
                    "v1_sentence": None,
                    "v2_sentence": v2_sentences[j],
                    "v1_index": None,
                    "v2_index": j,
                    "similarity_score": 0.0,
                    "status": "added"
                })
                pair_id += 1

        elif i >= n:
            # Addition (v2 only)
            pairs.append({
                "pair_id": f"add_{pair_id:03d}",
                "v1_sentence": None,
                "v2_sentence": v2_sentences[j],
                "v1_index": None,
                "v2_index": j,
                "similarity_score": 0.0,
                "status": "added"
            })
            pair_id += 1

        elif j >= m:
            # Deletion (v1 only)
            pairs.append({
                "pair_id": f"del_{pair_id:03d}",
                "v1_sentence": v1_sentences[i],
                "v2_sentence": None,
                "v1_index": i,
                "v2_index": None,
                "similarity_score": 0.0,
                "status": "deleted"
            })
            pair_id += 1

    return pairs


def _handle_empty_case(v1_sentences: List[str], v2_sentences: List[str]) -> Dict:
    """Handle edge cases where one or both inputs are empty."""
    pairs = []

    if not v1_sentences and not v2_sentences:
        return {"pairs": [], "similarity_matrix": np.array([])}

    if not v1_sentences:
        pairs = [{
            "pair_id": f"add_{i}",
            "v1_sentence": None,
            "v2_sentence": sent,
            "v1_index": None,
            "v2_index": i,
            "similarity_score": 0.0,
            "status": "added"
        } for i, sent in enumerate(v2_sentences)]

    if not v2_sentences:
        pairs = [{
            "pair_id": f"del_{i}",
            "v1_sentence": sent,
            "v2_sentence": None,
            "v1_index": i,
            "v2_index": None,
            "similarity_score": 0.0,
            "status": "deleted"
        } for i, sent in enumerate(v1_sentences)]

    return {"pairs": pairs, "similarity_matrix": np.array([])}


# ============================================================================
# SUMMARY OF METHODS
# ============================================================================

METHODS = {
    "lexical": lexical_hungarian,
    "semantic": semantic_hungarian,
    "hybrid": hybrid_hungarian,
    "greedy_merge": greedy_with_merges,
    "adaptive": adaptive_hungarian
}

def get_method_info() -> Dict[str, str]:
    """Return information about each method."""
    return {
        "lexical": "TF-IDF + Hungarian. Fast, fails on heavy paraphrasing.",
        "semantic": "Embeddings + Hungarian. Handles paraphrasing, requires API.",
        "hybrid": "Lexical pre-filter + semantic refinement. Balanced speed/accuracy.",
        "greedy_merge": "Greedy matching with merge/split detection. Handles 2→1, 1→2.",
        "adaptive": "Tries semantic first, falls back to greedy if quality is low."
    }
