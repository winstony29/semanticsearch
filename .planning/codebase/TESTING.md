# Testing Patterns

**Analysis Date:** 2026-05-09 (post-merge of `origin/main`)

## Test Framework

**Runner:**
- pytest 8.3.3 + pytest-asyncio 0.24.0
- Config: `pytest.ini` (root)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
addopts = -ra -q
```

`asyncio_mode = auto` lets `async def` test functions run without explicit decoration; some files still use `@pytest.mark.asyncio` for clarity.

**Assertion library:** pytest built-in `assert` + `pytest.raises`

**Run commands:**
```bash
pytest                                # All tests under tests/
pytest -v                             # Verbose
pytest tests/test_classification.py   # Single file
pytest -k "above_stable"             # Filter by name
```

No watch mode, no coverage flag configured.

## Test File Organization

**pytest-collected (`tests/`):**
- `tests/conftest.py` — `sys.path` setup; no `@pytest.fixture`-decorated fixtures
- `tests/test_align_adapter.py` — Winston adapter (`backend/services/align.py`) with mocked OpenAI
- `tests/test_classification.py` — `ml/classification.py` boundary tests
- `tests/test_embeddings_retry.py` — tenacity retry behavior
- `tests/test_metrics.py` — `aggregate_metrics()` counts and weighting
- `tests/test_mock_align.py` — `ml/_mock_align.py` shape contract
- `tests/test_pipeline.py` — `ml/pipeline.py::run_diff()` with mocked deps
- `tests/test_scoring.py` — cosine + drift remap

**Standalone scripts (NOT collected by pytest — outside `testpaths`):**
- `test_alignment.py` (root) — manual alignment runner
- `test_all_alignments.py` (root) — alignment method comparison (uses real OpenAI; needs `OPENAI_API_KEY`)
- `ml/quick_test.py`, `ml/run_experiments.py`, `ml/visual_demo.py`, `ml/demo_alignment_comparison.py` — runnable demos with `if __name__ == "__main__"` entry points

**Fixture corpus (NOT a pytest module):**
- `ml/test_cases.py` — 12 hand-built edge cases under `TEST_CASES: dict`; helpers `get_test_case`, `get_all_test_cases`, `get_test_cases_by_difficulty`. Lower-case `test_*` name is incidental; not collected because `pytest.ini` restricts to `tests/`.

## Suite Organization

Class-based grouping with `Test<Subject>` and method-level tests. Example from `tests/test_classification.py`:

```python
class TestClassifyPairs:
    def test_above_stable_is_unchanged(self):
        scored = [(_pair(0), STABLE_THRESHOLD + 0.01, 5.0)]
        kept, split = classify_pairs(scored)
        assert len(kept) == 1
        assert kept[0].classification == "unchanged"
        assert split == []

    def test_at_stable_is_unchanged(self):
        scored = [(_pair(0), STABLE_THRESHOLD, 14.0)]
        kept, split = classify_pairs(scored)
        assert kept[0].classification == "unchanged"

    def test_between_thresholds_is_modified(self):
        sim = (STABLE_THRESHOLD + MODIFIED_THRESHOLD) / 2
        scored = [(_pair(0), sim, 50.0)]
        kept, split = classify_pairs(scored)
        assert kept[0].classification == "modified"
```

**Patterns:**
- One class per subject
- Method names describe the boundary or property under test
- Inline arrange/act/assert
- No setup/teardown helpers — each test is self-contained

## Mocking

**Framework:** `unittest.mock` (`MagicMock`, `patch`, `patch.object`) + `monkeypatch` from pytest, combined with pytest-asyncio.

**Patterns:**

```python
# tests/test_align_adapter.py — patching AsyncOpenAI
@pytest.mark.asyncio
async def test_real_align_smoke_identical_text():
    fake_client = MagicMock()
    fake_client.embeddings.create = _fake_create_factory()
    with patch.object(align_mod, "USE_REAL_ALIGN", True), \
         patch.object(emb, "AsyncOpenAI", return_value=fake_client):
        result = await align_mod.align(before, after)
```

```python
# tests/test_pipeline.py — monkeypatch with @pytest.fixture
@pytest.fixture
def patched_pipeline(monkeypatch):
    embeddings = _build_realistic_embeddings()
    async def fake_embed(alignment):
        return embeddings
    monkeypatch.setattr(pipeline_mod, "embed_clauses", fake_embed)
```

**What gets mocked:**
- `AsyncOpenAI` (embeddings + chat completions)
- `USE_REAL_ALIGN` flag
- `embed_clauses`, `extract_concepts` (via monkeypatch)

**What does NOT get mocked:**
- Pure compute (cosine, drift remap, classification thresholds)
- Pydantic schemas

## Fixtures and Factories

- `tests/test_pipeline.py` defines a `@pytest.fixture` for the patched pipeline (only fixture in the suite)
- Inline factory helpers per file: `_pair()`, `_br()`, `_pr()`, `_fake_create_factory()`, `_build_realistic_embeddings()`
- Deterministic RNG seeding: `rng = np.random.default_rng(7)`
- `tests/conftest.py` is minimal — `sys.path` setup only

## Coverage

- Not configured. No `pytest-cov`, no `.coveragerc`, no `--cov` flag
- No CI to enforce coverage

## Test Types Present

- **Unit:** `test_classification.py`, `test_metrics.py`, `test_scoring.py`
- **Smoke / integration with mocks:** `test_align_adapter.py`, `test_mock_align.py`, `test_pipeline.py`
- **Regression:** `test_embeddings_retry.py` (tenacity retry on `APIConnectionError`)
- **E2E against live FastAPI server:** none
- **Standalone runners (out-of-band):** `test_alignment.py`, `test_all_alignments.py`, `ml/quick_test.py`, `ml/visual_demo.py`, `ml/run_experiments.py`, `ml/demo_alignment_comparison.py`

## Common Patterns

**Async tests:**
```python
@pytest.mark.asyncio
async def test_real_align_smoke_identical_text():
    result = await align_mod.align(before, after)
```

**Error testing:**
```python
with pytest.raises(APIConnectionError):
    await emb.embed_clauses(alignment)
```

**Retry-attempt counting:**
```python
attempts = {"n": 0}
async def failing_create(**kwargs):
    attempts["n"] += 1
    raise APIConnectionError(...)
```

**Boundary testing:** Tests deliberately probe exact threshold values (`STABLE_THRESHOLD`, `STABLE_THRESHOLD + 0.01`, etc.).

**Parametrize / Snapshot:** Not used.

## Status Discrepancy: TESTING_REPORT.md vs. reality

`TESTING_REPORT.md` reports things like "100% (4/4) passed" and "Core Functionality Coverage: 75%". Those numbers refer to **manual runs of standalone scripts** (`test_alignment.py`, `ml/quick_test.py`, etc.), not the pytest suite.

Actual pytest collection picks up only the 7 files under `tests/`. The standalone scripts at the repo root and under `ml/` are intentionally outside `testpaths`. The fixture corpus `ml/test_cases.py` exists but no test currently asserts against it.

If a real coverage signal is needed, the gap to close is:
- No live OpenAI integration test in pytest
- No `/compare` or `/api/diff` endpoint test against the FastAPI app
- Threshold-tuning corpus (`ml/test_cases.py`) is not wired into a regression test

---

*Testing analysis: 2026-05-09*
*Update when test patterns change*
