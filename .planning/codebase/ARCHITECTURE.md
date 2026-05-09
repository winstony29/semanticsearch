# Architecture

**Analysis Date:** 2026-05-09

## Pattern Overview

**Overall:** Layered async pipeline for semantic document comparison — FastAPI backend + React/TypeScript frontend, with a clean ML slice (`ml/`) sitting behind a backend-owned alignment seam.

**Key Characteristics:**
- Async-first ML pipeline: `asyncio.gather()` parallelizes embeddings + concept extraction (`ml/pipeline.py`)
- Staged integration seam: mock alignment (`ml/_mock_align.py`) is swappable for real Hungarian algorithm (`backend/services/_align_impl.py`) via `USE_REAL_ALIGN` env flag
- Dual API contracts: legacy `/compare` (sentence pairs) + new `/api/diff` (clause-based, see `ML_ARCHITECTURE.md`)
- Best-effort concept extraction: LLM failures degrade gracefully to empty concepts without breaking the diff
- All ML tuning constants centralized in `ml/thresholds.py`
- Stateless per request (no DB); in-memory dict for legacy explanation polling only

## Layers

**API / Router Layer:** `backend/routes/`
- Purpose: HTTP routing, request validation, response shaping
- Contains: `compare.py` (legacy `/compare`), `diff.py` (new `/api/diff`), `explanation.py` (`/explanation/{id}` polling)
- Depends on: `backend/models/schemas.py`, `backend/services/`, `ml/pipeline.py`
- Used by: `backend/main.py` (router registration)

**Service / Adapter Layer:** `backend/services/`
- Purpose: Integration seams, business logic, tokenization
- Contains: `align.py` (alignment dispatcher), `_align_impl.py` (vendored Winston `semantic_hungarian`), `tokenizer.py` (spaCy + regex fallback), `ml_client.py` (legacy mock bridge)
- Depends on: `backend/models/schemas.py`, `ml/_mock_align.py`, `ml/embeddings.py` (when real alignment is on)
- Used by: routes layer + `ml/pipeline.py`

**ML Slice Layer:** `ml/`
- Purpose: Embedding, scoring, classification, concept extraction, orchestration
- Contains: `embeddings.py`, `scoring.py`, `classification.py`, `concepts.py`, `metrics.py`, `pipeline.py`, `thresholds.py`, `_mock_align.py`
- Depends on: `backend/models/schemas.py`, `backend/services/align.py`, OpenAI SDK, NumPy
- Used by: `backend/routes/diff.py` via `ml.pipeline.run_diff()`

**Data / Schema Layer:** `backend/models/schemas.py`
- Purpose: Single source of truth for all DTOs
- Contains: Legacy (`CompareRequest`, `SentencePair`, `CompareResponse`) and new (`DiffRequest`, `ClauseUnit`, `AlignedPair`, `AlignmentResult`, `DiffResponse`, `Concept`, `ConceptDiff`) schemas
- Type literals: `Classification` (unchanged|modified|added|removed), `ConceptStatus` (new|removed|weakened|strengthened|unchanged — `removed` added in current uncommitted change)
- Used by: every backend module

**Frontend Layer:** `frontend/src/`
- Purpose: Input panel, side-by-side diff viewer, summary metrics
- Contains: `App.tsx`, `components/InputPanel.tsx`, `components/DiffViewer.tsx`, `components/SummaryBar.tsx`, `api/client.ts`, `types/api.ts`

## Data Flow

**`/api/diff` request lifecycle:**

1. Frontend POST → `frontend/src/components/InputPanel.tsx` → `frontend/src/api/client.ts::compareDocuments()` → `/api/diff` with `{ before, after }` (DiffRequest)
2. Router `backend/routes/diff.py::diff_documents()` calls `ml.pipeline.run_diff(before, after)`
3. Alignment: `backend/services/align.py::align()` dispatches to `ml/_mock_align.py::mock_align()` or `_real_align()` based on `USE_REAL_ALIGN`; returns `AlignmentResult` (paired clauses + unmatched lists)
4. Concurrent (via `asyncio.gather()`):
   - **Task A** `ml/embeddings.py::embed_clauses()` → OpenAI embeddings, batched + L2-normalized
   - **Task B** `ml/concepts.py::extract_concepts()` → gpt-4o-mini structured output (or empty `ConceptDiff` on failure)
5. Synchronous post-processing on embeddings:
   - `ml/scoring.py::score_pairs()` — cosine similarity → drift remap (0–100)
   - `ml/classification.py::classify_pairs()` — threshold buckets (unchanged ≥0.93, modified 0.65–0.92, removed <0.65); optional split for low-similarity pairs
   - `ml/classification.py::classify_unmatched()` — mark added/removed
