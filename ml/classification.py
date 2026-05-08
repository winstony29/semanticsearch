"""Step 3 — Classification.

Owner: Agent 2 (embed/score/classify).

Threshold-based classification of pairs and unmatched clauses, including the
post-Hungarian re-classify split for low-similarity pairs.
"""

from dataclasses import dataclass

from backend.models.schemas import AlignedPair, Classification, ClauseUnit
from ml.thresholds import STABLE_THRESHOLD, MODIFIED_THRESHOLD, REMOVED_THRESHOLD


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
) -> tuple[list[ClassifiedPair], list[ClassifiedClause]]:
    """Apply thresholds and the post-Hungarian split.

    Returns (kept_pairs, split_off_clauses) where split_off_clauses are
    created when similarity < REMOVED_THRESHOLD.
    """
    kept_pairs: list[ClassifiedPair] = []
    split_off_clauses: list[ClassifiedClause] = []

    for pair, sim, drift in scored:
        if sim >= STABLE_THRESHOLD:
            classification: Classification = "unchanged"
            kept_pairs.append(ClassifiedPair(pair, sim, drift, classification))
        elif sim >= MODIFIED_THRESHOLD:
            classification = "modified"
            kept_pairs.append(ClassifiedPair(pair, sim, drift, classification))
        else:  # sim < REMOVED_THRESHOLD
            # Split into "removed" and "added".
            split_off_clauses.append(
                ClassifiedClause(pair.before, "removed", 100.0)
            )
            split_off_clauses.append(
                ClassifiedClause(pair.after, "added", 100.0)
            )

    return kept_pairs, split_off_clauses


def classify_unmatched(
    unmatched_before: list[ClauseUnit],
    unmatched_after: list[ClauseUnit],
) -> list[ClassifiedClause]:
    """Classify unmatched clauses: before -> 'removed', after -> 'added'."""
    result: list[ClassifiedClause] = []
    for clause in unmatched_before:
        result.append(ClassifiedClause(clause, "removed", 100.0))
    for clause in unmatched_after:
        result.append(ClassifiedClause(clause, "added", 100.0))
    return result
