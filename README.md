# Semantic Diff

> "Git diff for prose" — compare two versions of a document and flag changes in meaning, not just words.

A hackathon project that uses embeddings, Hungarian algorithm alignment, and LLM explanations to perform semantic comparison of document versions.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ (for backend & ML)
- Node.js 18+ (for frontend)
- OpenAI API key (for embeddings)
- Anthropic API key (for LLM explanations)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys

# Run the server
python main.py
```

Backend will run on http://localhost:8000

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env

# Run dev server
npm run dev
```

Frontend will run on http://localhost:5173

### 3. Test the API

Visit http://localhost:8000/docs for the interactive API documentation (FastAPI auto-generated).

Or use the test data in `test_data/` directory.

## 📁 Project Structure

```
.
├── backend/                 # FastAPI server (Winston's domain)
│   ├── main.py             # App entry point
│   ├── routes/             # API endpoints
│   │   ├── compare.py      # POST /compare endpoint
│   │   └── explanation.py  # GET /explanation/{id} endpoint
│   ├── services/           # Business logic
│   │   ├── tokenizer.py    # spaCy sentence tokenization
│   │   └── ml_client.py    # ML layer client
│   └── models/             # Pydantic schemas
│       └── schemas.py      # Data contract models
│
├── ml/                      # ML layer (Nickolas's domain)
│   ├── semantic_engine.py  # Embedding + Hungarian alignment
│   └── llm_explainer.py    # LLM explanation generation
│
├── frontend/                # React frontend
│   └── src/
│       ├── components/      # UI components
│       │   ├── InputPanel.tsx      # FE Engineer 2
│       │   ├── DiffViewer.tsx      # FE Engineer 1
│       │   └── SummaryBar.tsx      # FE Engineer 2
│       ├── types/           # TypeScript types
│       │   └── api.ts       # Data contract (matches backend)
│       └── api/             # API client
│           └── client.ts    # HTTP client functions
│
├── test_data/               # Sample documents for testing
└── files (1)/               # Original planning docs
    ├── 01_ROADMAP.md
    ├── 02_TEAM_SPLIT.md
    ├── 03_DATA_CONTRACT.md
    └── 04_CLAUDE_CODE_PROMPTS.md
```

## 🔄 Pipeline Flow

```
FE (React) → POST /compare → BE (FastAPI) → ML (Python) → BE → FE
                                                ↓ (async)
                                            LLM explanation
```

1. **Frontend**: User pastes v1 (original) and v2 (revised) text
2. **Backend**: Tokenizes both into sentences using spaCy
3. **ML Layer**:
   - Embeds all sentences in one batch
   - Runs Hungarian algorithm for optimal alignment
   - Scores each pair with cosine similarity
   - Classifies: GREEN (≥0.85), YELLOW (0.60-0.85), RED (<0.60)
4. **Backend**: Returns immediate response, kicks off async LLM explanations
5. **Frontend**: Displays side-by-side diff, polls for explanations

## 🎯 Team Responsibilities

| Role | Person | Focus |
|------|--------|-------|
| Backend | Winston | FastAPI server, tokenization, API routing, async LLM calls |
| ML | Nickolas | Embeddings, Hungarian alignment, scoring, LLM prompts |
| Frontend 1 | TBD | Diff viewer, side-by-side layout, color-coded highlighting |
| Frontend 2 | TBD | Input form, summary dashboard, accept/reject flow, polling |

## 📊 Data Contract

See `files (1)/03_DATA_CONTRACT.md` for the complete API specification.

**Key endpoints:**

- `POST /compare` - Compare two document versions
  - Input: `{ v1_text: string, v2_text: string }`
  - Output: `{ comparison_id, pairs[], summary }`

- `GET /explanation/{comparison_id}` - Poll for async LLM explanations
  - Output: `{ status, explanations: { pair_id: string } }`

## 🧪 Testing

Use the sample data in `test_data/`:

```bash
# Sample 1: Personal statement (first → third person changes)
# Expected: 1 RED, 2 YELLOW

# Sample 2: Business document (commitment level changes + addition)
# Expected: 1 GREEN, 1 YELLOW, 1 ADDED
```

