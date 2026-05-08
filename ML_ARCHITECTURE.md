# Embeddings Scope — ML Slice Architecture

> **Audience.** This document is the working specification for the ML pipeline of Embeddings Scope. It is written to be consumed by Claude Code agents operating on this codebase, and by the human ML lead reviewing their output. It assumes the FastAPI scaffold already exists (`app/main.py`, `app/models.py`, `app/services.py`, `app/config.py`).
>
> **Scope.** This document covers only the ML slice — the code path from "receive aligned pairs from the backend lead's `align()` function" through "return the full structured response to the API endpoint." It does not cover frontend, deployment, or the alignment algorithm itself.

---

## 1. System context: where the ML slice fits

The full pipeline, end to end:

```
                         ┌────────────────────────┐
  POST /api/diff ───────▶│  app/main.py endpoint  │
  { before, after }      └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │  align(before, after)  │  ← BACKEND LEAD owns
                         │  Hungarian + merging   │     (separate file,
                         │  Returns: pairs +      │      same codebase)
                         │  unmatched lists       │
                         └───────────┬────────────┘
                                     │
                                     ▼
                  ┌──────────────────────────────────────┐
                  │           ML SLICE (this doc)        │
                  │                                      │
                  │  ┌──── parallel via asyncio.gather ──┐
                  │  │                                   │
                  │  │  embed_pairs()    extract_concepts()
                  │  │       │                  │        │
                  │  │       ▼                  │        │
                  │  │  score_pairs()           │        │
                  │  │       │                  │        │
                  │  │       ▼                  │        │
                  │  │  classify_pairs()        │        │
                  │  │       │                  │        │
                  │  │       ▼                  │        │
                  │  │  aggregate_metrics()     │        │
                  │  │       │                  │        │
                  │  │       └────────┬─────────┘        │
                  │  │                ▼                  │
                  │  │      assemble_response()          │
                  │  └───────────────────────────────────┘
                  │                                      │
                  └──────────────────┬───────────────────┘
                                     │
                                     ▼
                              DiffResponse JSON
```

**The ML slice's contract.**

*Input:* The output of `align(before_text, after_text)` plus the original two strings.

```python
class AlignmentResult(BaseModel):
    pairs: list[AlignedPair]                # paired clauses
    unmatched_before: list[ClauseUnit]      # appears only in v1
    unmatched_after:  list[ClauseUnit]      # appears only in v2
    original_before: str
    original_after:  str

class ClauseUnit(BaseModel):
    id: str                                  # "b0", "b1", ... or "a0", "a1", ...
    text: str                                # may span multiple sentences if merged

class AlignedPair(BaseModel):
    before: ClauseUnit                       # may be a merged group
    after:  ClauseUnit                       # may be a merged group
```

*Output:* The full `DiffResponse` defined in §6 of this document.

**Critical understanding.** The unit of analysis is no longer the sentence — it is the **clause** as defined by the backend lead's algorithm. A clause may span multiple original sentences if Hungarian-with-merging grouped them. The ML slice does not split or merge text; it operates on whatever units `align()` produces.

---

## 2. The pipeline, step by step

### Step 1 — Embed pairs
**File:** `app/ml/embeddings.py`

For each `AlignedPair`, embed the `before.text` and `after.text` using OpenAI's `text-embedding-3-small`. Also embed the unmatched clauses on both sides (needed for completeness, even though they have no partner).

