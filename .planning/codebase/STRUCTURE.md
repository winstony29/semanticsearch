# Codebase Structure

**Analysis Date:** 2026-05-09

## Directory Layout

```
semanticsearch/
├── backend/                # FastAPI server, services, schemas
│   ├── main.py             # App entry, router registration, CORS
│   ├── models/
│   │   └── schemas.py      # Pydantic data contract (single source of truth)
│   ├── routes/
│   │   ├── compare.py      # POST /compare (legacy, mocked)
│   │   ├── diff.py         # POST /api/diff (new, ML-backed)
│   │   └── explanation.py  # GET /explanation/{id} (legacy polling)
│   ├── services/
│   │   ├── align.py        # Alignment seam (mock → real Hungarian)
│   │   ├── ml_client.py    # Legacy ML wrapper (mock data)
│   │   └── tokenizer.py    # spaCy sentence tokenization (legacy)
│   ├── utils/              # (empty)
│   ├── requirements.txt    # Canonical Python deps
│   └── .env.example
├── ml/                     # Async ML pipeline
│   ├── __init__.py
│   ├── pipeline.py         # Step 6: run_diff() orchestrator
│   ├── embeddings.py       # Step 1: OpenAI batch embed + tenacity retry
│   ├── scoring.py          # Step 2: cosine similarity + drift remap
│   ├── classification.py   # Step 3: threshold-based labelling
│   ├── metrics.py          # Step 4: DiffSummary aggregation
│   ├── concepts.py         # Step 5: gpt-4o-mini structured output
│   ├── thresholds.py       # All tunable constants
│   ├── _mock_align.py      # Hand-crafted mock alignment (dev only)
│   ├── demo.py             # Runnable CLI: --mock, --before, --after
│   └── requirements.txt    # Mirror of backend deps for standalone install
├── frontend/               # React + TypeScript + Vite (separate branch)
│   ├── src/
│   ├── package.json
│   └── tsconfig.json
├── tests/                  # pytest suite (root-relative imports)
│   ├── conftest.py         # sys.path injection for absolute imports
│   ├── test_classification.py
│   ├── test_scoring.py
│   ├── test_metrics.py
│   ├── test_embeddings_retry.py
│   ├── test_mock_align.py
│   └── test_pipeline.py
├── notes/                  # Dev handoff docs
│   ├── integration-with-winston.md
│   └── ml-branch-handoff.md
├── test_data/              # Sample documents for manual testing
├── files (1)/              # Original planning docs (ROADMAP, TEAM_SPLIT, DATA_CONTRACT, PROMPTS)
├── ML_ARCHITECTURE.md      # Definitive ML spec (7 sections)
├── README.md
├── pytest.ini              # asyncio_mode = auto, testpaths = tests
└── .planning/codebase/     # This map
```

## Directory Purposes

**`backend/`:**
- Purpose: FastAPI server, HTTP layer, data contracts, service seams
- Contains: app entry, route handlers, Pydantic schemas, service classes
- Key files: `backend/main.py`, `backend/models/schemas.py`, `backend/services/align.py`
- Subdirectories: `models/` (schemas), `routes/` (one module per endpoint group), `services/` (cross-cutting), `utils/` (empty)

**`ml/`:**
- Purpose: Async ML pipeline — embeddings, scoring, classification, metrics, concepts, orchestration
- Contains: numbered pipeline steps + thresholds + mock + demo
- Key files: `ml/pipeline.py` (entry `run_diff`), `ml/thresholds.py` (config), `ml/_mock_align.py` (dev fallback)
- Pattern: each file is one pipeline stage; underscore-prefixed (`_mock_align.py`) marks internal/dev-only

**`tests/`:**
- Purpose: pytest unit + integration tests
- Contains: `test_<module>.py` files, `conftest.py` (sys.path setup)
- Key files: `tests/test_pipeline.py` (integration), `tests/test_embeddings_retry.py` (regression)

