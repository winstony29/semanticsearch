# Coding Conventions

**Analysis Date:** 2026-05-09

## Naming Patterns

**Files:**
- `snake_case.py` for all Python modules (e.g., `ml/embeddings.py`, `backend/services/align.py`)
- `_underscore_prefix.py` for dev-only/internal modules (e.g., `ml/_mock_align.py`)
- `test_<module>.py` for tests, mirroring source module name

**Functions:**
- `snake_case` (e.g., `run_diff`, `embed_clauses`, `cosine_to_drift`, `classify_pairs`)
- Underscore-prefixed for module-private helpers (`_build_before_clauses`, `_unit`, `_near`, `_pair`)

**Variables:**
- `snake_case` for locals
- `UPPER_SNAKE_CASE` for module constants (`STABLE_THRESHOLD`, `EMBEDDING_MODEL`, `FULL_DRIFT`)

**Types:**
- `PascalCase` for Pydantic models and dataclasses (`AlignedPair`, `ClassifiedPair`, `DiffResponse`, `ClauseUnit`)
- `PascalCase` for `Literal` type aliases (`Classification`, `ConceptStatus`)

**Identifiers (domain-specific):**
- Clause IDs: `b{n}` for before, `a{n}` for after (assumed throughout pipeline)

## Code Style

**Formatting:**
- 4-space indentation (PEP 8)
- Double quotes for strings (consistent across codebase)
- Modern type hints: lowercase generics (`list[X]`, `dict[str, Y]`, `tuple[...]`) — no `List`/`Dict` from `typing`
- Approx. 80–100 char line length (no enforced cap)

**Linting:**
- No linter config detected (`ruff`, `flake8`, `black`, `isort` all absent)
- Relies on implicit PEP 8 + comprehensive type hints
- No `pyproject.toml` defining tool config

## Import Organization

**Order (PEP 8 style):**
1. stdlib (`import asyncio`, `import time`, `import sys`)
2. third-party (`from openai import AsyncOpenAI`, `import numpy as np`)
3. local (`from backend.models.schemas import ...`, `from ml.thresholds import ...`)

**Grouping:** Blank line between groups; alphabetical within group.

**Path aliases:** None — use full absolute imports (e.g., `from ml.pipeline import run_diff`, not `from .pipeline import ...`). This requires the `sys.path` injection in `backend/main.py` and `tests/conftest.py`.

## Error Handling

**Patterns:**
- Broad `try/except Exception as exc:` at integration boundaries (see `ml/concepts.py:88-92`, `backend/routes/diff.py:14-20`)
- Graceful degradation in ML slice — return empty result + status flag rather than propagate
- HTTP boundary raises `HTTPException(500, detail=...) from exc`
- Tenacity decorator for retryable transients in `ml/embeddings.py`
- Defensive clamps on numeric outputs (`max(-1.0, min(1.0, sim))` in `ml/scoring.py`)

**Error types:**
- Standard library exceptions; no custom Error subclasses defined
- OpenAI SDK exceptions (`RateLimitError`, `APIConnectionError`, `APIStatusError`) explicitly enumerated in retry config

## Logging

**Framework:**
- None — `print(..., file=sys.stderr)` only
- Examples: `ml/concepts.py:80-92`, `backend/main.py:21-30`, `backend/routes/diff.py:20`

**Patterns:**
- Stderr-only, unstructured
- No correlation IDs, no levels
- Mostly silent on success; emits only on warnings/errors

## Comments & Docstrings

**Module docstrings:**
- Present on all `ml/*.py` modules; describe pipeline step + ownership note (e.g., "Owner: Agent 2 (embed/score/classify)")
- Reference architecture spec sections (e.g., "per ML_ARCHITECTURE.md §1")

**Function docstrings:**
- Google-style multi-line docstrings on public functions
- Pure functions get short docstrings; orchestrators get numbered procedural descriptions

**Inline comments:**
- Used to clarify non-obvious logic (e.g., "Weights by combined character length of both sides")
- Sparse and high-signal

**TODO comments:**
- Present (e.g., `backend/main.py:24` Anthropic stub, `backend/routes/compare.py:168` LLM-explanation stub)
- No formal `TODO(username):` convention

## Function Design

**Size:** Generally 10–50 lines; pure ML functions stay small.

**Parameters:** Type-hinted; small parameter lists (≤4) typical. No object-bag pattern observed.

**Return values:**
- Explicit returns
- Multiple-return tuples used (e.g., `classify_pairs` returns `(kept, split)`)
- Pydantic models for cross-boundary returns

**Async:** `async def` only where I/O-bound (`embed_clauses`, `extract_concepts`, `run_diff`); pure helpers stay sync.

**Pure-function bias:** ML scoring/classification/metrics are pure (no I/O, no mutation of inputs).

## Module Design

**Exports:**
- No explicit `__all__`
- Modules expose top-level functions/classes by import path (no barrel re-exports)
- `ml/__init__.py` and `backend/models/__init__.py` are docstring-only

**Internal vs public:**
- Underscore prefix marks private (`_mock_align.py`, `_build_before_clauses`)
- Public API is everything else

**Circular dependency avoidance:**
- `ml/` and `backend/services/` both import from `backend/models/schemas.py` (one-way dependency on schemas)
- `backend/services/align.py` imports `ml/_mock_align`, but `ml/` does not import from `backend/services/`

---

*Convention analysis: 2026-05-09*
*Update when patterns change*