**Implementation notes:**
- Collect all texts that need embedding into a single flat list. Track their position in the list so embeddings can be reassociated after the call.
- Batch into a single async call when possible (`text-embedding-3-small` accepts up to 2048 inputs per request; we'll always be well under).
- L2-normalize all returned embeddings defensively. OpenAI's v3 embeddings are already unit-normalized, but re-normalizing costs nothing and protects against future API changes.
- Replace any empty or whitespace-only string with a single space before sending — the API rejects empty strings with a 400.
- Use `AsyncOpenAI` from the `openai` SDK with built-in retries, plus a `tenacity` decorator for additional resilience on `RateLimitError`, `APIConnectionError`, `APIStatusError`.

**Output of this step:** A dict mapping each clause id to its normalized embedding vector. This dict is the only structure downstream code needs — pair similarity becomes `dot(embeddings[pair.before.id], embeddings[pair.after.id])`.

### Step 2 — Score pairs
**File:** `app/ml/scoring.py`

For each `AlignedPair`, compute cosine similarity between the two embeddings. Since both vectors are unit-normalized, this is a dot product:

```python
similarity = float(np.dot(embeddings[pair.before.id], embeddings[pair.after.id]))
```

**No matrix needed at this stage.** The full similarity matrix was a feature of the old greedy-matching design. Now that `align()` has already chosen the pairs, you only need pair-wise dot products — `O(n)` where `n` is pair count.

Convert similarity to a 0-100 drift score using a clamped remap from `[0.5, 1.0]`:

```python
def cosine_to_drift(similarity: float) -> float:
    sim = max(0.5, min(1.0, similarity))
    return round((1.0 - sim) / 0.5 * 100.0, 2)
```

The 0.5 floor is empirical — `text-embedding-3-small` rarely produces similarities below ~0.4 even for unrelated text. Anchoring at 0.5 prevents every diff from looking 30-50% drifted by default.

### Step 3 — Classify pairs and unmatched
**File:** `app/ml/classification.py`

Define three threshold constants at the top of the file:

```python
STABLE_THRESHOLD   = 0.93  # ≥ this similarity ⇒ "unchanged"
MODIFIED_THRESHOLD = 0.65  # in [MODIFIED, STABLE) ⇒ "modified"
REMOVED_THRESHOLD  = 0.65  # below this ⇒ pair is bogus, split into added/removed
```

These start as guesses and are tuned in the threshold-tuning sprint (§7).

**Classification logic for paired clauses:**

```
similarity ≥ STABLE_THRESHOLD          → "unchanged" (both sides)
MODIFIED_THRESHOLD ≤ sim < STABLE       → "modified"  (both sides)
similarity < REMOVED_THRESHOLD          → split: before becomes "removed",
                                          after becomes "added"
                                          (Hungarian forced a bad pairing)
```

**Classification logic for unmatched clauses (no partner from `align()`):**

```
unmatched_before  → "removed"
unmatched_after   → "added"
```

The post-Hungarian threshold check in step 3 handles the case where `align()` was forced to pair two unrelated clauses because of its assignment constraints. We undo the pairing and treat both sides as standalone.

### Step 4 — Aggregate document metrics
**File:** `app/ml/metrics.py`

Compute summary statistics over all classified clauses:

- `unchanged_count`, `modified_count`, `added_count`, `removed_count`
- `before_count` = total clauses on the before side (paired + unmatched_before)
- `after_count`  = total clauses on the after side (paired + unmatched_after)
- `overall_drift` = mean drift score across all paired clauses, weighted by clause length (longer clauses count more)
- `pct_text_edited` = character-level Levenshtein distance / max(len(before), len(after)) * 100
- `pct_meaning_edited` = `overall_drift` (these are the headline two numbers)

The gap between `pct_text_edited` and `pct_meaning_edited` is the "did words change without meaning changing, or vice versa" insight. For paraphrase examples, expect `pct_text_edited` high and `pct_meaning_edited` low. For minor edits with semantic impact, the reverse.

### Step 5 — Concept extraction (parallel, cuttable)
**File:** `app/ml/concepts.py`

Runs **concurrently** with steps 1–4 via `asyncio.gather`. Takes the raw `original_before` and `original_after` strings (not the aligned pairs) and produces a list of high-level concepts with status tags.

Use OpenAI's `client.chat.completions.parse(...)` with a Pydantic schema for guaranteed structured output:

```python
from pydantic import BaseModel, Field
from typing import Literal

class Concept(BaseModel):
    name: str = Field(..., description="Short noun phrase (3-8 words) naming the idea, obligation, right, or theme.")
    status: Literal["new", "weakened", "strengthened", "unchanged"]
    evidence: str = Field(..., description="Verbatim quote (≤240 chars) supporting the classification.")
    evidence_before_ids: list[str] = Field(default_factory=list)
    evidence_after_ids:  list[str] = Field(default_factory=list)

class ConceptDiff(BaseModel):
    summary: str
    concepts: list[Concept]
```

**The evidence_*_ids problem.** GPT-4o-mini doesn't know your clause ids. Options:

1. **Pass clause ids in the prompt.** Format the document as `[b0] First clause text. [b1] Second clause text...` and ask the model to return the ids. Reliable but bloats the prompt.
2. **Skip ids in the LLM output, link them post-hoc.** The model returns evidence quotes; you do substring matching against the clause texts to find which ids the evidence belongs to. Cheaper prompt, more code.
3. **Skip ids entirely.** The frontend just shows the evidence quote, no linking to specific clauses. Easiest, but loses the "click chip → highlight relevant clauses" interaction.

**Recommendation:** Start with option 3. If time permits in hour 5, upgrade to option 2 — substring matching is ~10 lines of code and doesn't require re-prompting.

**Always wrap this call in try/except.** A refusal, timeout, JSON failure, or rate limit must never break the rest of the response. On any failure, return an empty list and set `concept_extraction = "failed"` in the response.

### Step 6 — Assemble response
**File:** `app/ml/pipeline.py` (or `app/services.py` if keeping the existing structure)

Combine outputs from steps 3, 4, 5 into the `DiffResponse` (§6). This is a pure data-shaping step — no logic, just construction.

---

## 3. File structure (extending the existing scaffold)

```
app/
├── main.py              # existing — FastAPI endpoint, no changes from your slice
├── models.py            # existing — extend with new Pydantic models from §6
├── services.py          # existing — becomes a thin orchestrator calling app/ml/
├── config.py            # existing — no changes
└── ml/                  # NEW — your slice lives here
    ├── __init__.py
    ├── embeddings.py    # step 1
    ├── scoring.py       # step 2
    ├── classification.py # step 3 + thresholds
    ├── metrics.py       # step 4
    ├── concepts.py      # step 5
    ├── pipeline.py      # step 6 — orchestrates 1-5 with asyncio.gather
    └── thresholds.py    # all tunable constants in one place
```

**Why a subpackage?** Keeps the ML logic isolated from API plumbing, makes it easy for Claude Code agents to operate on `app/ml/` without touching API code, and lets the threshold-tuning sprint live in one obvious file.

---

## 4. What you can build before the backend lead's `align()` is ready

Almost everything. The interface is defined; that's all you need.

**Mock alignment for development.** Create `app/ml/_mock_align.py` with a function matching `align()`'s signature that returns hand-crafted pairs. This lets you build and test steps 1-5 against realistic-shaped data without waiting for real Hungarian.

```python
def mock_align(before_text: str, after_text: str) -> AlignmentResult:
    # Returns 4-5 hardcoded pairs covering all classification cases:
    # - one near-identical pair (will classify as unchanged)
    # - one paraphrased pair (modified, mid drift)
    # - one substantively changed pair (modified, high drift)
    # - one unmatched_before (will classify as removed)
    # - one unmatched_after (will classify as added)
    ...
```

**What works against the mock:**
- Embedding pipeline (real OpenAI calls on mock pair texts).
- Scoring and drift calculation.
- Classification thresholds.
- Metrics aggregation.
- Concept extraction (operates on raw text — entirely independent of `align()`).
- Response assembly.
- The threshold tuning sprint.

**What requires the real `align()`:**
- The single integration moment where you swap `mock_align` for `align`. Should be a one-line change.
- End-to-end testing with real Hungarian output, especially edge cases (merged clauses, padding-induced bad pairs).

**Hard dependency you must coordinate on early.** Pin the `AlignmentResult` schema with the backend lead in the first 30 minutes. Type names, field names, whether `ClauseUnit` carries any metadata beyond `id` and `text`. Once locked, both of you are unblocked.

---

## 5. Common pitfalls

### Embedding-related

**OpenAI rejects empty strings with HTTP 400.** Replace any empty or whitespace-only text with `" "` before batching. Easy to miss because most text inputs are fine.

**The default `dimensions` is 1536.** Don't pass `dimensions=512` or anything smaller "for speed" — Matryoshka truncation hurts paraphrase similarity meaningfully and the speed gain is negligible at our scale.

**SDK retries are not a substitute for tenacity.** The OpenAI SDK retries on transient errors but not on all of them. Wrap embedding calls with `tenacity.retry(retry=retry_if_exception_type((RateLimitError, APIConnectionError, APIStatusError)), wait=wait_random_exponential(min=1, max=30), stop=stop_after_attempt(6))`.

**Don't re-embed unmatched clauses if they appeared in the pairs list.** Build a deduplicated set of clause ids before embedding. Unlikely to happen with Hungarian (it's bijective except for unmatched), but defensive.

