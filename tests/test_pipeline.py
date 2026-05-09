"""Integration test for ml.pipeline.run_diff with mocked OpenAI calls.

This is the smoke we used to run inline; promoted to a real test so anyone
on the branch can reproduce it.
"""

import numpy as np
import pytest

import ml.pipeline as pipeline_mod
from backend.models.schemas import ConceptDiff
from ml._mock_align import SAMPLE_AFTER, SAMPLE_BEFORE


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def _near(v: np.ndarray, eps: float, rng: np.random.Generator) -> np.ndarray:
    """Unit vector with ~sqrt(1-eps^2) cosine similarity to v."""
    perp = _unit(rng.standard_normal(v.shape).astype("float32"))
    perp = _unit(perp - perp.dot(v) * v)
    return _unit(np.sqrt(max(0.0, 1.0 - eps * eps)) * v + eps * perp)


def _build_realistic_embeddings():
    """Hand-built embeddings producing similarities that match the mock's
    expected classification per pair.
    """
    rng = np.random.default_rng(7)
    base = _unit(rng.standard_normal(1536).astype("float32"))

    emb = {
        "b0": base,
        "a0": _near(base, 0.24, rng),  # ~0.97 sim → unchanged
        "b1": _unit(rng.standard_normal(1536).astype("float32")),
        "b2": _unit(rng.standard_normal(1536).astype("float32")),
        "b3": _unit(rng.standard_normal(1536).astype("float32")),
        "b4": _unit(rng.standard_normal(1536).astype("float32")),
    }
    emb["a1"] = _near(emb["b1"], 0.62, rng)  # ~0.78 → modified
    emb["a2"] = emb["b2"].copy()             # 1.00 → unchanged (verbatim)
    emb["a3"] = _near(emb["b3"], 0.95, rng)  # ~0.31 → split
    emb["a4"] = _unit(rng.standard_normal(1536).astype("float32"))
    return emb


@pytest.fixture
def patched_pipeline(monkeypatch):
    """Replace embed_clauses and extract_concepts with deterministic stubs."""
    embeddings = _build_realistic_embeddings()

    async def fake_embed(alignment):
        return embeddings

    async def fake_concepts(before, after):
        return ConceptDiff(summary="", concepts=[]), "ok"

    monkeypatch.setattr(pipeline_mod, "embed_clauses", fake_embed)
    monkeypatch.setattr(pipeline_mod, "extract_concepts", fake_concepts)


@pytest.mark.asyncio
async def test_run_diff_assembles_full_response_shape(patched_pipeline):
    result = await pipeline_mod.run_diff(SAMPLE_BEFORE, SAMPLE_AFTER)

    # Five clauses on each side: 4 paired + 1 unmatched per side (one of
    # the paired pairs splits into removed+added).
    assert len(result.before_clauses) == 5
    assert len(result.after_clauses) == 5
    assert sorted(c.id for c in result.before_clauses) == ["b0", "b1", "b2", "b3", "b4"]
    assert sorted(c.id for c in result.after_clauses) == ["a0", "a1", "a2", "a3", "a4"]


@pytest.mark.asyncio
async def test_run_diff_classifications_match_expected(patched_pipeline):
    result = await pipeline_mod.run_diff(SAMPLE_BEFORE, SAMPLE_AFTER)

    cls_b = {c.id: c.classification for c in result.before_clauses}
    cls_a = {c.id: c.classification for c in result.after_clauses}

    # Two unchanged (paraphrase + verbatim), one modified, one split, two unmatched.
    assert cls_b["b0"] == "unchanged" and cls_a["a0"] == "unchanged"
    assert cls_b["b1"] == "modified" and cls_a["a1"] == "modified"
    assert cls_b["b2"] == "unchanged" and cls_a["a2"] == "unchanged"
    assert cls_b["b3"] == "removed" and cls_a["a3"] == "added"
    assert cls_b["b4"] == "removed"
    assert cls_a["a4"] == "added"


@pytest.mark.asyncio
async def test_run_diff_pairs_excludes_split(patched_pipeline):
    result = await pipeline_mod.run_diff(SAMPLE_BEFORE, SAMPLE_AFTER)
    # The bogus b3<->a3 pair must not appear in pair_renderings.
    pair_ids = {(p.before_id, p.after_id) for p in result.pairs}
    assert pair_ids == {("b0", "a0"), ("b1", "a1"), ("b2", "a2")}


@pytest.mark.asyncio
async def test_run_diff_summary_counts(patched_pipeline):
    result = await pipeline_mod.run_diff(SAMPLE_BEFORE, SAMPLE_AFTER)
    s = result.summary
    assert s.before_count == 5
    assert s.after_count == 5
    assert s.unchanged == 2
    assert s.modified == 1
    assert s.added == 2
    assert s.removed == 2


@pytest.mark.asyncio
async def test_run_diff_concept_failure_doesnt_break(monkeypatch):
    """If extract_concepts raises, the pipeline must still return a response."""
    monkeypatch.setattr(
        pipeline_mod, "embed_clauses",
        lambda *_a, **_k: _async_value(_build_realistic_embeddings()),
    )

    async def boom(*_a, **_kw):
        raise RuntimeError("simulated LLM failure")

    monkeypatch.setattr(pipeline_mod, "extract_concepts", boom)

    result = await pipeline_mod.run_diff(SAMPLE_BEFORE, SAMPLE_AFTER)
    assert result.concept_extraction == "failed"
    assert result.concepts == []


async def _async_value(v):
    return v
