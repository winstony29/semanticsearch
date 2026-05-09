"""Verify the tenacity retry on embed_clauses actually fires.

This is a regression guard for the bug where ``retry=lambda exc: ...`` was
treated by tenacity as a RetryCallState predicate, never matched, and
therefore never retried.
"""

from unittest.mock import MagicMock, patch

import pytest
from openai import APIConnectionError

import ml.embeddings as emb
from ml._mock_align import mock_align


@pytest.mark.asyncio
async def test_retries_on_api_connection_error_then_reraises():
    attempts = {"n": 0}

    async def failing_create(**kwargs):
        attempts["n"] += 1
        raise APIConnectionError(request=MagicMock())

    fake_client = MagicMock()
    fake_client.embeddings.create = failing_create

    alignment = await mock_align("x", "y")

    with patch.object(emb, "AsyncOpenAI", return_value=fake_client):
        with pytest.raises(APIConnectionError):
            await emb.embed_clauses(alignment)

    # tenacity stop_after_attempt(6) → exactly 6 calls before reraise.
    assert attempts["n"] == 6


@pytest.mark.asyncio
async def test_no_retry_on_non_retryable_exception():
    """A plain ValueError is not in the retryable tuple — should fire once."""
    attempts = {"n": 0}

    async def fail_once(**kwargs):
        attempts["n"] += 1
        raise ValueError("not retryable")

    fake_client = MagicMock()
    fake_client.embeddings.create = fail_once

    alignment = await mock_align("x", "y")

    with patch.object(emb, "AsyncOpenAI", return_value=fake_client):
        with pytest.raises(ValueError):
            await emb.embed_clauses(alignment)

    assert attempts["n"] == 1
