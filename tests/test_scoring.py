"""Unit tests for ml.scoring."""

import numpy as np
import pytest

from backend.models.schemas import AlignedPair, ClauseUnit
from ml.scoring import cosine_to_drift, score_pair, score_pairs


class TestCosineToDrift:
    def test_identical_is_zero_drift(self):
        assert cosine_to_drift(1.0) == 0.0

    def test_floor_is_full_drift(self):
        assert cosine_to_drift(0.5) == 100.0

    def test_midpoint(self):
        assert cosine_to_drift(0.75) == 50.0

    def test_clamps_above_ceiling(self):
        # FP overshoot — must not produce negative drift.
        assert cosine_to_drift(1.0000001) == 0.0
        assert cosine_to_drift(2.0) == 0.0

    def test_clamps_below_floor(self):
        assert cosine_to_drift(0.0) == 100.0
        assert cosine_to_drift(-1.0) == 100.0

    def test_rounded_to_two_decimals(self):
        result = cosine_to_drift(0.93)
        # (1 - 0.93) / 0.5 * 100 = 14.0
        assert result == pytest.approx(14.0, abs=0.01)


class TestScorePair:
    def test_identical_unit_vectors(self):
        v = np.array([1.0, 0.0, 0.0])
        assert score_pair(v, v) == pytest.approx(1.0)

    def test_orthogonal_unit_vectors(self):
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        assert score_pair(a, b) == pytest.approx(0.0)

    def test_clamps_above_one(self):
        # Construct vectors whose raw dot product exceeds 1 due to FP.
        a = np.array([1.0 + 1e-10, 0.0])
        result = score_pair(a, a)
        assert result <= 1.0

    def test_clamps_below_neg_one(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        assert score_pair(a, b) == pytest.approx(-1.0)


class TestScorePairs:
    def test_returns_tuple_per_pair(self):
        pairs = [
            AlignedPair(
                before=ClauseUnit(id="b0", text="x"),
                after=ClauseUnit(id="a0", text="y"),
            ),
        ]
        v = np.array([1.0, 0.0])
        embeddings = {"b0": v, "a0": v}
        result = score_pairs(pairs, embeddings)
        assert len(result) == 1
        pair, sim, drift = result[0]
        assert pair is pairs[0]
        assert sim == pytest.approx(1.0)
        assert drift == 0.0

    def test_preserves_order(self):
        pairs = [
            AlignedPair(
                before=ClauseUnit(id=f"b{i}", text=""),
                after=ClauseUnit(id=f"a{i}", text=""),
            )
            for i in range(3)
        ]
        embeddings = {pid: np.array([1.0, 0.0]) for p in pairs for pid in (p.before.id, p.after.id)}
        result = score_pairs(pairs, embeddings)
        assert [r[0].before.id for r in result] == ["b0", "b1", "b2"]
