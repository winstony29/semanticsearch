# Testing Patterns

**Analysis Date:** 2026-05-09

## Test Framework

**Runner:**
- pytest 8.3.3
- Config: `pytest.ini` at project root

**Assertion Library:**
- pytest built-in `assert`
- Common matchers: equality, `pytest.approx` for floats, `pytest.raises` for exceptions

**Run Commands:**
```bash
pytest                                    # Run all tests
pytest tests/test_pipeline.py             # Single file
pytest -k test_classify                   # Match by name
pytest -ra -q                             # (default per pytest.ini)
```

`pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
addopts = -ra -q
```

## Test File Organization

**Location:**
- All tests in `tests/` directory at project root (not co-located with source)

**Naming:**
- `test_<module>.py` — mirrors the source module name (e.g., `tests/test_scoring.py` mirrors `ml/scoring.py`)
- No filename distinction between unit, integration, regression — type inferred by content

**Structure:**
```
tests/
├── conftest.py                  # sys.path injection only (no shared fixtures)
├── test_classification.py       # unit, sync
├── test_scoring.py              # unit, sync
├── test_metrics.py              # unit, sync
├── test_mock_align.py           # unit, async
├── test_embeddings_retry.py     # regression, async, mocks AsyncOpenAI
└── test_pipeline.py             # integration, async, monkeypatched stages
```

## Test Structure

**Suite Organization:**
```python
# Class-based grouping by function
class TestClassifyPairs:
    def test_above_stable_is_unchanged(self):
        scored = [(_pair(0), STABLE_THRESHOLD + 0.01, 5.0)]
        kept, split = classify_pairs(scored)
        assert len(kept) == 1
        assert kept[0].classification == "unchanged"
        assert split == []

    def test_below_modified_is_split(self):
        ...
```

**Patterns:**
- Arrange-Act-Assert style
- Class-based grouping by function under test (`TestCosineToDrift`, `TestScorePair`, `TestClassifyPairs`)
- Module-level `_helper()` functions (e.g., `_pair(idx)`, `_unit()`, `_near(...)`) for fixture-style data
- Boundary cases tested explicitly ("at threshold", "above threshold", "below threshold")

## Mocking

**Frameworks:**
- `unittest.mock` (`MagicMock`, `patch`, `patch.object`)
- pytest's `monkeypatch` fixture (preferred for module-attribute replacement)

**Patterns:**

Module-attribute replacement via `monkeypatch` (preferred for async pipeline stubs — `tests/test_pipeline.py`):
```python
@pytest.fixture
def patched_pipeline(monkeypatch):
    async def fake_embed(alignment):
        return _build_realistic_embeddings()

    async def fake_concepts(before, after):
        return ConceptDiff(concepts=[]), "ok"

    monkeypatch.setattr(pipeline_mod, "embed_clauses", fake_embed)
    monkeypatch.setattr(pipeline_mod, "extract_concepts", fake_concepts)
```

Side-effect tracking with counter dicts (`tests/test_embeddings_retry.py`):
```python
attempts = {"n": 0}

async def failing_create(**kwargs):
    attempts["n"] += 1
    raise APIConnectionError(request=MagicMock())

fake_client = MagicMock()
fake_client.embeddings.create = failing_create

with patch.object(emb, "AsyncOpenAI", return_value=fake_client):
    with pytest.raises(APIConnectionError):
        await emb.embed_clauses(alignment)

assert attempts["n"] == 6   # tenacity retried 6 times
```

**What to mock:**
- OpenAI SDK clients (AsyncOpenAI)
- Async pipeline stages when running integration tests deterministically

**What NOT to mock:**
- Pure ML functions (scoring, classification, metrics) — tested directly
- Mock alignment (`ml/_mock_align.py`) — used as real input

## Fixtures and Factories

**`tests/conftest.py`:**
```python
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
```
Used solely to enable `from ml.pipeline import run_diff` and `from backend.models.schemas import ...` from the tests directory. **No shared pytest fixtures defined.**

**Factories:**
- Local `_helper()` functions inside each test module (e.g., `_pair()`, `_unit()`, `_near()`, `_build_realistic_embeddings()`)
- No shared factory module (note: `_build_mock_embeddings` is duplicated between `tests/test_pipeline.py` and `ml/demo.py` — see CONCERNS)

## Coverage

**Requirements:**
- No coverage target enforced
- No `.coveragerc` or `[tool.coverage]` config

**Configuration:**
- None

**View Coverage:**
- Not currently set up. Could run: `pip install pytest-cov && pytest --cov=ml --cov=backend`

## Test Types

**Unit (sync, pure):**
- `tests/test_scoring.py`, `tests/test_classification.py`, `tests/test_metrics.py`
- Test pure functions in isolation; no I/O, no mocks

**Unit (async):**
- `tests/test_mock_align.py`
- `@pytest.mark.asyncio` decorator (or `asyncio_mode = auto` lifts that requirement)

**Regression (mocked):**
- `tests/test_embeddings_retry.py`
- Mocks `AsyncOpenAI` to verify tenacity retry policy (6 attempts before re-raise)

**Integration:**
- `tests/test_pipeline.py`
- Drives `run_diff()` end-to-end with stubbed embedding + concept stages
- Validates full `DiffResponse` shape and classification correctness

**E2E / route:**
- None present (gap noted in CONCERNS — no `test_routes.py` for `/api/diff`)

## Common Patterns

**Async testing:**
```python
async def test_run_diff_assembles_full_response_shape(patched_pipeline):
    response = await run_diff(SAMPLE_BEFORE, SAMPLE_AFTER)
    assert isinstance(response, DiffResponse)
    assert [c.id for c in response.before_clauses] == ["b0", "b1", "b2", "b3", "b4"]
```

**Error testing:**
```python
with pytest.raises(APIConnectionError):
    await emb.embed_clauses(alignment)
```

**Snapshot testing:** Not used.

---

*Testing analysis: 2026-05-09*
*Update when test patterns change*
