"""Step 6 — Pipeline orchestration.

Owner: Agent 4 (pipeline + metrics).

Top-level entry point: ``run_diff(before: str, after: str) -> DiffResponse``.
Calls the backend lead's ``align()`` (or the mock), then runs embeddings/
scoring/classification and concept extraction concurrently via
``asyncio.gather``, finally assembling the ``DiffResponse``.
"""

import asyncio
import time

from backend.models.schemas import (
    AlignedPair,
    ClauseRendering,
    Concept,
    ConceptDiff,
    DiffResponse,
    PairRendering,
)
from backend.services.align import align
from ml.classification import (
    ClassifiedClause,
    ClassifiedPair,
    classify_pairs,
    classify_unmatched,
)
from ml.concepts import extract_concepts
from ml.embeddings import embed_clauses
from ml.metrics import aggregate_metrics
from ml.scoring import score_alignment


async def run_diff(before: str, after: str) -> DiffResponse:
    """Orchestrate the full ML pipeline end-to-end.

    1. Align the documents (synchronous, backend lead's algorithm or mock).
    2. Concurrently:
       a. Embed, score, and classify the pairs.
       b. Extract high-level concepts from the raw text.
    3. Aggregate metrics and assemble the DiffResponse.
    """
    start = time.perf_counter()

    # Step 1: Align documents.
    alignment = align(before, after)

    # Step 2: Run embeddings + concept extraction concurrently.
    embed_task = asyncio.create_task(embed_clauses(alignment))
    concept_task = asyncio.create_task(extract_concepts(before, after))

    # Wait for embeddings to complete.
    embeddings = await embed_task

    # Score and classify the alignment.
    scored = score_alignment(alignment.pairs, embeddings)
    kept_pairs, split_clauses = classify_pairs(scored)
    unmatched_classified = classify_unmatched(
        alignment.unmatched_before, alignment.unmatched_after
    )

    # Wait for concept extraction to complete.
    # extract_concepts returns a tuple (ConceptDiff, status).
    concepts_data: ConceptDiff
    concept_status: str = "ok"
    try:
        concepts_data, concept_status = await concept_task
    except Exception:
        # Graceful failure: return empty concepts but don't break the response.
        concepts_data = ConceptDiff(summary="", concepts=[])
        concept_status = "failed"

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # Build the three rendering views.
    before_clauses = _build_before_clauses(
        kept_pairs, split_clauses, unmatched_classified
    )
    after_clauses = _build_after_clauses(
        kept_pairs, split_clauses, unmatched_classified
    )
    pair_renderings = _build_pair_renderings(kept_pairs)

    # Aggregate metrics.
    summary = aggregate_metrics(
        before_clauses,
        after_clauses,
        pair_renderings,
        alignment.original_before,
        alignment.original_after,
        elapsed_ms,
    )

    # Assemble response.
    return DiffResponse(
        before_clauses=before_clauses,
        after_clauses=after_clauses,
        pairs=pair_renderings,
        summary=summary,
        concepts=concepts_data.concepts,
        concept_extraction=concept_status,
    )


def _build_before_clauses(
    kept_pairs: list[ClassifiedPair],
    split_clauses: list[ClassifiedClause],
    unmatched_classified: list[ClassifiedClause],
) -> list[ClauseRendering]:
    """Build the before-side clause renderings."""
    before_clauses: list[ClauseRendering] = []

    # From kept pairs: unchanged or modified, each paired with its partner.
    for cp in kept_pairs:
        before_clauses.append(
            ClauseRendering(
                id=cp.pair.before.id,
                text=cp.pair.before.text,
                classification=cp.classification,
                drift_score=cp.drift_score,
                paired_with=cp.pair.after.id,
            )
        )

    # From split clauses: before side becomes "removed".
    for cc in split_clauses:
        if cc.clause.id.startswith("b"):
            before_clauses.append(
                ClauseRendering(
                    id=cc.clause.id,
                    text=cc.clause.text,
                    classification="removed",
                    drift_score=100.0,
                    paired_with=None,
                )
            )

    # From unmatched: only the "removed" ones (unmatched_before).
    for cc in unmatched_classified:
        if cc.classification == "removed":
            before_clauses.append(
                ClauseRendering(
                    id=cc.clause.id,
                    text=cc.clause.text,
                    classification="removed",
                    drift_score=100.0,
                    paired_with=None,
                )
            )

    return before_clauses


def _build_after_clauses(
    kept_pairs: list[ClassifiedPair],
    split_clauses: list[ClassifiedClause],
    unmatched_classified: list[ClassifiedClause],
) -> list[ClauseRendering]:
    """Build the after-side clause renderings."""
    after_clauses: list[ClauseRendering] = []

    # From kept pairs: unchanged or modified, each paired with its partner.
    for cp in kept_pairs:
        after_clauses.append(
            ClauseRendering(
                id=cp.pair.after.id,
                text=cp.pair.after.text,
                classification=cp.classification,
                drift_score=cp.drift_score,
                paired_with=cp.pair.before.id,
            )
        )

    # From split clauses: after side becomes "added".
    for cc in split_clauses:
        if cc.clause.id.startswith("a"):
            after_clauses.append(
                ClauseRendering(
                    id=cc.clause.id,
                    text=cc.clause.text,
                    classification="added",
                    drift_score=100.0,
                    paired_with=None,
                )
            )

    # From unmatched: only the "added" ones (unmatched_after).
    for cc in unmatched_classified:
        if cc.classification == "added":
            after_clauses.append(
                ClauseRendering(
                    id=cc.clause.id,
                    text=cc.clause.text,
                    classification="added",
                    drift_score=100.0,
                    paired_with=None,
                )
            )

    return after_clauses


def _build_pair_renderings(kept_pairs: list[ClassifiedPair]) -> list[PairRendering]:
    """Build pair renderings for only the kept pairs."""
    pair_renderings: list[PairRendering] = []
    for cp in kept_pairs:
        pair_renderings.append(
            PairRendering(
                before_id=cp.pair.before.id,
                after_id=cp.pair.after.id,
                similarity=cp.similarity,
                drift_score=cp.drift_score,
                classification=cp.classification,
            )
        )
    return pair_renderings
