# Alignment Method Comparison

Test of semantic_hungarian, greedy_with_merges, and smith_waterman using OpenAI text-embedding-3-small.

## Scenario 1 - Merge (2→1)

v1:
- [0] The weather was sunny.
- [1] We decided to go to the beach.
- [2] Everyone had a great time.

v2:
- [0] The sunny weather prompted us to go to the beach.
- [1] Everyone had a great time.

| Method | Pairs | Del | Add | Avg Sim |
|--------|-------|-----|-----|---------|
| semantic_hungarian | 2 | 1 | 0 | 0.87 |
| greedy_with_merges | 3 | 0 | 0 | 0.78 |
| smith_waterman | 2 | 1 | 0 | 0.87 |

semantic_hungarian:
- v1[1] ↔ v2[0] score=0.73
- v1[2] ↔ v2[1] score=1.00

greedy_with_merges:
- v1[2] ↔ v2[1] score=1.00
- v1[1] ↔ v2[0] score=0.73
- v1[0] ↔ v2[0] score=0.60

smith_waterman:
- v1[1] ↔ v2[0] score=0.73
- v1[2] ↔ v2[1] score=1.00

## Scenario 2 - Reorder

v1:
- [0] First we ate lunch.
- [1] Then we went swimming.
- [2] Finally we drove home.

v2:
- [0] We went swimming.
- [1] We drove home.
- [2] First we ate lunch.

| Method | Pairs | Del | Add | Avg Sim |
|--------|-------|-----|-----|---------|
| semantic_hungarian | 3 | 0 | 0 | 0.95 |
| greedy_with_merges | 3 | 0 | 0 | 0.95 |
| smith_waterman | 2 | 1 | 1 | 0.92 |

semantic_hungarian:
- v1[0] ↔ v2[2] score=1.00
- v1[1] ↔ v2[0] score=0.93
- v1[2] ↔ v2[1] score=0.90

greedy_with_merges:
- v1[0] ↔ v2[2] score=1.00
- v1[1] ↔ v2[0] score=0.93
- v1[2] ↔ v2[1] score=0.90

smith_waterman:
- v1[1] ↔ v2[0] score=0.93
- v1[2] ↔ v2[1] score=0.90

## Scenario 3 - Semantic drift

v1:
- [0] We should consider expanding to Japan.
- [1] Our revenue grew 10% last quarter.

v2:
- [0] We plan to expand to Japan.
- [1] Revenue increased by 10% in Q3.

| Method | Pairs | Del | Add | Avg Sim |
|--------|-------|-----|-----|---------|
| semantic_hungarian | 2 | 0 | 0 | 0.82 |
| greedy_with_merges | 2 | 0 | 0 | 0.82 |
| smith_waterman | 2 | 0 | 0 | 0.82 |

semantic_hungarian:
- v1[0] ↔ v2[0] score=0.84
- v1[1] ↔ v2[1] score=0.80

greedy_with_merges:
- v1[0] ↔ v2[0] score=0.84
- v1[1] ↔ v2[1] score=0.80

smith_waterman:
- v1[0] ↔ v2[0] score=0.84
- v1[1] ↔ v2[1] score=0.80

## Scenario 4 - Completely unrelated

v1:
- [0] The API documentation covers authentication flows.

v2:
- [0] Preheat the oven to 350 degrees.
- [1] Mix flour and sugar in a bowl.

| Method | Pairs | Del | Add | Avg Sim |
|--------|-------|-----|-----|---------|
| semantic_hungarian | 0 | 1 | 2 | 0.00 |
| greedy_with_merges | 0 | 1 | 2 | 0.00 |
| smith_waterman | 0 | 1 | 2 | 0.00 |

All methods: no pairs
