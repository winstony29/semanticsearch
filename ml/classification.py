"""Step 3 — Classification.

Owner: Agent 2 (embed/score/classify).

Threshold-based classification of pairs and unmatched clauses, including the
optional post-Hungarian re-classify split for low-similarity pairs.
"""

from dataclasses import dataclass

from backend.models.schemas import AlignedPair, Classification, ClauseUnit
from ml.thresholds import (
    FULL_DRIFT,
    MODIFIED_THRESHOLD,
    REMOVED_THRESHOLD,
    STABLE_THRESHOLD,
)


@dataclass
class ClassifiedPair:
    """A pair with its final classification after all checks."""

    pair: AlignedPair
    similarity: float
    drift_score: float
    classification: Classification


@dataclass
class ClassifiedClause:
    """A single classified clause (from a pair or unmatched)."""

    clause: ClauseUnit
    classification: Classification
    drift_score: float


def classify_pairs(
    scored: list[tuple[AlignedPair, float, float]],
    *,
    split_below_threshold: bool = True,
) -> tuple[list[ClassifiedPair], list[ClassifiedClause]]:
    """Apply thresholds and (optionally) the post-Hungarian split.

    Args:
        scored: ``(pair, similarity, drift_score)`` tuples from
            ``score_pairs``.
        split_below_threshold: When True (default), pairs with similarity
            below ``REMOVED_THRESHOLD`` are split into a ``removed`` clause
            (before) plus an ``added`` clause (after) and dropped from the
            kept pairs. Set to False when the upstream alignment step has
            already pre-pruned low-similarity pairs (e.g. Winston's
            ``_run_hungarian_with_threshold`` with a ``match_threshold``);
            otherwise the same pairs would be pruned twice.

    Returns:
        ``(kept_pairs, split_off_clauses)``. ``split_off_clauses`` is empty
        when ``split_below_threshold`` is False or when no pairs fell below
        ``REMOVED_THRESHOLD``.
    """
    kept_pairs: list[ClassifiedPair] = []
    split_off_clauses: list[ClassifiedClause] = []

    for pair, sim, drift in scored:
        if sim >= STABLE_THRESHOLD:
            kept_pairs.append(ClassifiedPair(pair, sim, drift, "unchanged"))
        elif sim >= MODIFIED_THRESHOLD:
            kept_pairs.append(ClassifiedPair(pair, sim, drift, "modified"))
        elif split_below_threshold:
            # Hungarian was forced into a bad pair. Treat both sides as
            # standalone clauses.
            split_off_clauses.append(
                ClassifiedClause(pair.before, "removed", FULL_DRIFT)
            )
            split_off_clauses.append(
                ClassifiedClause(pair.after, "added", FULL_DRIFT)
            )
        else:
            # Trust upstream pre-prune — keep the pair as "modified".
            kept_pairs.append(ClassifiedPair(pair, sim, drift, "modified"))

    return kept_pairs, split_off_clauses


def classify_unmatched(
    unmatched_before: list[ClauseUnit],
    unmatched_after: list[ClauseUnit],
) -> list[ClassifiedClause]:
    """Classify unmatched clauses: before -> 'removed', after -> 'added'."""
    result: list[ClassifiedClause] = []
    for clause in unmatched_before:
        result.append(ClassifiedClause(clause, "removed", FULL_DRIFT))
    for clause in unmatched_after:
        result.append(ClassifiedClause(clause, "added", FULL_DRIFT))
    return result
