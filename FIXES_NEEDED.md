# 🔧 Fixes Needed to Get Stubs Working

This document lists **exactly** what needs to be fixed for end-to-end functionality.

---

## 🎯 Critical Path (Must Fix for MVP)

### 1. **ML Layer: Replace Mock Embeddings** ⚠️ CRITICAL
**File:** `ml/semantic_engine.py`
**Line:** 65-75
**Priority:** HIGHEST (nothing works without this)

**Current (Mock):**
```python
def _get_embeddings(sentences: list[str]) -> np.ndarray:
    """Get embeddings for all sentences in a single batch."""
    # Mock implementation - returns random embeddings
    return np.random.rand(len(sentences), 384)
```

**Fix Option 1 (OpenAI - Recommended):**
```python
def _get_embeddings(sentences: list[str]) -> np.ndarray:
    """Get embeddings using OpenAI API."""
    from openai import OpenAI
    import os

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=sentences
    )

    return np.array([d.embedding for d in response.data])
```

**Fix Option 2 (Local - Free but slower):**
```python
def _get_embeddings(sentences: list[str]) -> np.ndarray:
    """Get embeddings using local sentence-transformers."""
    from sentence_transformers import SentenceTransformer

    # Load once globally, not per-call
    global _model
    if '_model' not in globals():
        _model = SentenceTransformer('all-MiniLM-L6-v2')

    return _model.encode(sentences)
```

**Testing:**
```bash
cd ml
python test_cases.py  # Should see real similarity scores
```

---

### 2. **Backend: Wire ML Layer** ⚠️ CRITICAL
**File:** `backend/services/ml_client.py`
**Line:** 22-27
**Priority:** HIGHEST

**Current (Mock):**
```python
def compare_sentences_ml(v1_sentences: list[str], v2_sentences: list[str]) -> MLResult:
    # TODO: Import and call the actual ML pipeline
    # For now, return mock data to test the API flow
    return _mock_ml_result(v1_sentences, v2_sentences)
```

**Fix:**
```python
def compare_sentences_ml(v1_sentences: list[str], v2_sentences: list[str]) -> MLResult:
    """Call ML layer to align and score sentence pairs."""
    import sys
    sys.path.append('../ml')  # Add ML directory to path

    from ml.semantic_engine import compare_sentences

    # Call real ML pipeline
    result_dict = compare_sentences(v1_sentences, v2_sentences)

    # Convert dict to MLResult (already matches schema)
    pairs = [SentencePair(**p) for p in result_dict["pairs"]]
    summary = DocumentSummary(**result_dict["summary"])

    return MLResult(pairs=pairs, summary=summary)
```

**Alternative (if path issues):**
```python
# Add to backend/main.py at top:
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'ml'))

# Then in ml_client.py:
from semantic_engine import compare_sentences
```

**Testing:**
```bash
cd backend
source ../venv/bin/activate
python main.py
# Test: POST to http://localhost:8000/compare with real text
```

**After this fix, delete the entire `_mock_ml_result()` function (lines 30-107)**

---

### 3. **Backend: Async LLM Explanations** 🔶 IMPORTANT
**File:** `backend/routes/compare.py`
**Line:** 58-59
**Priority:** MEDIUM (feature works without it, but less useful)

**Current (Stubbed):**
```python
# TODO: Implement async explanation generation
# background_tasks.add_task(generate_explanations_async, comparison_id, ml_result.pairs)
```

**Fix:**
```python
# Add this function at top of file, after imports
async def generate_explanations_async(comparison_id: str, pairs: list):
    """Generate LLM explanations for yellow and red pairs."""
    import sys
    sys.path.append('../../ml')
    from ml.llm_explainer import generate_explanations

    # Filter to yellow/red pairs
    pairs_dict = [
        {
            "pair_id": p.pair_id,
            "v1_sentence": p.v1_sentence,
            "v2_sentence": p.v2_sentence,
            "similarity_score": p.similarity_score,
            "severity": p.severity
        }
        for p in pairs
        if p.severity in ["yellow", "red"]
    ]

    # Generate explanations
    explanations = await generate_explanations(pairs_dict)

    # Update store
    explanation_store[comparison_id]["explanations"].update(explanations)
    explanation_store[comparison_id]["status"] = "complete"

# Then uncomment line 59:
background_tasks.add_task(generate_explanations_async, comparison_id, ml_result.pairs)
```

