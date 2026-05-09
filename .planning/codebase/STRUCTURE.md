# Codebase Structure

**Analysis Date:** 2026-05-09

## Directory Layout

```
semanticsearch/
├── backend/                  # FastAPI server + alignment seam
│   ├── main.py              # Entry point: load .env, CORS, mount routers
│   ├── models/
│   │   └── schemas.py       # All Pydantic DTOs (legacy + new contracts)
│   ├── routes/
│   │   ├── compare.py       # POST /compare (legacy)
│   │   ├── diff.py          # POST /api/diff (new)
│   │   └── explanation.py   # GET /explanation/{id}
│   ├── services/
│   │   ├── align.py         # Alignment dispatcher (mock ↔ real)
│   │   ├── _align_impl.py   # Vendored Winston semantic_hungarian
│   │   ├── ml_client.py     # Legacy mock bridge (deprecated)
│   │   └── tokenizer.py     # spaCy → regex fallback
│   ├── utils/               # (empty placeholder)
│   ├── requirements.txt
│   ├── .env                 # ⚠️ tracked in git — see CONCERNS.md
│   └── .env.example
│
├── ml/                       # ML slice
│   ├── pipeline.py          # run_diff() orchestrator
│   ├── embeddings.py        # OpenAI embeddings + batching + tenacity retry
│   ├── scoring.py           # Cosine + drift remap
│   ├── classification.py    # Threshold buckets + split
│   ├── concepts.py          # gpt-4o-mini concept extraction
│   ├── metrics.py           # Counts, drift, Levenshtein text-edit %
│   ├── thresholds.py        # Single source of truth for ML tunables
│   ├── _mock_align.py       # Hand-crafted mock alignment
│   ├── test_cases.py        # Threshold-tuning fixture corpus (NOT pytest)
│   ├── demo.py              # Manual integration demo
│   └── requirements.txt
│
├── frontend/                 # React + TypeScript UI
│   ├── package.json
│   ├── vite.config.ts       # Vite + /api proxy → :8000
│   ├── tsconfig.json
│   ├── .env.example
│   └── src/
│       ├── main.tsx         # Vite entry
│       ├── App.tsx          # Root: InputPanel ↔ DiffViewer
│       ├── api/client.ts    # HTTP client
│       ├── components/      # InputPanel.tsx, DiffViewer.tsx, SummaryBar.tsx
│       ├── types/api.ts     # TS mirrors of Pydantic schemas
│       └── styles/App.css
│
├── tests/                    # pytest suite
│   ├── conftest.py          # sys.path setup; no fixtures
│   ├── test_align_adapter.py
│   ├── test_classification.py
│   ├── test_embeddings_retry.py
│   ├── test_metrics.py
│   ├── test_mock_align.py
│   ├── test_pipeline.py
│   └── test_scoring.py
│
├── notes/                    # Handoff & integration docs
│   ├── integration-with-winston.md
│   └── multilingual-handoff.md
│
├── test_data/                # Sample documents for manual testing
├── .planning/                # GSD milestone/phase tracking
├── .claude/                  # Claude Code config
├── README.md
├── ML_ARCHITECTURE.md       # Detailed ML slice design
├── pytest.ini
└── .gitignore
```

## Directory Purposes

