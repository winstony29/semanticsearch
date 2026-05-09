"""
FIX #3: Add async explanations to backend/routes/compare.py

COPY-PASTE READY - Add this function at the top, after the imports
"""

# Add this import at top of file
import sys
from pathlib import Path

# Add this function after the router definition (line 7)
async def generate_explanations_async(comparison_id: str, pairs: list):
    """
    Generate LLM explanations for yellow and red pairs.

    Runs in background, updates explanation_store when complete.
    """
    # Add ml directory to path
    ml_path = Path(__file__).parent.parent.parent / 'ml'
    sys.path.insert(0, str(ml_path))

    from llm_explainer import generate_explanations

    # Convert Pydantic models to dicts for ML layer
    pairs_dict = [
        {
            "pair_id": p.pair_id,
            "v1_sentence": p.v1_sentence,
            "v2_sentence": p.v2_sentence,
            "similarity_score": p.similarity_score,
            "severity": p.severity
        }
        for p in pairs
        if p.severity in ["yellow", "red"]  # Only explain problematic pairs
    ]

    if not pairs_dict:
        # No yellow/red pairs, mark as complete
        explanation_store[comparison_id]["status"] = "complete"
        return

    try:
        # Generate explanations (async LLM calls)
        explanations = await generate_explanations(pairs_dict)

        # Update explanation store
        explanation_store[comparison_id]["explanations"].update(explanations)
        explanation_store[comparison_id]["status"] = "complete"

    except Exception as e:
        print(f"Error generating explanations: {e}")
        explanation_store[comparison_id]["status"] = "error"


# Then in the compare_documents function, UNCOMMENT line 59:
# Change from:
#     # TODO: Implement async explanation generation
#     # background_tasks.add_task(generate_explanations_async, comparison_id, ml_result.pairs)

# To:
#     background_tasks.add_task(generate_explanations_async, comparison_id, ml_result.pairs)
