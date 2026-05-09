# Codebase Concerns

**Analysis Date:** 2026-05-09 (post-merge of `origin/main`)

> The merge from `origin/main` brought a multi-method alignment toolkit, an aggregator service, a multilingual tokenizer rewrite, and several "QUICK_FIXES" patch files. It also surfaced or created several integration breaks. Cross-reference `CRITICAL_ANALYSIS.md`, `FIXES_NEEDED.md`, and `notes/integration-with-winston.md` for the most up-to-date plans.

## Merge Impact Summary

- ✅ **Tokenizer rewrite resolves the multilingual concern** — wtpsplit + spaCy multi-model + regex fallback supersedes the old English-only spaCy gate
- ✅ **Padding bug** in `_run_hungarian_with_threshold` updated (1.0 → 10.0) per `CRITICAL_ANALYSIS.md`
- ❌ **Legacy `/compare` is now broken at runtime** — `backend/services/ml_client.py` imports `ml.semantic_engine`, which doesn't exist
- ❌ **Six QUICK_FIXES patch files were merged but not applied** — they live in `QUICK_FIXES/` as separate copy-paste recipes
- ⚠️ **Multiple alignment files now coexist** without a unifying dispatcher: `_align_impl.py`, `_mock_align.py`, `alignment_methods.py`, `smith_waterman_alignment.py`
- ⚠️ **Schema mismatch** between merged alignment methods and the new pipeline's `AlignmentResult` — adapter described in `notes/integration-with-winston.md`, not yet implemented
- ⚠️ **Documentation drift**: `ml/NICKOLAS_README.md` describes the pre-refactor architecture (sentence-level, GREEN/YELLOW/RED) and contradicts `ML_ARCHITECTURE.md`

---

## Known Bugs

**Legacy `/compare` route broken — `ml.semantic_engine` does not exist:**
- Files: `backend/services/ml_client.py`, `backend/routes/compare.py`
- Issue: `ml_client.py` imports `ml.semantic_engine.compare_sentences()`. There is no `ml/semantic_engine.py` in the tree → `ModuleNotFoundError` on first POST `/compare`.
- Why: Merge brought the consumer (`ml_client.py`) but not the producer module (`ml/semantic_engine.py`).
- Impact: `/compare` endpoint fails immediately. Anything still pointing at `/compare` (frontend or external) is dead.
- Fix approach: Either (a) create `ml/semantic_engine.py` exposing `compare_sentences(v1, v2)` that wraps `ml/alignment_methods.py` + `ml/embeddings.py`, or (b) deprecate `/compare` and redirect callers to `/api/diff`. (b) is the cleaner choice given `/api/diff` already covers the use case.
- Status: NEW (introduced by merge)

**Stub remains: async LLM explanations are commented out:**
- Files: `backend/routes/compare.py`
- Issue: `# TODO: Implement async explanation generation`; the `background_tasks.add_task(...)` call is commented. `QUICK_FIXES/fix3_async_explanations.py` exists but is not applied.
- Impact: `GET /explanation/{comparison_id}` always returns empty.
- Fix approach: Apply `QUICK_FIXES/fix3_async_explanations.py`. Or, if `/compare` is being deprecated (see above), drop the explanation route and the polling store altogether.
- Status: STILL OPEN

**Embedding retry exhaustion is uncaught:**
- Files: `ml/embeddings.py`, `backend/routes/diff.py`
- Issue: Tenacity re-raises after 6 attempts; the exception bubbles to the route's generic `except Exception` and returns an opaque 500.
- Impact: OpenAI outages produce a confusing error. No partial response.
- Fix approach: Catch `_RETRYABLE_OPENAI_ERRORS` after exhaustion in `embed_clauses()` and either return a structured error or a degraded response.
- Status: STILL OPEN

**Concept extraction has no retry:**
- Files: `ml/concepts.py`, `ml/pipeline.py`
- Issue: A single OpenAI call wrapped in `except Exception` → returns `status="failed"`. Transient connection blips look the same as a model refusal.
- Fix approach: Add tenacity retry mirroring `ml/embeddings.py`. Distinguish retryable errors from refusals.
- Status: STILL OPEN

**Bare `except:` in tokenizer guard imports:**
- Files: `backend/services/tokenizer.py`
- Issue: Optional-dependency probes (`try: import wtpsplit ... except: ...`) are written too broadly.
- Impact: Real load failures (OOM, permission, corrupted model) are silently masked as "library unavailable".
- Fix approach: Narrow to `except (ImportError, OSError):`.
- Status: STILL OPEN

## Tech Debt

