# Codebase Structure

**Analysis Date:** 2026-05-09 (post-merge of `origin/main`)

## Directory Layout

```
semanticsearch/
├── backend/                          # FastAPI server + alignment seam
│   ├── main.py                      # Entry: load .env, CORS, mount routers
│   ├── models/
│   │   └── schemas.py               # Pydantic DTOs (legacy + new contracts)
│   ├── routes/
│   │   ├── compare.py               # POST /compare (legacy)
│   │   ├── diff.py                  # POST /api/diff (new)
│   │   └── explanation.py           # GET /explanation/{id}
│   ├── services/
│   │   ├── align.py                 # Alignment dispatcher (mock ↔ real)
│   │   ├── _align_impl.py           # Vendored Winston Hungarian (staging)
│   │   ├── ml_client.py             # Legacy /compare bridge (broken)
│   │   ├── tokenizer.py             # wtpsplit / spaCy / regex multilingual split
│   │   └── aggregator.py            # Clause→sentence score rollup
│   ├── utils/                       # (placeholder)
│   ├── requirements.txt
│   └── .env.example
│
├── ml/                               # ML slice
│   ├── pipeline.py                  # run_diff() orchestrator
│   ├── embeddings.py                # OpenAI embeddings + tenacity retry
│   ├── scoring.py                   # Cosine + drift remap
│   ├── classification.py            # Threshold buckets
│   ├── concepts.py                  # gpt-4o-mini concept extraction
│   ├── metrics.py                   # Counts, drift, text-edit %
│   ├── thresholds.py                # Single source of truth for tunables
│   ├── _mock_align.py               # Hand-built mock alignment
│   ├── alignment_methods.py         # Multi-method toolkit (NOT wired)
│   ├── smith_waterman_alignment.py  # Sequence-alignment alt (NOT wired)
│   ├── test_cases.py                # Threshold-tuning corpus (NOT pytest)
│   ├── demo.py                      # Manual integration demo
│   ├── demo_alignment_comparison.py # Algorithm bench
│   ├── quick_test.py                # Standalone smoke runner
│   ├── visual_demo.py               # Visual algorithm comparison
│   ├── run_experiments.py           # Experiment driver
│   ├── DEMO_GUIDE.md
│   ├── NICKOLAS_README.md           # Stale — pre-refactor guidance
│   └── requirements.txt
│
├── frontend/                         # React + TypeScript UI
│   ├── package.json
│   ├── vite.config.ts               # Vite + /api proxy → :8000
│   ├── tsconfig.json
│   ├── .env.example
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts
│       ├── components/              # InputPanel.tsx, DiffViewer.tsx, SummaryBar.tsx
│       ├── types/api.ts
│       └── styles/App.css
│
├── tests/                            # pytest suite (testpaths)
│   ├── conftest.py                  # sys.path setup; no fixtures
│   ├── test_align_adapter.py
│   ├── test_classification.py
│   ├── test_embeddings_retry.py
│   ├── test_metrics.py
│   ├── test_mock_align.py
│   ├── test_pipeline.py
│   └── test_scoring.py
│
├── QUICK_FIXES/                      # Copy-paste hackathon patches (NOT auto-applied)
│   ├── README.md                    # Patch instructions
│   ├── fix1_embeddings_openai.py
│   ├── fix1_embeddings_local.py     # sentence-transformers fallback
│   ├── fix2_backend_integration.py
│   ├── fix3_async_explanations.py
│   ├── fix_CRITICAL_padding.py
│   └── fix_CRITICAL_quality_score.py
│
├── notes/                            # Handoff & integration docs
│   ├── integration-with-winston.md
│   ├── multilingual-handoff.md
│   └── ml-branch-handoff.md
│
├── test_data/                        # Sample documents for manual testing
├── files (1)/                        # Legacy roadmap & planning docs
├── .planning/                        # GSD planning artifacts (this map)
├── .claude/                          # Claude Code config (gitignored)
│
├── README.md                         # Project overview
├── ML_ARCHITECTURE.md               # Detailed ML slice spec
├── CRITICAL_ANALYSIS.md             # Algorithm audit + recommendations
├── FIXES_NEEDED.md                  # Known issues from origin/main
├── TESTING_REPORT.md                # Manual test summary (not pytest)
├── TESTED_AND_READY.md              # Sign-off notes from origin/main
├── alignment_test_results.md        # Bench results
├── test_alignment.py                # Root-level standalone script (NOT pytest)
├── test_all_alignments.py           # Root-level standalone script (NOT pytest)
├── pytest.ini
└── .gitignore
```

## Directory Purposes