### Scoring-related

**Cosine similarity on un-normalized vectors gives nonsense.** Normalize defensively after the API call returns, even though OpenAI claims to return normalized vectors. One bad assumption here corrupts every drift score.

**Floating-point similarity values can exceed 1.0.** After `np.dot`, clamp to `[-1.0, 1.0]` before passing to `cosine_to_drift`. Values like `1.0000000002` arise from floating-point error and produce negative drift scores otherwise.

### Classification-related

**Thresholds tuned for sentences may not work for clauses.** Clauses are typically shorter and more semantically dense than full sentences. Run the tuning sprint *after* `align()` is producing real clauses, not before. Don't trust thresholds developed against sentence-level test data.

**The post-Hungarian threshold check is critical.** Without it, Hungarian will produce pairs like `("The cat sat on the mat", "Termination requires 30 days notice")` because it was the least-bad option. These show up in the demo as "modified" with drift score 78 and confuse judges. Always re-classify pairs below `REMOVED_THRESHOLD` as `removed`+`added`.

**`STABLE_THRESHOLD = 0.93` is high.** `text-embedding-3-small` gives 0.93+ even for paraphrases with ~70% word overlap. If your demo shows everything as "modified" when most things are barely changed, lower stable to 0.90 first.

### Concept extraction-related

