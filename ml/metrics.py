"""Step 4 — Metrics.

Owner: Agent 4 (pipeline + metrics).

Aggregates classified clauses into the ``DiffSummary``: counts, length-weighted
``overall_drift``, character-level Levenshtein ``pct_text_edited``, and
``pct_meaning_edited`` (alias of overall_drift).
"""
