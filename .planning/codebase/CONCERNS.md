# Codebase Concerns

**Analysis Date:** 2026-05-09

> Concerns surfaced by parallel exploration agents. Critical items at top. Cross-reference `notes/integration-with-winston.md` and `notes/multilingual-handoff.md` for the most up-to-date plans.

## Security

**Live OpenAI API key in tracked `.env`:**
- Files: `backend/.env`
- Issue: A real `OPENAI_API_KEY` (`sk-proj-…`) appears in the working copy and the file is not gitignored. Risk of public exposure if the repo is ever published or shared.
- Why: Quickstart shortcut; `.env` was created and not added to `.gitignore`.
- Impact: Token theft, billing abuse, potential malicious use of your account.
- Fix approach: (1) Rotate the key in the OpenAI dashboard immediately. (2) Add `backend/.env` to `.gitignore`. (3) Purge from history: `git rm --cached backend/.env && git commit -m "chore: untrack .env"` and consider rewriting history if it was ever pushed. (4) Keep only `backend/.env.example`.

**Bare `except:` in tokenizer fallback:**
- Files: `backend/services/tokenizer.py`
- Issue: `try: spacy.load(...) except: SPACY_AVAILABLE = False` swallows every exception, including OOM, permission errors, or import-time failures.
- Why: Originally added to handle both `ImportError` and missing model, but written too broadly.
- Impact: Real load failures are masked; tokenization silently degrades to a regex splitter.
- Fix approach: Narrow to `except (ImportError, OSError):`. (Or remove spaCy entirely per multilingual fix below.)

## Tech Debt

**Uncommitted change to `backend/models/schemas.py`:**
- Files: `backend/models/schemas.py`
- Issue: `ConceptStatus` literal now includes `"removed"` (matches `ml/concepts.py`) but the change is unstaged/uncommitted.
- Why: Schema evolved alongside concept extraction; not yet committed.
- Impact: Tests/CI run against stale schema if a worker re-clones; reproducibility gap.
- Fix approach: Commit with a tight message — e.g. `schemas: add 'removed' to ConceptStatus literal`.

**Double threshold pruning between Winston and ML classifier:**
- Files: `ml/classification.py`, `ml/pipeline.py`, `ml/thresholds.py`, `notes/integration-with-winston.md`
- Issue: `_align_impl.py` prunes pairs with cosine < 0.6 inside the Hungarian matcher; `classify_pairs()` re-prunes < `REMOVED_THRESHOLD = 0.65` afterward. Borderline pairs (0.60–0.65) get split into added+removed instead of staying as `modified`.
- Why: Two layers were tuned independently before integration.
- Impact: UX shows spurious add/delete pairs that should be a single modification.
- Fix approach: Pick one source of truth. Recommended: drop the post-Hungarian re-prune in `classify_pairs()` and set `ALIGNMENT_PRE_PRUNES = True` in `ml/thresholds.py`. Or lower Winston's match threshold to ~0.45 and keep our classifier as authoritative.

**Legacy `/compare` route is mock-only:**
- Files: `backend/routes/compare.py`, `backend/services/ml_client.py`
- Issue: `compare_sentences_ml()` returns hardcoded mock data (`# TODO: call actual ML pipeline`). Uses old `green/yellow/red` schema.
- Why: Superseded by `/api/diff` but never removed.
- Impact: Frontend code paths that still hit `/compare` see fake results. Confusing dual contract.
- Fix approach: Either deprecate (return 410 / redirect to `/api/diff`) or wire it to `run_diff()` and translate the response.

**Sync stub in legacy compare path will break async wiring:**
- Files: `backend/routes/compare.py`, `backend/services/ml_client.py`
- Issue: `compare_sentences_ml()` is sync; if anyone wires it to `await run_diff(...)` later, it'll raise.
- Fix approach: Make `ml_client.compare_sentences_ml` async and `await` it from the route (the route handler is already async).

**Inconsistent input size limits:**
- Files: `backend/models/schemas.py`, `ml/concepts.py`
- Issue: API caps `before`/`after` at 20_000 chars; concept extraction independently truncates at 60_000. CLI/demo entry has no limit.
- Fix approach: Pick one boundary (e.g., 30_000 per side, ~60k combined) and apply uniformly. Document in OpenAPI description.

## Known Bugs

**English-only tokenizer breaks multilingual diffs:**
- Files: `backend/services/tokenizer.py`, `notes/multilingual-handoff.md`
- Issue: spaCy `en_core_web_sm` only handles Latin punctuation; non-English (CJK `。！？`, Arabic `؟`, Devanagari `।`) falls back to naive `split(". ")` and produces malformed clauses.
- Why: Hackathon scope was English-only.
- Impact: Cross-lingual diffs (a stated future feature) silently produce wrong clause boundaries.
- Fix approach: Drop spaCy; use the regex sentence splitter spec'd in `notes/multilingual-handoff.md`. Drop `spacy==3.8.2` from `backend/requirements.txt` and remove the `python -m spacy download` step from `README.md`.

## Fragile Areas

