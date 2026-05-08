from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from routes import compare, explanation

# Load environment variables
load_dotenv()

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
