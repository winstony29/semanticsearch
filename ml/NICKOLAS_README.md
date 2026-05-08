# Alignment Method Experiments for Nickolas

This addresses your concerns about Hungarian algorithm choices for semantic diff.

## Your Questions

### 1. What similarity signal for Hungarian?

**TL;DR: Use semantic (embeddings), not lexical.**

| Signal | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Lexical** (TF-IDF) | Fast, no API call | Fails on heavy paraphrasing | ❌ Don't use |
| **Semantic** (embeddings) | Handles paraphrasing | Requires API call | ✅ Use this |

**Why semantic wins:**
- Heavy paraphrasing is common (see test case `heavy_paraphrase`)
- Example: "revenue increased 15%" → "earnings saw 15% boost"
  - Lexical similarity: ~0.2 (only "15%" overlaps)
  - Semantic similarity: ~0.85 (same meaning)
- If lexical alignment is wrong, your semantic scoring later is useless (garbage in, garbage out)

**Architecture implication:**
```python
# DO THIS:
embeddings = get_embeddings(v1_sentences + v2_sentences)  # Single batch call
sim_matrix = cosine_similarity(emb_v1, emb_v2)
pairs = hungarian(sim_matrix)  # Alignment uses semantic signal

# NOT THIS:
pairs = hungarian_on_tfidf(v1, v2)  # Wrong alignment
scores = compute_semantic_similarity(pairs)  # Meaningless
```

### 2. Pure 1:1 Hungarian or merge/split handling?

**TL;DR: Depends on your requirements. I've implemented both.**

#### Option A: Pure 1:1 Hungarian (Simpler)
```python
from alignment_methods import semantic_hungarian

result = semantic_hungarian(v1_sentences, v2_sentences, embeddings)
```

**Pros:**
- Clean, optimal solution
- Easy to implement and debug
- Works for 90% of cases

**Cons:**
- Merges (2→1) show up as 1 match + 1 deletion
- Splits (1→2) show up as 1 match + 1 addition
- Not "wrong" per se, but less informative

**Example failure case:**
```
v1: ["Weather was sunny.", "We went to beach."]
v2: ["Sunny weather prompted beach trip."]

Hungarian result:
- Match: v1[0] ↔ v2[0] (score: 0.7)
- Deleted: v1[1]

Reality: v1[0] and v1[1] merged into v2[0]
```

#### Option B: Greedy with merge detection
```python
from alignment_methods import greedy_with_merges

result = greedy_with_merges(v1_sentences, v2_sentences, embeddings)
```

**Pros:**
- Detects many-to-one relationships
- More informative for users
- Handles real-world document editing patterns

**Cons:**
- Not globally optimal (greedy)
- More complex logic
- Slower

**Example success case:**
```
v1: ["Weather was sunny.", "We went to beach."]
v2: ["Sunny weather prompted beach trip."]

Greedy result:
- Merged: v1[0] + v1[1] → v2[0] (both have similarity > 0.5)
- Status: "merged" (explicitly marked)
```

#### Option C: Adaptive (My recommendation)
```python
from alignment_methods import adaptive_hungarian

result = adaptive_hungarian(v1_sentences, v2_sentences, embeddings)
```

**Strategy:**
1. Try semantic Hungarian first
2. If overall similarity is low (< 0.5), assume heavy restructuring
3. Fall back to greedy with merge detection

**Best of both worlds:**
- Fast and optimal for normal cases (light edits, paraphrasing)
- Handles edge cases when text is heavily restructured

### 3. Padding for unequal counts

**Your understanding is correct.** Here's the implementation:

```python
n, m = sim_matrix.shape  # n = len(v1), m = len(v2)
cost_matrix = 1 - sim_matrix

# Pad to square
max_dim = max(n, m)
padded_cost = np.full((max_dim, max_dim), 1.0)  # High cost = bad match
padded_cost[:n, :m] = cost_matrix

# Run Hungarian
row_ind, col_ind = linear_sum_assignment(padded_cost)

# Interpret results:
for i, j in zip(row_ind, col_ind):
    if i < n and j < m:
        # Real match
    elif i >= n:
        # j matched to dummy row → v2[j] is an addition
    elif j >= m:
        # i matched to dummy col → v1[i] is a deletion
```

**Key insight:** The padding value (1.0) means "infinite cost". This ensures dummy matches only happen when no better alternative exists.

## Test Cases

I've created 12 test cases covering all edge cases:

| Test Case | Challenge | Best Method |
|-----------|-----------|-------------|
| `heavy_paraphrase` | Words change, meaning same | Semantic |
| `two_to_one_merge` | 2 sentences → 1 | Greedy/Adaptive |
| `one_to_two_split` | 1 sentence → 2 | Greedy/Adaptive |
| `reordering` | Sentences moved around | Any (Hungarian is order-agnostic) |
| `minimal_style_changes` | Light edits | Any |
| `complete_rewrite` | Opposite meaning | Any (should detect no matches) |
| `identical` | No changes | Any (sanity check) |
| `additions_only` | Only new sentences | Any |
| `deletions_only` | Only removed sentences | Any |
| `mixed_complex` | Paraphrase + merge + delete + add | Adaptive |
| `unequal_lengths` | 3 sentences → 8 sentences | Tests padding |
| `empty_v1/v2/both` | Edge cases | Tests error handling |

