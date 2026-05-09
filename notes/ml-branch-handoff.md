# ML branch — handoff & status

Snapshot of what's on the `ML` branch as of the first push to `origin/ML`.
Useful as: a one-pager for anyone joining the branch, a checkpoint to refer
back to, and a record of what's verified vs. what's still pending API keys.

---

## TL;DR

The ML slice from `ML_ARCHITECTURE.md` is structurally complete and unit-
tested without needing API keys. Real-API validation is the remaining gap
and only blocks once `OPENAI_API_KEY` is available.

| | Status |
|---|---|
| Code structure | ✅ Complete per ML_ARCHITECTURE.md §1–§6 |
| Schemas / contracts | ✅ Locked, both legacy `/compare` and new `/api/diff` |
| Mock alignment + end-to-end pipeline | ✅ Working |
| Pytest test suite | ✅ 42 tests, all passing |
| Real OpenAI embeddings | ⏳ Awaiting key |
| Real GPT-4o-mini concept extraction | ⏳ Awaiting key |
| Threshold tuning (doc §7) | ⏳ Needs real embeddings to be meaningful |
| Backend lead's real `align()` | ⏳ Awaiting Winston's push |
| Frontend wired to `/api/diff` | ⏳ Out of ML lead's scope |

---

## Commit history (newest first)

```
5b14ba0 docs: notes/integration-with-winston.md
3756524 ml: demo.py — runnable end-to-end pipeline demo
a8dec1b ml: P1 — startup validation for OPENAI_API_KEY + pytest test suite
3003bc2 ml: P2 cleanup — flag for post-Hungarian split, FULL_DRIFT constant,
                        score_pairs rename, drop unreachable "skipped" path
574027b ml: P0 fixes — tenacity retry actually fires; align() is async
996dd5f ml: Agent 4 — metrics, pipeline orchestrator, /api/diff endpoint
0612475 ml: Agent 3 — concept extraction (step 5)
fcdf777 ml: Agent 2 — embeddings, scoring, classification (steps 1-3)
daf8cb5 ml: Agent 1 foundations — schemas, align stub, ml/ package skeleton
b8b730b Initial hackathon skeleton: Semantic Diff tool   (← origin/main shares)
```

