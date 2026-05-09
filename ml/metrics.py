"""Step 4 — Metrics.

Owner: Agent 4 (pipeline + metrics).

Aggregates classified clauses into the ``DiffSummary``: counts, length-weighted
``overall_drift``, character-level Levenshtein ``pct_text_edited``, and
``pct_meaning_edited`` (alias of overall_drift).
"""

import re

from Levenshtein import distance as levenshtein_distance

from backend.models.schemas import ClauseRendering, DiffSummary, PairRendering

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to a single space and strip the ends.

    Used before Levenshtein so a pure-reformatting edit (line breaks added,
    indentation changed, multiple spaces collapsed) does not inflate the
    `pct_text_edited` headline metric.
    """
    return _WHITESPACE_RE.sub(" ", text).strip()


def aggregate_metrics(
    before_clauses: list[ClauseRendering],
    after_clauses: list[ClauseRendering],
    pair_renderings: list[PairRendering],
    original_before: str,
    original_after: str,
    elapsed_ms: int,
) -> DiffSummary:
    """Compute document-level metrics.

    - before_count, after_count: total clauses on each side.
    - Classification counts: unchanged, modified, added, removed.
    - overall_drift: mean drift across paired clauses, weighted by clause length.
    - pct_text_edited: character-level Levenshtein distance as % of max length.
    - pct_meaning_edited: alias of overall_drift.
    - Clamped to [0, 100].
    """
    # Count clauses by classification.
    unchanged_count = sum(1 for c in before_clauses if c.classification == "unchanged")
    modified_count = sum(1 for c in before_clauses if c.classification == "modified")
    added_count = sum(1 for c in after_clauses if c.classification == "added")
    removed_count = sum(1 for c in before_clauses if c.classification == "removed")

    before_count = len(before_clauses)
    after_count = len(after_clauses)

    # Compute overall_drift: mean drift across paired clauses, weighted by length.
    # For paired clauses (those that weren't split), use the pair's drift score.
    # For added/removed (drift_score=100), they don't contribute to paired drift.
    paired_drift_sum = 0.0
    paired_length_sum = 0.0

    for pair in pair_renderings:
        # Find the before and after clause for this pair to get their text lengths.
        before_clause = next((c for c in before_clauses if c.id == pair.before_id), None)
        after_clause = next((c for c in after_clauses if c.id == pair.after_id), None)

        if before_clause and after_clause:
            # Weight by combined character length of both sides.
            combined_len = len(before_clause.text) + len(after_clause.text)
            paired_drift_sum += pair.drift_score * combined_len
            paired_length_sum += combined_len

    if paired_length_sum > 0:
        overall_drift = paired_drift_sum / paired_length_sum
    else:
        # No paired clauses. If everything is added/removed, default to 100.
        # Otherwise default to mean of all drifts.
        all_drifts = [c.drift_score for c in before_clauses + after_clauses]
        if all_drifts:
            overall_drift = sum(all_drifts) / len(all_drifts)
        else:
            overall_drift = 100.0

    overall_drift = max(0.0, min(100.0, overall_drift))

    # Compute pct_text_edited: character-level Levenshtein on
    # whitespace-normalised text. Reformatting (extra newlines, indentation
    # changes) should not register as edits.
    norm_before = _normalize_whitespace(original_before)
    norm_after = _normalize_whitespace(original_after)
    lev_distance = levenshtein_distance(norm_before, norm_after)
    max_len = max(len(norm_before), len(norm_after))
    if max_len > 0:
        pct_text_edited = (lev_distance / max_len) * 100.0
    else:
        pct_text_edited = 0.0

    pct_text_edited = max(0.0, min(100.0, pct_text_edited))

    # pct_meaning_edited is an alias of overall_drift.
    pct_meaning_edited = overall_drift

    return DiffSummary(
        before_count=before_count,
        after_count=after_count,
        unchanged=unchanged_count,
        modified=modified_count,
        added=added_count,
        removed=removed_count,
        overall_drift=overall_drift,
        pct_text_edited=pct_text_edited,
        pct_meaning_edited=pct_meaning_edited,
        embedding_model="text-embedding-3-small",
        chat_model="gpt-4o-mini",
        alignment="hungarian",
        elapsed_ms=elapsed_ms,
    )
