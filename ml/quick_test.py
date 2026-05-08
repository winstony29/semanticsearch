"""
QUICKEST TEST - Run this for instant results!

Shows one clear example of how alignment works.
"""

import numpy as np
import sys

# Add parent directory to path
sys.path.insert(0, '.')

from alignment_methods import semantic_hungarian

# ============================================================================
# SIMPLE MOCK EMBEDDINGS
# ============================================================================

def quick_mock_embeddings(sentences):
    """Super simple mock - just for demo."""
    embeddings = []
    for sent in sentences:
        # Use word count and length as features (padded to 384 dims)
        word_count = len(sent.split())
        char_count = len(sent)
        feature = np.random.rand(384) * 0.1  # Small random noise
        feature[0] = word_count / 20.0  # Normalize
        feature[1] = char_count / 100.0
        # Add some semantic-like features based on keywords
        if "sunny" in sent.lower() or "weather" in sent.lower():
            feature[2:10] = 0.8
        if "beach" in sent.lower():
            feature[10:20] = 0.8
        if "great time" in sent.lower() or "had fun" in sent.lower():
            feature[20:30] = 0.8

        embeddings.append(feature)

    return np.array(embeddings)


# ============================================================================
# TEST CASE: SENTENCE MERGING
# ============================================================================

print("=" * 80)
print("QUICK TEST: Sentence Merging Example")
print("=" * 80)

v1 = [
    "The weather was sunny.",
    "We decided to go to the beach.",
    "Everyone had a great time."
]

v2 = [
    "The sunny weather prompted us to go to the beach.",
    "Everyone had a great time."
]

print("\n📄 VERSION 1 (Original):")
for i, sent in enumerate(v1):
    print(f"  [{i}] {sent}")

print("\n📄 VERSION 2 (Revised):")
for i, sent in enumerate(v2):
    print(f"  [{i}] {sent}")

print("\n🤔 What happened?")
print("  Sentences 0 and 1 from v1 were merged into sentence 0 of v2.")
print("  Sentence 2 stayed the same.")

# Get embeddings
embeddings = quick_mock_embeddings(v1 + v2)

# Run semantic Hungarian
print("\n🔍 Running Semantic Hungarian Alignment...")
result = semantic_hungarian(v1, v2, embeddings, threshold=0.6)

print("\n✨ RESULTS:")
print("-" * 80)

for pair in result["pairs"]:
    status = pair["status"]
    v1_idx = pair.get("v1_index")
    v2_idx = pair.get("v2_index")
    score = pair.get("similarity_score", 0.0)

    if status == "matched":
        emoji = "🟢" if score >= 0.85 else "🟡" if score >= 0.60 else "🔴"
        print(f"{emoji} MATCHED: v1[{v1_idx}] ↔ v2[{v2_idx}]  (similarity: {score:.2f})")
        print(f"   v1: {pair['v1_sentence']}")
        print(f"   v2: {pair['v2_sentence']}")
    elif status == "added":
        print(f"➕ ADDED: v2[{v2_idx}] (new sentence in v2)")
        print(f"   {pair['v2_sentence']}")
    elif status == "deleted":
        print(f"➖ DELETED: v1[{v1_idx}] (removed from v2)")
        print(f"   {pair['v1_sentence']}")

    print()

print("=" * 80)
print("\n💡 OBSERVATION:")
print("   Hungarian algorithm picks the BEST 1:1 matching.")
print("   It matched v1[0] or v1[1] to v2[0], but not both.")
print("   The other appears as 'deleted'.")
print()
print("   This is a limitation of pure 1:1 Hungarian!")
print("   For merge detection, use greedy_with_merges method.")
print()
print("🚀 Try the full demo: python demo.py")
print("📚 See ml/NICKOLAS_README.md for detailed analysis")
print()
