# Codebase Concerns

**Analysis Date:** 2026-05-09

## Tech Debt

**`sys.path` injection still active:**
- Issue: `backend/main.py` and `ml/demo.py` inject the project root into `sys.path` so sibling packages (`backend.*`, `ml.*`) are importable
- Files: `backend/main.py`, `ml/demo.py`, `tests/conftest.py`
- Why: No shared parent package; absolute imports require sys.path setup
- Impact: Fragile to layout changes; cannot run modules from arbitrary cwd
- Fix approach: Reorganize into a single root package, or document this as intentional and lock down with tests

**Duplicated mock-embedding helpers:**
- Issue: `_build_mock_embeddings()`, `_unit()`, `_near()` appear identically in two places
- Files: `ml/demo.py`, `tests/test_pipeline.py`
- Why: Helpers were not extracted to a shared module
- Impact: Drift risk between demo and tests
- Fix approach: Move helpers into `tests/conftest.py` (or a `tests/_helpers.py`) and import from both call sites

**Legacy `/compare` endpoint with stale mock data:**
- Issue: `backend/routes/compare.py` + `backend/services/ml_client.py` return hardcoded similarity scores (0.92/0.75/0.55); not maintained
- Files: `backend/routes/compare.py`, `backend/services/ml_client.py`
- Why: Original placeholder predates the ML branch
- Impact: Frontend wired to `/compare` will see stale mock results that diverge from `/api/diff`
- Fix approach: Either deprecate `/compare` or have it call `run_diff` and adapt to the legacy schema

**Unused backward-compat alias:**
- Issue: `score_alignment = score_pairs` defined but unused
- Files: `ml/scoring.py`
- Why: Refactor leftover
- Impact: Negligible; dead code
- Fix approach: Remove

## Known Bugs / Integration Risks

**Double-pruning when Winston's real align() lands:**
- Issue: Winston's `semantic_hungarian()` (in `origin/main:ml/alignment_methods.py`) pre-prunes at `match_threshold`; ML slice then re-prunes via `REMOVED_THRESHOLD` in `classify_pairs`. Both firing on the same pairs surfaces every borderline pair as removed/added instead of modified.
- Files: `ml/classification.py`, `notes/integration-with-winston.md`
- Why: Winston's branch and ML branch developed independently
- Impact: HIGH — visibly degrades output quality
- Fix approach: Pick one threshold owner. Recommended (per notes): pass `split_below_threshold=False` post-Hungarian and trust Winston's `match_threshold`. Pin the decision before merge.

**Schema mismatch between Winston's align() and AlignmentResult:**
- Issue: Winston returns `{method, pairs, similarity_matrix}` with mixed status ("matched", "added", "deleted", "merged", "split") in a flat `pairs` list. ML expects `AlignmentResult{pairs: [AlignedPair], unmatched_before, unmatched_after}`. "merged" has no representation in current schema.
- Files: `backend/models/schemas.py`, `notes/integration-with-winston.md` (adapter sketch lines 186–234)
- Impact: HIGH — direct wire-up will fail
- Fix approach: Implement the adapter sketch in `backend/services/align.py`; decide on `paired_with: list[str]` vs `Classification = "merged"` extension before merging Winston's code

**Merging not actually concatenated:**
- Issue: Winston's code tags merged pairs but does not concatenate texts into a single ClauseUnit
- Files: `origin/main:ml/alignment_methods.py`, `ML_ARCHITECTURE.md` §1, §6
- Impact: MEDIUM — undercounts clauses on real merges
- Fix approach: Add merge-text-concatenation in the alignment adapter

**Frontend types stale vs new contract:**
- Issue: Frontend TypeScript types reflect legacy `/compare` shapes, not `DiffResponse`
- Files: `frontend/src/types/api.ts` (per handoff notes)
- Impact: HIGH for UI integration
- Fix approach: Frontend lead regenerates TS types from `backend/models/schemas.py`