**`gpt-4o-mini` can refuse with `refusal=...` even on innocuous content.** The Pydantic-parsed response will have `parsed=None` and `refusal=<string>`. Check for this explicitly; don't assume `parsed` is always populated.

**Long documents can blow the context window.** GPT-4o-mini has 128K tokens, which is plenty for hackathon-scale contracts (5K-10K tokens). But if a judge pastes a 50K-token document, you'll see `BadRequestError`. Cap inputs at 60K characters per side defensively.

**Concept extraction must never block the rest of the response.** Wrap the entire call in try/except returning an empty `ConceptDiff(summary="", concepts=[])`. The frontend renders the panel empty if `concepts == []`.

**Don't fire the call sequentially after embeddings.** Use `asyncio.gather(embed_and_score_task, extract_concepts_task)`. Wall-clock saving is 2-3 seconds per request.

### Architecture-related

**Don't compute the full similarity matrix.** It was a feature of the greedy-matching design. With `align()` upstream, you only need pair-wise dot products. Computing a matrix is O(n²) work for nothing.

**Don't put thresholds in multiple files.** Single source of truth in `app/ml/thresholds.py`. The tuning sprint involves changing 3 numbers; if those numbers exist in 3 files you'll change 1 and wonder why the demo broke.

**Don't add caching.** Tempting at hour 5 ("memoize embeddings for repeated demo runs!") and a major source of subtle bugs. The pipeline is already fast enough. Cache later, never tonight.

---

## 6. The complete JSON contract

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

Classification = Literal["unchanged", "modified", "added", "removed"]
ConceptStatus  = Literal["new", "weakened", "strengthened", "unchanged"]
ConceptExtractionStatus = Literal["ok", "skipped", "failed"]

class DiffRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    before: str = Field(..., min_length=1, max_length=20_000)
    after:  str = Field(..., min_length=1, max_length=20_000)

class ClauseRendering(BaseModel):
    """A clause as displayed in either the before or after column."""
    id: str                                          # "b0", "a0", ...
    text: str                                        # may span multiple original sentences if merged
    classification: Classification
    drift_score: float = Field(..., ge=0, le=100)
    paired_with: Optional[str] = None                # id of partner on the other side, or None

class PairRendering(BaseModel):
    """A clause pair, for hover-connector rendering."""
    before_id: str
    after_id: str
    similarity: float = Field(..., ge=-1.0, le=1.0)
    drift_score: float = Field(..., ge=0, le=100)
    classification: Classification

