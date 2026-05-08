# Claude Code Generation Prompts

Use these as starting prompts when scaffolding with Claude Code / Cursor / other LLM tools.

---

## Backend (Winston)

### Prompt 1: Scaffold FastAPI server

```
Create a FastAPI project for a semantic diff tool.

Structure:
- main.py (app entry, CORS, routes)
- routes/compare.py (POST /compare endpoint)
- routes/explanation.py (GET /explanation/{comparison_id} endpoint)
- services/tokenizer.py (sentence splitting with spaCy en_core_web_sm)
- services/ml_client.py (calls the ML layer — for now just a function call)
- models/schemas.py (all Pydantic models from the data contract)

POST /compare should:
1. Accept { v1_text: str, v2_text: str }
2. Tokenize both texts into sentences using spaCy
3. Pass sentences to ML layer (imported function)
4. Generate a comparison_id (uuid4)
5. Return CompareResponse immediately with explanation fields set to null
6. Kick off async background task to generate LLM explanations for yellow/red pairs
7. Store explanations in an in-memory dict keyed by comparison_id

GET /explanation/{comparison_id} should:
1. Return current state of explanations (pending/partial/complete)
2. Return dict of pair_id → explanation string

Use these exact Pydantic models: [paste from 03_DATA_CONTRACT.md]

Add CORS middleware allowing localhost:5173 (Vite default).
```

### Prompt 2: spaCy tokenizer

```
Write a function tokenize_text(text: str) -> list[str] that:
1. Uses spaCy en_core_web_sm to split text into sentences
2. Strips whitespace from each sentence
3. Filters out empty strings
4. Returns the list of sentence strings

Include a fallback: if spaCy fails, split on ". " as a basic fallback.
```

---

## ML Layer (Nickolas)

### Prompt 1: Core pipeline

```
Write a Python module semantic_engine.py that implements the full semantic diff pipeline.

Function signature:
def compare_sentences(v1_sentences: list[str], v2_sentences: list[str]) -> MLResult

Steps:
1. Concatenate v1_sentences + v2_sentences into one list.
2. Call OpenAI text-embedding-3-small to embed all sentences in a single batch.
3. Split embeddings back into emb_v1 and emb_v2.
4. Compute cosine similarity matrix using sklearn.metrics.pairwise.cosine_similarity.
5. Build cost matrix: 1 - sim_matrix.
6. Pad to square with fill_value=1.0 if lengths differ.
7. Run scipy.optimize.linear_sum_assignment on padded cost matrix.
8. For each matched pair, read off similarity score. Classify:
   - score >= 0.85 → "green"
   - 0.60 <= score < 0.85 → "yellow"
   - score < 0.60 → "red"
9. Detect additions (v2 indices matched to padded rows) and deletions (v1 indices matched to padded cols).
10. Compute DocumentSummary: overall_score, counts per severity.
11. Return MLResult with pairs list and summary.

Use these exact data models: [paste from 03_DATA_CONTRACT.md]

Include constants at the top:
THRESHOLD_GREEN = 0.85
THRESHOLD_YELLOW = 0.60
EMBEDDING_MODEL = "text-embedding-3-small"
PADDING_PENALTY = 1.0
```

### Prompt 2: LLM explanation generator

```
Write a function:
async def generate_explanations(pairs: list[SentencePair]) -> dict[str, str]

For each pair with severity "yellow" or "red":
1. Call Claude API (claude-sonnet-4-20250514) with this prompt:
   "Original: {v1_sentence}
    Revised: {v2_sentence}
    Similarity score: {score}
    In one sentence, explain how the meaning changed between the original and revised version."
2. Collect responses into a dict: pair_id → explanation string.
3. Return the dict.

Use asyncio.gather to parallelize the LLM calls.
Skip pairs with severity "green", "added", or "deleted".
```

---

## Frontend (FE Engineers)

### Prompt 1: React scaffold + input form (FE Engineer 2)

```
Create a React (Vite + TypeScript) project for a semantic diff viewer.

Components needed:
- App.tsx (main layout)
- InputPanel.tsx (two textareas side by side, "Compare" button)
- DiffViewer.tsx (renders comparison results)
- SummaryBar.tsx (bottom bar with overall stats)

InputPanel:
- Two <textarea> elements, left labeled "Version 1 (Original)", right labeled "Version 2 (Revised)"
- "Compare" button that POSTs to http://localhost:8000/compare
- Loading spinner while waiting for response
- Store response in App-level state and pass to DiffViewer

Use these TypeScript interfaces: [paste from 03_DATA_CONTRACT.md]
```

### Prompt 2: Diff viewer component (FE Engineer 1)

```
Create a DiffViewer React component that takes a CompareResponse and renders:

1. Side-by-side layout: v1 sentences on the left, v2 sentences on the right.
2. Each v2 sentence is highlighted with a background color based on severity:
   - green: #22c55e (20% opacity background)
   - yellow: #eab308 (20% opacity background)
   - red: #ef4444 (20% opacity background)
   - added: #3b82f6 (blue, 20% opacity)
3. Deleted v1 sentences shown on left side with gray strikethrough.
4. Each pair shows a similarity score badge (e.g., "97%") to the right of the v2 sentence.
5. Hovering a v2 sentence highlights the corresponding v1 sentence.
6. Each pair has Accept / Reject buttons (store state locally for now).

Props:
- pairs: SentencePair[]
- summary: DocumentSummary

Keep it clean and minimal. No fancy animations yet.
```

### Prompt 3: Summary bar (FE Engineer 2)

```
Create a SummaryBar React component that shows:
1. Overall semantic accuracy as a percentage with a progress bar
   - Bar color: green if >= 85%, yellow if >= 60%, red if < 60%
2. Counts: "X green, Y yellow, Z red, A added, B deleted"
3. Accept All / Reject All buttons

Props:
- summary: DocumentSummary
```

---

## Testing Data

Use this pair for initial testing:

**v1 (original):**
```
Hi I am Nickolas and I am participating in a hackathon. I am doing this with my 3 other friends. I can not wait to start building and win first prize.
```

**v2 (revised):**
```
Nickolas will be participating in a hackathon. He has 3 other friends at the hackathon. He is impatient to collect his first prize money.
```

Expected behavior:
- Sentence 1: moderate drift (first person → third person, slight meaning change) → YELLOW
- Sentence 2: moderate drift ("doing this with" vs "has friends at") → YELLOW
- Sentence 3: major drift ("can't wait to start building and win" vs "impatient to collect prize money" — removes the building aspect, assumes winning) → RED
