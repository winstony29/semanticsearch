# Integration with Winston's `origin/main`

Working notes on what's on `origin/main` (Winston's branch) and how it relates
to the ML slice we built on the `ML` branch from `ML_ARCHITECTURE.md`.

**Status:** not merged. Fetched only. Decision deferred.

**Update 2026-05-09 — staging done.** Five integration prep items landed
on the `ML` branch:

1. Merged-clauses schema decided (option A — `paired_with: Optional[str |
   list[str]]`). See `backend/models/schemas.py::ClauseRendering` and
   `ML_ARCHITECTURE.md` §6.
2. Adapter shim staged behind `USE_REAL_ALIGN` flag in
   `backend/services/align.py`. Vendored copy of `semantic_hungarian` +
   helpers in `backend/services/_align_impl.py`. Default still routes to
   `mock_align`.
3. `ALIGNMENT_PRE_PRUNES` flag added in `ml/thresholds.py`, threaded
   through `pipeline.py`. Default `False`. Flip to `True` together with
   `USE_REAL_ALIGN=1`.
4. `pct_text_edited` now whitespace-normalised in `ml/metrics.py` so
   reformatting-only edits read as 0%.
5. Winston's `ml/test_cases.py` cherry-picked into `ml/test_cases.py` for
   threshold-tuning corpus (14 fixtures, not pytest functions).

Smoke test for the staged adapter lives in `tests/test_align_adapter.py`
(3 cases, mocked OpenAI). When Winston pushes finished work, replace
`backend/services/_align_impl.py` and flip the two flags.

---

## What Winston put on `origin/main`

Three commits past `b8b730b`:

| Commit | Adds |
|---|---|
| `26b79dc` | `ml/alignment_methods.py` (5 alignment strategies), `ml/test_cases.py` (12 edge cases), `ml/run_experiments.py`, `ml/NICKOLAS_README.md`, plus updates to `README.md` and `ml/requirements.txt` |
| `f4388ee` | `ml/demo.py`, `ml/quick_test.py`, `ml/visual_demo.py`, `ml/DEMO_GUIDE.md` |
| `57c497b` | `TESTED_AND_READY.md`, `test_alignment.py` |

The five alignment methods in `alignment_methods.py`:

| Method | Note |
|---|---|
| `lexical_hungarian(v1, v2, threshold=0.3)` | TF-IDF + Hungarian. Cheap baseline. |
| `semantic_hungarian(v1, v2, embeddings, threshold=0.6)` | The MVP path; Winston flags this as "recommended". |
| `hybrid_hungarian(...)` | TF-IDF pre-filter zeroes unlikely cells, then semantic. Speed optimisation. |
| `greedy_with_merges(...)` | Greedy descending-similarity match with merge/split tagging. |
| `adaptive_hungarian(...)` | Tries semantic first; falls back to greedy if mean matched score < 0.5. |

All five share `_run_hungarian_with_threshold` and `_handle_empty_case` helpers.

---

## Why we did not auto-merge

Winston is operating from the **original 7-hour roadmap**, not from
`ML_ARCHITECTURE.md`. His `NICKOLAS_README.md` references files and concepts
that no longer exist on the `ML` branch. Direct merge would land conflicting
files in `ml/` and stale guidance in his README.

---

## Three real compatibility issues

### 1. Output schema mismatch (biggest)

Winston's methods return:

```python
{
    "method": "semantic_hungarian",
    "pairs": [
        {"pair_id": "pair_001",
         "v1_sentence": ..., "v2_sentence": ...,
         "v1_index": ..., "v2_index": ...,
         "similarity_score": ...,
         "status": "matched" | "added" | "deleted" | "merged" | "split"},
        ...
    ],
    "similarity_matrix": np.ndarray,
}
```

`pairs` is a **flat list** mixing matched + added + deleted + merged + split.

Our `backend.models.schemas.AlignmentResult` wants:

```python
class AlignmentResult(BaseModel):
    pairs: list[AlignedPair]              # only matched
    unmatched_before: list[ClauseUnit]    # added/deleted on v1 side
    unmatched_after:  list[ClauseUnit]    # added/deleted on v2 side
    original_before: str
    original_after:  str
```

**Fix:** ~30-line adapter shim. See "Path forward" below.

### 2. Sentence-level, not clause-level

Winston's inputs are `v1_sentences: list[str]` — pre-split sentences. Our
contract uses **clauses** (post-merge, may span multiple sentences).
`greedy_with_merges` tags merges with a `status: "merged"` flag but does
not actually concatenate the merged sentences into a single ClauseUnit text.

For non-merging cases, sentence == clause and Winston's output is
acceptable. For merging cases, his output undercounts: 2 sentences merged
into 1 v2 sentence yield 1 match + 1 deletion (in `semantic_hungarian`) or
2 separate "merged" entries (in `greedy_with_merges`) — never a single
combined-text clause.

