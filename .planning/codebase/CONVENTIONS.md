# Coding Conventions

**Analysis Date:** 2026-05-09

## Naming Patterns

**Files:**
- snake_case for Python (`ml_client.py`, `test_cases.py`)
- Underscore-prefixed for internal/private modules (`_mock_align.py`, `_align_impl.py`)
- PascalCase `.tsx` for React components (`DiffViewer.tsx`, `InputPanel.tsx`)
- kebab-case `.md` for cross-team notes (`integration-with-winston.md`)

**Functions / Variables:**
- snake_case throughout (`tokenize_text`, `embed_clauses`, `score_pair`, `cosine_to_drift`, `classify_pairs`)
- Async I/O-bound functions use `async def` (no special prefix)

**Classes / Pydantic models:**
- PascalCase: `CompareRequest`, `DiffResponse`, `ClauseUnit`, `AlignmentResult`, `ClassifiedPair`

**Constants:**
- UPPER_SNAKE_CASE (`STABLE_THRESHOLD`, `EMBEDDING_MODEL`, `MAX_CONCEPT_INPUT_CHARS`, `USE_REAL_ALIGN`)
- Underscore-prefixed for module-private constants (`_RETRYABLE_OPENAI_ERRORS`, `_PROJECT_ROOT`)

**Types:**
- `Literal[...]` for closed-set string types (`Classification`, `ConceptStatus`)
- Modern Python 3.10+ generics: `list[str]`, `dict[str, np.ndarray]` (not `List` / `Dict`)
- `Optional[T]` for nullable

## Code Style

**Formatting:**
- 4-space indentation
- Double quotes for strings and docstrings
- Line length: ~80–88 chars (no formatter config detected — likely Black-compatible by convention)
- No semicolons (Python)
- Type hints on virtually every function signature

**Linting / Formatting tools:**
- No `pyproject.toml [tool.ruff/black]`, `.flake8`, or `.pre-commit-config.yaml` detected
- Conventions enforced manually / by review

## Import Organization

**Order (observed):**
1. Standard library (`os`, `sys`, `asyncio`, `pathlib.Path`)
2. Third-party (`fastapi`, `pydantic`, `numpy`, `openai`, `tenacity`)
3. Local — both styles in use:
   - Absolute: `from backend.models.schemas import ...`, `from ml.embeddings import ...`
   - Relative-ish: `from models.schemas import ...`, `from services.tokenizer import ...` (works because `backend/main.py` and `tests/conftest.py` adjust `sys.path`)

**Grouping:**
- Blank line between groups (informal)
- No automated import sorting tool detected

**Path Aliases:**
- None — `sys.path` manipulation in `backend/main.py` and `tests/conftest.py` enables both module styles

## Error Handling

**Patterns:**
- **Defensive retry at boundaries:** `ml/embeddings.py` wraps OpenAI calls with `@retry()` (tenacity), 6 attempts, exponential backoff, retryable on `(RateLimitError, APIConnectionError, APIStatusError)`
- **Graceful degradation for best-effort steps:** `ml/concepts.py` and `ml/pipeline.py` catch `Exception` and return `ConceptDiff(status="failed")` so the pipeline finishes
- **Empty-input defense:** `embed_clauses()` substitutes `" "` for empty strings to avoid OpenAI 400s
- **Numerical clamping:** Cosine clamped to `[-1.0, 1.0]` via `min/max` (`ml/scoring.py`)
- **Manual fallback in tokenizer:** spaCy → naive regex split (`backend/services/tokenizer.py`); uses bare `except:` (flagged in CONCERNS.md)
- **Route-level catch:** `backend/routes/diff.py` wraps `run_diff()` in `try/except Exception` → `HTTPException(500)`

**Custom errors:**
- None defined — relies on stdlib `Exception` and `HTTPException` from FastAPI

## Logging

**Framework:**
- No `logging` module configured
- `print(..., file=sys.stderr)` for warnings and best-effort failure messages
- Locations: `backend/main.py` (env var warnings), `backend/services/tokenizer.py` (spaCy fallback warning), `ml/concepts.py` (concept extraction failure), `ml/demo.py`

**Patterns:**
- Unstructured stderr writes only — no JSON logging, request IDs, or timing

## Comments / Docstrings

**Module-level docstrings:**
- Every module has a top docstring describing its role and owner where relevant. Examples:
  - `ml/embeddings.py` — `"""Step 1 — Embeddings. Owner: Agent 2..."""`
  - `ml/scoring.py` — `"""Step 2 — Scoring..."""`

**Function docstrings:**
- Google-style: `Args:`, `Returns:`, `Notes:` sections. Example from `backend/services/tokenizer.py`:
  ```python
  def tokenize_text(text: str) -> list[str]:
      """
      Split text into sentences.

      Args:
          text: Input text to tokenize

      Returns:
          List of sentence strings, whitespace stripped, empty strings removed
      """
  ```

**Pydantic field descriptions:**
- Heavy use of `Field(..., description="...")` on schema fields in `backend/models/schemas.py`

**Inline comments:**
- Sparing — primarily for non-obvious intent (e.g., backwards-compat aliases in `ml/scoring.py`)

**TODO comments:**
- Plain `# TODO: ...` (no username convention)
- Examples in `backend/main.py` (`/health` checks), `backend/services/ml_client.py` (legacy stub)

## Function Design

**Size:** Mostly compact, 10–50 lines; helpers extracted aggressively
**Parameters:** Tight, function-specific (`score_pair(a, b)`); rarely exceed 3 args
**Return values:** Explicit and typed; tuples used for multi-return (`(pair, sim, drift)`)
**Async split:** I/O-bound = `async def` (`embed_clauses`, `extract_concepts`, `align`); pure compute = sync (`score_pairs`, `classify_pairs`, `aggregate_metrics`)

## Module Design

**Schema location:** `backend/models/schemas.py` is the single source of truth for DTOs — both legacy and new contracts
**Threshold location:** `ml/thresholds.py` is the single source of truth for tunables
**Barrel files:** `__init__.py` files are minimal/empty — no re-exports; consumers import directly from leaf modules
**Service abstraction:** `backend/services/` contains seams (alignment dispatcher, tokenizer); ML slice (`ml/`) imports from it
**ML pipeline split:** Each step lives in its own module (`embeddings.py`, `scoring.py`, ...); `pipeline.py` orchestrates

---

*Convention analysis: 2026-05-09*
*Update when patterns change*