class DiffSummary(BaseModel):
    before_count: int
    after_count: int
    unchanged: int
    modified: int
    added: int
    removed: int
    overall_drift: float = Field(..., ge=0, le=100)
    pct_text_edited: float = Field(..., ge=0, le=100)
    pct_meaning_edited: float = Field(..., ge=0, le=100)
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    alignment: str = "hungarian"
    elapsed_ms: int

class Concept(BaseModel):
    name: str
    status: ConceptStatus
    evidence: str
    evidence_before_ids: list[str] = Field(default_factory=list)
    evidence_after_ids:  list[str] = Field(default_factory=list)

class DiffResponse(BaseModel):
    before_clauses: list[ClauseRendering]
    after_clauses:  list[ClauseRendering]
    pairs: list[PairRendering]
    summary: DiffSummary
    concepts: list[Concept]
    concept_extraction: ConceptExtractionStatus = "ok"
```

**Notes on schema design:**

- `before_clauses` and `after_clauses` are what the frontend iterates to render the two columns. Each is self-contained.
- `pairs` is a relational view used for hover connectors. Frontend builds a Map keyed by either side's id.
- The redundancy between the three lists is intentional and small (~30% bytes) — pays for itself in frontend simplicity.
- Merged clauses (one v2 clause paired with two v1 clauses) are **not represented** in this schema. If the backend lead's Hungarian-with-merging produces them, decide between (a) extend `paired_with` to be `Optional[str | list[str]]`, or (b) add a fifth `Classification = "merged"`. Defer the decision until merging actually appears in test output.

---

## 7. Threshold tuning sprint

Time-boxed to **20 minutes**. Run it *after* `align()` is producing real clauses, ideally hour 3-4 of the build.

**Method:**

1. Hand-craft 5 pair examples covering the spectrum: identical, trivial paraphrase, heavy paraphrase, substantively changed, totally unrelated.
2. Run the embedding + scoring pipeline on all five.
3. Print `(label, similarity, current_classification)` for each.
4. Adjust thresholds:
   - `STABLE_THRESHOLD` = the lowest similarity you'd still call "no meaningful change"
   - `MODIFIED_THRESHOLD = REMOVED_THRESHOLD` = the highest similarity you'd still call "different idea"
5. Re-run; verify all 5 examples classify the way you'd expect a human to read them.
6. Lock the constants. Move on.

**Sanity check:** Run on identical Before and After. Overall drift should be 0. Run on Before vs an entirely unrelated paragraph. Overall drift should be near 100. If either is wrong, your remap function is broken, not your thresholds.

**Don't over-tune.** Five examples is enough. Twenty is over-fitting to your test set.

---

## 8. Parallel agent orchestration (4 Claude Code agents)

The plan: 4 agents working in parallel git worktrees on a shared `feature/ml-slice` integration branch. Each agent owns disjoint files and merges to integration when done.

### Worktree setup (one-time)

```bash
git checkout -b feature/ml-slice
git worktree add ../ml-agent-1 feature/ml-slice
git worktree add ../ml-agent-2 feature/ml-slice
git worktree add ../ml-agent-3 feature/ml-slice
git worktree add ../ml-agent-4 feature/ml-slice
```

Each worktree is an independent working directory pointing at the same branch. **Agents must `git pull` before starting and merge to `feature/ml-slice` after each completed file.** The human (you) is the integration manager.

### Dependency graph between agent tasks

```
                Agent 1 (Foundations)
                ┌───────────────────┐
                │ models.py changes │
                │ thresholds.py     │
                │ _mock_align.py    │
                └────────┬──────────┘
                         │
              all other agents depend on this
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  Agent 2 (Embed/    Agent 3        Agent 4
  Score/Classify)    (Concepts)     (Pipeline +
        │                │           Metrics)
        │                │                │
        └────────────────┴────────────────┘
                         │
                Final integration
                  (human review)
