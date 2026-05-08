# Team Split — Semantic Diff

## Team Members

| Role | Person | Focus |
|------|--------|-------|
| Backend Engineer | Winston | FastAPI server, sentence tokenization, API routing, async LLM calls |
| ML Engineer | Nickolas | Embedding pipeline, Hungarian alignment, scoring, LLM explanation prompts |
| Frontend Engineer 1 | TBD | Diff viewer component, side-by-side layout, color-coded highlighting |
| Frontend Engineer 2 | TBD | Input UI, summary dashboard, accept/reject flow, polling for async explanations |

---

## Detailed Responsibilities

### Winston (Backend)

**Owns:** FastAPI server, request/response contracts, orchestration between FE and ML.

Tasks:
1. Scaffold FastAPI project with `/compare` POST endpoint.
2. Implement sentence tokenization using spaCy (`en_core_web_sm`).
3. Call ML layer with tokenized sentences, receive scores + pairs.
4. Implement async endpoint `/explanation/{comparison_id}` for LLM results.
5. Kick off LLM explanation calls asynchronously after returning initial scores to FE.
6. Handle error cases: empty input, single sentence, identical texts.
7. CORS config for React frontend.

Key decisions Winston owns:
- Request/response JSON schema (see `03_DATA_CONTRACT.md`).
- How to pass data to ML layer (direct function call if monorepo, or internal HTTP if separate service).
- Async job management for LLM explanations (simple in-memory dict is fine for hackathon).

### Nickolas (ML)

**Owns:** Embedding, alignment, scoring, LLM prompt engineering.

Tasks:
1. Set up OpenAI embedding calls (batch, single API call for all sentences).
2. Implement Hungarian alignment using `scipy.optimize.linear_sum_assignment`.
3. Compute cosine similarity scores per aligned pair.
4. Classify pairs into GREEN/YELLOW/RED by threshold.
5. Compute document-level summary stats (overall score, drift count).
6. Detect additions (unmatched v2 sentences) and deletions (unmatched v1 sentences).
7. Write the LLM explanation prompt — given a sentence pair and score, generate a one-sentence explanation of the semantic change.
8. Threshold calibration — test with sample document pairs and adjust 0.85/0.60 defaults.

Key decisions Nickolas owns:
- Embedding model choice (OpenAI vs local sentence-transformers).
- Similarity thresholds for GREEN/YELLOW/RED.
- LLM prompt template for explanations.
- Padding penalty value for Hungarian (default 1.0).

### Frontend Engineer 1 — Diff Viewer

**Owns:** The core diff display component.

Tasks:
1. Side-by-side layout: v1 (left, read-only) and v2 (right, highlighted).
2. Color-code each v2 sentence: green (≥0.85), yellow (0.60–0.85), red (<0.60).
3. Show similarity score badge next to each v2 sentence.
4. Highlight corresponding v1 sentence on hover/click.
5. Draw connector lines between matched pairs (stretch goal).
6. Handle additions (v2-only, marked as "NEW") and deletions (v1-only, marked as "REMOVED").

### Frontend Engineer 2 — Input + Summary + Actions

**Owns:** Input form, summary dashboard, accept/reject UX.

Tasks:
1. Two text areas for pasting v1 and v2, with a "Compare" button.
2. Loading state while ML pipeline runs.
3. Summary bar at bottom: overall semantic accuracy %, drift count, progress bar visualization.
4. Accept/reject buttons per sentence pair.
5. Poll `/explanation/{comparison_id}` endpoint and populate explanation tooltips as they arrive.
6. "Accept All" / "Reject All" bulk actions.
7. Final output: cleaned v2 text with rejected changes reverted.

---

## Integration Points

```
FE Engineer 2 (input) → POST /compare → Winston (BE) → Nickolas (ML)
                                                              ↓
FE Engineer 1 (diff viewer) ← JSON response ← Winston (BE) ←─┘
                                                              ↓ (async)
FE Engineer 2 (explanations) ← polling ← Winston (BE) ← Nickolas (LLM calls)
```

---

## Timeline (7 hours)

| Time | Winston (BE) | Nickolas (ML) | FE 1 (Diff Viewer) | FE 2 (Input/Summary) |
|------|-------------|---------------|---------------------|----------------------|
| Hour 0–1 | FastAPI scaffold, spaCy setup, `/compare` endpoint stub | Embedding + Hungarian pipeline working in a notebook | React scaffold, diff viewer component with mock data | Input form, "Compare" button, loading state |
| Hour 1–2 | Wire BE → ML integration, return real data | Scoring + classification logic, test with sample texts | Consume real API data, color-coded rendering | Summary bar with mock data |
| Hour 2–3 | Async LLM explanation endpoint | LLM prompt engineering, threshold calibration | Hover/click interactivity between pairs | Wire summary to real API data |
| Hour 3–5 | Bug fixes, edge cases, CORS issues | Edge cases (empty, identical, totally rewritten) | Polish: connector lines, animations, responsive | Accept/reject per sentence, polling for explanations |
| Hour 5–6 | End-to-end testing with team | End-to-end testing with team | End-to-end testing with team | End-to-end testing with team |
| Hour 6–7 | Demo prep | Demo prep | Demo prep | Demo prep |

---

## Pre-build Checklist (tonight)

- [ ] Agree on data contract (see `03_DATA_CONTRACT.md`)
- [ ] Scaffold FastAPI project with hello-world endpoint
- [ ] Scaffold React project with Vite
- [ ] Get OpenAI API key set up and tested
- [ ] Install spaCy + `en_core_web_sm` model
- [ ] Nickolas: have a working notebook that takes two sentence lists and returns aligned pairs + scores
- [ ] FE: have diff viewer rendering with hardcoded mock data matching the data contract
- [ ] Prepare 2–3 demo document pairs (contract, essay, email) with known semantic drifts
