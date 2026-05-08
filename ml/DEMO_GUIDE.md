# Running the Demos - NO API KEYS NEEDED!

You can test the alignment methods RIGHT NOW without any API keys or setup. All demos use smart mock embeddings.

## 🚀 Quick Start (30 seconds)

```bash
cd ml
python quick_test.py
```

Shows one clear example of sentence merging and Hungarian alignment in action.

## 🎨 Visual Demo (2 minutes)

```bash
python visual_demo.py
```

Shows similarity matrices as ASCII heatmaps! Compare lexical vs semantic alignment visually.

Output looks like:
```
LEXICAL SIMILARITY (TF-IDF)
       v2[0]  v2[1]  v2[2]
v1[0]   ██     ░░
v1[1]   ░░     ▓▓

SEMANTIC SIMILARITY (Embeddings)
       v2[0]  v2[1]  v2[2]
v1[0]   ██     ▒▒
v1[1]   ▓▓     ██
```

Legend: `██` = high similarity, `░░` = low

## 🎪 Full Interactive Demo (5 minutes)

```bash
python demo.py
```

Walks through 5 scenarios:
1. Light paraphrasing (easy)
2. Heavy paraphrasing (lexical fails)
3. Sentence merging (Hungarian limitation)
4. Mixed changes (real-world)
5. Complete rewrite (rejection test)

Shows results from 3 different methods side-by-side.

## 📊 Full Experiment Suite (10 minutes)

```bash
# Install additional dependency
pip install tabulate

# Run all methods on all test cases
python run_experiments.py --methods all --test-cases all
```

Generates comparison table and JSON results.

For specific tests:
```bash
python run_experiments.py --methods semantic adaptive --test-cases heavy_paraphrase two_to_one_merge
```

## 🎯 What to Try

### Test 1: See the difference between methods
```bash
python demo.py
# Press ENTER through scenarios
# Watch for "Heavy Paraphrasing" - lexical vs semantic difference is clear
```

### Test 2: Understand similarity matrices
```bash
python visual_demo.py
# Look at the heatmap patterns
# Dark squares = high similarity
```

### Test 3: See merge detection
```bash
python quick_test.py
# Shows why pure Hungarian can't detect 2→1 merges
```

### Test 4: Run the full benchmark
```bash
python run_experiments.py --methods semantic greedy_merge --test-cases two_to_one_merge mixed_complex
# Compare how semantic vs greedy handles merges
```

## 📝 Sample Output

### quick_test.py
```
📄 VERSION 1 (Original):
  [0] The weather was sunny.
  [1] We decided to go to the beach.
  [2] Everyone had a great time.

📄 VERSION 2 (Revised):
  [0] The sunny weather prompted us to go to the beach.
  [1] Everyone had a great time.

🔍 Running Semantic Hungarian Alignment...

✨ RESULTS:
🟡 MATCHED: v1[0] ↔ v2[0]  (similarity: 0.73)
   v1: The weather was sunny.
   v2: The sunny weather prompted us to go to the beach.

🟢 MATCHED: v1[2] ↔ v2[1]  (similarity: 0.98)
   v1: Everyone had a great time.
   v2: Everyone had a great time.

➖ DELETED: v1[1] (removed from v2)
   We decided to go to the beach.
```

### visual_demo.py
```
SEMANTIC SIMILARITY (Embeddings)

       v2[0]  v2[1]
v1[0]   ▓▓     ░░   The weather was sunny.
v1[1]   ▓▓     ░░   We decided to go to the beach.
v1[2]   ░░     ██   Everyone had a great time.

💡 Notice: Both v1[0] and v1[1] have high similarity (▓▓) to v2[0]
   This shows the merge! But Hungarian can only pick one.
```

### demo.py (Interactive)
```
=================================================================
  2. Heavy Paraphrasing (Lexical Fails)
=================================================================

V1 (Original):
  [0] The company's revenue increased by 15% last quarter.
  [1] We are planning to expand into Asian markets.

V2 (Revised):
  [0] Last quarter saw a 15% boost in corporate earnings.
  [1] Next year, we'll enter markets across Asia.

💡 What to notice: Lexical will struggle (different words), semantic should work.

--- LEXICAL (TF-IDF) ---
Matched pairs (1):
  🔴 v1[0] ↔ v2[0]  (similarity: 0.42)  ← LOW! Words differ too much

--- SEMANTIC (EMBEDDINGS) ---
Matched pairs (2):
  🟢 v1[0] ↔ v2[0]  (similarity: 0.87)  ← HIGH! Meaning preserved
  🟢 v1[1] ↔ v2[1]  (similarity: 0.82)  ← HIGH! Meaning preserved
```

## 🎓 Learning Path

**If you're Nickolas:**
1. Run `python visual_demo.py` first - understand similarity matrices
2. Run `python demo.py` - see method differences
3. Read `NICKOLAS_README.md` - deep dive into choices
4. Run experiments with real embeddings (replace mock in run_experiments.py)
5. Pick your method and integrate

**If you're Winston:**
1. Run `python quick_test.py` - see what the ML layer returns
2. Understand the pair format (matched/added/deleted)
3. Wire this into `backend/services/ml_client.py`

**If you're a FE Engineer:**
1. Run `python quick_test.py` - see the JSON structure
2. Note: pairs have v1_index, v2_index, similarity_score, status
3. This is what your API will return

## ⚠️ Important Notes

1. **Mock Embeddings**: These demos use word-overlap based mock embeddings. They're good enough to demonstrate differences, but real embeddings (OpenAI/sentence-transformers) will be MORE accurate.

2. **Similarity Scores**: The mock scores are approximate. With real embeddings:
   - Identical sentences → ~0.99
   - Light paraphrase → ~0.85-0.95
   - Heavy paraphrase → ~0.70-0.85
   - Different meaning → <0.50

3. **Next Step**: Replace `get_mock_embeddings()` in `run_experiments.py` with real API call, then re-run experiments.

## 🐛 Troubleshooting

**ImportError: No module named 'alignment_methods'**
```bash
# Make sure you're in the ml/ directory
cd ml
python quick_test.py
```

**ImportError: No module named 'tabulate'**
```bash
# Only needed for run_experiments.py
pip install tabulate
# Or just skip that one, run demo.py instead
```

**Demos are too slow**
- They're instant (no API calls!)
- If you see "Computing embeddings..." hanging, you might have accidentally triggered real API
- Use the mock versions in the demo scripts

## 📚 Files Overview

| File | Purpose | Time | API Needed? |
|------|---------|------|-------------|
| `quick_test.py` | Simplest demo, one example | 30 sec | ❌ No |
| `visual_demo.py` | ASCII heatmap matrices | 2 min | ❌ No |
| `demo.py` | Full interactive walkthrough | 5 min | ❌ No |
| `run_experiments.py` | Benchmark all methods | 10 min | ❌ No (with mock) |
| | | | ✅ Yes (with real embeddings) |

## 🎯 What You'll Learn

After running these demos, you'll understand:
- ✅ Why semantic > lexical for paraphrasing
- ✅ Why pure Hungarian can't detect merges
- ✅ When to use greedy vs Hungarian
- ✅ How similarity thresholds affect results
- ✅ What JSON structure your backend will return

Now go run them! Start with `python quick_test.py` 🚀