```

### Agent assignments and dependencies

**Agent 1 — Foundations.** Must run first and complete before others start.

*Owns:* `app/models.py` (extends with new Pydantic types from §6), `app/ml/__init__.py`, `app/ml/thresholds.py` (initial constants), `app/ml/_mock_align.py` (5 hand-crafted test pairs).

*Why first:* Every other agent imports types from `models.py` and pairs from the mock. If they start before Agent 1 commits, they'll write their own duplicate types that conflict at integration.

*Estimated time:* 30 minutes.

*Done condition:* `from app.models import AlignmentResult, AlignedPair, ClauseUnit, DiffResponse` works in a Python REPL. Mock returns 5 pairs covering all classification cases.

**Agent 2 — Embedding, scoring, classification.** Starts after Agent 1 commits.

*Owns:* `app/ml/embeddings.py`, `app/ml/scoring.py`, `app/ml/classification.py`.

*Implements:* Steps 1, 2, 3 of the pipeline. `embed_pairs(alignment_result) -> dict[str, np.ndarray]`. `score_pair(before_emb, after_emb) -> float`. `cosine_to_drift(similarity) -> float`. `classify_pair(similarity) -> Classification`. The post-Hungarian threshold check.

*Estimated time:* 60 minutes.

*Done condition:* End-to-end test on the mock alignment produces a list of `(pair, similarity, drift, classification)` tuples with sensible values for all 5 mock cases.

**Agent 3 — Concept extraction.** Starts after Agent 1 commits. Independent of Agents 2 and 4.

*Owns:* `app/ml/concepts.py`.

*Implements:* Step 5. The Pydantic `Concept` and `ConceptDiff` schemas, the system prompt, the `extract_concepts(before_text, after_text) -> ConceptDiff` async function with try/except wrapping. Optional: post-hoc evidence-id linking via substring matching.

*Estimated time:* 45 minutes.

*Done condition:* Returns a valid `ConceptDiff` for at least 2 hand-crafted document pairs. Returns empty `ConceptDiff(summary="", concepts=[])` on simulated API failure (test by passing a fake client that raises).

**Agent 4 — Pipeline orchestration and metrics.** Starts after Agent 1 commits. Can develop against stub functions for Agents 2 and 3 if they aren't done yet.

*Owns:* `app/ml/metrics.py`, `app/ml/pipeline.py`, modifications to `app/services.py` to wire `pipeline.py` into the existing `/api/diff` endpoint.

*Implements:* Step 4 (`aggregate_metrics`), Step 6 (`assemble_response`), and the top-level orchestrator using `asyncio.gather`:

```python
async def run_diff(before: str, after: str) -> DiffResponse:
    alignment = align(before, after)  # backend lead's function (or mock)
    embed_task = asyncio.create_task(embed_and_score(alignment))
    concept_task = asyncio.create_task(extract_concepts(before, after))
    scored_pairs, embeddings = await embed_task
    concepts = await concept_task
    classified = classify_all(scored_pairs, alignment.unmatched_before, alignment.unmatched_after)
    summary = aggregate_metrics(classified, before, after)
    return assemble_response(classified, concepts, summary)
```

*Estimated time:* 60 minutes.

*Done condition:* `curl -X POST localhost:8000/api/diff -d '{"before": "...", "after": "..."}'` returns a valid `DiffResponse` JSON.

### Suggested launch sequence

```
T+0 min:    Launch Agent 1.
T+30 min:   Agent 1 commits foundations to feature/ml-slice.
            You pull in all 4 worktrees: `git -C ../ml-agent-N pull` for N=2,3,4.
