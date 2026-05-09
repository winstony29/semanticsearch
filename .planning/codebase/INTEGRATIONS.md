# External Integrations

**Analysis Date:** 2026-05-09 (post-merge of `origin/main`)

## APIs & External Services

**OpenAI (primary, active):**
- SDK: `openai==1.54.3` — `AsyncOpenAI` client
- Embeddings: `text-embedding-3-small` — `ml/embeddings.py::_embed_batch_normalized()` (batched + L2-normalized)
- Chat (concept extraction): `gpt-4o-mini` with structured output — `ml/concepts.py::extract_concepts()`
- Auth: `OPENAI_API_KEY` env var (loaded from `backend/.env`); checked at startup in `backend/main.py`
- Retry: tenacity with exponential backoff, `stop_after_attempt(6)` on `(RateLimitError, APIConnectionError, APIStatusError)`
- Input cap: 60_000 chars per side for concept extraction (`MAX_CONCEPT_INPUT_CHARS` in `ml/thresholds.py`)

**Anthropic (declared, unused post-merge):**
- SDK installed (`anthropic==0.39.0`)
- `ANTHROPIC_API_KEY` declared in `backend/.env.example` but no active code path

## Local / Embedded Models

**sentence-transformers `all-MiniLM-L6-v2` (NEW, not yet wired):**
- File: `QUICK_FIXES/fix1_embeddings_local.py`
- Purpose: Free, offline embedding fallback (~90 MB model, CPU-capable, ~100 sentences/sec)
- Status: Provided as a copy-paste patch — not integrated into the active pipeline yet

**spaCy language models (lazy-loaded):**
- Models: `en_core_web_sm`, `zh_core_web_sm`, `ja_core_web_sm`, `ko_core_news_sm`, `de_core_news_sm`
- Detected by Unicode-range language sniff in `backend/services/tokenizer.py`
- Required: `python -m spacy download en_core_web_sm` (others optional, code falls through to regex)

**wtpsplit (SaT-3l):**
- Optional multilingual sentence splitter — `backend/services/tokenizer.py`
- Graceful fallback to spaCy / regex if missing

## Data Storage

**Databases:**
- None — no persistent database

**Vector Stores:**
- None — cosine similarity computed in-process via NumPy

**File Storage:**
- None — `test_data/` for sample documents only

**Caching:**
- None

**In-process state:**
- `explanation_store: dict[str, dict]` in `backend/routes/compare.py` — keyed by `comparison_id`, lost on restart, single-process only

## Authentication & Identity

- None — no JWT, OAuth, or per-user authentication
- Service-level API keys (`OPENAI_API_KEY`) only

## Monitoring & Observability

- FastAPI auto-docs: `/docs`, `/redoc`, `/openapi.json`
- Health endpoints: `GET /`, `GET /health`, `GET /api/diff/health` — spaCy + OpenAI checks still TODO stubs in `backend/main.py`
- No structured logging, tracing, or metrics — `print(..., file=sys.stderr)` only
- No Sentry / DataDog / OTel

## CI/CD & Deployment

- Not detected — no `.github/workflows/`, `Dockerfile`, or deploy scripts
- Run locally: `python backend/main.py` (Uvicorn `reload=True` for dev), `npm run dev` from `frontend/`

## API Surface

Endpoints defined in `backend/main.py` and routers under `backend/routes/`:

- `GET /` — root health
- `GET /health` — detailed health (TODO stubs)
- `POST /compare` — legacy sentence-level (`backend/routes/compare.py`) — currently broken, see CONCERNS.md
- `POST /api/diff` — clause-level pipeline (`backend/routes/diff.py` → `ml/pipeline.py::run_diff()`)
- `GET /api/diff/health`
- `GET /explanation/{comparison_id}` — async explanation polling (stub)
- `GET /explanation/test/alive`

## Webhooks

- None (incoming or outgoing)

## Feature Flags & Staged Integrations

- `USE_REAL_ALIGN` (env var, default `0`) — `backend/services/align.py`
  - `0` → `ml/_mock_align.py::mock_align()`
  - `1` → `backend/services/_align_impl.py::semantic_hungarian()` (vendored from origin/main, snapshot-only)
- `ALIGNMENT_PRE_PRUNES` — `ml/thresholds.py` (default `False`); flip to `True` if `USE_REAL_ALIGN=1` to suppress double-prune
- Embedding source: OpenAI (active) vs. local sentence-transformers (`QUICK_FIXES/fix1_embeddings_local.py`) — no flag yet, would require code change

## Environment Configuration

**Development:**
- Required: `OPENAI_API_KEY`
- Optional: `CORS_ORIGINS`, `PORT`, `HOST`, `ANTHROPIC_API_KEY` (unused), `USE_REAL_ALIGN`
- Templates: `backend/.env.example`, `frontend/.env.example`
- Vite proxy: `/api` → `http://localhost:8000`

**Staging / Production:**
- Not configured

---

*Integration audit: 2026-05-09*
*Update when adding/removing external services*