## Security

**API key validation only at boot, only as warning:**
- Issue: `backend/main.py:21-30` warns to stderr if `OPENAI_API_KEY` is missing but does not block startup; `/api/diff` then fails per-request with a generic 500
- Files: `backend/main.py`, `ml/embeddings.py`, `ml/concepts.py`
- Risk: Silent misconfiguration; users get cryptic errors at request time
- Fix approach: Add a stricter check that raises during startup unless an explicit `ALLOW_NO_KEYS=1` is set (for tests)

**Permissive CORS:**
- Issue: `allow_methods=["*"]`, `allow_headers=["*"]` in `backend/main.py`
- Risk: Acceptable for hackathon, anti-pattern for prod
- Fix approach: Restrict to `POST` + `Content-Type` before deploy

**Unredacted exception messages logged / returned:**
- Issue: `backend/routes/diff.py:20` returns raw exception text via `HTTPException(500, detail=...)`; `ml/concepts.py:88-92` prints exceptions to stderr
- Risk: Low (unlikely to contain secrets), but no redaction layer
- Fix approach: Wrap exceptions; log full traceback server-side, return generic message to client

## Performance Bottlenecks

**No caching of identical-input pipelines:**
- Issue: Identical `(before, after)` pairs re-run embeddings + concept extraction every request
- Files: `ml/pipeline.py`
- Impact: Cost waste in production, no impact on hackathon
- Fix approach: Deferred per `ML_ARCHITECTURE.md` §5

**Document size cap may be too tight:**
- Issue: `DiffRequest` enforces `max_length=20_000` per side; real contracts often exceed this
- Files: `backend/models/schemas.py`
- Impact: Will reject realistic inputs
- Fix approach: Raise cap when chunking lands

**Concept extraction truncates lossily at 60K chars:**
- Issue: Hardcoded `MAX_CONCEPT_INPUT_CHARS = 60_000` with `[TRUNCATED at 60,000 chars]` marker
- Files: `ml/thresholds.py`, `ml/concepts.py`
- Impact: Acceptable per spec; flagged for later chunking work

## Fragile Areas

**Alignment seam (`backend/services/align.py`):**
- Why fragile: Currently delegates to `ml/_mock_align`; swap-in of Winston's real algorithm changes the output schema
- Files: `backend/services/align.py`, `ml/_mock_align.py`
- Common failures: Schema mismatch, double-pruning, missing merge representation
- Safe modification: Write adapter + tests against both mock and real outputs before flipping the import
- Test coverage: NONE for the adapter (gap)

**Clause ID format (`b{n}` / `a{n}`) assumed throughout:**
- Why fragile: `ml/pipeline.py` checks `id.startswith("b")` / `id.startswith("a")` to attribute split clauses; if Winston's align() returns different IDs, split logic silently breaks
- Files: `ml/pipeline.py`, `ml/_mock_align.py`, `ml/metrics.py`
- Safe modification: Document ID format in `ClauseUnit` docstring; assert in alignment adapter
- Test coverage: Implicit via `tests/test_pipeline.py`

**Concept extraction silent failure:**
- Why fragile: Broad `except Exception` returns empty + `status="failed"`; failures hidden unless stderr is read
- Files: `ml/concepts.py:88-92`
- Safe modification: Switch to `logging` module so failures are aggregable
- Test coverage: None for failure path

## Scaling Limits

**No persistence — all state lost on restart:**
- Current capacity: per-request only
- Limit: legacy `explanation_store` dict grows unbounded in `backend/routes/compare.py`
- Symptoms at limit: memory leak in long-running process
- Scaling path: Move legacy explanation cache to Redis or strip the endpoint

**OpenAI rate limits:**
- Current capacity: tier-dependent (default 3500 req/min for embeddings)
- Symptoms at limit: tenacity retries 6× with backoff, then re-raises → 500
- Scaling path: Acceptable for hackathon; add request-level concurrency limiter if scaling up