T+30 min:   Launch Agents 2, 3, 4 in parallel. They all see Agent 1's work.
T+90 min:   Agent 3 (concepts) finishes first (smallest scope).
T+90 min:   Agent 2 (embed/score/classify) finishes.
T+90 min:   Agent 4 (pipeline) finishes — but its tests fail until 2 and 3's commits land.
T+95 min:   Human: pull all branches, run end-to-end test in agent 4's worktree.
T+105 min:  Threshold tuning sprint (you, manually).
T+120 min:  ML slice complete and ready for backend lead's real `align()`.
```

### Coordination rules

- **Before starting work:** Each agent runs `git pull origin feature/ml-slice` to see prior commits.
- **Before committing:** Each agent runs the codebase's test suite (or at least imports their own module without errors) to avoid breaking integration.
- **File ownership is strict.** No agent edits a file outside its assignment list. If Agent 2 needs a new field on a Pydantic model, it requests the change in a comment for Agent 1 (or the human) to add. Cross-cutting edits cause merge hell.
- **Communication via commit messages.** "Adds embed_pairs(); requires AlignmentResult.original_before to exist" tells the next agent what to look for.
- **The human is the integration manager.** Agents do not merge other agents' work. You pull all branches, resolve any conflicts (rare with strict file ownership), and verify integration.

### Pitfalls of running 4 agents in parallel

**Diverging type definitions.** Agent 2 writes `Classification = Literal["stable", ...]` while the spec says `"unchanged"`. Agent 1's commit must land first so all others import the canonical types — don't let them define their own.

**Agents stepping on `services.py`.** This file existed before the ML slice and is touched by Agent 4. If any other agent imports from it or modifies it, conflicts. Agent 4 owns `services.py` exclusively for ML-slice changes; others import from `app.ml.*` only.

**Inconsistent async signatures.** Agent 2's `embed_pairs` is async, Agent 3's `extract_concepts` is async, Agent 4's `aggregate_metrics` is sync. Don't let an agent decide whether their function is async on their own — it's specified above. If it doesn't make a network call, it's sync.

**Over-eager refactoring.** An agent might decide to "clean up" `app/services.py` while in there. Forbid this in their kickoff prompt: "Do not modify files outside your assignment. Do not refactor existing code."

**Shared scratch files.** If two agents both create `app/ml/utils.py` with different contents, conflict. Agent 1 should pre-create any shared utility files (even empty ones) so others know they exist and don't duplicate.

### Agent kickoff prompt template

When launching each agent in its worktree, give it a prompt of this shape:

```
You are working in a git worktree at <path>, on branch feature/ml-slice.

Read /path/to/ML_ARCHITECTURE.md in full before starting.

Your assignment: <Agent N — task name from §8>.

Files you own (and may create or modify):
  <list>

Files you MUST NOT modify:
  Anything outside your owned list. If you need a change in another file,
  add a TODO comment in your own code and continue.

Before starting:
  git pull origin feature/ml-slice
  Verify <prerequisites from §8> are present.

When done:
  Run any tests for your module.
  git add <your files>
  git commit -m "<descriptive message naming the function added>"
  git push origin feature/ml-slice
  Report what you committed.

Do not refactor unrelated code. Do not modify configuration files.
```

---

## 9. Order of operations on Saturday

Putting it all together, the sequence the ML lead should follow:

1. **First 30 minutes (solo).** Read this document end to end. Open the existing scaffold. Confirm everything in `app/main.py`, `models.py`, `services.py`, `config.py` matches expectations. Have the 30-minute coordination conversation with the backend lead — agree on the `AlignmentResult` schema and lock it in `models.py`.

2. **Worktree setup (5 minutes).** Create the 4 worktrees and the integration branch.

3. **Launch Agent 1 (30 minutes wall-clock).** Foundations. Wait for commit.

4. **Launch Agents 2, 3, 4 in parallel (60-90 minutes wall-clock).** Monitor progress, integrate as they finish.

5. **Threshold tuning sprint (20 minutes solo).** With real or mock alignment, run the 5-example methodology in §7. Lock the constants.

6. **Integration with backend lead's real `align()` (5-10 minutes).** Replace the import in `pipeline.py`. Run end-to-end. Sanity-check on demo examples.

7. **Polish and edge cases (remainder).** Help backend lead with merge edge cases. Help frontend interpret JSON contract. Build demo example pairs.

By the end, you have a complete, tested ML pipeline that takes raw text in and returns the full structured response, ready for the frontend to consume.

---

## 10. What to flag if asked

For the 3-minute demo and judge Q&A, the honest technical limitations of the ML slice:

- **Threshold tuning is empirical.** Five hand-labelled examples, 20 minutes of tuning. Production would use a held-out evaluation set.
- **English-only.** `text-embedding-3-small` is multilingual but we tested only English.
- **No semantic reasoning beyond similarity.** Two clauses with similar embeddings might still differ in legal meaning in ways embeddings miss (e.g., `"shall"` vs `"may"`). The tool is a triage aid, not a substitute for human review.
- **Concept extraction reliability.** GPT-4o-mini with structured outputs is schema-conformant but can refuse or mis-categorize. Wrapped to fail gracefully.
- **Costs are negligible.** ~$0.001 per diff at hackathon scale.

Don't oversell. The tool surfaces likely meaning changes for humans to review faster — that's the honest value proposition.
