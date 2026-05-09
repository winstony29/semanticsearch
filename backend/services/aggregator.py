"""
Score aggregation from clause-level to sentence-level.

Takes clause-level pairs from the ML pipeline and aggregates scores back to sentence level.
"""

from collections import defaultdict


def aggregate_clause_scores_to_sentences(
    clause_pairs: list[dict],
    v1_clause_to_sentence: list[int],
    v2_clause_to_sentence: list[int],
    v1_sentences: list[str],
    v2_sentences: list[str],
) -> list[dict]:
    """
    Takes clause-level pairs from the ML pipeline and aggregates
    scores back to sentence level.

    For each sentence pair, the sentence score = mean of its clause scores.

    Args:
        clause_pairs: List of clause-level pair dicts from ML pipeline
        v1_clause_to_sentence: Mapping from v1 clause index to sentence index
        v2_clause_to_sentence: Mapping from v2 clause index to sentence index
        v1_sentences: Original v1 sentences before clause splitting
        v2_sentences: Original v2 sentences before clause splitting

    Returns:
        List of sentence-level pair dicts with aggregated scores
    """
    # Group clause scores by (v1_sentence_idx, v2_sentence_idx)
    sentence_pair_scores = defaultdict(list)

    matched_v1_sentences = set()
    matched_v2_sentences = set()

    for pair in clause_pairs:
        if pair["status"] == "matched":
            v1_ci = pair["v1_index"]
            v2_ci = pair["v2_index"]
            if v1_ci is not None and v2_ci is not None:
                v1_si = v1_clause_to_sentence[v1_ci]
                v2_si = v2_clause_to_sentence[v2_ci]
                sentence_pair_scores[(v1_si, v2_si)].append(pair["similarity_score"])
                matched_v1_sentences.add(v1_si)
                matched_v2_sentences.add(v2_si)

    # Build sentence-level pairs
    result = []
    pair_counter = 0

    # Matched sentence pairs
    for (v1_si, v2_si), scores in sentence_pair_scores.items():
        avg_score = sum(scores) / len(scores)
        if avg_score >= 0.85:
            severity = "green"
        elif avg_score >= 0.60:
            severity = "yellow"
        else:
            severity = "red"

        result.append({
            "pair_id": f"pair_{pair_counter:03d}",
            "v1_sentence": v1_sentences[v1_si],
            "v2_sentence": v2_sentences[v2_si],
            "v1_index": v1_si,
            "v2_index": v2_si,
            "similarity_score": round(avg_score, 4),
            "status": "matched",
            "severity": severity,
            "explanation": None,
        })
        pair_counter += 1

    # Deleted sentences (v1 sentences with no match)
    for v1_si, sentence in enumerate(v1_sentences):
        if v1_si not in matched_v1_sentences:
            result.append({
                "pair_id": f"del_{pair_counter:03d}",
                "v1_sentence": sentence,
                "v2_sentence": None,
                "v1_index": v1_si,
                "v2_index": None,
                "similarity_score": 0.0,
                "status": "deleted",
                "severity": "deleted",
                "explanation": None,
            })
            pair_counter += 1

    # Added sentences (v2 sentences with no match)
    for v2_si, sentence in enumerate(v2_sentences):
        if v2_si not in matched_v2_sentences:
            result.append({
                "pair_id": f"add_{pair_counter:03d}",
                "v1_sentence": None,
                "v2_sentence": sentence,
                "v1_index": None,
                "v2_index": v2_si,
                "similarity_score": 0.0,
                "status": "added",
                "severity": "added",
                "explanation": None,
            })
            pair_counter += 1

    return result
