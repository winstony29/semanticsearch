"""Unit tests for ml.metrics."""

import pytest

from backend.models.schemas import ClauseRendering, PairRendering
from ml.metrics import aggregate_metrics


def _br(id_: str, text: str, classification: str, drift: float, paired_with=None) -> ClauseRendering:
    return ClauseRendering(
        id=id_, text=text, classification=classification,
        drift_score=drift, paired_with=paired_with,
    )


def _pr(b: str, a: str, sim: float, drift: float, classification: str) -> PairRendering:
    return PairRendering(
        before_id=b, after_id=a, similarity=sim,
        drift_score=drift, classification=classification,
    )


class TestAggregateMetrics:
    def test_counts_by_classification(self):
        before = [
            _br("b0", "x", "unchanged", 0.0, "a0"),
            _br("b1", "y", "modified", 50.0, "a1"),
            _br("b2", "z", "removed", 100.0),
        ]
        after = [
            _br("a0", "x", "unchanged", 0.0, "b0"),
            _br("a1", "y'", "modified", 50.0, "b1"),
            _br("a2", "new", "added", 100.0),
        ]
        pairs = [
            _pr("b0", "a0", 1.0, 0.0, "unchanged"),
            _pr("b1", "a1", 0.75, 50.0, "modified"),
        ]
        s = aggregate_metrics(before, after, pairs, "x y z", "x y' new", elapsed_ms=42)
        assert s.before_count == 3
        assert s.after_count == 3
        assert s.unchanged == 1
        assert s.modified == 1
        assert s.added == 1
        assert s.removed == 1
        assert s.elapsed_ms == 42

    def test_overall_drift_is_length_weighted(self):
        # Longer pair (drift 100) should dominate over shorter pair (drift 0).
        long_text = "x" * 100
        short_text = "y"
        before = [
            _br("b0", short_text, "unchanged", 0.0, "a0"),
            _br("b1", long_text, "modified", 100.0, "a1"),
        ]
        after = [
            _br("a0", short_text, "unchanged", 0.0, "b0"),
            _br("a1", long_text, "modified", 100.0, "b1"),
        ]
        pairs = [
            _pr("b0", "a0", 1.0, 0.0, "unchanged"),
            _pr("b1", "a1", 0.5, 100.0, "modified"),
        ]
        s = aggregate_metrics(before, after, pairs, "", "", elapsed_ms=1)
        # Unweighted mean would be 50.0; length-weighted should be much
        # closer to 100 since the long pair dominates.
        assert s.overall_drift > 95.0

    def test_pct_text_edited_levenshtein(self):
        # Identical strings -> 0%
        s = aggregate_metrics([], [], [], "hello world", "hello world", elapsed_ms=0)
        assert s.pct_text_edited == 0.0

    def test_pct_text_edited_full_replace(self):
        s = aggregate_metrics([], [], [], "abcd", "wxyz", elapsed_ms=0)
        assert s.pct_text_edited == 100.0

    def test_pct_text_edited_ignores_whitespace_reformatting(self):
        # Same content; only whitespace differs (newlines, indentation,
        # collapsed double-spaces). Should read as 0% edit.
        before = "Hello world. This is a test."
        after = "  Hello   world.\n\n\tThis is a test.  "
        s = aggregate_metrics([], [], [], before, after, elapsed_ms=0)
        assert s.pct_text_edited == 0.0

    def test_pct_text_edited_real_edit_still_counted(self):
        # Whitespace differs AND a word changes. Edit should still register
        # — only the whitespace noise gets stripped.
        before = "Hello world. This is a test."
        after = "Hello\nworld. That  is a test."
        s = aggregate_metrics([], [], [], before, after, elapsed_ms=0)
        assert s.pct_text_edited > 0.0
        # Sanity bound: 4-char swap ("This"→"That") on a ~28-char string
        # should be well under 50%.
        assert s.pct_text_edited < 50.0

    def test_pct_meaning_edited_aliases_overall_drift(self):
        before = [_br("b0", "x", "modified", 30.0, "a0")]
        after = [_br("a0", "y", "modified", 30.0, "b0")]
        pairs = [_pr("b0", "a0", 0.85, 30.0, "modified")]
        s = aggregate_metrics(before, after, pairs, "abc", "abd", elapsed_ms=0)
        assert s.pct_meaning_edited == s.overall_drift

    def test_no_pairs_no_clauses(self):
        # All-empty inputs default to 100.0 drift per the doc's "everything
        # is added/removed" framing.
        s = aggregate_metrics([], [], [], "", "", elapsed_ms=0)
        assert s.overall_drift == 100.0
        assert s.pct_text_edited == 0.0  # no chars to edit

    def test_clamps_to_zero_hundred(self):
        # Edge case: ensure the clamp explicitly applies
        s = aggregate_metrics([], [], [], "hi", "hello world this is much longer", elapsed_ms=0)
        assert 0.0 <= s.pct_text_edited <= 100.0

    def test_default_models_in_summary(self):
        s = aggregate_metrics([], [], [], "x", "x", elapsed_ms=0)
        assert s.embedding_model == "text-embedding-3-small"
        assert s.chat_model == "gpt-4o-mini"
        assert s.alignment == "hungarian"