**Testing:**
```bash
# POST to /compare, note the comparison_id
# Wait 5-10 seconds
# GET /explanation/{comparison_id}
# Should see explanations populated
```

---

## 🎨 Frontend Fixes (Not Critical for Backend Testing)

### 4. **Frontend: Add CSS Styling** 🟡 OPTIONAL
**Files:**
- `frontend/src/components/InputPanel.tsx`
- `frontend/src/components/DiffViewer.tsx`
- `frontend/src/components/SummaryBar.tsx`

**Current:** Components have structure but minimal styling

**Fix:** Add actual CSS (FE engineers can do this during hackathon)

Example for InputPanel:
```css
/* Add to frontend/src/styles/App.css */
.input-panel {
  padding: 2rem;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.text-areas {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.text-area-container textarea {
  width: 100%;
  height: 300px;
  padding: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  font-family: monospace;
}

button {
  background: #667eea;
  color: white;
  padding: 0.75rem 2rem;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 1rem;
}

button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
```

---

### 5. **Frontend: Wire API Polling** 🟡 OPTIONAL
**File:** `frontend/src/components/DiffViewer.tsx`

**Current:** No polling for explanations

**Fix:**
```typescript
import { useEffect, useState } from 'react';
import { getExplanations } from '../api/client';

// Inside DiffViewer component
const [explanations, setExplanations] = useState<Record<string, string>>({});

useEffect(() => {
  if (!comparisonId) return;

  const pollExplanations = async () => {
    const response = await getExplanations(comparisonId);
    setExplanations(response.explanations);

    if (response.status !== 'complete') {
      // Poll again in 2 seconds
      setTimeout(pollExplanations, 2000);
    }
  };

  pollExplanations();
}, [comparisonId]);
```

---

## 📋 Quick Fix Checklist

Priority order for hackathon:

- [ ] **1. ML embeddings** (`ml/semantic_engine.py:65-75`)
  - Choose OpenAI or local
  - Add API key to `.env`
  - Test with `python ml/test_cases.py`

- [ ] **2. Backend ML integration** (`backend/services/ml_client.py:22-27`)
  - Import real ML function
  - Delete mock function
  - Test with backend running

- [ ] **3. Async explanations** (`backend/routes/compare.py:58-59`)
  - Add async function
  - Uncomment background task
  - Test with polling

- [ ] **4. Frontend styling** (all component files)
  - Add CSS
  - Make it look good
  - FE engineers handle this

- [ ] **5. Frontend polling** (`frontend/src/components/DiffViewer.tsx`)
  - Add useEffect hook
  - Poll for explanations
  - FE engineers handle this

---

## 🧪 Testing Each Fix

### After Fix #1 (ML Embeddings)
```bash
cd ml
source ../venv/bin/activate
python quick_test.py  # Should see real similarity scores (not random)
```

### After Fix #2 (Backend Integration)
```bash
cd backend
python main.py
# In another terminal:
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{
    "v1_text": "The dog ran quickly.",
    "v2_text": "The dog ran fast."
  }'
# Should see real similarity scores from ML layer
```

### After Fix #3 (Async Explanations)
```bash
# Same as above, but wait and then:
curl http://localhost:8000/explanation/{comparison_id}
# Should see explanations populated
```

---

## 📝 Code Snippets Ready to Copy-Paste

All fixes above are copy-pasteable! Just:
1. Open the file
2. Find the line number
3. Replace the stubbed code
4. Test

---

## ⏱️ Time Estimates

| Fix | Time | Who |
|-----|------|-----|
| #1: ML embeddings | 10 min | Nickolas |
| #2: Backend integration | 5 min | Winston |
| #3: Async explanations | 15 min | Winston |
| #4: Frontend styling | 1-2 hrs | FE engineers |
| #5: Frontend polling | 30 min | FE engineers |

**Total critical path: 30 minutes** (fixes #1-3)

After that, the API works end-to-end and FE can style at leisure!

---

## 🚀 Recommended Order

1. **Nickolas**: Fix #1 (embeddings) first thing in morning
2. **Winston**: Fix #2 (backend) immediately after
3. **Test together**: POST to /compare, verify real results
4. **Winston**: Add #3 (async) while FE sets up
5. **FE Engineers**: Work on #4-5 while backend stabilizes

With this plan, you'll have a working demo in < 1 hour! 🎯
