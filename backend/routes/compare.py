from fastapi import APIRouter, BackgroundTasks
from models.schemas import CompareRequest, CompareResponse, SentencePairOut, DocumentSummary
from services.tokenizer import tokenize_text
from services.ml_client import compare_sentences_ml
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

    # Step 1: Tokenize
    v1_sentences = tokenize_text(request.v1_text)
    v2_sentences = tokenize_text(request.v2_text)

    # Step 2: Call ML layer
    ml_result = compare_sentences_ml(v1_sentences, v2_sentences)

    # Step 3: Convert to response format (set explanations to None)
    pairs_out = [
        SentencePairOut(
            pair_id=pair.pair_id,
            v1_sentence=pair.v1_sentence,
            v2_sentence=pair.v2_sentence,
            v1_index=pair.v1_index,
            v2_index=pair.v2_index,
            similarity_score=pair.similarity_score,
            status=pair.status,
            severity=pair.severity,
            explanation=None  # Will be populated asynchronously
        )
        for pair in ml_result.pairs
    ]

    # Step 4: Initialize explanation store
    explanation_store[comparison_id] = {
        "status": "pending",
        "explanations": {pair.pair_id: None for pair in ml_result.pairs}
    }

    # Step 5: Kick off background task for LLM explanations
    # TODO: Implement async explanation generation
    # background_tasks.add_task(generate_explanations_async, comparison_id, ml_result.pairs)

    return CompareResponse(
        comparison_id=comparison_id,
        pairs=pairs_out,
        summary=ml_result.summary
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
