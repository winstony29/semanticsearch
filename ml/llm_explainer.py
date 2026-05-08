"""
LLM-powered explanation generator for semantic changes.

Generates natural language explanations for sentence pairs with moderate to high drift.
"""

import os
import asyncio
from typing import Optional
from anthropic import AsyncAnthropic


# Initialize Anthropic client
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

EXPLANATION_MODEL = "claude-sonnet-4-20250514"


async def generate_explanation(
    v1_sentence: str,
    v2_sentence: str,
    similarity_score: float
) -> str:
    """
    Generate a one-sentence explanation of how meaning changed.

    Args:
        v1_sentence: Original sentence
        v2_sentence: Revised sentence
        similarity_score: Semantic similarity (0-1)

    Returns:
        One-sentence explanation of the change
    """
    prompt = f"""Original: {v1_sentence}
Revised: {v2_sentence}
Similarity score: {similarity_score:.2f}

In one sentence, explain how the meaning changed between the original and revised version. Focus on semantic differences, not stylistic changes."""

    try:
        response = await client.messages.create(
            model=EXPLANATION_MODEL,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    except Exception as e:
        return f"Error generating explanation: {str(e)}"


async def generate_explanations(pairs: list[dict]) -> dict[str, str]:
    """
    Generate explanations for all yellow and red pairs in parallel.

    Args:
        pairs: List of sentence pair dicts (from semantic_engine)

    Returns:
        Dict mapping pair_id → explanation string
    """
    # Filter to only yellow and red pairs
    needs_explanation = [
        p for p in pairs
        if p.get("severity") in ["yellow", "red"]
    ]

    if not needs_explanation:
        return {}

    # Generate explanations in parallel
    tasks = [
        generate_explanation(
            p["v1_sentence"],
            p["v2_sentence"],
            p["similarity_score"]
        )
        for p in needs_explanation
    ]

    explanations = await asyncio.gather(*tasks)

    # Build result dict
    return {
        pair["pair_id"]: explanation
        for pair, explanation in zip(needs_explanation, explanations)
    }


# Test function
async def test():
    """Test the explanation generator."""
    v1 = "We should consider expanding to Japan."
    v2 = "We plan to expand to Japan."
    score = 0.72

    explanation = await generate_explanation(v1, v2, score)
    print(f"Explanation: {explanation}")


if __name__ == "__main__":
    asyncio.run(test())
