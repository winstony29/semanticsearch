# Data Contract — Semantic Diff

This is the single source of truth for all data types flowing between Frontend, Backend, and ML.

---

## 1. FE → BE: Compare Request

**Endpoint:** `POST /compare`

```json
{
  "v1_text": "string — original version, plaintext",
  "v2_text": "string — revised version, plaintext"
}
```

TypeScript type:
```typescript
interface CompareRequest {
  v1_text: string;
  v2_text: string;
}
```

Python type:
```python
class CompareRequest(BaseModel):
    v1_text: str
    v2_text: str
```

---

## 2. BE → ML: Tokenized Sentences

This is an internal call (function call or internal HTTP, not exposed to FE).

```python
class TokenizedInput(BaseModel):
    v1_sentences: list[str]
    v2_sentences: list[str]
```

Example:
```json
{
  "v1_sentences": [
    "We should consider expanding to Japan.",
    "Our revenue grew 10% last quarter."
  ],
  "v2_sentences": [
    "We plan to expand to Japan.",
    "Revenue increased by 10% in Q3."
  ]
}
```

---

## 3. ML → BE: Alignment + Scores

```python
class SentencePair(BaseModel):
    pair_id: str              # unique ID, e.g. "pair_001"
    v1_sentence: str | None   # None if addition (v2-only)
    v2_sentence: str | None   # None if deletion (v1-only)
    v1_index: int | None      # index in original v1_sentences list
    v2_index: int | None      # index in original v2_sentences list
    similarity_score: float   # 0.0 to 1.0, cosine similarity
    status: str               # "matched" | "added" | "deleted"
    severity: str             # "green" | "yellow" | "red" | "added" | "deleted"

class DocumentSummary(BaseModel):
    overall_score: float      # mean of all matched pair scores
    total_pairs: int          # number of matched pairs
    green_count: int          # pairs with score >= 0.85
    yellow_count: int         # pairs with 0.60 <= score < 0.85
    red_count: int            # pairs with score < 0.60
    added_count: int          # v2 sentences with no v1 match
    deleted_count: int        # v1 sentences with no v2 match

class MLResult(BaseModel):
    pairs: list[SentencePair]
    summary: DocumentSummary
```

---

## 4. BE → FE: Compare Response

**Endpoint:** `POST /compare` (response)

```python
class CompareResponse(BaseModel):
    comparison_id: str             # UUID for fetching async explanations later
    pairs: list[SentencePairOut]
    summary: DocumentSummary
```

```python
class SentencePairOut(BaseModel):
    pair_id: str
    v1_sentence: str | None
    v2_sentence: str | None
    v1_index: int | None
    v2_index: int | None
    similarity_score: float        # 0.0 to 1.0
    status: str                    # "matched" | "added" | "deleted"
    severity: str                  # "green" | "yellow" | "red" | "added" | "deleted"
    explanation: str | None        # null initially, populated via async polling
```

TypeScript type:
```typescript
interface SentencePair {
  pair_id: string;
  v1_sentence: string | null;
  v2_sentence: string | null;
  v1_index: number | null;
  v2_index: number | null;
  similarity_score: number;
  status: "matched" | "added" | "deleted";
  severity: "green" | "yellow" | "red" | "added" | "deleted";
  explanation: string | null;
}

interface DocumentSummary {
  overall_score: number;
  total_pairs: number;
  green_count: number;
  yellow_count: number;
  red_count: number;
  added_count: number;
  deleted_count: number;
}

interface CompareResponse {
  comparison_id: string;
  pairs: SentencePair[];
  summary: DocumentSummary;
}
```

Example response:
```json
{
  "comparison_id": "abc-123-def",
  "pairs": [
    {
      "pair_id": "pair_001",
      "v1_sentence": "We should consider expanding to Japan.",
      "v2_sentence": "We plan to expand to Japan.",
      "v1_index": 0,
      "v2_index": 0,
      "similarity_score": 0.72,
      "status": "matched",
      "severity": "yellow",
      "explanation": null
    },
    {
      "pair_id": "pair_002",
      "v1_sentence": "Our revenue grew 10% last quarter.",
      "v2_sentence": "Revenue increased by 10% in Q3.",
      "v1_index": 1,
      "v2_index": 1,
      "similarity_score": 0.91,
      "status": "matched",
      "severity": "green",
      "explanation": null
    },
    {
      "pair_id": "pair_003",
      "v1_sentence": null,
      "v2_sentence": "We expect further growth in Q4.",
      "v1_index": null,
      "v2_index": 2,
      "similarity_score": 0.0,
      "status": "added",
      "severity": "added",
      "explanation": null
    }
  ],
  "summary": {
    "overall_score": 0.815,
    "total_pairs": 2,
    "green_count": 1,
    "yellow_count": 1,
    "red_count": 0,
    "added_count": 1,
    "deleted_count": 0
  }
}
```

---

## 5. FE → BE: Poll Explanations

**Endpoint:** `GET /explanation/{comparison_id}`

Response:
```python
class ExplanationResponse(BaseModel):
    comparison_id: str
    status: str                           # "pending" | "partial" | "complete"
    explanations: dict[str, str | None]   # pair_id → explanation string or null if not ready
```

TypeScript:
```typescript
interface ExplanationResponse {
  comparison_id: string;
  status: "pending" | "partial" | "complete";
  explanations: Record<string, string | null>;
}
```

Example:
```json
{
  "comparison_id": "abc-123-def",
  "status": "partial",
  "explanations": {
    "pair_001": "Changed from tentative consideration to a firm commitment to expand.",
    "pair_002": null
  }
}
```

FE polls this endpoint every 2–3 seconds until `status === "complete"`.

---

## 6. Severity Thresholds

These are the defaults. Nickolas owns calibration.

| Severity | Score Range | Color | Meaning |
|----------|-------------|-------|---------|
| `green` | `score >= 0.85` | `#22c55e` | Meaning preserved, safe rephrase |
| `yellow` | `0.60 <= score < 0.85` | `#eab308` | Moderate drift, review recommended |
| `red` | `score < 0.60` | `#ef4444` | Major semantic change, likely meaning shift |
| `added` | N/A | `#3b82f6` (blue) | New sentence in v2, no v1 counterpart |
| `deleted` | N/A | `#6b7280` (gray) | v1 sentence removed in v2 |

---

## 7. Variable Naming Conventions

Use these names consistently across all three layers:

| Concept | Python (BE/ML) | TypeScript (FE) | JSON key |
|---------|----------------|-----------------|----------|
| Original text | `v1_text` | `v1Text` | `v1_text` |
| Revised text | `v2_text` | `v2Text` | `v2_text` |
| Original sentences | `v1_sentences` | `v1Sentences` | `v1_sentences` |
| Revised sentences | `v2_sentences` | `v2Sentences` | `v2_sentences` |
| Similarity score | `similarity_score` | `similarityScore` | `similarity_score` |
| Pair identifier | `pair_id` | `pairId` | `pair_id` |
| Severity label | `severity` | `severity` | `severity` |
| Overall score | `overall_score` | `overallScore` | `overall_score` |
| Comparison ID | `comparison_id` | `comparisonId` | `comparison_id` |

Convention: **snake_case** in Python and JSON, **camelCase** in TypeScript. FE should convert at the API boundary.