## Dependencies at Risk

**`anthropic` 0.39.0 declared but unused:**
- Risk: Dead dependency; bloat without value yet
- Files: `backend/requirements.txt`
- Impact: Negligible
- Fix approach: Either wire up the explanation flow OR drop the dependency until needed

**`scikit-learn`, `scipy` declared but unused:**
- Risk: Same as above — pre-emptively installed, never imported
- Files: `backend/requirements.txt`
- Fix approach: Drop or use

**`pydantic` missing from `ml/requirements.txt`:**
- Issue: `ml/classification.py`, `ml/concepts.py` import pydantic; mirror file omits it
- Files: `ml/requirements.txt`
- Impact: ML slice cannot install standalone as advertised
- Fix approach: Add `pydantic==2.9.2` to `ml/requirements.txt`

## Missing Critical Features

**Merged-clause representation undefined:**
- Problem: `ClauseRendering.paired_with: Optional[str]` cannot represent 1:N or N:1 merges
- Files: `backend/models/schemas.py`
- Blocks: Faithful representation of Winston's "merged" status
- Implementation complexity: Low — extend `paired_with` to `Optional[str | list[str]]` OR add `Classification = "merged"`

**Concept evidence not linked to clause IDs:**
- Problem: `Concept.evidence_before_ids` / `evidence_after_ids` declared but never populated by `ml/concepts.py`
- Files: `ml/concepts.py`, `backend/models/schemas.py`
- Blocks: "Click concept → highlight clause" UX
- Implementation complexity: Medium — substring-match evidence quotes against clauses post-extraction

**Async LLM-explanation flow stubbed but not wired:**
- Problem: `BackgroundTasks` reference in `backend/routes/compare.py:168` is a TODO; `routes/explanation.py` polling endpoint exists but receives nothing
- Files: `backend/routes/compare.py`, `backend/routes/explanation.py`
- Blocks: Anthropic-powered explanations
- Implementation complexity: Medium — wire Anthropic SDK + background task

## Test Coverage Gaps

**No route-level tests for `/api/diff`:**
- What's not tested: HTTP layer, CORS, request validation, status code mapping
- Files: `backend/routes/diff.py` — no `tests/test_routes_diff.py`
- Risk: Schema or routing regressions slip through unit tests
- Priority: HIGH
- Difficulty: Low — FastAPI `TestClient` + monkeypatched `run_diff`

**No tests for the alignment adapter:**
- What's not tested: `backend/services/align.py` translation between Winston's output and `AlignmentResult`
- Files: `backend/services/align.py`
- Risk: Adapter bugs surface at integration time
- Priority: HIGH (write before merging Winston's code)
- Difficulty: Medium — needs sample Winston output fixtures

**No failure-path test for concept extraction:**
- What's not tested: That `extract_concepts` returns empty + `status="failed"` on exception
- Files: `ml/concepts.py`
- Priority: MEDIUM
- Difficulty: Low — patch `AsyncOpenAI` to raise

**No CORS smoke test:**
- What's not tested: Wide-open CORS configuration
- Files: `backend/main.py`
- Priority: LOW
- Difficulty: Low

## Documentation Gaps

**Threshold-tuning runbook missing:**
- Issue: `ML_ARCHITECTURE.md` §7 references a "5-example, 20-minute tuning sprint" but no script exists
- Files: `ml/thresholds.py`
- Fix approach: Add `ml/tune_thresholds.py` once real embeddings are reachable

**No runbook for `/api/diff` deployment:**
- Issue: `README.md` documents legacy endpoints; doesn't call out that `/api/diff` requires `OPENAI_API_KEY`
- Files: `README.md`
- Fix approach: Add a section once API stabilizes

---

*Concerns audit: 2026-05-09*
*Update as issues are fixed or new ones discovered*
