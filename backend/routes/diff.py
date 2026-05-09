"""FastAPI router for the /api/diff endpoint.

Wires the ML pipeline (ml.pipeline.run_diff) into the REST API.
"""

from fastapi import APIRouter, HTTPException

from backend.models.schemas import DiffRequest, DiffResponse
from ml.pipeline import run_diff

router = APIRouter()


@router.post("", response_model=DiffResponse)
async def diff_documents(request: DiffRequest) -> DiffResponse:
    """Compare two document versions and return semantic diff."""
    try:
        return await run_diff(request.before, request.after)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"diff pipeline failed: {e}") from e


@router.get("/health")
async def health():
    """Health check for the diff endpoint."""
    return {"status": "ok", "endpoint": "/api/diff"}