6. `ml/metrics.py::aggregate_metrics()` — counts, length-weighted drift, Levenshtein text-edit %, concept_status
7. `ml/pipeline.py::_build_before_clauses() / _build_after_clauses() / _build_pair_renderings()` — assemble `ClauseRendering` lists and `PairRendering` connectors for UI
8. Return `DiffResponse` → Frontend `DiffViewer` renders side-by-side with classifications

**State Management:**
- Stateless per request for `/api/diff`
- Legacy `/compare` uses `explanation_store: dict[uuid, state]` in `backend/routes/compare.py` — single-process only

## Key Abstractions

| Abstraction | File | Pattern |
|---|---|---|
| `AlignmentResult` | `backend/models/schemas.py` | Contract between `align()` and ML slice |
| `ClauseUnit` | `backend/models/schemas.py` | Atomic text unit with stable ID (`b0`, `a0`, …) |
| `DiffResponse` | `backend/models/schemas.py` | Final API response |
| `align()` | `backend/services/align.py` | Dispatcher (mock ↔ real Hungarian) |
| `run_diff()` | `ml/pipeline.py` | Top-level orchestrator |
| `embed_clauses()` | `ml/embeddings.py` | Batched embeddings + tenacity retry |
| `score_pairs()` | `ml/scoring.py` | Cosine + drift remap |
| `classify_pairs()` | `ml/classification.py` | Threshold-based bucketing + split |
| `extract_concepts()` | `ml/concepts.py` | LLM structured-output extraction |
| `aggregate_metrics()` | `ml/metrics.py` | Summary stats |
| Thresholds module | `ml/thresholds.py` | Single source of truth for tunables |

## Entry Points

**FastAPI app:**
- Location: `backend/main.py`
- Triggers: `python backend/main.py` or `uvicorn backend.main:app`
- Responsibilities: Load `.env`, init FastAPI, register CORS middleware, mount routers (`compare`, `diff`, `explanation`), expose `/health`

**Diff endpoint:**
- Location: `backend/routes/diff.py::diff_documents()`
- Triggers: `POST /api/diff`
- Responsibilities: Validate `DiffRequest`, call `run_diff()`, catch exceptions → `HTTPException(500)`

**Pipeline orchestrator:**
- Location: `ml/pipeline.py::run_diff()`
- Triggers: Invoked by diff route
- Responsibilities: Align → embeddings + concepts (parallel) → score → classify → metrics → assemble response

**Frontend:**
- Location: `frontend/src/main.tsx` → `frontend/src/App.tsx`
- Triggers: Browser load on `http://localhost:5173`
- Responsibilities: Render `InputPanel` ↔ `DiffViewer`; manage compare result state

## Error Handling

**Strategy:** Layered defensive handling — retry at the boundary, graceful degradation in best-effort steps, generic 500s at the route boundary.

**Patterns:**
- Tenacity retry on OpenAI errors (`ml/embeddings.py`): 6 attempts with exponential backoff for `(RateLimitError, APIConnectionError, APIStatusError)`. **Retry exhaustion is not caught** — propagates up
- Concept extraction wraps everything in `except Exception` (`ml/concepts.py`) and returns `ConceptDiff(status="failed")` so the pipeline keeps going
- Pipeline-level catch in `ml/pipeline.py` for concept failures only
- Route-level `except Exception` in `backend/routes/diff.py` returns `HTTPException(500, detail=...)`
- Pydantic auto-422 on schema validation failures
- Tokenizer falls back from spaCy → regex via bare `except:` (broad — flagged in CONCERNS.md)

## Cross-Cutting Concerns

**Configuration:**
- `.env` via python-dotenv (`backend/main.py`)
- Tunables in `ml/thresholds.py`: `STABLE_THRESHOLD`, `MODIFIED_THRESHOLD`, `REMOVED_THRESHOLD`, `DRIFT_FLOOR`, `DRIFT_CEIL`, `EMBEDDING_MODEL`, `CHAT_MODEL`, `MAX_CONCEPT_INPUT_CHARS`, `ALIGNMENT_PRE_PRUNES`

**Logging:**
- `print(..., file=sys.stderr)` only — no `logging` module
- Warnings at startup for missing env vars (`backend/main.py`)
- Tokenizer warns when spaCy unavailable

**Validation:**
- Pydantic at API boundary (`backend/models/schemas.py`)
- Input size cap: `max_length=20_000` per side on `DiffRequest`
- Defensive cap inside concept extraction: 60_000 chars per side

**Auth:**
- None

**Async Wiring:**
- ML pipeline functions are async where I/O-bound (embeddings, concepts), sync where pure compute (scoring, classification, metrics)
- `asyncio.gather()` parallelizes the two LLM-bound steps in `run_diff()`

---

*Architecture analysis: 2026-05-09*
*Update when major patterns change*
