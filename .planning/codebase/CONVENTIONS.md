# Coding Conventions

**Analysis Date:** 2026-05-09 (post-merge of `origin/main`)

## Naming Patterns

**Files:**
- snake_case for Python — `ml_client.py`, `alignment_methods.py`, `smith_waterman_alignment.py`
- Underscore prefix for private/vendored modules — `_mock_align.py`, `_align_impl.py`
- `test_*.py` for pytest files (under `tests/`); same prefix at root for standalone scripts
- PascalCase `.tsx` for React components — `DiffViewer.tsx`, `InputPanel.tsx`
- kebab-case `.md` for cross-team notes — `integration-with-winston.md`

**Functions / Variables:**
- snake_case throughout (`tokenize_text`, `embed_clauses`, `score_pair`, `classify_pairs`, `aggregate_metrics`)
- Async I/O = `async def`, no special prefix

**Classes / Pydantic models:**
- PascalCase: `CompareRequest`, `DiffResponse`, `ClauseUnit`, `AlignmentResult`, `ClassifiedPair`, `SmithWatermanAligner`, `TokenizedResult`

**Constants:**
- UPPER_SNAKE_CASE: `STABLE_THRESHOLD`, `EMBEDDING_MODEL`, `MAX_CONCEPT_INPUT_CHARS`, `USE_REAL_ALIGN`, `WTPSPLIT_AVAILABLE`, `CLAUSE_SPLIT_WORD_THRESHOLD`
- Underscore prefix for module-private (`_RETRYABLE_OPENAI_ERRORS`, `_PROJECT_ROOT`, `_model`)

**Types:**
- Modern PEP 585 generics: `list[str]`, `dict[str, np.ndarray]` (Python 3.10+)
- `Literal[...]` for closed string sets (`Classification`, `ConceptStatus`)
- `Optional[T]` for nullable
- Some merged code uses legacy `typing.List`/`Dict` (e.g., portions of `alignment_methods.py`) — minor inconsistency with the rest of the codebase

## Code Style

**Formatting:**
- 4-space indentation throughout
- Double quotes for strings and docstrings
- Line length: ~80–100 chars (no formatter config detected)
- No semicolons (Python)
- Type hints on virtually every function signature

**Linting / Formatting:**
- No `pyproject.toml [tool.ruff/black]`, `.flake8`, or `.pre-commit-config.yaml` detected
- Conventions enforced by review

## Import Organization

**Order (observed):**
1. Standard library (`os`, `sys`, `asyncio`, `pathlib.Path`)
2. Third-party (`fastapi`, `pydantic`, `numpy`, `openai`, `tenacity`, `scipy`, `sklearn`)
3. Local — both styles in use:
   - Absolute: `from backend.models.schemas import ...`, `from ml.embeddings import ...`
   - Relative-ish: `from models.schemas import ...`, `from services.tokenizer import ...` (works because `backend/main.py` and `tests/conftest.py` adjust `sys.path`)

**Grouping:** blank line between groups (informal, not enforced)

**Path manipulation:**
- `backend/services/ml_client.py` does `sys.path.insert(0, 'ml')` for sibling imports
- `tests/conftest.py` adds project root to `sys.path` so absolute imports work

**Path Aliases:** None

## Error Handling

- **Defensive retry at boundaries:** tenacity in `ml/embeddings.py` (6 attempts, exp. backoff, retryable on `(RateLimitError, APIConnectionError, APIStatusError)`)
- **Graceful degradation in best-effort steps:** `ml/concepts.py` and `ml/pipeline.py` catch `Exception` → `ConceptDiff(status="failed")`
- **Empty-input defense:** `embed_clauses()` substitutes `" "` for empty strings to avoid OpenAI 400s
- **Numerical clamping:** Cosine clamped to `[-1.0, 1.0]` (`ml/scoring.py`)
- **Graceful tokenizer fallback:** wtpsplit → spaCy → regex via guarded imports
- **Route-level catch:** `backend/routes/diff.py` wraps `run_diff()` → `HTTPException(500)`
- **Result-style returns in alignment methods:** `ml/alignment_methods.py` returns `dict` shapes rather than raising

**Custom errors:** None defined — relies on stdlib `Exception` and FastAPI `HTTPException`

## Logging

- No `logging` module configured anywhere
- Warnings via `print(..., file=sys.stderr)` — `backend/main.py` (env warnings), `backend/services/tokenizer.py` (fallback warnings), `ml/concepts.py` (extraction failures), `ml/demo.py`
- Section dividers in some merged files (e.g., `=====` headers in `ml/alignment_methods.py`)
- No structured logging, no request IDs, no per-step timing

## Comments / Docstrings

**Module docstrings:** Every module has a top-level docstring. Many ML modules call out their step number and "Owner" (e.g., `"""Step 1 — Embeddings. Owner: Agent 2..."""`).

**Function docstrings:** Google-style with `Args:` / `Returns:` / `Notes:` sections. Example from `ml/alignment_methods.py`:

```python
def semantic_hungarian(v1_sentences: List[str], v2_sentences: List[str],
                       embeddings: np.ndarray, threshold: float = 0.6) -> Dict:
    """Hungarian alignment using semantic embeddings.

    Pros: Handles paraphrasing well, meaning-based matching
    Cons: Requires API call or local model, slower

    Args:
        embeddings: Pre-computed embeddings for v1_sentences + v2_sentences
        threshold: Minimum similarity to consider a valid match
    """
```

**Pydantic field descriptions:** Heavy use of `Field(..., description="...")` in `backend/models/schemas.py`

**Inline comments:** Sparing; explain *why* not *what* (e.g., `# Bias the vectors a bit so identical text → identical vec.`)

**TODO comments:** plain `# TODO: ...`, no username convention. Active TODOs in `backend/main.py` (health checks), `backend/routes/compare.py` (async explanation generation), `backend/services/ml_client.py` (legacy stub).

## Function Design

- Compact (10–50 lines); helpers extracted aggressively
- Tight, function-specific parameters; rarely > 3 args
- Explicit, typed returns; tuples for multi-return (`(pair, sim, drift)`)
- Async split: I/O-bound `async def`, pure compute sync

## Module Design

- `backend/models/schemas.py` is the single source of truth for DTOs (legacy + new)
- `ml/thresholds.py` is the single source of truth for tunables
- `__init__.py` files are minimal/empty — no barrel re-exports
- Service abstraction in `backend/services/` houses seams (alignment, tokenizer, aggregator); ML slice imports from it
- ML pipeline split: each step in its own module (`embeddings.py`, `scoring.py`, …); `pipeline.py` orchestrates

## Divergences Introduced by the Merge

- Mixed type-hint styles: most code uses PEP 585 (`list[str]`); some merged code uses `typing.List`/`Dict`. Minor.
- Section divider comments (`=====`) only appear in merged files
- Standalone runnable scripts (`test_alignment.py`, `test_all_alignments.py`, `ml/quick_test.py`, `ml/run_experiments.py`, `ml/visual_demo.py`, `ml/demo_alignment_comparison.py`) use `test_*` / `*_test*` prefixes by convention but are not pytest tests — they have `if __name__ == "__main__":` entry points and live outside `testpaths = tests`

---

*Convention analysis: 2026-05-09*
*Update when patterns change*
