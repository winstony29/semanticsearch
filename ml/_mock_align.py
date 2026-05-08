"""
Mock alignment for ML-slice development.

Mirrors the signature of the backend lead's ``align(before, after)`` so the
pipeline can be built and tested before the real Hungarian-with-merging is
ready. Swap the import in ``backend/services/align.py`` when ``align()``
ships — should be a one-line change.

Returns hand-crafted clauses covering every classification case the ML
slice needs to handle:

  - near-identical pair             ⇒ "unchanged"
  - identical pair (verbatim)       ⇒ "unchanged" (sanity check on remap)
  - heavy paraphrase                ⇒ "modified" (mid drift)
  - bogus Hungarian-forced pair     ⇒ post-Hungarian split into
                                       "removed" + "added"
  - one unmatched_before clause     ⇒ "removed"
  - one unmatched_after clause      ⇒ "added"

The texts are intentionally domain-flavoured (a contract excerpt) so concept
extraction has something meaningful to extract during end-to-end testing.
"""

from backend.models.schemas import AlignedPair, AlignmentResult, ClauseUnit


_ORIGINAL_BEFORE = (
    "The Service Provider shall deliver the goods within thirty (30) days. "
    "Either party may terminate this agreement upon thirty days written notice. "
    "All disputes will be resolved through binding arbitration in Singapore. "
    "Confidential information must not be disclosed to third parties. "
    "The Buyer agrees to pay all invoices within fifteen (15) business days."
)

_ORIGINAL_AFTER = (
    "The Service Provider must deliver the goods within thirty (30) days. "
    "Either party is entitled to terminate this agreement at any time, with "
    "or without cause, by providing written notice. "
    "All disputes will be resolved through binding arbitration in Singapore. "
    "The total liability of either party shall not exceed the fees paid in "
    "the preceding twelve months. "
    "Late payments shall accrue interest at 1.5% per month."
)


def mock_align(before_text: str, after_text: str) -> AlignmentResult:
    """Return a hand-crafted ``AlignmentResult`` covering all classification cases.

    The arguments are accepted to match the real ``align()`` signature but are
    not actually used — the output is fixed.
    """

    pairs = [
        # 1. Near-identical: only "shall" → "must". Should be unchanged.
        AlignedPair(
            before=ClauseUnit(
                id="b0",
                text="The Service Provider shall deliver the goods within thirty (30) days.",
            ),
            after=ClauseUnit(
                id="a0",
                text="The Service Provider must deliver the goods within thirty (30) days.",
            ),
        ),
        # 2. Heavy paraphrase: termination clause. "thirty days notice" → "any
        #    time, with or without cause". Same surface concept, materially
        #    different obligation. Should classify as modified, mid-to-high drift.
        AlignedPair(
            before=ClauseUnit(
                id="b1",
                text="Either party may terminate this agreement upon thirty days written notice.",
            ),
            after=ClauseUnit(
                id="a1",
                text=(
                    "Either party is entitled to terminate this agreement at any time, "
                    "with or without cause, by providing written notice."
                ),
            ),
        ),
        # 3. Identical sentence (verbatim arbitration clause). Sanity check
        #    that exact text round-trips as unchanged.
        AlignedPair(
            before=ClauseUnit(
                id="b2",
                text="All disputes will be resolved through binding arbitration in Singapore.",
            ),
            after=ClauseUnit(
                id="a2",
                text="All disputes will be resolved through binding arbitration in Singapore.",
            ),
        ),
        # 4. Bogus Hungarian-forced pair. Confidentiality (before) was matched
        #    to a brand-new liability-cap clause (after) because nothing else
        #    was available. Similarity should fall below REMOVED_THRESHOLD;
        #    the post-Hungarian check in classification.py must split this
        #    into "removed" (b3) + "added" (a3) instead of calling it modified.
        AlignedPair(
            before=ClauseUnit(
                id="b3",
                text="Confidential information must not be disclosed to third parties.",
            ),
            after=ClauseUnit(
                id="a3",
                text=(
                    "The total liability of either party shall not exceed the fees "
                    "paid in the preceding twelve months."
                ),
            ),
        ),
    ]

    # 5. Unmatched on the before side — payment-term clause was deleted in v2.
    unmatched_before = [
        ClauseUnit(
            id="b4",
            text="The Buyer agrees to pay all invoices within fifteen (15) business days.",
        ),
    ]

    # 6. Unmatched on the after side — late-payment clause is brand new in v2.
    unmatched_after = [
        ClauseUnit(
            id="a4",
            text="Late payments shall accrue interest at 1.5% per month.",
        ),
    ]

    return AlignmentResult(
        pairs=pairs,
        unmatched_before=unmatched_before,
        unmatched_after=unmatched_after,
        original_before=before_text or _ORIGINAL_BEFORE,
        original_after=after_text or _ORIGINAL_AFTER,
    )


# Sample texts re-exported so other modules and tests can import them without
# duplicating the strings.
SAMPLE_BEFORE: str = _ORIGINAL_BEFORE
SAMPLE_AFTER: str = _ORIGINAL_AFTER
