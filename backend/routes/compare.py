from fastapi import APIRouter, BackgroundTasks
from models.schemas import CompareRequest, CompareResponse, SentencePairOut, DocumentSummary
from services.tokenizer import tokenize_text
from services.ml_client import compare_sentences_ml
from services.aggregator import aggregate_clause_scores_to_sentences
import uuid

router = APIRouter()

# In-memory storage for async explanation results
explanation_store: dict[str, dict] = {}


@router.post("", response_model=CompareResponse)
async def compare_documents(request: CompareRequest, background_tasks: BackgroundTasks):
    """
    Compare two document versions and return semantic diff.

    Steps:
    1. Tokenize both texts into sentences
    2. Call ML layer for alignment and scoring
    3. Generate comparison_id
    4. Return immediate response with null explanations
    5. Kick off background task for LLM explanations
    """
    # Generate unique comparison ID
    comparison_id = str(uuid.uuid4())

    # Step 1: Tokenize into clauses and sentences
    v1_result = tokenize_text(request.v1_text)
    v2_result = tokenize_text(request.v2_text)

    # Step 2: Call ML layer with clauses (not sentences)
    ml_result = compare_sentences_ml(v1_result.clauses, v2_result.clauses)

    # Step 3: Aggregate clause-level scores back to sentence level
    sentence_pairs = aggregate_clause_scores_to_sentences(
        clause_pairs=ml_result.pairs,
        v1_clause_to_sentence=v1_result.clause_to_sentence,
        v2_clause_to_sentence=v2_result.clause_to_sentence,
        v1_sentences=v1_result.sentences,
        v2_sentences=v2_result.sentences,
    )

    # Step 4: Convert to response format (set explanations to None)
    pairs_out = [
        SentencePairOut(
            pair_id=pair["pair_id"],
            v1_sentence=pair["v1_sentence"],
            v2_sentence=pair["v2_sentence"],
            v1_index=pair["v1_index"],
            v2_index=pair["v2_index"],
            similarity_score=pair["similarity_score"],
            status=pair["status"],
            severity=pair["severity"],
            explanation=None  # Will be populated asynchronously
        )
        for pair in sentence_pairs
    ]

    # Step 5: Initialize explanation store
    explanation_store[comparison_id] = {
        "status": "pending",
        "explanations": {pair["pair_id"]: None for pair in sentence_pairs}
    }

    # Step 6: Calculate summary from sentence-level pairs
    total_pairs = len(sentence_pairs)
    green_count = sum(1 for p in sentence_pairs if p["severity"] == "green")
    yellow_count = sum(1 for p in sentence_pairs if p["severity"] == "yellow")
    red_count = sum(1 for p in sentence_pairs if p["severity"] == "red")
    added_count = sum(1 for p in sentence_pairs if p["status"] == "added")
    deleted_count = sum(1 for p in sentence_pairs if p["status"] == "deleted")

    summary = DocumentSummary(
        total_pairs=total_pairs,
        green_count=green_count,
        yellow_count=yellow_count,
        red_count=red_count,
        added_count=added_count,
        deleted_count=deleted_count,
    )

    # Step 7: Kick off background task for LLM explanations
    # TODO: Implement async explanation generation
    # background_tasks.add_task(generate_explanations_async, comparison_id, sentence_pairs)

    return CompareResponse(
        comparison_id=comparison_id,
        pairs=pairs_out,
        summary=summary
    )


@router.get("/test")
async def test_compare():
    """Test endpoint to verify compare route is working."""
    return {
        "status": "ok",
        "message": "Compare endpoint is accessible",
        "endpoints": {
            "POST /compare": "Main comparison endpoint",
            "GET /compare/test": "This test endpoint"
        }
    }
