import os
import sys
from pathlib import Path

# Make the project root importable so sibling packages (e.g. `ml`) resolve
# regardless of cwd. The existing `from routes import ...` style continues
# to work because `backend/` is the runtime cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import compare, explanation, diff

# Load environment variables
load_dotenv()

# Warn loudly at boot if API keys required by /api/diff are missing.
# Doesn't block startup — legacy /compare may still work, and we want the
# server to come up so health checks pass.
_missing_keys = [k for k in ("OPENAI_API_KEY",) if not os.getenv(k)]
if _missing_keys:
    print(
        f"WARN: missing env var(s) {_missing_keys}. "
        "POST /api/diff will fail at request time until they are set.",
        file=sys.stderr,
    )

# Create FastAPI app
app = FastAPI(
    title="Semantic Diff API",
    description="Git diff for prose - semantic comparison of document versions",
    version="0.1.0"
)

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(compare.router, prefix="/compare", tags=["compare"])
app.include_router(explanation.router, prefix="/explanation", tags=["explanation"])
app.include_router(diff.router, prefix="/api/diff", tags=["diff"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Semantic Diff API is running",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "services": {
            "api": "ok",
            "spacy": "not_checked",  # TODO: add spaCy check
            "openai": "not_checked",  # TODO: add OpenAI check
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