**Winston adapter shim is staged behind a flag:**
- Files: `backend/services/align.py`, `backend/services/_align_impl.py`, `notes/integration-with-winston.md`
- Issue: `USE_REAL_ALIGN=0` by default. Real path drops Winston's `"merged"` and `"split"` status values silently and doesn't concatenate merged-text into a single `ClauseUnit`.
- Why: Winston's algorithm is not finalized on his branch; vendored snapshot in `_align_impl.py` is staging only.
- Impact: When flipped on prematurely, merged clauses vanish (count mismatch). Not safe for real traffic.
- Fix approach: Wait for Winston's final push, then follow the 5-step plan in `notes/integration-with-winston.md`. Decide whether to handle merged/split now or defer.

**Embedding retry exhaustion is uncaught:**
- Files: `ml/embeddings.py`, `backend/routes/diff.py`
- Issue: Tenacity re-raises after 6 attempts; the exception bubbles to the route's generic `except Exception` and returns an opaque 500.
- Why: No graceful degradation path designed.
- Impact: OpenAI outages produce a confusing error with no fallback. No partial response.
- Fix approach: Catch `_RETRYABLE_OPENAI_ERRORS` after exhaustion in `embed_clauses()` and either return a structured error or a degraded response (e.g., metrics from Levenshtein only).

**Concept extraction has no retry:**
- Files: `ml/concepts.py`, `ml/pipeline.py`
- Issue: A single OpenAI call wrapped in `except Exception` → returns `status="failed"`. Transient connection blips look the same as a model refusal.
- Fix approach: Add tenacity retry mirroring `ml/embeddings.py`. Distinguish retryable errors from refusals.

## Scaling Limits

**No persistence:**
- Files: `backend/routes/compare.py` (`explanation_store`)
- Issue: Explanation polling state lives in a process-local dict; lost on restart and unsafe across multiple workers.
- Impact: Can't horizontally scale the legacy compare flow.
- Fix approach: If `/compare` survives, move state to Redis or drop the polling pattern entirely.

**Multilingual thresholds not calibrated:**
- Files: `ml/thresholds.py`, `notes/multilingual-handoff.md`
- Issue: `STABLE_THRESHOLD=0.93` / `MODIFIED_THRESHOLD=0.65` are tuned for same-language pairs. Faithful translations sit around 0.80–0.88, so most cross-lingual pairs will be tagged `modified`.
- Impact: False positives for cross-lingual diffs.
- Fix approach: Run the threshold-tuning sprint (`ML_ARCHITECTURE.md` §7) once translation pairs are available. Config-only change in `ml/thresholds.py`.

## Test Coverage Gaps

**`ml/test_cases.py` is not a real test suite:**
- Files: `ml/test_cases.py`
- Issue: Contains 12+ fixture cases for threshold tuning, but no pytest assertions. Naming overlaps with pytest convention; only excluded because `pytest.ini` restricts collection to `tests/`.
- Fix approach: Rename to `ml/_threshold_tuning_corpus.py` to make intent obvious. Wire into a real regression test once thresholds stabilize.

**Legacy `/compare` route untested:**
- Files: `backend/routes/compare.py`, `backend/services/ml_client.py`
- Issue: No tests cover the legacy mock path or the in-memory explanation store.
- Fix approach: Either deprecate (no tests needed) or add `tests/test_compare_route.py`.

**No live OpenAI integration test:**
- Files: `tests/`
- Issue: All OpenAI calls are mocked. No smoke test against the real API.
- Fix approach: Add a gated integration test (e.g., `pytest -m live`) that exercises a tiny diff against the real API. Skip in CI by default.

## Missing Critical Features

**Health check endpoints are stubs:**
- Files: `backend/main.py`
- Issue: `/health` returns `"not_checked"` for spaCy and OpenAI.
- Fix approach: Implement quick checks — `spacy.load(...)` in a try, an inexpensive OpenAI `models.list()` call.

**No structured logging / observability:**
- Files: across the codebase
- Issue: Errors via `print(..., file=sys.stderr)`; no request IDs, no per-step timing, no telemetry.
- Fix approach: Add `logging` config (JSON formatter), per-request correlation IDs, optional OTel integration. Replace stderr `print` calls.

## Dependencies at Risk

**scipy 1.14.1 / scikit-learn 1.5.2:**
- Files: `backend/requirements.txt`, `ml/requirements.txt`
- Issue: Both have known low-severity CVEs (scipy: CVE-2024-35192; sklearn: CVE-2024-4685). Not exploitable in this app's surface, but flagged for awareness.
- Fix approach: Add `pip-audit` or Dependabot. Bump on next routine maintenance.

**No lockfiles committed:**
- Files: `backend/requirements.txt`, `ml/requirements.txt`, `frontend/package.json`
- Issue: Pinned exact versions in requirements but no `*.lock` to capture transitive deps. Frontend has no `package-lock.json`.
- Fix approach: Generate and commit `package-lock.json`. Consider `pip-compile` for Python.

---

*Concerns audit: 2026-05-09*
*Update as issues are fixed or new ones discovered*
