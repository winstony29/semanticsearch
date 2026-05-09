"""Unit tests for ml.classification."""

import pytest

from backend.models.schemas import AlignedPair, ClauseUnit
from ml.classification import (
    ClassifiedClause,
    ClassifiedPair,
    classify_pairs,
    classify_unmatched,
)
from ml.thresholds import (
    FULL_DRIFT,
    MODIFIED_THRESHOLD,
    REMOVED_THRESHOLD,
    STABLE_THRESHOLD,
)


def _pair(idx: int) -> AlignedPair:
    return AlignedPair(
        before=ClauseUnit(id=f"b{idx}", text=f"before {idx}"),
        after=ClauseUnit(id=f"a{idx}", text=f"after {idx}"),
    )


class TestClassifyPairs:
    def test_above_stable_is_unchanged(self):
        scored = [(_pair(0), STABLE_THRESHOLD + 0.01, 5.0)]
        kept, split = classify_pairs(scored)
        assert len(kept) == 1
        assert kept[0].classification == "unchanged"
        assert split == []

    def test_at_stable_is_unchanged(self):
        # Boundary: >= STABLE_THRESHOLD
        scored = [(_pair(0), STABLE_THRESHOLD, 14.0)]
        kept, split = classify_pairs(scored)
        assert kept[0].classification == "unchanged"

    def test_between_thresholds_is_modified(self):
        sim = (STABLE_THRESHOLD + MODIFIED_THRESHOLD) / 2
        scored = [(_pair(0), sim, 50.0)]
        kept, split = classify_pairs(scored)
        assert kept[0].classification == "modified"
        assert split == []

    def test_below_removed_splits_by_default(self):
        scored = [(_pair(0), REMOVED_THRESHOLD - 0.1, 100.0)]
        kept, split = classify_pairs(scored)
        assert kept == []
        assert len(split) == 2
        before, after = split
        assert before.classification == "removed"
        assert before.clause.id == "b0"
        assert before.drift_score == FULL_DRIFT
        assert after.classification == "added"
        assert after.clause.id == "a0"

    def test_below_removed_kept_as_modified_when_flag_off(self):
        # When the upstream alignment has already pre-pruned, our split
        # would be a double-prune. Flag opts out.
        scored = [(_pair(0), REMOVED_THRESHOLD - 0.1, 100.0)]
        kept, split = classify_pairs(scored, split_below_threshold=False)
        assert len(kept) == 1
        assert kept[0].classification == "modified"
        assert split == []

    def test_mixed_input(self):
        scored = [
            (_pair(0), 0.99, 2.0),  # unchanged
            (_pair(1), 0.78, 44.0),  # modified
            (_pair(2), 0.30, 100.0),  # split
        ]
        kept, split = classify_pairs(scored)
        assert len(kept) == 2
        assert {c.classification for c in kept} == {"unchanged", "modified"}
        assert len(split) == 2  # one removed + one added from the bogus pair

    def test_drift_score_passed_through(self):
        scored = [(_pair(0), 0.78, 43.99)]
        kept, _ = classify_pairs(scored)
        assert kept[0].drift_score == 43.99


class TestClassifyUnmatched:
    def test_unmatched_before_becomes_removed(self):
        clauses = [ClauseUnit(id="b9", text="orphan")]
        result = classify_unmatched(clauses, [])
        assert len(result) == 1
        assert result[0].classification == "removed"
        assert result[0].drift_score == FULL_DRIFT

    def test_unmatched_after_becomes_added(self):
        clauses = [ClauseUnit(id="a9", text="orphan")]
        result = classify_unmatched([], clauses)
        assert result[0].classification == "added"

    def test_both_sides(self):
        before = [ClauseUnit(id="b9", text="x")]
        after = [ClauseUnit(id="a9", text="y")]
        result = classify_unmatched(before, after)
        assert [r.classification for r in result] == ["removed", "added"]

    def test_empty(self):
        assert classify_unmatched([], []) == []