**`frontend/`:**
- Purpose: React + TypeScript UI (not active on ML branch)
- Contains: Vite app, components, API client

**`notes/`:**
- Purpose: Branch-handoff docs, integration risks, decision logs
- Key files: `notes/integration-with-winston.md`, `notes/ml-branch-handoff.md`

**`test_data/`, `files (1)/`:**
- Purpose: Sample documents and original planning artifacts (read-only)

## Key File Locations

**Entry Points:**
- `backend/main.py` - FastAPI app, `uvicorn backend.main:app`
- `ml/pipeline.py:run_diff()` - Pipeline entry
- `ml/demo.py` - CLI demo (`python -m ml.demo`)

**Configuration:**
- `pytest.ini` - test discovery + `asyncio_mode = auto`
- `ml/thresholds.py` - all ML tunables
- `backend/.env.example` / `frontend/.env.example` - env var declarations
- No `pyproject.toml`, no `ruff.toml`, no `.flake8`

**Core Logic:**
- `backend/models/schemas.py` - Pydantic contract (DiffRequest, DiffResponse, AlignmentResult, ClauseUnit, AlignedPair, ClauseRendering, Concept, DiffSummary)
- `ml/pipeline.py` - orchestration
- `ml/embeddings.py`, `ml/scoring.py`, `ml/classification.py`, `ml/metrics.py`, `ml/concepts.py` - pipeline stages

**Testing:**
- `tests/conftest.py` - sys.path injection (no shared fixtures)
- `tests/test_pipeline.py` - end-to-end with monkeypatched embeddings/concepts

**Documentation:**
- `README.md` - Setup + endpoints
- `ML_ARCHITECTURE.md` - Definitive ML spec
- `notes/*.md` - Handoff and integration risk docs

## Naming Conventions

**Files:**
- `snake_case.py` for all Python modules
- `_underscore_prefix.py` for internal/dev-only modules (`ml/_mock_align.py`)
- `test_<module>.py` mirrors source module name in `tests/`

**Directories:**
- `snake_case` for Python packages
- Singular module names (`schemas.py`), plural for collections (`routes/`, `services/`, `models/`)

**Special Patterns:**
- Clause IDs: `b{n}` for before, `a{n}` for after — assumed throughout `ml/pipeline.py`, `ml/_mock_align.py`, `ml/metrics.py`
- Classification literals: lowercase strings (`"unchanged"`, `"modified"`, `"added"`, `"removed"`)

## Where to Add New Code

**New ML pipeline stage:**
- Implementation: `ml/<stage>.py` — single-purpose module, pure functions where possible
- Wiring: import + call from `ml/pipeline.py:run_diff()`
- Tests: `tests/test_<stage>.py` mirroring existing patterns
- Constants: add to `ml/thresholds.py` (do NOT inline magic numbers)

**New API endpoint:**
- Route module: `backend/routes/<endpoint>.py` (define `router = APIRouter(...)`)
- Wire into app: `app.include_router(...)` in `backend/main.py`
- Schema: add request/response models to `backend/models/schemas.py`
- Tests: `tests/test_routes_<endpoint>.py` (currently no route tests exist — see CONCERNS)

**New service:**
- Implementation: `backend/services/<service>.py`
- Imports schemas from `backend/models/schemas.py`

**Threshold tuning:**
- Edit `ml/thresholds.py` only

**Mock data for dev:**
- Follow `ml/_mock_align.py` pattern; monkey-patch into pipeline (see `ml/demo.py:_install_mocks()`)

## Special Directories

**`.planning/codebase/`:**
- Purpose: This map (auto-generated by `/gsd:map-codebase`)
- Source: 4 parallel Explore agents
- Committed: Yes (planning artifacts)

**`.claude/`:**
- Purpose: Claude Code harness config, custom skills/agents
- Committed: Per `.gitignore` rules (currently untracked per `git status`)

**`__pycache__/`:**
- Purpose: Python bytecode
- Committed: No

---

*Structure analysis: 2026-05-09*
*Update when directory structure changes*
