"""
Quick demo to test alignment methods RIGHT NOW with fake data.

No API keys needed! Uses mock embeddings that simulate semantic similarity.

Usage:
    python demo.py
"""

import numpy as np
from typing import List
import warnings
warnings.filterwarnings('ignore')

# Import our alignment methods
from alignment_methods import (
    lexical_hungarian,
    semantic_hungarian,
    greedy_with_merges,
    adaptive_hungarian
)

# ============================================================================
# SMART MOCK EMBEDDINGS (simulates semantic similarity)
# ============================================================================

def get_smart_mock_embeddings(sentences: List[str]) -> np.ndarray:
    """
    Generate mock embeddings that actually reflect semantic similarity.

    Strategy:
    - Similar sentences get similar embeddings
    - Uses word overlap + simple heuristics
    - Good enough to demonstrate alignment differences
    """
    embeddings = []

    for sent in sentences:
        # Extract features
        words = set(sent.lower().split())

        # Create a 384-dimensional embedding
        # Use word presence as features
        feature_vector = np.zeros(384)

        # Simple hash-based embedding
        for i, word in enumerate(words):
            # Hash each word to multiple dimensions
            hash_val = hash(word)
            for j in range(10):  # Each word affects 10 dimensions
                idx = (hash_val + j) % 384
                feature_vector[idx] += 1.0

        # Normalize
        if np.linalg.norm(feature_vector) > 0:
            feature_vector = feature_vector / np.linalg.norm(feature_vector)

        embeddings.append(feature_vector)

    return np.array(embeddings)


# ============================================================================
# DEMO SCENARIOS
# ============================================================================

DEMO_SCENARIOS = {
    "1. Light Paraphrasing (Easy)": {
        "v1": [
            "The dog ran quickly.",
            "It was very excited.",
            "The park was crowded."
        ],
        "v2": [
            "The dog ran fast.",
            "It was extremely excited.",
            "The park was crowded."
        ],
        "what_to_notice": "All methods should match these correctly. High similarity."
    },

    "2. Heavy Paraphrasing (Lexical Fails)": {
        "v1": [
            "The company's revenue increased by 15% last quarter.",
            "We are planning to expand into Asian markets.",
            "Customer satisfaction has improved significantly."
        ],
        "v2": [
            "Last quarter saw a 15% boost in corporate earnings.",
            "Next year, we'll enter markets across Asia.",
            "Clients are much happier with our service now."
        ],
        "what_to_notice": "Lexical will struggle (different words), semantic should work."
    },

    "3. Sentence Merging (2→1) - Hungarian Limitation": {
        "v1": [
            "The weather was sunny.",
            "We decided to go to the beach.",
            "Everyone had a great time."
        ],
        "v2": [
            "The sunny weather prompted us to go to the beach.",
            "Everyone had a great time."
        ],
        "what_to_notice": "Pure Hungarian can't detect merge. Greedy method might."
    },

    "4. Mixed Changes (Real World)": {
        "v1": [
            "We offer three pricing tiers.",
            "Basic costs $10 per month.",
            "Pro costs $30 per month.",
            "All plans include support."
        ],
        "v2": [
            "Our pricing has three tiers.",
            "Basic is $10/month and Pro is $30/month.",
            "We also offer a free trial."
        ],
        "what_to_notice": "Paraphrase + merge + addition. Tests all capabilities."
    },

    "5. Complete Rewrite (Should Reject Matching)": {
        "v1": [
            "The project is going well.",
            "Revenue is increasing.",
            "No changes needed."
        ],
        "v2": [
            "Everything is broken.",
            "We're losing money.",
            "Major changes required immediately."
        ],
        "what_to_notice": "Methods should recognize low similarity and mark as deletions+additions."
    }
}


# ============================================================================
# DEMO RUNNER
# ============================================================================

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_sentences(label: str, sentences: List[str]):
    """Print numbered sentences."""
    print(f"\n{label}:")
    for i, sent in enumerate(sentences):
        print(f"  [{i}] {sent}")


