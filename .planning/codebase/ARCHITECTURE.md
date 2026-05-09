# Architecture

**Analysis Date:** 2026-05-09 (post-merge of `origin/main`)

## Pattern Overview

**Overall:** Dual-pipeline FastAPI backend with a clean ML slice. Two parallel REST endpoints (`/compare` legacy, `/api/diff` new) sit on top of a shared service layer. The merge from `origin/main` introduced a multi-method alignment toolkit and an aggregator service alongside the existing async pipeline.

**Key Characteristics:**
- Async-first ML pipeline: `asyncio.gather()` parallelizes embeddings + concept extraction (`ml/pipeline.py::run_diff()`)
- Alignment seam: `backend/services/align.py` is the contract point; `USE_REAL_ALIGN` env flag gates mock vs. vendored Hungarian
- Multiple alignment algorithms now coexist: `_mock_align`, `_align_impl` (vendored Winston Hungarian), `alignment_methods.py` (TF-IDF / semantic / greedy / adaptive Hungarian), `smith_waterman_alignment.py` (sequence alignment) — only the first two are reachable from the API
- Multilingual tokenization: wtpsplit → spaCy → regex fallback
- Best-effort concept extraction: LLM failures degrade to empty `ConceptDiff` without breaking the pipeline
- All ML tunables centralized in `ml/thresholds.py`
- Stateless per request; in-memory `explanation_store` for legacy polling only

## Layers

**API / Router Layer:** `backend/routes/`
- `compare.py` — POST `/compare` (legacy sentence-level)
- `diff.py` — POST `/api/diff` (new clause-level, wires to `ml/pipeline.py::run_diff()`)
- `explanation.py` — GET `/explanation/{id}` (async polling stub)

**Service / Adapter Layer:** `backend/services/`
- `align.py` — alignment dispatcher (`USE_REAL_ALIGN`)
- `_align_impl.py` — vendored `semantic_hungarian()` snapshot from origin/main (staging only)
- `tokenizer.py` — multilingual sentence + clause splitter (wtpsplit / spaCy / regex)
- `aggregator.py` — aggregate clause-level scores back to sentence level for legacy `/compare`
- `ml_client.py` — legacy bridge from `/compare` to ML; **currently broken** (imports nonexistent `ml.semantic_engine`)

**ML Slice Layer:** `ml/`
- `pipeline.py` — `run_diff()` orchestrator
- `embeddings.py`, `scoring.py`, `classification.py`, `concepts.py`, `metrics.py` — pipeline steps
- `thresholds.py` — single source of truth for tunables
- `_mock_align.py` — default alignment (test harness)
- `alignment_methods.py` — multi-method exploration (lexical Hungarian, semantic Hungarian, greedy w/ merges, adaptive) — **not wired into the API**
- `smith_waterman_alignment.py` — bioinformatics-style alternative — **not wired into the API**
- Demo / experiment scripts: `demo.py`, `quick_test.py`, `run_experiments.py`, `visual_demo.py`, `demo_alignment_comparison.py`

**Data / Schema Layer:** `backend/models/schemas.py`
- Legacy: `CompareRequest`, `SentencePair`, `DocumentSummary`, `CompareResponse`
- New: `DiffRequest`, `ClauseUnit`, `AlignedPair`, `AlignmentResult`, `DiffResponse`, `Concept`, `ConceptDiff`
- Type literals: `Classification` (unchanged|modified|added|removed), `ConceptStatus` (new|removed|weakened|strengthened|unchanged)

**Frontend Layer:** `frontend/src/`
- `App.tsx`, `api/client.ts`, `components/{InputPanel,DiffViewer,SummaryBar}.tsx`, `types/api.ts`

## Data Flow

**Flow A — `/api/diff` (new, clause-level):**

1. Frontend POST `{ before, after }` → `frontend/src/components/InputPanel.tsx` → `frontend/src/api/client.ts`
2. `backend/routes/diff.py::diff_documents()` calls `ml.pipeline.run_diff(before, after)`
3. `backend/services/align.py::align()` dispatches:
   - `USE_REAL_ALIGN=0` → `ml/_mock_align.py::mock_align()`
   - `USE_REAL_ALIGN=1` → `backend/services/_align_impl.py::semantic_hungarian()`
   - Returns `AlignmentResult` (paired clauses + unmatched lists)
4. `asyncio.gather()` runs in parallel:
   - **A:** `ml/embeddings.py::embed_clauses()` — batched OpenAI `text-embedding-3-small`, L2-normalized
   - **B:** `ml/concepts.py::extract_concepts()` — `gpt-4o-mini` structured output → `ConceptDiff`
5. `ml/scoring.py::score_pairs()` — cosine → drift remap
6. `ml/classification.py::classify_pairs()` + `classify_unmatched()` — apply thresholds, optionally split low-similarity pairs
7. `ml/metrics.py::aggregate_metrics()` — counts, length-weighted drift, Levenshtein text-edit %, `concept_extraction` status
8. `ml/pipeline.py` builds `ClauseRendering` lists + `PairRendering` connectors → `DiffResponse`
9. Frontend `DiffViewer` renders side-by-side

**Flow B — `/compare` (legacy, sentence-level):** ⚠️ broken at runtime — see CONCERNS.md