Nine commits ahead of `b8b730b`. Diverges from `origin/main` (which has
Winston's three experimental commits) at the same `b8b730b` ancestor.

---

## File layout

```
backend/
├── main.py                # FastAPI app, mounts /api/diff alongside /compare
├── models/schemas.py      # Pydantic types for both contracts
├── routes/
│   ├── compare.py         # legacy — untouched
│   ├── explanation.py     # legacy — untouched
│   └── diff.py            # NEW — POST /api/diff
└── services/
    ├── align.py           # placeholder for backend lead's algorithm
    ├── ml_client.py       # legacy
    └── tokenizer.py       # legacy

ml/
├── __init__.py
├── thresholds.py          # all tunable constants in one place
├── _mock_align.py         # canned AlignmentResult for dev
├── embeddings.py          # async OpenAI embeddings + tenacity
├── scoring.py             # cosine sim + cosine_to_drift remap
├── classification.py      # threshold ladder + post-Hungarian split
├── concepts.py            # gpt-4o-mini structured output
├── metrics.py             # length-weighted drift + Levenshtein
├── pipeline.py            # asyncio orchestrator (run_diff)
└── demo.py                # python -m ml.demo

tests/                     # 42 pytest tests, all passing
├── conftest.py
├── test_scoring.py
├── test_classification.py
├── test_metrics.py
├── test_mock_align.py
├── test_embeddings_retry.py
└── test_pipeline.py

notes/
├── integration-with-winston.md     # how to wire his align() in
└── ml-branch-handoff.md            # this file

ML_ARCHITECTURE.md         # the spec the slice was built from
pytest.ini
```

---

## Running things

### Tests (no API keys needed)

```bash
pip install -r backend/requirements.txt
python -m pytest tests/
# expect: 42 passed
```

### Pipeline demo, mock mode (no API keys needed)

```bash
python -m ml.demo --mock
```

Pretty-prints the full `DiffResponse` with colored classifications. Exercises
every classification path: unchanged (paraphrase + verbatim), modified, the
post-Hungarian split into removed+added, and unmatched on each side.

### Pipeline demo, live mode (needs `OPENAI_API_KEY`)

```bash
export OPENAI_API_KEY=sk-...
python -m ml.demo
# or with custom text:
python -m ml.demo --before "..." --after "..."
```

### Booting the FastAPI server

```bash
cd backend && python main.py
# server on http://localhost:8000
# routes: /api/diff, /api/diff/health, /compare, /explanation/{id}, /docs, /health
```

Sample request once the key is set:

```bash
curl -X POST http://localhost:8000/api/diff \
  -H "Content-Type: application/json" \
  -d '{"before": "We should consider expanding to Japan.",
       "after":  "We plan to expand to Japan."}'
```

---

## What's tested

`pytest` covers:

- `cosine_to_drift` remap math + clamping (5 cases)
- `score_pair` identity / orthogonal / FP overshoot clamping (4 cases)
- `score_pairs` ordering + return shape (2 cases)
- `classify_pairs` — every threshold boundary, both with and without
  `split_below_threshold` flag (7 cases)
- `classify_unmatched` — both directions, empty case (4 cases)
- `aggregate_metrics` — counts, length-weighted drift (verifies long pair
  dominates short), Levenshtein corner cases, model defaults, edge clamping
  (8 cases)
- `_mock_align` async signature, ID uniqueness/namespacing, sample defaults
  (4 cases)
- **Tenacity retry regression guard** — fault-injects `APIConnectionError`,
  asserts exactly 6 retries before reraise; non-retryable `ValueError`
  fires once (2 cases)
- `run_diff` end-to-end with monkey-patched OpenAI calls — response shape,
  classification of every clause, summary counts, graceful concept failure
  (5 cases)

**What's not tested** (and only can be once keys arrive):

- Real OpenAI embeddings response parsing (`response.data[i].embedding`)
- Real `gpt-4o-mini` structured output (`message.parsed`, `message.refusal`)
- `tenacity.retry` decorator on the actual async function under load (the
  tests fault-inject; behaviour against a real OpenAI 429 is unverified)
- Threshold values produce sensible classifications on real-world text

---

## Integration seams

The two places the next person plugs into:

### 1. `backend/services/align.py::align()`

Currently delegates to `ml._mock_align.mock_align`. When Winston pushes a
real Hungarian-with-merging implementation, swap the body. Signature is
locked as `async def align(before: str, after: str) -> AlignmentResult`.

See `notes/integration-with-winston.md` for the adapter sketch. His current
`alignment_methods.py` returns a flat `dict`; that file documents the
~30-line dict→`AlignmentResult` translator and which thresholds need
reconciling to avoid double-pruning.

### 2. Frontend → `POST /api/diff`

Existing FE is wired to `/compare` (legacy). New endpoint `/api/diff`
returns `DiffResponse` per `ML_ARCHITECTURE.md` §6:

- `before_clauses[]` + `after_clauses[]` — render the two columns
- `pairs[]` — relational view for hover connectors
- `summary` — overall stats including the headline `pct_text_edited` vs.
  `pct_meaning_edited` numbers
- `concepts[]` + `concept_extraction` status

TypeScript types from `frontend/src/types/api.ts` cover only the legacy
contract; new types need to be authored mirroring `backend/models/schemas.py`.

---

## Configuration / dependencies

### Required env vars

`OPENAI_API_KEY` — used by `ml/embeddings.py` (text-embedding-3-small) and
`ml/concepts.py` (gpt-4o-mini). Backend boots without it but `/api/diff`
returns 500 at request time and a warning prints to stderr.

`ANTHROPIC_API_KEY` — only the legacy concept-explanation flow used this;
the new pipeline doesn't call Anthropic. Can be ignored.

### Tunables (`ml/thresholds.py`)

```python
STABLE_THRESHOLD   = 0.93   # >= this similarity ⇒ "unchanged"
MODIFIED_THRESHOLD = 0.65   # in [MODIFIED, STABLE) ⇒ "modified"
REMOVED_THRESHOLD  = 0.65   # below this ⇒ post-Hungarian split
DRIFT_FLOOR        = 0.5    # cosine values below this clamped (drift = 100)
DRIFT_CEIL         = 1.0
EMBEDDING_MODEL    = "text-embedding-3-small"
CHAT_MODEL         = "gpt-4o-mini"
ALIGNMENT_NAME     = "hungarian"
MAX_CONCEPT_INPUT_CHARS = 60_000
FULL_DRIFT         = 100.0
```

Threshold-tuning sprint (`ML_ARCHITECTURE.md` §7) edits this file only.
**Do not tune until real embeddings are flowing through.**

---

## Known gaps / open questions

Captured here so they're not lost between sessions:

1. **Merged-clauses schema** (`ML_ARCHITECTURE.md` §6 deferred). If
   Winston's eventual `align()` produces 2:1 merged clauses, `paired_with:
   Optional[str]` can't represent it. Decide between extending to
   `Optional[str | list[str]]` or adding `Classification = "merged"`.
2. **Double-prune risk** when Winston's adapter ships. Use
   `classify_pairs(scored, split_below_threshold=False)` if his
   `match_threshold` is doing the work upstream.
3. **`pct_text_edited` is whitespace-sensitive Levenshtein.** A
   reformatting-only edit will look like high text edit. Acceptable for
   now; revisit if it confuses the demo.
4. **`DiffRequest` 20 K char/side cap** is hardcoded in the schema. If a
   judge pastes a longer document the request 422s.
5. **No streaming or partial response.** A 5-second `/api/diff` request
   returns nothing until the whole pipeline finishes. Not a big deal at
   hackathon scale.
6. **No caching.** Repeating the same diff costs the full embedding bill
   each time. Deliberately deferred per `ML_ARCHITECTURE.md` §5.

---

## Coordination state

- Winston has not seen `ML_ARCHITECTURE.md`. His `origin/main` commits
  reference the original 7-hour roadmap and use `ml/` for alignment
  experiments. The doc later moved alignment ownership to backend
  but didn't relocate the file. See `notes/integration-with-winston.md`
  for the full picture.
- Frontend lead status unknown; existing FE is wired to legacy
  `/compare` only.
- Held off merging `origin/main` per user direction. Fetch is current
  (`origin/main` = `57c497b`) and available locally for browsing.
