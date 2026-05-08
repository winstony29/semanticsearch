"""
Backend lead's clause alignment — placeholder stub.

This file is the integration seam between the backend lead's Hungarian-with-
merging algorithm and the ML slice. The real implementation will replace the
body of ``align()``; the signature is locked per ML_ARCHITECTURE.md §1.

Until then, this module delegates to ``ml._mock_align.mock_align`` so the
end-to-end pipeline (POST /api/diff) is wireable on the ML branch.

When the real align() ships, swap the import below — the call site in
``ml/pipeline.py`` does not change.
"""

from backend.models.schemas import AlignmentResult
from ml._mock_align import mock_align


async def align(before: str, after: str) -> AlignmentResult:
    """Align two documents into clause pairs + unmatched-side lists.

    Args:
        before: Original document text.
        after: Revised document text.

    Returns:
        ``AlignmentResult`` containing matched ``AlignedPair``s plus any
        ``ClauseUnit``s that could not be paired (one list per side).

    Note:
        The returned object is currently produced by the mock. The mock's
        output is *fixed* — it ignores the input strings and returns
        hand-crafted clauses suitable for development and threshold tuning.
    """
    return await mock_align(before, after)
