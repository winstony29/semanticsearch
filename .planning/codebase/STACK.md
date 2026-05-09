# Technology Stack

**Analysis Date:** 2026-05-09

## Languages

**Primary:**
- Python 3.10+ — Backend API and ML slice (`backend/`, `ml/`)
- TypeScript 5.5.3 — Frontend UI (`frontend/src/`)

**Secondary:**
- JavaScript — Vite/build glue (transpiled output)

## Runtime

**Environment:**
- Python 3.10+ via FastAPI 0.115.0 + Uvicorn 0.32.0 (async HTTP server)
- Node.js 18+ for Vite dev server (port 5173)
- No `.python-version` or `.nvmrc` committed — versions documented in `README.md`
- No Docker / containerization

**Package Manager:**
- Python: `pip` with `backend/requirements.txt` and `ml/requirements.txt` (mirrors ML deps)
- Frontend: `npm` with `frontend/package.json`
- No lockfiles committed (`package-lock.json`, `poetry.lock`, `uv.lock` absent — likely gitignored or not generated)

## Frameworks

**Core:**
- FastAPI 0.115.0 — Async Python web framework with auto OpenAPI docs (`backend/main.py`)
- React 18.3.1 — Frontend UI framework
- Vite 5.4.1 — Frontend bundler / dev server (`frontend/vite.config.ts`)

**Testing:**
- pytest 8.3.3 — Test runner (`pytest.ini`)
- pytest-asyncio 0.24.0 — Async test support (`asyncio_mode = auto`)

**Build/Dev:**
- Vite 5.4.1 with React plugin — TS transpilation + HMR
- TypeScript 5.5.3 compiler

**NLP / ML:**
- spaCy 3.8.2 — Sentence tokenization (`backend/services/tokenizer.py`); requires `en_core_web_sm` model download

## Key Dependencies

**Critical:**
- `openai==1.54.3` — Embedding generation (`text-embedding-3-small`) and concept extraction (`gpt-4o-mini` structured output) — used in `ml/embeddings.py`, `ml/concepts.py`
- `anthropic==0.39.0` — Reserved for LLM explanations; **installed but not yet integrated**
- `pydantic==2.9.2` — Request/response schemas across `backend/models/schemas.py`
- `tenacity==9.0.0` — Retry logic for OpenAI calls (`ml/embeddings.py`)
- `numpy==1.26.4` — Embedding numerical ops (L2 normalization, cosine)
- `scipy==1.14.1` — Linear assignment / Hungarian algorithm (used by `backend/services/_align_impl.py`)
- `scikit-learn==1.5.2` — Cosine similarity helpers in vendored Winston code (`backend/services/_align_impl.py`)
- `python-Levenshtein==0.26.1` — Text-edit % metric (`ml/metrics.py`)
- `spacy==3.8.2` — Sentence segmentation (currently active in tokenizer; flagged for replacement, see `notes/multilingual-handoff.md`)

**Infrastructure:**
- `python-dotenv==1.0.1` — Load `.env` files at startup (`backend/main.py`)

## Configuration

**Environment:**
- `.env` files via python-dotenv (no `config.py` / `settings.py`)
- Backend template: `backend/.env.example` — `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `PORT`, `HOST`, `CORS_ORIGINS`
- Frontend template: `frontend/.env.example` — `VITE_API_URL`
- ML tuning constants centralized in `ml/thresholds.py` (single source of truth — thresholds, model IDs, input caps, feature flags)
- Feature flag: `USE_REAL_ALIGN` env var (default `0`) gates mock vs. real Hungarian alignment in `backend/services/align.py`

**Build:**
- `pytest.ini` — pytest config (asyncio_mode=auto, testpaths=tests)
- `frontend/vite.config.ts` — Vite + React plugin + `/api` proxy to `http://localhost:8000`
- `frontend/tsconfig.json` — TypeScript compiler options

## Platform Requirements

**Development:**
- Linux / macOS / Windows (any platform with Python 3.10+ and Node 18+)
- Internet access required for OpenAI API (embeddings + concept extraction)
- spaCy model download step: `python -m spacy download en_core_web_sm`

**Production:**
- Not deployed — local-only hackathon project
- No CI/CD, Dockerfile, or deployment scripts detected

---

*Stack analysis: 2026-05-09*
*Update after major dependency changes*
