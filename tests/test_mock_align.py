"""Unit tests for ml._mock_align."""

import pytest

from ml._mock_align import SAMPLE_AFTER, SAMPLE_BEFORE, mock_align


@pytest.mark.asyncio
async def test_returns_alignment_result_with_expected_counts():
    result = await mock_align(SAMPLE_BEFORE, SAMPLE_AFTER)
    assert len(result.pairs) == 4
    assert len(result.unmatched_before) == 1
    assert len(result.unmatched_after) == 1


@pytest.mark.asyncio
async def test_clause_ids_are_unique_and_namespaced():
    result = await mock_align("", "")
    before_ids = (
        [p.before.id for p in result.pairs]
        + [c.id for c in result.unmatched_before]
    )
    after_ids = (
        [p.after.id for p in result.pairs]
        + [c.id for c in result.unmatched_after]
    )
    assert len(before_ids) == len(set(before_ids)), "duplicate before ids"
    assert len(after_ids) == len(set(after_ids)), "duplicate after ids"
    assert all(bid.startswith("b") for bid in before_ids)
    assert all(aid.startswith("a") for aid in after_ids)


@pytest.mark.asyncio
async def test_originals_default_to_samples_when_inputs_empty():
    result = await mock_align("", "")
    assert result.original_before == SAMPLE_BEFORE
    assert result.original_after == SAMPLE_AFTER


@pytest.mark.asyncio
async def test_originals_passthrough_when_provided():
    result = await mock_align("custom before", "custom after")
    assert result.original_before == "custom before"
    assert result.original_after == "custom after"
