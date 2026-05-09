# Quick Fix Files - Copy-Paste Ready!

These files contain the exact code to replace stubs and get everything working.

## How to Use

1. **Open the file you need to fix**
2. **Find the line number** (specified in FIXES_NEEDED.md)
3. **Copy the code from the appropriate file here**
4. **Paste and replace** the stubbed code
5. **Test!**

---

## Fix #1: ML Embeddings

**Choose ONE:**

### Option A: OpenAI (Recommended - Fast & Accurate)
- **File:** `fix1_embeddings_openai.py`
- **Cost:** ~$0.00002 per 1000 tokens (pennies)
- **Setup:** Add `OPENAI_API_KEY` to `.env`
- **Speed:** Very fast

### Option B: Local (Free - Slower first run)
- **File:** `fix1_embeddings_local.py`
- **Cost:** FREE
- **Setup:** `pip install sentence-transformers`
- **Speed:** Good, but downloads 90MB model first time

**Where to paste:**
- File: `ml/semantic_engine.py`
- Line: 65-75
- Replace: The entire `_get_embeddings()` function

---

## Fix #2: Backend Integration

- **File:** `fix2_backend_integration.py`
- **Time:** 2 minutes

**Where to paste:**
- File: `backend/services/ml_client.py`
- Line: 11-27
- Replace: The `compare_sentences_ml()` function
- **ALSO DELETE:** Lines 30-107 (entire `_mock_ml_result()` function)

---

## Fix #3: Async Explanations

- **File:** `fix3_async_explanations.py`
- **Time:** 5 minutes

**Where to paste:**
- File: `backend/routes/compare.py`
- Line: After line 10 (after `explanation_store` definition)
- Action: **ADD** the new function
- Then: **UNCOMMENT** line 59

---

## Testing After Each Fix

### After Fix #1
```bash
cd ml
python quick_test.py
# Should see realistic similarity scores (not random 0.5-1.0)
```

### After Fix #2
```bash
cd backend
python main.py

# In another terminal:
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"v1_text":"The dog ran.","v2_text":"The dog walked."}'

# Should return real alignment results
```

### After Fix #3
```bash
# Same POST as above, save the comparison_id
# Wait 5 seconds, then:
curl http://localhost:8000/explanation/{comparison_id}

# Should see explanations for yellow/red pairs
```

---

## Order of Operations

**Morning of hackathon:**

1. **Nickolas (9:00 AM):**
   - Fix #1 (choose OpenAI or local)
   - Test with `python ml/quick_test.py`
   - ✅ Embeddings working

2. **Winston (9:10 AM):**
   - Fix #2 (backend integration)
   - Start backend: `python main.py`
   - ✅ API working with real ML

3. **Together (9:20 AM):**
   - Test end-to-end
   - POST to /compare
   - Verify real results
   - ✅ Core functionality working

4. **Winston (9:30 AM):**
   - Fix #3 (async explanations)
   - Test polling
   - ✅ Full feature set working

5. **FE Engineers (9:30 AM onward):**
   - Style components
   - Wire up API calls
   - Polish UI
   - ✅ Beautiful demo ready

**By 10:00 AM: Working prototype!**
**By 12:00 PM: Polished demo!**

---

## Quick Reference

| Fix | File | Line | Action | Time |
|-----|------|------|--------|------|
| #1 | `ml/semantic_engine.py` | 65 | Replace function | 10 min |
| #2 | `backend/services/ml_client.py` | 11 | Replace + delete | 5 min |
| #3 | `backend/routes/compare.py` | 10 | Add function + uncomment | 15 min |

**Total: 30 minutes to working demo**

---

## Common Issues

**"ModuleNotFoundError: No module named 'openai'"**
```bash
pip install openai
```

**"ModuleNotFoundError: No module named 'sentence_transformers'"**
```bash
pip install sentence-transformers
```

**"No such file or directory: ml/semantic_engine.py"**
```bash
# Make sure sys.path is correct
# Check the path in fix2_backend_integration.py
```

**Backend can't import from ML:**
```python
# Try this in ml_client.py instead:
import sys
sys.path.append('/absolute/path/to/ml')
from semantic_engine import compare_sentences
```

---

Good luck with the hackathon! 🚀

All the hard work is done - these are just the final connections!