**backend/**
- Purpose: FastAPI API server + backend-owned integration seams
- Contains: `main.py` entry, `models/`, `routes/`, `services/`
- Key files: `main.py`, `models/schemas.py`, `services/align.py`

**backend/models/**
- Purpose: Pydantic DTOs — single shared contract between frontend, backend, ML slice
- Key file: `schemas.py` (both legacy and new contract families)

**backend/routes/**
- Purpose: FastAPI routers per endpoint family
- Key files: `compare.py` (legacy), `diff.py` (new — wires to ML pipeline), `explanation.py` (polling)

**backend/services/**
- Purpose: Business logic + integration seams
- Key files: `align.py` (mock/real dispatcher), `_align_impl.py` (vendored Winston code), `tokenizer.py` (sentence split), `ml_client.py` (legacy mock)

**ml/**
- Purpose: ML pipeline modules; each step lives in its own file
- Owners: ML team (Agents 2/3/4 per `ML_ARCHITECTURE.md`)
- Key files: `pipeline.py`, `embeddings.py`, `scoring.py`, `classification.py`, `concepts.py`, `metrics.py`, `thresholds.py`

**frontend/src/**
- Purpose: React UI — input panel + side-by-side diff viewer + summary
- Key files: `App.tsx`, `api/client.ts`, `components/DiffViewer.tsx`, `types/api.ts`

**tests/**
- Purpose: pytest suite mirroring ML and adapter modules
- Naming: `test_<module>.py` matching the source it covers

**notes/**
- Purpose: Cross-team handoff and decision documents
- Key files: `integration-with-winston.md` (staged rollout plan), `multilingual-handoff.md` (tokenizer + threshold concerns)

**test_data/**
- Purpose: Sample input documents for manual testing and demos

**.planning/**
- Purpose: GSD-tracked planning artifacts (milestones, phases, this codebase map)

## Key File Locations

**Entry Points:**
- `backend/main.py` — FastAPI app boot (`python backend/main.py` or `uvicorn backend.main:app`)
- `frontend/src/main.tsx` — Vite dev server entry (`npm run dev` from `frontend/`)
- `ml/demo.py` — Manual integration demo for the ML pipeline

**Configuration:**
- `pytest.ini` — pytest config (asyncio_mode=auto, testpaths=tests)
- `frontend/vite.config.ts` — Vite + React + `/api` proxy
- `frontend/tsconfig.json` — TS compiler
- `backend/.env` / `backend/.env.example` — API keys, host/port, CORS
- `frontend/.env.example` — `VITE_API_URL`
- `ml/thresholds.py` — All ML tunables (model IDs, thresholds, input caps, feature flags)

**Core Logic:**
- Alignment dispatcher: `backend/services/align.py`
- Mock alignment: `ml/_mock_align.py`
- Real alignment (vendored): `backend/services/_align_impl.py`
- Pipeline orchestrator: `ml/pipeline.py`
- Per-step modules: `ml/embeddings.py`, `ml/scoring.py`, `ml/classification.py`, `ml/concepts.py`, `ml/metrics.py`

**Testing:**
- Suite: `tests/test_*.py`
- Fixture corpus (not pytest): `ml/test_cases.py`

**Documentation:**
- `README.md` — Project overview & quick start
- `ML_ARCHITECTURE.md` — Detailed ML slice design (steps 1–7, contracts, thresholds)
- `notes/integration-with-winston.md` — Staged Winston integration plan
- `notes/multilingual-handoff.md` — Tokenizer + multilingual threshold concerns

## Naming Conventions

**Files:**
- snake_case for Python (`ml_client.py`, `test_classification.py`, `_mock_align.py`)
- Underscore prefix for internal/vendored modules (`_mock_align.py`, `_align_impl.py`)
- PascalCase for React components (`DiffViewer.tsx`, `InputPanel.tsx`)
- kebab-case for some markdown notes (`integration-with-winston.md`)
- UPPERCASE.md for top-level project docs (`README.md`, `ML_ARCHITECTURE.md`)

**Directories:**
- snake_case / lowercase (`backend/`, `ml/`, `frontend/`, `tests/`, `notes/`, `test_data/`)
- Plural for collections (`models/`, `routes/`, `services/`, `components/`)

**Special Patterns:**
- `test_*.py` for pytest files (under `tests/`)
- `_*.py` for private/internal modules
- `__init__.py` minimal (no barrel re-exports)
- Clause IDs: `b0`, `b1` (before) / `a0`, `a1` (after)
- Pair IDs: `pair_000`, `pair_add_001`, `pair_del_002` (legacy)

## Where to Add New Code

**New API endpoint:**
- Route: new file under `backend/routes/`
- Register: in `backend/main.py` with `app.include_router(...)`
- DTOs: add to `backend/models/schemas.py`
- Tests: `tests/test_<route_name>.py`

**New service / business logic:**
- Module: `backend/services/<name>.py`
- Tests: `tests/test_<name>.py`

**New ML pipeline step:**
- Module: `ml/<step_name>.py`
- Wire into: `ml/pipeline.py::run_diff()` (likely as another `asyncio.create_task` if I/O-bound)
- Tunables: add constants to `ml/thresholds.py`
- Tests: `tests/test_<step_name>.py`

**New frontend component:**
- Component: `frontend/src/components/<Name>.tsx` (PascalCase)
- API types: update `frontend/src/types/api.ts`
- API call: extend `frontend/src/api/client.ts`

**ML tuning:**
- Edit `ml/thresholds.py` only — no changes to scoring/classification logic should be needed

**Utilities:**
- `backend/utils/` is currently empty; reserved for shared helpers

## Special Directories

**backend/utils/**
- Currently empty; reserved for cross-cutting helpers

**files (1)/**
- Legacy artifact at the repo root from an earlier upload; not referenced in code

**__pycache__/, .pytest_cache/, node_modules/**
- Auto-generated, gitignored

---

*Structure analysis: 2026-05-09*
*Update when directory structure changes*
