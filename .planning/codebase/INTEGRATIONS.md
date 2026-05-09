# External Integrations

**Analysis Date:** 2026-05-09

## APIs & External Services

**OpenAI (Primary, active):**
- Used for embeddings (`text-embedding-3-small`) and concept extraction (`gpt-4o-mini`)
- SDK: `openai==1.54.3` (AsyncOpenAI client)
- Auth: `OPENAI_API_KEY` env var (loaded from `backend/.env`)
- Embedding call: `ml/embeddings.py` — `AsyncOpenAI().embeddings.create(...)`, batched with L2 normalization
- Concept extraction call: `ml/concepts.py` — `AsyncOpenAI().chat.completions.parse(...)` with structured `ConceptDiff` schema
- Retry strategy: `tenacity` exponential backoff, `stop_after_attempt(6)` on `RateLimitError`, `APIConnectionError`, `APIStatusError` (`ml/embeddings.py`)
- Input cap: 60,000 chars per side for concept extraction (`MAX_CONCEPT_INPUT_CHARS` in `ml/thresholds.py`)

**Anthropic (Reserved, not integrated):**
- SDK installed (`anthropic==0.39.0`) but no code path uses it yet
- Auth env var declared: `ANTHROPIC_API_KEY` (in `backend/.env.example`)
- Intended for explanation generation per `README.md`, currently unimplemented

## Data Storage

**Databases:**
- None — no persistent database
- All embeddings computed on-the-fly per request

**Vector Stores:**
- None — no Pinecone / Weaviate / Qdrant / Chroma / FAISS detected
- Cosine similarity computed in-process via NumPy dot products (`ml/scoring.py`)

**File Storage:**
- None
- `test_data/` holds sample input documents for manual testing only

**Caching:**
- None — no Redis, no in-memory cache layer

**In-process state:**
- Explanation polling store: `backend/routes/compare.py` defines `explanation_store` as a Python dict keyed by UUID `comparison_id`
- Lost on restart; not safe for multi-process deployment

## Authentication & Identity

**Auth Provider:**
- None — no JWT, OAuth, session, or per-user auth
- API keys (`OPENAI_API_KEY`, future `ANTHROPIC_API_KEY`) are shared service credentials, not per-user

**OAuth:**
- Not applicable

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, no Rollbar)

**Analytics:**
- Not detected

**Logs:**
- stdout / stderr only via `print(..., file=sys.stderr)` — no `logging` module configured
- Startup warnings for missing env vars in `backend/main.py`
- Concept extraction failures logged to stderr in `ml/concepts.py`

## CI/CD & Deployment

**Hosting:**
- Not deployed — local development only

**CI Pipeline:**
- Not detected — no `.github/workflows/`, no `Makefile`, no `Dockerfile`

## Environment Configuration

**Development:**
- Required env vars: `OPENAI_API_KEY` (for `/api/diff`), optionally `CORS_ORIGINS`, `PORT`, `HOST`, `ANTHROPIC_API_KEY`
- Templates: `backend/.env.example`, `frontend/.env.example`
- Frontend dev: Vite proxy at `http://localhost:5173` forwards `/api` → `http://localhost:8000`
- ⚠️ **`backend/.env` appears to contain a real OPENAI_API_KEY and is tracked in git — see CONCERNS.md #1**

**Staging / Production:**
- Not configured

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## API Surface

Endpoints defined in `backend/main.py` and routers under `backend/routes/`:

- `GET /` — root health
- `GET /health` — detailed health (spaCy / OpenAI checks are TODO stubs)
- `POST /api/diff` — primary semantic diff endpoint (`backend/routes/diff.py` → `ml/pipeline.py::run_diff()`)
- `GET /api/diff/health` — diff endpoint health
- `POST /compare` — legacy mock-only compare endpoint (`backend/routes/compare.py`)
- `GET /explanation/{comparison_id}` — async explanation polling (legacy)
- `GET /explanation/test/alive` — explanation health stub

## Feature Flags & Staged Integrations

- `USE_REAL_ALIGN` (default `0`) — gates `backend/services/_align_impl.py` (vendored Winston `semantic_hungarian`) vs. `ml/_mock_align.py` mock
- When flipped on, real path calls `ml/embeddings.py::embed_texts()` for pair scoring
- See `notes/integration-with-winston.md` for the staged rollout plan

---

*Integration audit: 2026-05-09*
*Update when adding/removing external services*