**Multiple alignment implementations, no unified dispatcher:**
- Files: `backend/services/align.py`, `backend/services/_align_impl.py`, `ml/_mock_align.py`, `ml/alignment_methods.py`, `ml/smith_waterman_alignment.py`
- Issue: `align.py` only routes between `_mock_align` and the vendored `_align_impl`. The merged `alignment_methods.py` (5 methods including TF-IDF, semantic Hungarian, greedy w/ merges, adaptive) and `smith_waterman_alignment.py` are not reachable from the API.
- Impact: Confusing surface — clear which file is "live" only by reading `align.py`. Risk of editing the wrong one.
- Fix approach: Decide which method wins, wire it through `align.py`. Delete (or move to `ml/experiments/`) the rest. Update `notes/integration-with-winston.md` once decided.
- Status: NEW (merge layered the complexity)

**Schema mismatch between merged alignment methods and new pipeline:**
- Files: `ml/alignment_methods.py`, `backend/models/schemas.py`, `backend/services/align.py`, `notes/integration-with-winston.md`
- Issue: `alignment_methods.py` returns `{"pairs": [...flat list with adds+dels mixed...], "similarity_matrix": ndarray}`. `AlignmentResult` expects `pairs` (matched only), `unmatched_before`, `unmatched_after` as separate buckets.
- Impact: Cannot wire merged methods into `align.py` without an adapter shim. Adapter is sketched in `notes/integration-with-winston.md` but not implemented.
- Fix approach: Implement the adapter in `backend/services/align.py` per the notes. Or rewrite the chosen method to return `AlignmentResult` directly.
- Status: STILL OPEN

**Double threshold pruning between alignment and classification:**
- Files: `ml/alignment_methods.py`, `ml/classification.py`, `ml/thresholds.py`, `notes/integration-with-winston.md`
- Issue: Merged `_run_hungarian_with_threshold` prunes < 0.6 inside the matcher; `classify_pairs()` re-prunes < `REMOVED_THRESHOLD = 0.65`. Pairs in 0.60–0.65 get split into added+removed instead of staying as `modified`.
- Fix approach: Pick one source of truth. Recommended: drop the post-Hungarian re-prune and set `ALIGNMENT_PRE_PRUNES = True` in `ml/thresholds.py`. Or lower the matcher's threshold to ~0.45 and trust the classifier.
- Status: STILL OPEN

**`USE_REAL_ALIGN` flag never flipped:**
- Files: `backend/services/align.py`
- Issue: Even after the merge, the dispatcher defaults to `_mock_align`. The vendored `_align_impl.py` is reachable only when `USE_REAL_ALIGN=1`, and nothing has been validated against it.
- Fix approach: Once the alignment subsystem is consolidated (see "Multiple alignment implementations" above), pick a default and remove the flag — or keep the flag and validate the on-path with a real test.
- Status: STILL OPEN

**Stale documentation: `ml/NICKOLAS_README.md`:**
- Files: `ml/NICKOLAS_README.md`
- Issue: Describes the pre-refactor architecture — sentence-level pipeline, GREEN/YELLOW/RED classification, references files like `ml/semantic_engine.py` that don't exist. Contradicts the current `ML_ARCHITECTURE.md`.
- Impact: Misleads anyone trying to onboard or apply QUICK_FIXES.
- Fix approach: Add a banner: "Pre-merge guidance — see `ML_ARCHITECTURE.md` and `notes/integration-with-winston.md` for current state." Or delete it.
- Status: STILL OPEN

**Inconsistent input size limits:**
- Files: `backend/models/schemas.py`, `ml/concepts.py`
- Issue: `DiffRequest` caps `before`/`after` at 20_000 chars; concept extraction independently truncates at 60_000. Demo runners have no cap.
- Fix approach: Pick a single limit (e.g., 30_000 per side) and apply uniformly. Document in the OpenAPI description.
- Status: STILL OPEN

**Standalone "test" scripts use `test_*` prefix:**
- Files: `test_alignment.py`, `test_all_alignments.py`, `ml/quick_test.py`
- Issue: Files named like pytest tests but are standalone scripts (use `if __name__ == "__main__":`). Pytest skips them only because `pytest.ini` restricts collection to `tests/`. Easy to mistake for tests when scanning the tree.
- Fix approach: Rename to `bench_*.py`, `demo_*.py`, or move under `scripts/`. Or wrap them as real pytest tests.
- Status: NEW (introduced by merge)

## Security

**Live OPENAI_API_KEY visible in `backend/.env` (working copy):**
- Files: `backend/.env`
- Issue: A real `sk-proj-…` key is present in the local working copy.
- Status: ✅ **`backend/.env` is NOT and was never tracked in git** — root `.gitignore` always matched `.env`, and `git log --all --diff-filter=A -- '**/.env'` returns nothing. The previous map's claim that it was committed was a false positive.
- Remaining risk: if the file content was ever shared (Slack, screenshot, copy-paste), the key is still exposed elsewhere even though git history is clean.
- Recommendation: low-cost belt-and-suspenders — rotate the key once before any public sharing of the repo.

