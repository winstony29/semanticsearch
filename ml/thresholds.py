"""
Single source of truth for all tunable constants in the ML slice.

The threshold-tuning sprint (ML_ARCHITECTURE.md §7) edits **this file only**.
"""

# ---- Classification thresholds (cosine similarity) -------------------------

# ≥ this similarity ⇒ "unchanged"
STABLE_THRESHOLD: float = 0.93

# in [MODIFIED_THRESHOLD, STABLE_THRESHOLD) ⇒ "modified"
MODIFIED_THRESHOLD: float = 0.65

# below this similarity, the Hungarian pairing is treated as bogus and the
# pair is split: before becomes "removed", after becomes "added".
REMOVED_THRESHOLD: float = 0.65


# ---- Drift remap -----------------------------------------------------------

# Cosine similarities are clamped into this range before being remapped to
# a 0–100 drift score. The 0.5 floor is empirical: text-embedding-3-small
# rarely produces similarities below ~0.4 even for unrelated text, and
# anchoring at 0.5 stops every diff from looking 30–50% drifted by default.
DRIFT_FLOOR: float = 0.5
DRIFT_CEIL: float = 1.0


# ---- API / model identifiers ----------------------------------------------

EMBEDDING_MODEL: str = "text-embedding-3-small"
CHAT_MODEL: str = "gpt-4o-mini"
ALIGNMENT_NAME: str = "hungarian"


# ---- Defensive guards ------------------------------------------------------

# Concept extraction input cap (per side). gpt-4o-mini has a 128K context
# window; this is a defensive ceiling well below that to keep latency and
# cost predictable.
MAX_CONCEPT_INPUT_CHARS: int = 60_000


# ---- Sentinels -------------------------------------------------------------

# Drift score assigned to clauses that have no partner — added, removed, or
# split-off from a low-similarity Hungarian pair. Treated as "fully drifted"
# because there is nothing to compare against.
FULL_DRIFT: float = 100.0
