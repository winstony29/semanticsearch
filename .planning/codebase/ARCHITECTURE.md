# Architecture

**Analysis Date:** 2026-05-09

## Pattern Overview

**Overall:** Layered FastAPI backend with an async ML pipeline as the core domain. Two coexisting contract flows: legacy `/compare` (sentence-based, mocked) and new `/api/diff` (clause-based, Hungarian-aligned).

**Key Characteristics:**
- Stateless request handling (no DB, no per-request cache)
- ML pipeline is async + embarrassingly parallel (`asyncio.gather` for embeddings + concept extraction)
- Locked data contract in Pydantic schemas, shared across layers
- All tunable constants centralized in one file (`ml/thresholds.py`)

## Layers

**API Layer:**
- Purpose: HTTP entry, CORS, validation, status codes
- Contains: FastAPI app + route handlers
- Files: `backend/main.py`, `backend/routes/diff.py`, `backend/routes/compare.py`, `backend/routes/explanation.py`
- Depends on: Schema layer, service layer, ML pipeline
- Used by: Frontend, external clients

**Schema / Contract Layer:**
- Purpose: Single source of truth for all cross-layer data shapes
- Contains: Pydantic models — `DiffRequest`, `DiffResponse`, `AlignmentResult`, `ClauseUnit`, `AlignedPair`, `ClauseRendering`, `Concept`, `DiffSummary`, `Classification` literal
- Files: `backend/models/schemas.py`
- Depends on: pydantic
- Used by: every other layer

**Service Layer (backend):**
- Purpose: Bridge between routes and ML pipeline; legacy mock fallbacks
- Contains:
  - `backend/services/align.py` — alignment seam (currently delegates to `ml/_mock_align.py`)
  - `backend/services/ml_client.py` — legacy mock wrapper for `/compare`
  - `backend/services/tokenizer.py` — spaCy sentence split + naive fallback (legacy)
- Depends on: schemas, ml modules
- Used by: routes, pipeline

**ML Slice (`ml/`):**
- Purpose: Embeddings → scoring → classification → metrics + concept extraction
- Files (numbered per pipeline step):
  - Step 1: `ml/embeddings.py` — AsyncOpenAI batch embed + L2 normalize, tenacity retry
  - Step 2: `ml/scoring.py` — cosine similarity (`np.dot` on unit vectors) + `cosine_to_drift()` 0–100 remap
  - Step 3: `ml/classification.py` — threshold-based unchanged/modified/added/removed labelling, splits low-similarity pairs
  - Step 4: `ml/metrics.py` — aggregates `DiffSummary` (counts, length-weighted overall_drift, Levenshtein `pct_text_edited`)
  - Step 5: `ml/concepts.py` — `gpt-4o-mini` structured output (`ConceptDiff`); best-effort, returns empty + `"failed"` on error
  - Step 6: `ml/pipeline.py` — `run_diff(before, after)` orchestrator
- Depends on: schemas, alignment service, OpenAI SDK, numpy, Levenshtein
- Used by: route handlers via `ml.pipeline.run_diff`

**Configuration:**
- Single source of truth: `ml/thresholds.py` (STABLE_THRESHOLD=0.93, MODIFIED_THRESHOLD=0.65, REMOVED_THRESHOLD=0.65, EMBEDDING_MODEL, CHAT_MODEL, FULL_DRIFT=100.0, MAX_CONCEPT_INPUT_CHARS=60_000)

## Data Flow

**POST /api/diff request lifecycle:**

1. Client posts `{before, after}` to `/api/diff` (`backend/routes/diff.py`)
2. Pydantic validates `DiffRequest` (each side ≤ 20_000 chars, ≥ 1)
3. Handler calls `ml.pipeline.run_diff(before, after)`
4. Pipeline calls `align()` (sync) → `AlignmentResult{pairs, unmatched_before, unmatched_after, originals}`
5. `asyncio.gather` runs in parallel:
   - Path A — `embed_clauses(alignment)` → `score_pairs()` → `classify_pairs()` → `classify_unmatched()`
   - Path B — `extract_concepts(before, after)` → `ConceptDiff` (graceful empty on failure)