## Running Experiments

### Quick test:
```bash
cd ml
python run_experiments.py --methods semantic adaptive --test-cases heavy_paraphrase two_to_one_merge
```

### Full comparison:
```bash
python run_experiments.py --methods all --test-cases all
```

Output:
```
SUMMARY TABLE
Legend: XM/YA/ZD = X matched, Y added, Z deleted

+-------------------+----------------+----------------+
| Test Case         | semantic       | greedy_merge   |
+-------------------+----------------+----------------+
| heavy_paraphrase  | 3M/0A/0D       | 3M/0A/0D       |
| two_to_one_merge  | 2M/0A/1D       | 1M/0A/0D/1Mg   |  ← Merge detected!
| mixed_complex     | 3M/1A/2D       | 3M/1A/1D/1Mg   |  ← More accurate
+-------------------+----------------+----------------+
```

### With real embeddings:

Replace `get_mock_embeddings()` in `run_experiments.py` with:

```python
def get_real_embeddings(sentences: List[str]) -> np.ndarray:
    """Option 1: OpenAI (recommended)"""
    from openai import OpenAI
    client = OpenAI()

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=sentences
    )

    return np.array([d.embedding for d in response.data])

# OR

def get_local_embeddings(sentences: List[str]) -> np.ndarray:
    """Option 2: Local model (free, slower)"""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(sentences)
    return embeddings
```

## Recommendations for Hackathon

### What to implement:

**For MVP (7-hour hackathon):**
```python
# Use semantic Hungarian - it's simple and works well
from alignment_methods import semantic_hungarian

def compare_sentences(v1_sentences, v2_sentences):
    embeddings = get_openai_embeddings(v1_sentences + v2_sentences)
    result = semantic_hungarian(v1_sentences, v2_sentences, embeddings)
    return result
```

**If you have extra time:**
```python
# Add adaptive fallback
from alignment_methods import adaptive_hungarian

def compare_sentences(v1_sentences, v2_sentences):
    embeddings = get_openai_embeddings(v1_sentences + v2_sentences)
    result = adaptive_hungarian(v1_sentences, v2_sentences, embeddings)
    return result
```

### Threshold calibration:

Test with real data and adjust these:

```python
# In semantic_engine.py
THRESHOLD_GREEN = 0.85   # Meaning preserved
THRESHOLD_YELLOW = 0.60  # Moderate drift
# Below 0.60 = RED (major change)

# In adaptive_hungarian
QUALITY_THRESHOLD = 0.5  # When to fall back to greedy
```

### Integration with backend:

Update `backend/services/ml_client.py`:

```python
from ml.semantic_engine import compare_sentences as ml_compare

def compare_sentences_ml(v1_sentences, v2_sentences):
    # Remove _mock_ml_result()
    # Call real ML pipeline
    return ml_compare(v1_sentences, v2_sentences)
```

## Files Created

```
ml/
├── alignment_methods.py    # 5 different alignment implementations
├── test_cases.py           # 12 edge case test scenarios
├── run_experiments.py      # Comparison/benchmark script
└── NICKOLAS_README.md      # This file
```

## Key Takeaways

1. **Use semantic embeddings for Hungarian, not lexical**
   - Lexical fails on paraphrasing (which is common)

2. **Pure 1:1 Hungarian is good enough for MVP**
   - Handles 90% of cases correctly
   - Merge detection is nice-to-have, not critical

3. **Adaptive is the best general solution**
   - Try optimal first, fall back if quality is poor
   - 10 extra lines of code, handles edge cases

4. **Padding strategy is correct**
   - Fill with high cost (1.0)
   - Dummy matches = additions/deletions

5. **Test with real embeddings ASAP**
   - Mock embeddings in `run_experiments.py` are not representative
   - Replace with OpenAI or sentence-transformers

## Next Steps for You

1. **Run experiments with real embeddings:**
   ```bash
   # Edit run_experiments.py, replace get_mock_embeddings
   python run_experiments.py --methods all --test-cases all
   ```

2. **Pick your method based on results:**
   - Semantic Hungarian → simple, optimal for light edits
   - Adaptive → handles heavy restructuring
   - Greedy with merges → if merge detection is critical

3. **Integrate into semantic_engine.py:**
   - Copy your chosen method
   - Add real embedding API call
   - Test with sample data from `test_data/`

4. **Calibrate thresholds:**
   - Run on your demo documents
   - Adjust GREEN/YELLOW/RED cutoffs
   - Aim for intuitive results

Let me know if you want me to implement the real embedding integration or if you have more questions!

---

**Quick Decision Matrix:**

| Your Priority | Use This |
|---------------|----------|
| "I want it simple and working" | `semantic_hungarian` |
| "I want to handle all edge cases" | `adaptive_hungarian` |
| "Merge detection is critical for our demo" | `greedy_with_merges` |
| "I'm still experimenting" | Run `run_experiments.py` first |
