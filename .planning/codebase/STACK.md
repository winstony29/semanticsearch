# Technology Stack

**Analysis Date:** 2026-05-09 (post-merge of `origin/main`)

## Languages

**Primary:**
- Python 3.10+ — Backend API and ML slice (`backend/`, `ml/`)
- TypeScript 5.5.3 — Frontend UI (`frontend/src/`)

**Secondary:**
- JavaScript — Vite build glue

## Runtime

**Environment:**
- FastAPI 0.115.0 + Uvicorn 0.32.0 (async Python HTTP server) — `backend/main.py`
- Node.js 18+ for Vite dev server (port 5173) — `frontend/`
- No `.python-version` / `.nvmrc` committed
- No Docker / containerization

**Package Manager:**
- Python: `pip` with `backend/requirements.txt` and `ml/requirements.txt`
- Frontend: `npm` with `frontend/package.json` (no lockfile committed)

## Frameworks

**Core:**
- FastAPI 0.115.0 — Async Python web framework — `backend/main.py`
- React 18.3.1 — Frontend UI
- Vite 5.4.1 — Frontend bundler — `frontend/vite.config.ts`
- Pydantic 2.9.2 — Schemas + validation — `backend/models/schemas.py`

**Testing:**
- pytest 8.3.3 — Test runner — `pytest.ini`
- pytest-asyncio 0.24.0 — `asyncio_mode = auto`

**Build/Dev:**
- Vite 5.4.1 with React plugin
- TypeScript 5.5.3 compiler

**NLP / ML (multi-engine after merge):**
- spaCy 3.8.2 — Multilingual sentence splitting — `backend/services/tokenizer.py` (lazy-loads `en_core_web_sm`, `zh_core_web_sm`, `ja_core_web_sm`, `ko_core_news_sm`, `de_core_news_sm`)
- wtpsplit (SaT-3l) — Optional multilingual sentence tokenizer with regex fallback — `backend/services/tokenizer.py`
- sentence-transformers 3.3.1 — Local embedding model `all-MiniLM-L6-v2` — provided as fallback in `QUICK_FIXES/fix1_embeddings_local.py` (not yet wired)

## Key Dependencies

**Critical:**
- `openai==1.54.3` — Embeddings (`text-embedding-3-small`) and chat (`gpt-4o-mini`) — `ml/embeddings.py`, `ml/concepts.py`
- `anthropic==0.39.0` — Reserved; not used post-merge per `notes/ml-branch-handoff.md`
- `pydantic==2.9.2` — All DTOs in `backend/models/schemas.py`
- `tenacity==9.0.0` — Retry on OpenAI errors (6 attempts, exp. backoff) — `ml/embeddings.py`
- `numpy==1.26.4` — Embedding math, alignment matrices
- `scipy==1.14.1` — Hungarian assignment (`linear_sum_assignment`) — used in `backend/services/_align_impl.py` and `ml/alignment_methods.py`
- `scikit-learn==1.5.2` — TF-IDF + cosine similarity — `ml/alignment_methods.py`
- `sentence-transformers==3.3.1` — Local embedding fallback — `QUICK_FIXES/fix1_embeddings_local.py`
- `python-Levenshtein==0.26.1` — String distance for text-edit metric
- `spacy==3.8.2` — Multilingual sentence splitting

## Configuration

**Environment:**
- `.env` via python-dotenv (see `backend/.env.example`, `frontend/.env.example`)
- `OPENAI_API_KEY` (required), `ANTHROPIC_API_KEY` (legacy/unused), `PORT`, `HOST`, `CORS_ORIGINS`
- Frontend: `VITE_API_URL`

**Feature flags:**
- `USE_REAL_ALIGN` (env var, default `0`) — `backend/services/align.py` — gates mock vs. vendored Hungarian
- `ALIGNMENT_PRE_PRUNES` — `ml/thresholds.py` (default `False`) — controls double-prune guard

**Tunables (single source of truth):** `ml/thresholds.py`
- `STABLE_THRESHOLD = 0.93`, `MODIFIED_THRESHOLD = 0.65`, `REMOVED_THRESHOLD = 0.65`
- `DRIFT_FLOOR = 0.5`, `DRIFT_CEIL = 1.0`
- `EMBEDDING_MODEL = "text-embedding-3-small"`, `CHAT_MODEL = "gpt-4o-mini"`
- `MAX_CONCEPT_INPUT_CHARS = 60_000`

**Build:**
- `pytest.ini` — `asyncio_mode=auto`, `testpaths=tests`
- `frontend/vite.config.ts`, `frontend/tsconfig.json`

## Platform Requirements

**Development:**
- Linux / macOS / Windows
- Python 3.10+ (uses `list[str]`, `dict[K,V]` PEP 585 generics)
- Internet access for OpenAI API
- spaCy models downloaded on demand: `python -m spacy download en_core_web_sm` (others optional)
- GPU optional (sentence-transformers and spaCy both CPU-capable)

**Production:**
- Not deployed; no Dockerfile, no CI, no deploy scripts

---

*Stack analysis: 2026-05-09*
*Update after major dependency changes*
