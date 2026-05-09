# External Integrations

**Analysis Date:** 2026-05-09

## APIs & External Services

**Embeddings & LLM:**
- OpenAI - `text-embedding-3-small` for clause embeddings, `gpt-4o-mini` for concept extraction
  - SDK/Client: `openai` 1.54.3 (AsyncOpenAI)
  - Used in: `ml/embeddings.py` (batch embed + L2 normalize), `ml/concepts.py` (structured output via `chat.completions.parse`)
  - Auth: `OPENAI_API_KEY` env var (no explicit pass; SDK reads env)
  - Resilience: tenacity retry decorator in `ml/embeddings.py` — `wait_random_exponential(min=1, max=30)`, 6 attempts, retries on `RateLimitError`/`APIConnectionError`/`APIStatusError`

**Anthropic (planned, not yet wired):**
- Anthropic - `claude-sonnet-*` for diff explanations
  - SDK/Client: `anthropic` 0.39.0 (declared in `backend/requirements.txt`)
  - Auth: `ANTHROPIC_API_KEY` env var (read in `backend/main.py:24`, key validation only)
  - Status: imported but no call site found; explanation flow stub at `backend/routes/compare.py:168` (TODO)

## Data Storage

**Databases:**
- None — fully stateless

**File Storage:**
- None

**Caching:**
- In-memory only: `explanation_store = {}` dict at module scope in `backend/routes/compare.py:14` (legacy `/compare` flow)

## Authentication & Identity

**Auth Provider:**
- None — no user auth on API endpoints

**OAuth Integrations:**
- None

## Monitoring & Observability

**Error Tracking:**
- None — errors logged via `print(..., file=sys.stderr)` (e.g., `ml/concepts.py:88-92`, `backend/routes/diff.py:20`)

**Analytics:**
- None

**Logs:**
- stdout/stderr only; no structured logging library

## CI/CD & Deployment

**Hosting:**
- Not yet deployed (hackathon)

**CI Pipeline:**
- None detected

## Environment Configuration

**Development:**
- Required env vars: `OPENAI_API_KEY` (required for `/api/diff`)
- Optional env vars: `ANTHROPIC_API_KEY`, `CORS_ORIGINS` (default `http://localhost:5173`), `PORT` (default 8000), `HOST`
- Secrets location: `.env` (gitignored), templates in `backend/.env.example` and `frontend/.env.example`
- Mock services: `ml/_mock_align.py` provides hand-crafted alignment for offline dev, `ml/demo.py --mock` runs the full pipeline without API keys

**Staging / Production:**
- N/A

## Webhooks & Callbacks

**Incoming:** None

**Outgoing / Background tasks:**
- FastAPI `BackgroundTasks` pattern stubbed in `backend/routes/compare.py:168` for async LLM explanation; not yet wired

## Integration Seams (Internal)

- `backend/services/align.py` - Seam between backend lead's Hungarian alignment (`ml/alignment_methods.py` on `origin/main`) and ML slice. Currently delegates to `ml/_mock_align.py`. One-line swap when Winston's real `align()` ships, plus an adapter for schema differences (see `notes/integration-with-winston.md`).
- `backend/models/schemas.py` - Locked Pydantic contract shared by API, ML pipeline, and (eventually) frontend TypeScript types.

---

*Integration audit: 2026-05-09*
*Update when adding/removing external services*
