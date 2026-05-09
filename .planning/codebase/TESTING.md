# Testing Patterns

**Analysis Date:** 2026-05-09

## Test Framework

**Runner:**
- pytest 8.3.3 (`backend/requirements.txt`)
- pytest-asyncio 0.24.0
- Config: `pytest.ini` at repo root

**`pytest.ini` content:**
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
addopts = -ra -q
```

`asyncio_mode = auto` means `async def` test functions run without explicit `@pytest.mark.asyncio` (though some files still use it).

**Assertion library:**
- pytest built-in `assert` + `pytest.raises`

**Run commands:**
```bash
pytest                                # Run all tests in tests/
pytest -v                             # Verbose
pytest tests/test_classification.py   # Single file
pytest -k "test_above_stable"        # Filter by name
```

No watch mode, no coverage flag configured by default.

## Test File Organization

**Location:** `tests/` directory only (per `pytest.ini` `testpaths = tests`)

**Naming:** `test_<module>.py` mirrors source file naming
- `tests/test_align_adapter.py` — `backend/services/align.py`
- `tests/test_classification.py` — `ml/classification.py`
- `tests/test_embeddings_retry.py` — `ml/embeddings.py`
- `tests/test_metrics.py` — `ml/metrics.py`
- `tests/test_mock_align.py` — `ml/_mock_align.py`
- `tests/test_pipeline.py` — `ml/pipeline.py`
- `tests/test_scoring.py` — `ml/scoring.py`

**Structure:**
```
tests/
├── conftest.py                  # sys.path setup; no fixtures
├── test_align_adapter.py
├── test_classification.py
├── test_embeddings_retry.py
├── test_metrics.py
├── test_mock_align.py
├── test_pipeline.py
└── test_scoring.py
```

## Test Structure

**Suite organization:** Class-based grouping (`Test<Subject>`) with method-level tests:

```python
# tests/test_classification.py
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
- One-class-per-subject grouping
- Method names describe the boundary or property under test
- Inline arrange/act/assert with comments only when boundary intent isn't obvious
- No `beforeEach`-style fixtures — each test self-contained

## Mocking

**Framework:** `unittest.mock` (`MagicMock`, `patch`, `patch.object`) combined with pytest-asyncio

**Patterns:**
```python
# tests/test_align_adapter.py — patching the AsyncOpenAI client
@pytest.mark.asyncio
async def test_real_align_smoke_identical_text():
    fake_client = MagicMock()
    fake_client.embeddings.create = _fake_create_factory()
    with patch.object(align_mod, "USE_REAL_ALIGN", True), \
         patch.object(emb, "AsyncOpenAI", return_value=fake_client):
        result = await align_mod.align(before, after)
```

**Helper factories** (defined in test files, not shared fixtures):
- `_fake_create_factory()` — fake OpenAI client (`tests/test_align_adapter.py`)
- `_pair(idx)`, `_br(...)`, `_pr(...)` — small test data builders

**What gets mocked:**
- `AsyncOpenAI` client (embeddings + chat completions)
- The `USE_REAL_ALIGN` flag in `backend/services/align.py`
- Specific module attributes via `patch.object`

**What does NOT get mocked:**
- Pure compute functions (cosine, drift remap, classification thresholds)
- Pydantic schema validation

## Fixtures and Factories

**No `@pytest.fixture` decorators detected** — tests inline-create their data via helper functions in each file.

**`tests/conftest.py`:** minimal — only adjusts `sys.path` so `backend.*` and `ml.*` imports resolve.

**Special:** `ml/test_cases.py` is **not** a pytest module — it's a fixture corpus
- 12 hand-built edge cases under `TEST_CASES: dict`
- Helpers: `get_test_case()`, `get_all_test_cases()`, `get_test_cases_by_difficulty()`, `print_test_case_summary()`
- Cherry-picked from `origin/main` for threshold-tuning experiments
- Not collected by pytest because `pytest.ini` restricts to `tests/`

## Coverage

**Not configured.** No `--cov` flag, no `.coveragerc`, no coverage tool in `requirements.txt`. Coverage tracked only manually if at all.

## Test Types Present

**Unit tests (majority):**
- `tests/test_classification.py` — boundary tests for `classify_pairs()` / `classify_unmatched()`
- `tests/test_metrics.py` — `aggregate_metrics()` counting + weighting + edge cases
- `tests/test_scoring.py` — cosine + drift remap pure compute

**Integration / smoke tests:**
- `tests/test_align_adapter.py` — Winston adapter end-to-end with mocked OpenAI
- `tests/test_mock_align.py` — mock alignment shape contract
- `tests/test_pipeline.py` — `run_diff()` wired with mocks

**Regression tests:**
- `tests/test_embeddings_retry.py` — verifies tenacity retry fires on `APIConnectionError`

**E2E:** None against the live FastAPI server; closest substitute is `ml/demo.py` for manual integration runs.

## Common Patterns

**Async tests:**
```python
@pytest.mark.asyncio
async def test_real_align_smoke_identical_text():
    result = await align_mod.align(before, after)
    assert result.pairs[0].before_clause.text == ...
```
(Decorator is technically optional under `asyncio_mode = auto`, but kept for clarity in some files.)

**Error testing:**
```python
with pytest.raises(APIConnectionError):
    await emb.embed_clauses(alignment)
```

**Retry attempt tracking:**
```python
attempts = {"n": 0}
async def failing_create(**kwargs):
    attempts["n"] += 1
    raise APIConnectionError(...)
```

**Boundary testing:** Tests deliberately probe at-threshold values (`STABLE_THRESHOLD`, `STABLE_THRESHOLD + 0.01`, `STABLE_THRESHOLD - 0.01`) to lock down classification behavior.

**Parametrize:** Not used. Multiple boundary tests are written as separate methods.

**Snapshot:** Not used.

---

*Testing analysis: 2026-05-09*
*Update when test patterns change*