6. Pipeline assembles `before_clauses`, `after_clauses`, `pair_renderings`
7. `aggregate_metrics()` produces `DiffSummary` (timed via `time.perf_counter`)
8. Returns `DiffResponse{before_clauses, after_clauses, pairs, summary, concepts, status}`

**State Management:**
- Stateless — every request rebuilds everything from input text
- No persistent storage; legacy `/compare` keeps an in-memory `explanation_store` dict (not used by `/api/diff`)

## Key Abstractions

**ClauseUnit:**
- Purpose: Atomic unit of text analysis (may span multiple sentences)
- Examples: `backend/models/schemas.py` — `id` is `b{n}` for before, `a{n}` for after
- Pattern: Immutable dataclass-like Pydantic model

**AlignedPair / AlignmentResult:**
- Purpose: Represents the Hungarian alignment between two documents
- Examples: `backend/models/schemas.py`
- Pattern: Structural separation — matched pairs vs `unmatched_before` / `unmatched_after`

**ClassifiedPair:**
- Purpose: AlignedPair + similarity + drift score + `Classification` literal
- Examples: `ml/classification.py`
- Pattern: Tagged result (function pure, no I/O)

**Concept / ConceptDiff:**
- Purpose: Named themes/obligations changing between versions
- Examples: `backend/models/schemas.py`, `ml/concepts.py`
- Pattern: LLM structured output via OpenAI `chat.completions.parse`

**DiffResponse:**
- Purpose: Final response payload
- Examples: `backend/models/schemas.py`
- Pattern: Locked schema; frontend types mirror it

## Entry Points

**HTTP:**
- Location: `backend/main.py` (FastAPI app + CORS + router includes)
- Triggers: `uvicorn backend.main:app`
- Responsibilities: env-var warnings on boot, mount `/`, `/health`, `/compare`, `/api/diff`, `/explanation/{id}`

**Pipeline:**
- Location: `ml/pipeline.py:run_diff()`
- Triggers: route handler call OR CLI demo
- Responsibilities: orchestrate align → embed/concepts → classify → metrics → assemble

**CLI Demo:**
- Location: `ml/demo.py`
- Triggers: `python -m ml.demo` with optional `--mock`, `--before`, `--after`
- Responsibilities: deterministic offline validation; monkey-patches embeddings + concepts when `--mock` set

## Error Handling

**Strategy:** Graceful degradation in ML slice, generic 500 at HTTP boundary.

**Patterns:**
- `ml/embeddings.py` — tenacity decorator, raises after 6 failed attempts
- `ml/concepts.py` — broad try/except, logs to stderr, returns empty `ConceptDiff` + `status="failed"` (never breaks pipeline)
- `backend/routes/diff.py:14-20` — try/except around `run_diff`, raises `HTTPException(500, detail=...)`
- `backend/main.py:21-30` — env-var warnings at boot (does NOT block startup)

## Cross-Cutting Concerns

**Logging:**
- `print(..., file=sys.stderr)` only; no `logging` module use

**Validation:**
- Pydantic on request boundary (DiffRequest length bounds)
- Defensive clamps inside ML (`max(-1.0, min(1.0, sim))` in scoring)
- Empty/whitespace clauses replaced with single space before OpenAI call

**Concurrency:**
- `AsyncOpenAI` clients
- `asyncio.gather(embed_task, concept_task)` for embarrassingly parallel ML work

**CORS:**
- Permissive by default (`allow_methods=["*"]`, `allow_headers=["*"]`); origin list from `CORS_ORIGINS` env

---

*Architecture analysis: 2026-05-09*
*Update when major patterns change*