## 🔬 ML Alignment Experiments (For Nickolas)

Multiple alignment methods have been implemented and tested:

```bash
cd ml
python run_experiments.py --methods all --test-cases all
```

**Available methods:**
- `lexical_hungarian` - TF-IDF similarity (fast but fails on paraphrasing)
- `semantic_hungarian` - Embedding-based (recommended for MVP)
- `hybrid_hungarian` - Lexical pre-filter + semantic refinement
- `greedy_with_merges` - Handles 2→1 and 1→2 sentence merging/splitting
- `adaptive_hungarian` - Auto-selects based on quality (recommended for production)

**Test cases:** 12 edge cases including heavy paraphrasing, merges, splits, reordering, etc.

See `ml/NICKOLAS_README.md` for detailed analysis and recommendations.

## 🛠️ Implementation Status

### ✅ Completed (Pre-hackathon)
- [x] Backend structure with FastAPI
- [x] All Pydantic models (data contract)
- [x] Sentence tokenization with spaCy
- [x] ML pipeline skeleton (embeddings + Hungarian)
- [x] **5 different alignment methods with experiments**
- [x] **12 edge case test scenarios**
- [x] **Experiment comparison framework**
- [x] LLM explanation module
- [x] Frontend structure with React + TypeScript
- [x] All TypeScript types (data contract)
- [x] Component stubs (InputPanel, DiffViewer, SummaryBar)
- [x] API client utilities
- [x] Test data samples

### 🚧 To Do (During hackathon)

**Winston (Backend):**
- [ ] Wire up ML layer integration (replace mock in `ml_client.py`)
- [ ] Implement async background task for LLM explanations
- [ ] Add error handling for edge cases
- [ ] Test end-to-end with real ML pipeline

**Nickolas (ML):**
- [ ] Run experiments with real embeddings (`python ml/run_experiments.py`)
- [ ] Choose alignment method (semantic_hungarian for MVP, adaptive for production)
- [ ] Implement actual embedding API call (OpenAI or sentence-transformers)
- [ ] Calibrate similarity thresholds based on experiment results
- [ ] Test LLM explanation prompt quality
- [ ] Integrate chosen method into semantic_engine.py

**FE Engineer 1 (Diff Viewer):**
- [ ] Implement full styling for diff viewer
- [ ] Add hover interactions between v1 ↔ v2
- [ ] Connector lines between matched pairs (stretch)
- [ ] Handle additions/deletions display
- [ ] Responsive layout

**FE Engineer 2 (Input + Summary):**
- [ ] Style input panel and textareas
- [ ] Implement polling for explanations
- [ ] Wire accept/reject buttons
- [ ] Accept All / Reject All functionality
- [ ] Final output generation (cleaned v2)

## 🔑 Configuration

### Severity Thresholds

```python
THRESHOLD_GREEN = 0.85   # Meaning preserved
THRESHOLD_YELLOW = 0.60  # Moderate drift
# Below 0.60 = RED (major semantic change)
```

### Embedding Models

**Option 1 (recommended):** OpenAI `text-embedding-3-small`
- Fast, cheap, good quality
- Requires API key

**Option 2 (local fallback):** `sentence-transformers/all-MiniLM-L6-v2`
- Free, runs locally
- Slightly lower quality

### LLM Models

Currently using: `claude-sonnet-4-20250514`
- Fallback: GPT-4o-mini

## 📝 Notes

- Mock ML results are currently returned from `backend/services/ml_client.py`
- Replace the `_mock_ml_result()` function once real ML pipeline is ready
- Frontend components have basic structure but need CSS styling
- Async explanation generation is stubbed (TODO in `routes/compare.py`)

## 🎉 Demo

For demo, prepare 2-3 document pairs showing:
1. Minor rewording (mostly green)
2. Moderate changes (yellow)
3. Major semantic drift (red)
4. Additions and deletions

Good demo examples: contract revisions, essay edits, email rewrites.

---

Built with FastAPI, React, OpenAI, Anthropic, spaCy, scikit-learn, and scipy.