def print_result(method_name: str, result: dict):
    """Print alignment results in a readable format."""
    print(f"\n--- {method_name.upper()} ---")

    pairs = result["pairs"]

    # Group by status
    matched = [p for p in pairs if p["status"] == "matched"]
    added = [p for p in pairs if p["status"] == "added"]
    deleted = [p for p in pairs if p["status"] == "deleted"]
    merged = [p for p in pairs if p.get("status") == "merged"]

    # Print matches
    if matched:
        print(f"\nMatched pairs ({len(matched)}):")
        for p in matched:
            score = p["similarity_score"]
            color = "🟢" if score >= 0.85 else "🟡" if score >= 0.60 else "🔴"
            print(f"  {color} v1[{p['v1_index']}] ↔ v2[{p['v2_index']}]  (similarity: {score:.2f})")

    # Print merges
    if merged:
        print(f"\nMerged ({len(merged)}):")
        for p in merged:
            print(f"  🔀 v1[{p['v1_index']}] → v2[{p['v2_index']}]  (merged)")

    # Print additions
    if added:
        print(f"\nAdded ({len(added)}):")
        for p in added:
            print(f"  ➕ v2[{p['v2_index']}]: NEW")

    # Print deletions
    if deleted:
        print(f"\nDeleted ({len(deleted)}):")
        for p in deleted:
            print(f"  ➖ v1[{p['v1_index']}]: REMOVED")

    # Summary
    avg_sim = np.mean([p["similarity_score"] for p in matched]) if matched else 0.0
    print(f"\nSummary: {len(matched)} matched, {len(added)} added, {len(deleted)} deleted")
    if matched:
        print(f"Average similarity: {avg_sim:.2f}")


def run_demo_scenario(name: str, scenario: dict):
    """Run one demo scenario with all methods."""
    print_section(name)

    v1_sentences = scenario["v1"]
    v2_sentences = scenario["v2"]

    print_sentences("V1 (Original)", v1_sentences)
    print_sentences("V2 (Revised)", v2_sentences)

    print(f"\n💡 What to notice: {scenario['what_to_notice']}")

    # Get embeddings
    embeddings = get_smart_mock_embeddings(v1_sentences + v2_sentences)

    # Run each method
    print("\n" + "-" * 80)

    # Method 1: Lexical
    try:
        result_lexical = lexical_hungarian(v1_sentences, v2_sentences, threshold=0.3)
        print_result("Lexical (TF-IDF)", result_lexical)
    except Exception as e:
        print(f"\n--- LEXICAL ---\nError: {e}")

    print("\n" + "-" * 80)

    # Method 2: Semantic
    try:
        result_semantic = semantic_hungarian(v1_sentences, v2_sentences, embeddings, threshold=0.6)
        print_result("Semantic (Embeddings)", result_semantic)
    except Exception as e:
        print(f"\n--- SEMANTIC ---\nError: {e}")

    print("\n" + "-" * 80)

    # Method 3: Greedy with merges
    try:
        result_greedy = greedy_with_merges(v1_sentences, v2_sentences, embeddings)
        print_result("Greedy with Merge Detection", result_greedy)
    except Exception as e:
        print(f"\n--- GREEDY ---\nError: {e}")

    input("\n⏎ Press ENTER to continue to next scenario...")


def main():
    """Run all demo scenarios."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SEMANTIC DIFF - ALIGNMENT METHOD DEMO                     ║
║                                                                              ║
║  Testing different alignment methods with mock data (no API keys needed!)   ║
╚══════════════════════════════════════════════════════════════════════════════╝

This demo shows:
- How lexical (TF-IDF) vs semantic (embeddings) alignment differs
- When pure Hungarian fails (merging/splitting)
- How different methods handle edge cases

Note: Using SMART MOCK embeddings (word-overlap based).
      Real embeddings (OpenAI/sentence-transformers) will be more accurate.
""")

    input("Press ENTER to start...")

    # Run each scenario
    for name, scenario in DEMO_SCENARIOS.items():
        run_demo_scenario(name, scenario)

    # Final summary
    print_section("DEMO COMPLETE")
    print("""
Key Takeaways:

1. LEXICAL vs SEMANTIC:
   - Lexical works when words overlap (light edits)
   - Semantic works even with heavy paraphrasing
   - → Use semantic for real-world use cases

2. PURE HUNGARIAN LIMITATION:
   - Can't detect 2→1 or 1→2 merges/splits
   - Shows as 1 match + 1 addition/deletion
   - → Use greedy with merges if this matters for your demo

3. NEXT STEPS:
   - Replace mock embeddings with real API (OpenAI/sentence-transformers)
   - Run: python run_experiments.py --methods all --test-cases all
   - Pick your method based on results

For Nickolas: See ml/NICKOLAS_README.md for full analysis and recommendations.
""")


if __name__ == "__main__":
    main()
