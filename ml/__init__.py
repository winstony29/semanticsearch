"""ML layer for semantic comparison and alignment."""

from .semantic_engine import compare_sentences
from .llm_explainer import generate_explanations

__all__ = ["compare_sentences", "generate_explanations"]
