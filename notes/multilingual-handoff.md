# Multilingual Support — Handoff to Backend Lead

**Date:** 2026-05-09
**From:** ML Lead (Nickolas)
**To:** Backend Lead
**Status:** ML side already covered; one backend change required.

---

## Product framing

The pipeline should accept input in any language. Primary use case is a
**translation fidelity check** — e.g. a user runs a contract through Google
Translate and wants to know whether the meaning was preserved. Same-language
diffs (revising a draft) keep working as a side effect.

---

## ML side: nothing to change

I audited the `ml/` slice end to end. It is already language-agnostic:

| File | Reason it's already fine |
|---|---|
| `ml/embeddings.py` | `text-embedding-3-small` is multilingual; equivalent meaning across languages embeds near each other |
| `ml/scoring.py` | `np.dot` is math, not text |
| `ml/classification.py` | Threshold comparisons on similarity scalars — language-blind |
| `ml/concepts.py` | `gpt-4o-mini` accepts multilingual input with the existing English prompt |
| `ml/metrics.py` | `pct_text_edited` runs on any string (cross-script result is less *meaningful*, but still numerically valid) |
| `ml/pipeline.py` / `ml/thresholds.py` | No text-language assumptions |

No tickets on my side.

---

## Backend side: replace `backend/services/tokenizer.py`

The single English lock-in in the whole project is here:

```python
# backend/services/tokenizer.py
nlp = spacy.load("en_core_web_sm")
```

On non-English input it falls back to `text.split(". ")`, which fails on:

- CJK punctuation: `。！？` (Chinese, Japanese)
- Languages without ASCII-style sentence terminators (e.g. Devanagari `।`, Arabic `؟`)
- Any text using fullwidth Unicode periods or no spacing between sentences

**Suggested replacement:** drop spaCy entirely and use a script-agnostic
regex. The contract `tokenize_text(text: str) -> list[str]` stays
unchanged so callers don't notice.

```python
import re

_TERMINATORS = r".!?。！？।؟‼⁇⁈⁉"
_SENTENCE_END = re.compile(
    rf"(?<=[{_TERMINATORS}])\s+|"
    rf"(?<=[{_TERMINATORS}])(?=[^\s{_TERMINATORS}])|"
    r"\n{2,}"
)

def tokenize_text(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    return [s.strip() for s in _SENTENCE_END.split(text) if s and s.strip()]
```

Also: drop `spacy==3.8.2` from `backend/requirements.txt` and the
`python -m spacy download en_core_web_sm` step from `README.md`.

**Recommended test cases (mirror in `tests/test_tokenizer.py`):**

1. English: `"Hello world. How are you?"` → 2 sentences
2. Spanish: `"Hola mundo. ¿Cómo estás?"` → 2 sentences
3. Chinese: `"你好世界。你好吗？"` → 2 sentences
4. Japanese: `"こんにちは。元気ですか？"` → 2 sentences
5. Mixed scripts in one input → 3 sentences
6. Empty / whitespace-only → `[]`
7. Unterminated single line → 1 sentence
8. `"Para one\n\nPara two"` (paragraph break only) → 2 sentences

---

## Out of scope (logged here so it isn't lost)

These are real but not blockers, and not anyone's job *right now*:

1. **Threshold recalibration for cross-lingual.** Cross-lingual cosine
   compresses (~0.80–0.88 for a faithful translation vs 0.93+ for
   same-language identical), so `STABLE_THRESHOLD=0.93` will tag most
   cross-lingual pairs as "modified". Owner: ML Lead, after we have
   real translation pairs to tune against. Re-run the §7 sprint in
   `ML_ARCHITECTURE.md`. Edits are config-only in `ml/thresholds.py`.

2. **`pct_text_edited` cross-script interpretation.** Character-level
   Levenshtein on `"Hola"` vs `"Hello"` looks like a big edit even when
   meaning is identical. The number is still computed correctly — the
   *interpretation* weakens. Owner: Frontend Lead may choose to hide or
   re-label this metric on cross-lingual diffs.

3. **Concept-prompt language tuning.** The English system prompt in
   `ml/concepts.py` works on multilingual input today. Could be tuned
   later for translation-fidelity framing ("did obligations / rights
   survive the translation"). Owner: ML Lead, optional polish.

4. **Frontend i18n.** Translating UI strings is independent. Owner:
   Frontend Lead, separate ticket.

5. **Winston's `align()` / tokenization upstream.** Once real
   `semantic_hungarian` lands (`USE_REAL_ALIGN=1`), confirm whether it
   does its own English-locked tokenization internally. If yes, it
   needs the same regex fix. Owner: whoever wires Winston in. Tracked
   in `notes/integration-with-winston.md`.

---

## Acceptance check

The whole feature is verified by running `python -m ml.demo` (or hitting
`/api/diff`) with a Spanish or Chinese input pair and getting back a
non-trivial `DiffResponse` whose clause counts match the source
sentence count. No code in `ml/` should need to change to make that
happen — only the tokenizer swap.