**Implication:** the "Hungarian-with-merging" envisioned in
`ML_ARCHITECTURE.md` §1 is not actually delivered yet. If we want it, we
have to write the merge-text-concatenation step ourselves.

### 3. Embedding interface differs

Winston: `embeddings: np.ndarray` of shape `(n+m, d)`, sliced by index.
Ours: `dict[str, np.ndarray]` keyed by clause id.

Easily reconciled in the adapter — re-key by id when building
`AlignedPair`s.

---

## Where Winston's design DOES match the doc

- **Post-Hungarian split logic exists** in `_run_hungarian_with_threshold`:
  pairs below threshold are split into `deleted` + `added`. Same idea as
  our `classify_pairs`'s `REMOVED_THRESHOLD` check, applied at alignment
  time instead of classification time.
  - **Watch out:** if Winston's `align()` is wired in directly, both layers
    do the same work. Either drop our re-classify or lower his
    `match_threshold` so it doesn't pre-prune things we still want
    classified as `modified`.
- **Empty-side handling** is symmetric: empty v1 → all v2 added,
  empty v2 → all v1 deleted.
- **Padding strategy** (square cost matrix, fill 1.0 for dummies) is
  identical to ours.

---

## Threshold collisions

| Threshold | Winston | Ours (`ml/thresholds.py`) | Notes |
|---|---|---|---|
| Top-tier "preserved meaning" | n/a (alignment doesn't need this) | `STABLE_THRESHOLD = 0.93` | Classification only |
| Hungarian-time match cutoff | `match_threshold = 0.6` | n/a | Alignment-time prune |
| Post-Hungarian split | implicit at `0.6` | `REMOVED_THRESHOLD = 0.65` | Both fire below their cutoff |
| Greedy match | `match_threshold = 0.6` | n/a | |
| Adaptive fallback trigger | mean matched score < `0.5` | n/a | |
| Old roadmap GREEN/YELLOW/RED | `0.85` / `0.60` (in his README) | n/a | Stale advice |

Pick a single threshold and apply it once. Two layers prune-then-prune
will look like every borderline pair is `added/removed` instead of
`modified` — confusing in the demo.

---

## What's stale in `NICKOLAS_README.md`

Every concrete integration instruction references the pre-`ML_ARCHITECTURE.md`
codebase. None of these instructions apply to the `ML` branch as it stands:

| Winston's advice | Actual state on `ML` |
|---|---|
| "Integrate into `semantic_engine.py`" | File deleted in Agent 1 commit |
| "Update `backend/services/ml_client.py`" | That's the legacy `/compare` shim; new `/api/diff` does not pass through it |
| `THRESHOLD_GREEN = 0.85` / `THRESHOLD_YELLOW = 0.60` | Doc uses `STABLE_THRESHOLD = 0.93` / `MODIFIED_THRESHOLD = 0.65` |
| GREEN / YELLOW / RED classes | Doc uses `unchanged` / `modified` / `added` / `removed` |
| `compare_sentences(v1_sentences, v2_sentences)` | Pipeline takes raw `before`/`after`; clauses, not sentences |
| "Add real embedding API call" | Already implemented in `ml/embeddings.py` (`embed_clauses`) |

---

## Coordination flags

Two non-code items.

1. **Winston has not seen `ML_ARCHITECTURE.md`.** It's only on the `ML`
   branch. Without it he does not know about the `AlignmentResult` schema,
   `b0`/`a0` clause IDs, the post-Hungarian re-classify split, or where
   the new boundary between his code and ours lives. The next round of
   his work will probably re-implement the same wrong contract.

2. **`ml/` is contested territory.** Original split made it the ML lead's
   folder. `ML_ARCHITECTURE.md` reassigned alignment to the backend lead
   but did not say where the alignment file should live. Winston put it
   in `ml/` because he was working from the original split. Either decide
   this together or accept the awkwardness.

---

## Path forward (when ready to integrate)

When you decide to wire Winston's algorithm in, the surgical sequence:

### 1. Copy the algorithm out of `ml/`

```bash
git show origin/main:ml/alignment_methods.py > backend/services/_align_impl.py
```

(Or pick just the helpers + `semantic_hungarian` you actually need.)

### 2. Write the adapter in `backend/services/align.py`

Replace the current `align()` body. Sketch:

```python
from typing import Iterable
import re

from backend.models.schemas import AlignedPair, AlignmentResult, ClauseUnit
from backend.services._align_impl import semantic_hungarian
from ml.embeddings import _normalize  # or inline the L2 normalisation

def _split_to_sentences(text: str) -> list[str]:
    # Cheap sentence split — replace with spaCy if needed.
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

async def align(before: str, after: str) -> AlignmentResult:
    v1 = _split_to_sentences(before)
    v2 = _split_to_sentences(after)

    # Embed both sides in one batch (use whatever embedding helper you expose).
    embeddings = await _embed_for_alignment(v1 + v2)  # shape (n+m, d)

    raw = semantic_hungarian(v1, v2, embeddings)

    paired:   list[AlignedPair] = []
    before_only: list[ClauseUnit] = []
    after_only:  list[ClauseUnit] = []

    for entry in raw["pairs"]:
        if entry["status"] == "matched":
            paired.append(AlignedPair(
                before=ClauseUnit(id=f"b{entry['v1_index']}", text=entry["v1_sentence"]),
                after =ClauseUnit(id=f"a{entry['v2_index']}", text=entry["v2_sentence"]),
            ))
        elif entry["status"] == "deleted":
            before_only.append(ClauseUnit(id=f"b{entry['v1_index']}", text=entry["v1_sentence"]))
        elif entry["status"] == "added":
            after_only.append(ClauseUnit(id=f"a{entry['v2_index']}", text=entry["v2_sentence"]))
        # "merged" / "split" — decide later; for now flatten as deleted/added.

    return AlignmentResult(
        pairs=paired,
        unmatched_before=before_only,
        unmatched_after=after_only,
        original_before=before,
        original_after=after,
    )
```

Note: making `align()` async introduces a small ripple — `ml/pipeline.py`
currently calls it synchronously. Either await it there or make the
embedding call sync (blocking) inside align — pick what's cleanest.

### 3. Reconcile thresholds

Two options:

- **Drop our post-Hungarian re-classify.** Update `ml/classification.py`'s
  `classify_pairs` to skip the `sim < REMOVED_THRESHOLD` split branch.
  Trust Winston's pre-prune.
- **Lower Winston's `match_threshold` to ~0.45.** Let more borderline
  pairs through, classify them ourselves. Keeps both layers but stops
  the double-prune.

Recommendation: drop ours. Single source of truth, no drift.

### 4. Send Winston a short note

Subject: ML branch contract update — before you wire your `align()` further

Hey Winston, quick heads-up — I built out the ML pipeline on the `ML`
branch against a new architecture spec (`ML_ARCHITECTURE.md`). Couple of
things to flag before you keep iterating on `alignment_methods.py`:

- The pipeline now treats the **alignment output as the seam**. Your
  function should return `AlignmentResult` (in `backend/models/schemas.py`):
  `pairs: list[AlignedPair]`, `unmatched_before / unmatched_after:
  list[ClauseUnit]`, plus the original strings. IDs are `b0/a0`, not
  `pair_001`. I wrote a thin adapter at `backend/services/align.py` that
  wraps your `semantic_hungarian` for now.
- New thresholds live in `ml/thresholds.py`: `STABLE = 0.93`,
  `MODIFIED = REMOVED = 0.65`. The legacy `THRESHOLD_GREEN/YELLOW`
  values from your README don't apply.
- Classification vocabulary is now `unchanged / modified / added /
  removed`, not `green/yellow/red`.
- New endpoint `POST /api/diff` is the canonical path; legacy `/compare`
  still works untouched.
- Take a look at `ML_ARCHITECTURE.md` (lives on the `ML` branch root).
  §1 has the schema; §8 has how I split it across agents.

If you're going to wire merging into `align()`, the doc has an open
question (§6 notes) about how merged clauses should be represented.
Worth pinning down before you build it — happy to chat.

### 5. Don't forget

- Run the threshold-tuning sprint (`ML_ARCHITECTURE.md` §7) **after**
  Winston's real alignment is producing real clauses. Five hand-picked
  examples, 20 minutes.
- `ml/test_cases.py` from Winston's branch is reusable for tuning. Worth
  cherry-picking if not merging the rest.
- Update `notes/` (this file) with whatever final decisions you make so
  the next person reading the branch isn't surprised.

---

## Quick file-tree comparison

What's on `origin/main:ml/` and not on `ML:ml/`:

```
ml/alignment_methods.py     # 5 align methods, 459 lines
ml/test_cases.py            # 12 edge cases
ml/run_experiments.py       # comparison harness
ml/NICKOLAS_README.md       # stale guidance
ml/DEMO_GUIDE.md            # reader's guide for demos
ml/demo.py                  # full walkthrough demo
ml/quick_test.py            # 30-second demo
ml/visual_demo.py           # ASCII heatmap demo
```

What's on `ML:ml/` and not on `origin/main:ml/`:

```
ml/__init__.py              # rewritten as slim package docstring
ml/_mock_align.py           # mock AlignmentResult for dev
ml/thresholds.py            # single source of truth for tunables
ml/embeddings.py            # AsyncOpenAI + tenacity
ml/scoring.py               # cosine_to_drift remap
ml/classification.py        # threshold ladder + post-Hungarian split
ml/concepts.py              # gpt-4o-mini structured output
ml/metrics.py               # length-weighted drift, Levenshtein
ml/pipeline.py              # asyncio orchestrator, run_diff()
```

Plus, on `ML` only:

```
ML_ARCHITECTURE.md          # the spec
backend/models/schemas.py   # extended with new /api/diff types
backend/services/align.py   # placeholder delegating to mock
backend/routes/diff.py      # POST /api/diff
backend/main.py             # adds sys.path inject + diff router
```
