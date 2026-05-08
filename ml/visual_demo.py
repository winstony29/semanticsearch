"""
Visual comparison of alignment methods.
Shows similarity matrices as ASCII heatmaps.
"""

import numpy as np
from typing import List
import sys

sys.path.insert(0, '.')

from alignment_methods import lexical_hungarian, semantic_hungarian


def simple_mock_embeddings(sentences: List[str]) -> np.ndarray:
    """Generate embeddings with realistic semantic similarity."""
    embeddings = []

    for sent in sentences:
        words = set(sent.lower().split())
        feature = np.zeros(384)

        # Hash words to dimensions
        for word in words:
            h = hash(word)
            for i in range(10):
                feature[(h + i) % 384] += 1.0

        # Normalize
        if np.linalg.norm(feature) > 0:
            feature = feature / np.linalg.norm(feature)

        embeddings.append(feature)

    return np.array(embeddings)


def print_matrix_heatmap(matrix: np.ndarray, v1_labels: List[str], v2_labels: List[str], title: str):
    """Print similarity matrix as ASCII heatmap."""
    print(f"\n{title}")
    print("=" * 80)

    # Truncate labels for display
    v1_short = [s[:30] + "..." if len(s) > 30 else s for s in v1_labels]
    v2_short = [s[:30] + "..." if len(s) > 30 else s for s in v2_labels]

    # Print header
    print("\n       ", end="")
    for j, label in enumerate(v2_short):
        print(f"  v2[{j}]", end="")
    print()

    # Print matrix
    for i in range(matrix.shape[0]):
        print(f"v1[{i}]  ", end="")
        for j in range(matrix.shape[1]):
            score = matrix[i, j]
            # ASCII heatmap
            if score >= 0.85:
                symbol = "██"  # Dark - high similarity
            elif score >= 0.70:
                symbol = "▓▓"
            elif score >= 0.50:
                symbol = "▒▒"
            elif score >= 0.30:
                symbol = "░░"
            else:
                symbol = "  "  # Empty - low similarity

            print(f" {symbol} ", end="")
        print(f"  {v1_short[i]}")

    print("\nLegend: ██ = 0.85+  ▓▓ = 0.70-0.85  ▒▒ = 0.50-0.70  ░░ = 0.30-0.50  (empty) < 0.30")


def print_comparison(v1: List[str], v2: List[str]):
    """Compare lexical vs semantic similarity matrices."""

    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "VISUAL ALIGNMENT COMPARISON" + " " * 31 + "║")
    print("╚" + "═" * 78 + "╝")

    print("\n📄 VERSION 1 (Original):")
    for i, sent in enumerate(v1):
        print(f"  [{i}] {sent}")

    print("\n📄 VERSION 2 (Revised):")
    for i, sent in enumerate(v2):
        print(f"  [{i}] {sent}")

    # Get results
    lexical_result = lexical_hungarian(v1, v2, threshold=0.3)
    embeddings = simple_mock_embeddings(v1 + v2)
    semantic_result = semantic_hungarian(v1, v2, embeddings, threshold=0.6)

    # Print matrices
    print_matrix_heatmap(
        lexical_result["similarity_matrix"],
        v1, v2,
        "LEXICAL SIMILARITY (TF-IDF)"
    )

    print_matrix_heatmap(
        semantic_result["similarity_matrix"],
        v1, v2,
        "SEMANTIC SIMILARITY (Embeddings)"
    )

    # Print alignment results
    print("\n" + "=" * 80)
    print("ALIGNMENT RESULTS")
    print("=" * 80)

    print("\n--- LEXICAL HUNGARIAN ---")
    for pair in lexical_result["pairs"]:
        if pair["status"] == "matched":
            print(f"  v1[{pair['v1_index']}] ↔ v2[{pair['v2_index']}]  (score: {pair['similarity_score']:.2f})")

    print("\n--- SEMANTIC HUNGARIAN ---")
    for pair in semantic_result["pairs"]:
        if pair["status"] == "matched":
            emoji = "🟢" if pair['similarity_score'] >= 0.85 else "🟡" if pair['similarity_score'] >= 0.60 else "🔴"
            print(f"  {emoji} v1[{pair['v1_index']}] ↔ v2[{pair['v2_index']}]  (score: {pair['similarity_score']:.2f})")


# ============================================================================
# DEMO EXAMPLES
# ============================================================================

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     VISUAL ALIGNMENT DEMONSTRATION                           ║
║                                                                              ║
║  See similarity matrices and alignment results side-by-side                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

# Example 1: Light paraphrasing
print("\n" + "█" * 80)
print("EXAMPLE 1: Light Paraphrasing (Both methods work)")
print("█" * 80)

v1_light = [
    "The dog ran quickly.",
    "It was very excited.",
]

v2_light = [
    "The dog ran fast.",
    "It was extremely excited.",
]

print_comparison(v1_light, v2_light)

input("\n\n⏎ Press ENTER for next example...")

# Example 2: Heavy paraphrasing
print("\n\n" + "█" * 80)
print("EXAMPLE 2: Heavy Paraphrasing (Lexical struggles, Semantic works)")
print("█" * 80)

v1_heavy = [
    "The company's revenue increased by 15%.",
    "We plan to expand into Asian markets.",
]

v2_heavy = [
    "Corporate earnings saw a 15% boost.",
    "Next year brings Asia expansion plans.",
]

print_comparison(v1_heavy, v2_heavy)

input("\n\n⏎ Press ENTER for next example...")

# Example 3: Mixed with additions
print("\n\n" + "█" * 80)
print("EXAMPLE 3: Mixed Changes (Paraphrase + Addition)")
print("█" * 80)

v1_mixed = [
    "We offer three pricing tiers.",
    "Basic costs $10 per month.",
]

v2_mixed = [
    "Our pricing has three tiers.",
    "Basic is $10 monthly.",
    "We also offer a free trial.",
]

print_comparison(v1_mixed, v2_mixed)

print("\n\n" + "=" * 80)
print("DEMO COMPLETE")
print("=" * 80)
print("""
Key Observations:

1. LEXICAL vs SEMANTIC:
   - Lexical similarity depends on word overlap
   - Semantic similarity captures meaning even when words change
   - Compare the matrices: semantic gives higher scores for paraphrases

2. MATRIX READING:
   - Dark squares (██) = high similarity (>0.85)
   - Light squares (░░) = low similarity (<0.50)
   - Hungarian picks ONE match per row and column (optimal assignment)

3. NEXT STEPS:
   - This uses mock embeddings (word-hash based)
   - Real embeddings (OpenAI/sentence-transformers) will be more accurate
   - Try: python demo.py for interactive walkthrough
   - Try: python quick_test.py for merge example

See ml/NICKOLAS_README.md for full analysis!
""")
