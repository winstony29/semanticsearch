"""Smoke tests for the staged Winston adapter in backend/services/align.py.

The ``USE_REAL_ALIGN`` path is off by default. These tests force it on at
the module level and patch the OpenAI embedding call so they run offline.

Goal: when Winston's real algorithm lands, the adapter shape, sentence
split, and dict→AlignmentResult translation are already known to behave.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import backend.services.align as align_mod
import ml.embeddings as emb


def _fake_create_factory(dim: int = 8):
    """Return an async ``embeddings.create`` that produces deterministic
    pseudo-embeddings — distinct vectors per text, normalized downstream.
    """
    async def fake_create(**kwargs):
        texts = kwargs["input"]

        def vec_for(t: str) -> list[float]:
            # Simple deterministic embedding based on character codes.
            v = np.zeros(dim, dtype=np.float32)
            for i, ch in enumerate(t):
                v[i % dim] += (ord(ch) % 17) / 17.0
            # Bias the vectors a bit so identical text → identical vec.
            return v.tolist()

        data = [MagicMock(embedding=vec_for(t)) for t in texts]
        response = MagicMock()
        response.data = data
        return response

    return fake_create


@pytest.mark.asyncio
async def test_real_align_smoke_identical_text():
    """Identical input produces matched pairs (no unmatched sides)."""
    fake_client = MagicMock()
    fake_client.embeddings.create = _fake_create_factory()

    before = "Hello world. This is a test."
    after = "Hello world. This is a test."

    with patch.object(align_mod, "USE_REAL_ALIGN", True), \
         patch.object(emb, "AsyncOpenAI", return_value=fake_client):
        result = await align_mod.align(before, after)

    assert result.original_before == before
    assert result.original_after == after
    # Two sentences each side; identical → both should match.
    assert len(result.pairs) == 2
    assert result.unmatched_before == []
    assert result.unmatched_after == []
    # IDs follow the b{index} / a{index} contract.
    for p in result.pairs:
        assert p.before.id.startswith("b")
        assert p.after.id.startswith("a")


@pytest.mark.asyncio
async def test_real_align_handles_empty_sides():
    """Empty before → all v2 land in unmatched_after; vice versa."""
    fake_client = MagicMock()
    fake_client.embeddings.create = _fake_create_factory()

    with patch.object(align_mod, "USE_REAL_ALIGN", True), \
         patch.object(emb, "AsyncOpenAI", return_value=fake_client):
        # Note: DiffRequest enforces min_length=1 at the API boundary,
        # but align() itself must still degrade gracefully on a
        # whitespace-only side that splits to zero sentences.
        result = await align_mod.align("   ", "All new. Totally new.")

    assert result.pairs == []
    assert result.unmatched_before == []
    assert len(result.unmatched_after) == 2
    for c in result.unmatched_after:
        assert c.id.startswith("a")


@pytest.mark.asyncio
async def test_default_path_still_uses_mock():
    """USE_REAL_ALIGN flag defaults off → the mock is what runs."""
    # No patch on USE_REAL_ALIGN here; rely on the in-file default.
    # Mock alignment ignores its inputs, so any non-empty string works.
    result = await align_mod.align("anything", "ignored")
    # The mock's contract is documented in ml/_mock_align.py — it returns
    # at least one pair with the canned ids.
    assert (
        len(result.pairs) > 0
        or result.unmatched_before
        or result.unmatched_after
    )
