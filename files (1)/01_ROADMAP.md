# Semantic Diff — Hackathon Pipeline Roadmap

## One-liner
"Git diff for prose" — compare two versions of a document and flag changes in meaning, not just words.

## Architecture Overview

```
FE (React) → POST /compare → BE (FastAPI) → ML (Python) → BE → FE
                                                ↓ (async)
                                            LLM explanation
```

## Pipeline (step by step)

### 1. Input (Frontend)
- User pastes two plaintext versions (v1 = original, v2 = revised) into a side-by-side editor.
- FE sends both texts as a single POST request to BE.

### 2. Sentence Tokenization (Backend)
- BE receives both texts.
- Splits each into sentences using `spaCy` (`en_core_web_sm`).
- Sends both sentence arrays to the ML layer.

### 3. Embedding (ML)
- ML receives `v1_sentences: list[str]` and `v2_sentences: list[str]`.
- Concatenates into a single batch: `all_sentences = v1_sentences + v2_sentences`.
- Sends one API call to OpenAI `text-embedding-3-small` (or uses `sentence-transformers` locally with `all-MiniLM-L6-v2`).
- Splits the returned embeddings back into `emb_v1` and `emb_v2`.

### 4. Alignment via Hungarian Algorithm (ML)
- Computes pairwise cosine similarity matrix: `sim_matrix = cosine_similarity(emb_v1, emb_v2)` → shape `(n, m)`.
- Converts to cost matrix: `cost_matrix = 1 - sim_matrix`.
- Pads to square if `n != m` (fill value = 1.0, meaning "no match").
- Runs `scipy.optimize.linear_sum_assignment(padded_cost)`.
- Produces aligned pairs, plus unmatched sentences flagged as additions or deletions.

### 5. Scoring (ML)
- For each aligned pair `(i, j)`, reads off `sim_matrix[i][j]` as the semantic similarity score.
- Classifies each pair:
  - `score >= 0.85` → GREEN (meaning preserved)
  - `0.60 <= score < 0.85` → YELLOW (moderate drift)
  - `score < 0.60` → RED (major semantic drift)
- Thresholds are configurable; these are starting defaults.

### 6. Document-level Summary (ML)
- Computes `overall_score = mean(all pair scores)`.
- Computes `drift_count = number of pairs below 0.85`.
- Returns summary stats alongside per-sentence results.

### 7. LLM Explanation — ASYNC (ML)
- For all YELLOW and RED pairs, sends a request to an LLM (Claude/GPT):
  - Prompt: "Sentence A: {v1}. Sentence B: {v2}. Explain how the meaning changed in one sentence."
- This runs asynchronously AFTER the initial response is sent to FE.
- FE receives scores first, then explanations stream in via polling or SSE.

### 8. Rendering (Frontend)
- Side-by-side view: v1 on left, v2 on right.
- Each v2 sentence is highlighted by severity (green/yellow/red).
- Each pair shows a similarity percentage badge.
- Clicking a pair expands to show the LLM explanation (once loaded).
- Accept/reject buttons per sentence pair.
- Summary bar at bottom: overall semantic accuracy %, number of flags.

---

## Sources of Truth

| Component | Library / Service | Why |
|-----------|-------------------|-----|
| Sentence splitting | `spaCy` (`en_core_web_sm`) | Reliable, handles abbreviations and edge cases better than nltk |
| Embeddings | OpenAI `text-embedding-3-small` | Fast, cheap, good quality. Fallback: `sentence-transformers/all-MiniLM-L6-v2` (local, free) |
| Alignment | `scipy.optimize.linear_sum_assignment` | Optimal 1:1 bipartite matching, 5 lines of code |
| Cosine similarity | `sklearn.metrics.pairwise.cosine_similarity` | Standard, vectorized, fast |
| LLM explanations | Claude API (`claude-sonnet-4-20250514`) or OpenAI GPT-4o-mini | Async call for natural language diff explanation |
| Backend framework | FastAPI | Lightweight, async-native, easy to set up |
| Frontend framework | React (Vite) | Fast to scaffold, component-based |

---

## Stretch Goals (if time permits)
1. PDF/DOCX upload support (PyMuPDF / python-docx for extraction).
2. Multi-to-one matching for merged/split sentences (expanded candidate set before Hungarian).
3. Paragraph-level hierarchical alignment (paragraph first, then sentence within matched paragraphs).
4. Persistent storage of past comparisons.
5. Export diff report as PDF.
