from fastapi import APIRouter, HTTPException
from models.schemas import ExplanationResponse

router = APIRouter()

# Import the explanation store from compare route
from routes.compare import explanation_store


@router.get("/{comparison_id}", response_model=ExplanationResponse)
async def get_explanations(comparison_id: str):
    """
    Poll for async LLM explanation results.

    Returns:
    - status: "pending" | "partial" | "complete"
    - explanations: dict of pair_id → explanation string (or null if not ready)
    """
    if comparison_id not in explanation_store:
        raise HTTPException(status_code=404, detail="Comparison ID not found")

    data = explanation_store[comparison_id]

    return ExplanationResponse(
        comparison_id=comparison_id,
        status=data["status"],
        explanations=data["explanations"]
    )


@router.get("/test/alive")
async def test_explanation():
    """Test endpoint to verify explanation route is working."""
    return {
        "status": "ok",
        "message": "Explanation endpoint is accessible",
        "endpoints": {
            "GET /explanation/{comparison_id}": "Poll for explanation results",
            "GET /explanation/test/alive": "This test endpoint"
        }
    }
