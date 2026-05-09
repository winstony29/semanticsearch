"""
Test all alignment methods with real OpenAI embeddings.
Compares semantic_hungarian, greedy_with_merges, and smith_waterman.
"""

import sys
import os
import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

sys.path.insert(0, 'ml')

from ml.alignment_methods import semantic_hungarian, greedy_with_merges
from ml.smith_waterman_alignment import SmithWatermanAligner


def get_embeddings(sentences):
    """Get OpenAI embeddings. Fails loudly if API key not set."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set!")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=sentences
    )

    embeddings = np.array([d.embedding for d in response.data])
    return embeddings


def smith_waterman(v1_sentences, v2_sentences, embeddings, threshold=0.5):
    """Wrapper for Smith-Waterman to match other method interfaces."""
    emb_v1 = embeddings[:len(v1_sentences)]
    emb_v2 = embeddings[len(v1_sentences):]
    sim_matrix = cosine_similarity(emb_v1, emb_v2)

    aligner = SmithWatermanAligner(gap_penalty=-0.3, min_similarity=threshold)
    result = aligner.align(v1_sentences, v2_sentences, sim_matrix)

    return {
        "method": "smith_waterman",
        "pairs": result["pairs"],
        "similarity_matrix": sim_matrix
    }


def analyze_result(result):
    """Extract statistics from result."""
    pairs = result["pairs"]

    matched = [p for p in pairs if p["status"] in ["matched", "merged", "split"]]
    deletions = len([p for p in pairs if p["status"] == "deleted"])
    additions = len([p for p in pairs if p["status"] == "added"])

    avg_sim = (
        sum(p["similarity_score"] for p in matched) / len(matched)
        if matched else 0.0
    )

    return {
        "pairs_found": len(matched),
        "deletions": deletions,
        "additions": additions,
        "avg_similarity": avg_sim,
        "all_pairs": matched
    }


def print_scenario_results(scenario_name, v1, v2, methods_results):
    """Print results for one scenario in table format."""
    print(f"\n### {scenario_name}")
    print()

    # Header
    print(f"{'Method':<25} | {'Pairs':<6} | {'Del':<4} | {'Add':<4} | {'Avg Sim':<8}")
    print("-" * 60)

    # Results for each method
    for method_name, result in methods_results.items():
        stats = analyze_result(result)
        print(f"{method_name:<25} | {stats['pairs_found']:<6} | "
              f"{stats['deletions']:<4} | {stats['additions']:<4} | "
              f"{stats['avg_similarity']:.2f}")

    print()

    # Print pairs for each method
    for method_name, result in methods_results.items():
        stats = analyze_result(result)
        print(f"{method_name}:")
        for pair in stats['all_pairs']:
            v1_idx = pair['v1_index']
            v2_idx = pair['v2_index']
            score = pair['similarity_score']
            print(f"  v1[{v1_idx}] \u2194 v2[{v2_idx}] score={score:.2f}")
        if not stats['all_pairs']:
            print("  (no pairs)")
        print()


def run_all_scenarios():
    """Run all 4 scenarios through all 3 methods."""

    scenarios = [
        {
            "name": "Scenario 1 - Merge (2\u21921)",
            "v1": [
                "The weather was sunny.",
                "We decided to go to the beach.",
                "Everyone had a great time."
            ],
            "v2": [
                "The sunny weather prompted us to go to the beach.",
                "Everyone had a great time."
            ]
        },
        {
            "name": "Scenario 2 - Reorder",
            "v1": [
                "First we ate lunch.",
                "Then we went swimming.",
                "Finally we drove home."
            ],
            "v2": [
                "We went swimming.",
                "We drove home.",
                "First we ate lunch."
            ]
        },
        {
            "name": "Scenario 3 - Semantic drift",
            "v1": [
                "We should consider expanding to Japan.",
                "Our revenue grew 10% last quarter."
            ],
            "v2": [
                "We plan to expand to Japan.",
                "Revenue increased by 10% in Q3."
            ]
        },
        {
            "name": "Scenario 4 - Completely unrelated",
            "v1": [
                "The API documentation covers authentication flows."
            ],
            "v2": [
                "Preheat the oven to 350 degrees.",
                "Mix flour and sugar in a bowl."
            ]
        }
    ]

    for scenario in scenarios:
        v1 = scenario["v1"]
        v2 = scenario["v2"]

        # Get embeddings
        all_sentences = v1 + v2
        embeddings = get_embeddings(all_sentences)

        # Run all methods
        results = {}
        results["semantic_hungarian"] = semantic_hungarian(v1, v2, embeddings, threshold=0.6)
        results["greedy_with_merges"] = greedy_with_merges(v1, v2, embeddings, match_threshold=0.6)
        results["smith_waterman"] = smith_waterman(v1, v2, embeddings, threshold=0.5)

        # Print results
        print_scenario_results(scenario["name"], v1, v2, results)


if __name__ == "__main__":
    print("Testing alignment methods with real OpenAI embeddings")
    print("=" * 60)
    run_all_scenarios()
    print("\nDone.")
