# Technology Stack

**Analysis Date:** 2026-05-09

## Languages

**Primary:**
- Python 3.10+ - All backend (`backend/main.py`) and ML (`ml/`) code
- TypeScript 5.5.3 - Frontend (`frontend/package.json`)

**Secondary:**
- JavaScript / Node.js 18+ - Frontend build tooling

## Runtime

**Environment:**
- Python 3.10+ (per `README.md`)
- Node.js 18+ (frontend only)

**Package Manager:**
- pip + venv for Python (install from `backend/requirements.txt` — canonical) and `ml/requirements.txt` (mirror, lets ML slice install standalone)
- npm for frontend (`frontend/package.json`)
- Lockfile: None detected (no `*.lock`)

## Frameworks

**Core:**
- FastAPI 0.115.0 - REST API + Swagger at `/docs` (`backend/main.py`, `backend/routes/`)
- Uvicorn 0.32.0 - ASGI server (`backend/main.py`)
- Pydantic 2.9.2 - Data contract / validation (`backend/models/schemas.py`)
- React 18.3.1 + Vite 5.4.1 - Frontend (`frontend/package.json`)

**Testing:**
- pytest 8.3.3 - Configured via `pytest.ini`
- pytest-asyncio 0.24.0 - `asyncio_mode = auto`

**Build/Dev:**
- No Python build step (interpreted, no compile)
- Vite for frontend bundling

## Key Dependencies

**Critical:**
- openai 1.54.3 - `text-embedding-3-small` in `ml/embeddings.py`, `gpt-4o-mini` structured output in `ml/concepts.py`
- numpy 1.26.4 - Embedding vectors + cosine sim in `ml/embeddings.py`, `ml/scoring.py`
- spacy 3.8.2 - Sentence tokenization in `backend/services/tokenizer.py` (requires `python -m spacy download en_core_web_sm`)
- tenacity 9.0.0 - Retry decorator on OpenAI calls in `ml/embeddings.py`
- python-Levenshtein 0.26.1 - `pct_text_edited` metric in `ml/metrics.py`
- python-dotenv 1.0.1 - Loads `.env` in `backend/main.py`
- anthropic 0.39.0 - Imported but not yet wired (planned LLM-explanation fallback)

**Infrastructure:**
- httpx 0.27.2 - Async HTTP (transitive via OpenAI / Anthropic SDKs)
- scikit-learn 1.5.2, scipy 1.14.1 - Pre-installed but not actively used yet

## Configuration

**Environment:**
- `.env` files loaded via python-dotenv (`backend/main.py:12`)
- `backend/.env.example` declares: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `PORT`, `HOST`, `CORS_ORIGINS`
- `frontend/.env.example` declares: `VITE_API_URL`
- All tunable ML constants centralized in `ml/thresholds.py` (STABLE_THRESHOLD, MODIFIED_THRESHOLD, REMOVED_THRESHOLD, EMBEDDING_MODEL, CHAT_MODEL, FULL_DRIFT, MAX_CONCEPT_INPUT_CHARS)

**Build:**
- `pytest.ini` (root) - test discovery + asyncio mode
- `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.*`

## Platform Requirements

**Development:**
- Cross-platform (Windows PowerShell or bash per `README.md`)
- spaCy English model installed locally
- OpenAI API key required for `/api/diff` endpoint

**Production:**
- Not yet deployed (hackathon project)
- Anthropic API key optional (currently unused)

---

*Stack analysis: 2026-05-09*
*Update after major dependency changes*