1. POST `{ v1_text, v2_text }` → `backend/routes/compare.py::compare_documents()`
2. `backend/services/tokenizer.py::tokenize_text()` produces clauses + sentences + clause→sentence mapping
3. `backend/services/ml_client.py::compare_sentences_ml()` calls `ml.semantic_engine.compare_sentences()` — **`ml/semantic_engine.py` does not exist** → `ModuleNotFoundError` on first request
4. (Intended) `backend/services/aggregator.py::aggregate_clause_scores_to_sentences()` rolls clause scores back up
5. (Intended) Returns `CompareResponse` + queues async explanations to `explanation_store` (also stubbed)

## State Management

- Stateless for `/api/diff`
- Legacy `/compare` uses an in-process dict: `explanation_store: dict[str, dict]` in `backend/routes/compare.py`
- Lost on restart, not safe across multiple workers

## Key Abstractions

| Abstraction | File | Purpose |
|---|---|---|
| `AlignmentResult` | `backend/models/schemas.py` | Contract between `align()` and ML slice |
| `ClauseUnit` | `backend/models/schemas.py` | Atomic text unit with stable ID (`b0`, `a0`, …) |
| `DiffResponse` | `backend/models/schemas.py` | Final `/api/diff` response |
| `align()` | `backend/services/align.py` | Mock ↔ real Hungarian dispatcher |
| `run_diff()` | `ml/pipeline.py` | Top-level orchestrator |
| `embed_clauses()` | `ml/embeddings.py` | Batched embeddings + retry |
| `score_pairs()` | `ml/scoring.py` | Cosine + drift remap |
| `classify_pairs()` | `ml/classification.py` | Threshold bucketing + optional split |
| `extract_concepts()` | `ml/concepts.py` | LLM structured-output extraction |
| `aggregate_metrics()` | `ml/metrics.py` | Summary stats |
| `tokenize_text()` | `backend/services/tokenizer.py` | Multilingual sentence + clause split |
| `aggregate_clause_scores_to_sentences()` | `backend/services/aggregator.py` | Clause→sentence rollup for legacy |
| Thresholds module | `ml/thresholds.py` | Single source of truth for tunables |

## Entry Points

| Entry Point | File | Trigger | Responsibilities |
|---|---|---|---|
| FastAPI app | `backend/main.py` | `python backend/main.py` / `uvicorn` | Load env, CORS, mount routers, expose `/health` |
| Diff endpoint | `backend/routes/diff.py::diff_documents()` | POST `/api/diff` | Validate, call `run_diff()`, return / 500 |
| Compare endpoint | `backend/routes/compare.py::compare_documents()` | POST `/compare` | Tokenize, call ML client, aggregate (currently broken) |
| Pipeline | `ml/pipeline.py::run_diff()` | invoked by diff route | Align → embeddings + concepts → score → classify → metrics → render |
| Frontend | `frontend/src/main.tsx` → `App.tsx` | browser load on `:5173` | Render `InputPanel` ↔ `DiffViewer` |

## Error Handling

- Tenacity retry on OpenAI errors (`ml/embeddings.py`, 6 attempts) — exhaustion is **not** caught and bubbles up
- Concept extraction wraps `Exception` → returns `ConceptDiff(status="failed")` so pipeline continues
- Pipeline-level catch in `ml/pipeline.py::run_diff()` for concept extraction only
- Route-level `except Exception` in `backend/routes/diff.py` → `HTTPException(500, detail=...)`
- `backend/routes/compare.py` does not wrap → implicit 500 (currently breaks on import)
- Pydantic auto-422 on schema validation failures
- Tokenizer falls back wtpsplit → spaCy → regex via guarded imports

## Cross-Cutting Concerns

**Configuration:**
- `.env` via python-dotenv (`backend/main.py`)
- ML tunables in `ml/thresholds.py`
- Feature flag `USE_REAL_ALIGN`

**Logging:**
- `print(..., file=sys.stderr)` only — no `logging` framework
- Warnings on missing env vars at startup; tokenizer fallbacks; concept-extraction failures

**Validation:**
- Pydantic at API boundary (`backend/models/schemas.py`)
- `DiffRequest` caps `before`/`after` at 20_000 chars; concept extraction independently truncates at 60_000

**Auth:**
- None

**Async wiring:**
- I/O-bound = `async def` (`embed_clauses`, `extract_concepts`, `align`)
- Pure compute = sync (`score_pairs`, `classify_pairs`, `aggregate_metrics`)
- `asyncio.gather()` parallelizes embeddings + concept extraction

## Alignment Subsystem

| File | Role | Reachable from API? |
|---|---|---|
| `backend/services/align.py` | Dispatcher (`USE_REAL_ALIGN`) | Yes — entry point |
| `backend/services/_align_impl.py` | Vendored Winston `semantic_hungarian` snapshot | Yes when `USE_REAL_ALIGN=1` |
| `ml/_mock_align.py` | Hand-built fixture pairs | Yes when `USE_REAL_ALIGN=0` (default) |
| `ml/alignment_methods.py` | Multi-method toolkit (TF-IDF, semantic, greedy, adaptive) | **No — exploration only** |
| `ml/smith_waterman_alignment.py` | Bioinformatics-style aligner (`SmithWatermanAligner`) | **No — exploration only** |

**Design intent:** the dispatcher is the contract; `alignment_methods.py` and `smith_waterman_alignment.py` are bench/experiment artifacts. When a winning algorithm is chosen, it gets wired through `align.py` (likely replacing the vendored `_align_impl.py`). See `notes/integration-with-winston.md` for the staged plan.

---

*Architecture analysis: 2026-05-09*
*Update when major patterns change*
