"""
Backend lead's clause alignment — staged integration seam.

Two paths live here:

1. **Mock path (default).** ``align()`` delegates to ``ml._mock_align`` so
   the end-to-end pipeline runs without a real algorithm. This is what
   ``run_diff()`` exercises today.

2. **Real path (staged).** When the ``USE_REAL_ALIGN`` flag is on,
   ``align()`` runs Winston's ``semantic_hungarian`` (vendored in
   ``backend/services/_align_impl.py``) wrapped in a dict→AlignmentResult
   adapter. Default is **off** because the vendored copy is a snapshot of
   ``origin/main`` work-in-progress and Winston's final algorithm has not
   been pushed yet.

When Winston's finished implementation lands, the only changes needed:

- Replace the body of ``backend/services/_align_impl.py`` with whatever
  he ships (or import from the new location if he relocates the file).
- Flip ``USE_REAL_ALIGN`` to ``True`` (here or via the env var).
- Set ``ALIGNMENT_PRE_PRUNES = True`` in ``ml/thresholds.py`` so the
  post-Hungarian re-classify in ``classify_pairs`` doesn't double-prune.

Signature is locked per ML_ARCHITECTURE.md §1:
``async def align(before: str, after: str) -> AlignmentResult``.
"""

from __future__ import annotations

import os
import re

from backend.models.schemas import AlignedPair, AlignmentResult, ClauseUnit
from ml._mock_align import mock_align


# ---- Feature flag ----------------------------------------------------------

# Off by default. Flip via env var (``USE_REAL_ALIGN=1``) for ad-hoc testing,
# or change the default below once Winston's real algorithm is wired in.
USE_REAL_ALIGN: bool = os.getenv("USE_REAL_ALIGN", "0") == "1"


# ---- Sentence splitter -----------------------------------------------------

# Cheap regex split — sufficient for the staged path. Replace with spaCy
# if Winston's eventual algorithm wants better boundary detection.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


# ---- Adapter (dict from semantic_hungarian → AlignmentResult) --------------

async def _real_align(before: str, after: str) -> AlignmentResult:
    """Run the vendored ``semantic_hungarian`` and translate to our schema.

    This is the entire ~30-line adapter from
    ``notes/integration-with-winston.md``. Kept behind ``USE_REAL_ALIGN``
    so the default ``run_diff()`` path remains the mock until Winston
    pushes finished work.
    """
    # Lazy imports — keep the mock path free of scipy/sklearn at import time.
    from backend.services._align_impl import semantic_hungarian
    from ml.embeddings import embed_texts

    v1 = _split_sentences(before)
    v2 = _split_sentences(after)

    if not v1 and not v2:
        return AlignmentResult(
            pairs=[],
            unmatched_before=[],
            unmatched_after=[],
            original_before=before,
            original_after=after,
        )

    embeddings = await embed_texts(v1 + v2)
    raw = semantic_hungarian(v1, v2, embeddings)

    paired: list[AlignedPair] = []
    before_only: list[ClauseUnit] = []
    after_only: list[ClauseUnit] = []

    for entry in raw["pairs"]:
        status = entry["status"]
        if status == "matched":
            paired.append(AlignedPair(
                before=ClauseUnit(
                    id=f"b{entry['v1_index']}",
                    text=entry["v1_sentence"],
                ),
                after=ClauseUnit(
                    id=f"a{entry['v2_index']}",
                    text=entry["v2_sentence"],
                ),
            ))
        elif status == "deleted":
            before_only.append(ClauseUnit(
                id=f"b{entry['v1_index']}",
                text=entry["v1_sentence"],
            ))
        elif status == "added":
            after_only.append(ClauseUnit(
                id=f"a{entry['v2_index']}",
                text=entry["v2_sentence"],
            ))
        # status == "merged" / "split" — Winston's `semantic_hungarian`
        # never produces these (only `greedy_with_merges` does). Left
        # unhandled deliberately; revisit when the merging schema
        # (resolved 2026-05-09 — list-valued `paired_with`) is exercised.

    return AlignmentResult(
        pairs=paired,
        unmatched_before=before_only,
        unmatched_after=after_only,
        original_before=before,
        original_after=after,
    )


# ---- Public entry point ----------------------------------------------------

async def align(before: str, after: str) -> AlignmentResult:
    """Align two documents into clause pairs + unmatched-side lists.

    Args:
        before: Original document text.
        after: Revised document text.

    Returns:
        ``AlignmentResult`` containing matched ``AlignedPair``s plus any
        ``ClauseUnit``s that could not be paired (one list per side).

    Note:
        Routes to the mock or the staged real path based on
        ``USE_REAL_ALIGN``. The mock's output is *fixed* — it ignores the
        input strings and returns hand-crafted clauses suitable for
        development.
    """
    if USE_REAL_ALIGN:
        return await _real_align(before, after)
    return await mock_align(before, after)