| Directory | Purpose | Notes |
|---|---|---|
| `backend/` | FastAPI app + integration seams | Backend lead |
| `backend/models/` | Pydantic DTOs | Single source of truth |
| `backend/routes/` | FastAPI routers | One file per endpoint family |
| `backend/services/` | Business logic + integration seams | Includes vendored Winston code (`_align_impl.py`) |
| `ml/` | ML pipeline modules + bench scripts | ML lead |
| `frontend/src/` | React UI | Vite-built |
| `tests/` | pytest suite | Only directory pytest collects from |
| `QUICK_FIXES/` | Copy-paste patch files for hackathon fixes | Not yet applied to source |
| `notes/` | Cross-team handoff and decision docs | |
| `test_data/` | Sample input documents | Manual testing only |
| `.planning/` | GSD planning artifacts | This map lives here |
| `files (1)/` | Legacy roadmap docs | Pre-merge artifact |

## Key File Locations

**Entry points:**
- `backend/main.py` — FastAPI app
- `frontend/src/main.tsx` — Vite dev server entry
- `ml/demo.py`, `ml/quick_test.py`, `ml/run_experiments.py` — manual ML runners

**Configuration:**
- `pytest.ini` — `asyncio_mode=auto`, `testpaths=tests`, `python_files=test_*.py`
- `frontend/vite.config.ts`, `frontend/tsconfig.json`
- `backend/.env` (gitignored), `backend/.env.example`, `frontend/.env.example`
- `ml/thresholds.py` — all ML tunables

**Core logic:**
- Alignment: `backend/services/align.py`, `backend/services/_align_impl.py`, `ml/_mock_align.py`, `ml/alignment_methods.py`, `ml/smith_waterman_alignment.py`
- Pipeline: `ml/pipeline.py`, `ml/embeddings.py`, `ml/scoring.py`, `ml/classification.py`, `ml/concepts.py`, `ml/metrics.py`
- Tokenization: `backend/services/tokenizer.py`
- Aggregation: `backend/services/aggregator.py`

**Testing:**
- pytest suite: `tests/test_*.py` (7 files)
- Standalone scripts (NOT pytest): `test_alignment.py`, `test_all_alignments.py` at root; `ml/quick_test.py`, `ml/run_experiments.py`, `ml/visual_demo.py`, `ml/demo_alignment_comparison.py`
- Fixture corpus: `ml/test_cases.py` (12 hand-built cases, exposes `TEST_CASES`)

**Documentation:**
- `README.md` — overview & quickstart
- `ML_ARCHITECTURE.md` — ML slice specification
- `CRITICAL_ANALYSIS.md`, `FIXES_NEEDED.md`, `TESTING_REPORT.md`, `TESTED_AND_READY.md`, `alignment_test_results.md` — merged from origin/main
- `notes/integration-with-winston.md`, `notes/multilingual-handoff.md`, `notes/ml-branch-handoff.md`
- `ml/NICKOLAS_README.md`, `ml/DEMO_GUIDE.md`

## Naming Conventions

**Files:**
- snake_case for Python (`ml_client.py`, `alignment_methods.py`)
- Underscore prefix for private/internal/vendored modules (`_mock_align.py`, `_align_impl.py`)
- `test_*.py` for pytest files (under `tests/`); the same prefix appears at the repo root for standalone scripts that pytest skips
- PascalCase `.tsx` for React components
- kebab-case for cross-team markdown notes
- UPPERCASE.md for top-level project docs

**Directories:**
- snake_case / lowercase

**Python identifiers:**
- snake_case for functions and variables
- PascalCase for classes and Pydantic models
- UPPER_SNAKE_CASE for constants

**Special patterns:**
- Clause IDs: `b0`, `b1` (before) / `a0`, `a1` (after)
- Pair IDs: `pair_000`, `pair_add_001`, `pair_del_002` (legacy)
- `*Request` / `*Response` / `*Result` / `*Unit` / `*Rendering` schema suffixes

## Where to Add New Code

**New REST endpoint:**
- Route: `backend/routes/<name>.py`
- Mount: `backend/main.py` `app.include_router(...)`
- DTOs: `backend/models/schemas.py`
- Test: `tests/test_<name>.py`

**New service / business logic:**
- Module: `backend/services/<name>.py`
- Test: `tests/test_<name>.py`

**New ML pipeline step:**
- Module: `ml/<step>.py`
- Wire into `ml/pipeline.py::run_diff()` (likely as another `asyncio.create_task` if I/O-bound)
- Constants: `ml/thresholds.py`
- Test: `tests/test_<step>.py`

**New alignment algorithm:**
- Module: `ml/<name>_alignment.py` or extend `ml/alignment_methods.py`
- To make it reachable from the API: register in `backend/services/align.py` (probably behind a new flag or replacing the vendored path)

**New frontend component:**
- File: `frontend/src/components/<Name>.tsx` (PascalCase)
- API types: update `frontend/src/types/api.ts`
- API call: extend `frontend/src/api/client.ts`

**ML tuning:**
- Edit `ml/thresholds.py` only

**Utilities:**
- `backend/utils/` is currently empty; reserved for shared helpers

## Special Directories

- `__pycache__/`, `.pytest_cache/`, `node_modules/` — gitignored
- `.claude/` — gitignored
- `backend/.env` — gitignored (always was, via root `.env` pattern)
- `files (1)/` — legacy artifact, not referenced by code

---

*Structure analysis: 2026-05-09*
*Update when directory structure changes*