**Bare `except:` (tokenizer):** see Known Bugs.

## Performance

**No scaling analysis post-merge:**
- Files: `ml/alignment_methods.py`, `CRITICAL_ANALYSIS.md`
- Issue: Hungarian assignment is O(n³). Test data uses 3–8 sentences. No benchmarks against documents with 50+ / 100+ / 500+ sentences.
- Fix approach: Add a perf test against synthetic large documents. If Hungarian becomes a bottleneck, evaluate the greedy-with-merges path or Smith-Waterman.
- Status: STILL OPEN

## Fragile Areas

**Vendored Winston code (`_align_impl.py`):**
- Files: `backend/services/_align_impl.py`
- Issue: Snapshot of code from origin/main. Not source-of-truth; will diverge from upstream over time.
- Fix approach: Once alignment is consolidated, delete the vendored copy and import directly. Or keep the vendor and pin the version (note in module docstring).
- Status: STILL OPEN

**Async pipeline called from a sync stub:**
- Files: `backend/routes/compare.py`, `backend/services/ml_client.py`
- Issue: `compare_sentences_ml()` is sync; if anyone wires it to `await run_diff(...)` later, it'll raise.
- Fix approach: Either deprecate the route or make the entire chain async (`/compare` handler is already `async def`).
- Status: STILL OPEN

## Test Coverage Gaps

**No endpoint integration tests:**
- Files: `tests/`
- Issue: pytest covers ML steps in isolation. There is no test that POSTs to `/api/diff` or `/compare` against the FastAPI `TestClient`.
- Impact: A breaking change like the missing `ml.semantic_engine` would be caught at runtime, not in CI.
- Fix approach: Add `tests/test_diff_endpoint.py` (and `tests/test_compare_endpoint.py` if `/compare` survives) using `httpx.AsyncClient` against the FastAPI app with mocked OpenAI.
- Status: STILL OPEN

**No live OpenAI smoke test:**
- Files: `tests/`
- Issue: All OpenAI calls are mocked. No gated live-API smoke test.
- Fix approach: Add a `pytest -m live` marker for one tiny end-to-end run; skip in CI by default.
- Status: STILL OPEN

**Threshold-tuning corpus unused:**
- Files: `ml/test_cases.py`
- Issue: 12 hand-built cases exist but no test asserts against them.
- Fix approach: Wire into a regression test (`tests/test_threshold_corpus.py`) that runs `run_diff()` (with mocked embeddings) and checks classifications against expected per-case outputs.
- Status: STILL OPEN

**Smith-Waterman is implemented but unused:**
- Files: `ml/smith_waterman_alignment.py`, `ml/demo_alignment_comparison.py`
- Issue: `CRITICAL_ANALYSIS.md` ranks it 9/10 on correctness vs. Hungarian's 6/10. Not benched against `ml/test_cases.py`. Not added to `demo_alignment_comparison.py` results table.
- Fix approach: Add to the comparison demo. If it wins, wire it through `align.py`.
- Status: STILL OPEN

## Missing Critical Features

**Health checks are stubs:**
- Files: `backend/main.py`
- Issue: `/health` returns `"not_checked"` for spaCy and OpenAI.
- Fix approach: `try: spacy.load(...)` for spaCy; one cheap OpenAI call (`models.list()`) for OpenAI.
- Status: STILL OPEN

**No structured logging / observability:**
- Files: across
- Issue: `print(..., file=sys.stderr)` only. No request IDs, timing, or telemetry.
- Fix approach: Add `logging` config (JSON formatter), per-request correlation IDs, optional OTel.
- Status: STILL OPEN

## Dependencies at Risk

**scipy 1.14.1 / scikit-learn 1.5.2:**
- Files: `backend/requirements.txt`, `ml/requirements.txt`
- Issue: Both have known low-severity CVEs. Not exploitable in this app's surface.
- Fix approach: `pip-audit` in CI; bump on routine maintenance.
- Status: STILL OPEN

**No lockfiles committed:**
- Files: `backend/requirements.txt`, `ml/requirements.txt`, `frontend/package.json`
- Issue: Pinned exacts in `requirements.txt`, but no `*.lock` for transitive deps. No `package-lock.json` for the frontend.
- Fix approach: Generate and commit `package-lock.json`. `pip-compile` for Python.
- Status: STILL OPEN

---

*Concerns audit: 2026-05-09*
*Update as issues are fixed or new ones discovered*
