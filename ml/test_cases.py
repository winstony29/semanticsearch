"""
Edge case test data for alignment experiments.

Each test case has:
- v1_sentences: Original version
- v2_sentences: Revised version
- expected_behavior: What should happen
- difficulty: How challenging for alignment algorithms
"""

TEST_CASES = {
    # ========================================================================
    # CASE 1: HEAVY PARAPHRASING (LOW LEXICAL, HIGH SEMANTIC)
    # ========================================================================
    "heavy_paraphrase": {
        "v1_sentences": [
            "The company's revenue increased by 15% in the last quarter.",
            "We are planning to expand into Asian markets next year.",
            "Customer satisfaction scores have improved significantly."
        ],
        "v2_sentences": [
            "Last quarter saw a 15% boost in corporate earnings.",
            "Next year, we'll be entering markets across Asia.",
            "Clients are much happier with our service now."
        ],
        "expected_behavior": {
            "pairs": 3,
            "all_matched": True,
            "note": "Words change completely but meaning preserved. Lexical methods will struggle."
        },
        "difficulty": "hard_for_lexical",
        "expected_lexical_score": 0.2,  # Low word overlap
        "expected_semantic_score": 0.85  # High meaning similarity
    },

    # ========================================================================
    # CASE 2: SENTENCE MERGING (2→1)
    # ========================================================================
    "two_to_one_merge": {
        "v1_sentences": [
            "The weather was sunny.",
            "We decided to go to the beach.",
            "Everyone had a great time."
        ],
        "v2_sentences": [
            "The sunny weather prompted us to go to the beach.",
            "Everyone had a great time."
        ],
        "expected_behavior": {
            "note": "Sentences 1 and 2 from v1 merged into sentence 1 of v2.",
            "challenge": "Pure Hungarian will only match sentence 1 OR 2, not both.",
            "greedy_should_detect": "Both v1[0] and v1[1] should have high similarity to v2[0]"
        },
        "difficulty": "impossible_for_pure_hungarian",
        "correct_mapping": {
            "v2[0]": ["v1[0]", "v1[1]"],  # Merged
            "v2[1]": ["v1[2]"]              # Normal match
        }
    },

    # ========================================================================
    # CASE 3: SENTENCE SPLITTING (1→2)
    # ========================================================================
    "one_to_two_split": {
        "v1_sentences": [
            "The project was delayed due to budget constraints and technical difficulties.",
            "The team is working on solutions."
        ],
        "v2_sentences": [
            "The project was delayed due to budget constraints.",
            "Technical difficulties also contributed to the delay.",
            "The team is working on solutions."
        ],
        "expected_behavior": {
            "note": "v1[0] split into v2[0] and v2[1].",
            "challenge": "Hungarian will only match v1[0] to either v2[0] OR v2[1], not both.",
            "result": "The other part looks like an addition."
        },
        "difficulty": "impossible_for_pure_hungarian",
        "correct_mapping": {
            "v1[0]": ["v2[0]", "v2[1]"],  # Split
            "v1[1]": ["v2[2]"]             # Normal match
        }
    },

    # ========================================================================
    # CASE 4: SENTENCE REORDERING
    # ========================================================================
    "reordering": {
        "v1_sentences": [
            "First, we need to gather requirements.",
            "Second, we design the system.",
            "Third, we implement the solution.",
            "Finally, we test everything."
        ],
        "v2_sentences": [
            "Testing comes at the end after implementation.",
            "First, gather all requirements.",
            "Then design and implement the system."
        ],
        "expected_behavior": {
            "note": "Sentences reordered and some merged. Tests algorithm's ability to match regardless of order.",
            "v2[0]": "Should match v1[3]",
            "v2[1]": "Should match v1[0]",
            "v2[2]": "Merges v1[1] and v1[2]"
        },
        "difficulty": "medium",
        "correct_mapping": {
            "v2[0]": ["v1[3]"],
            "v2[1]": ["v1[0]"],
            "v2[2]": ["v1[1]", "v1[2]"]
        }
    },

    # ========================================================================
    # CASE 5: MINIMAL CHANGES (STYLE ONLY)
    # ========================================================================
    "minimal_style_changes": {
        "v1_sentences": [
            "The dog ran quickly.",
            "It was very excited.",
            "The park was crowded today."
        ],
        "v2_sentences": [
            "The dog ran fast.",
            "It was extremely excited.",
            "The park was crowded today."
        ],
        "expected_behavior": {
            "pairs": 3,
            "all_matched": True,
            "similarity_range": [0.85, 1.0],
            "note": "Minor word changes, meaning fully preserved. All methods should work."
        },
        "difficulty": "easy"
    },

    # ========================================================================
    # CASE 6: COMPLETE REWRITE (LOW SIMILARITY EVERYWHERE)
    # ========================================================================
    "complete_rewrite": {
        "v1_sentences": [
            "The financial report shows concerning trends.",
            "Revenue has declined steadily.",
            "We need to take immediate action."
        ],
        "v2_sentences": [
            "Everything is going great!",
            "Sales are through the roof.",
            "No changes needed, keep doing what we're doing."
        ],
        "expected_behavior": {
            "note": "Completely opposite meaning. All should be marked as deleted + added.",
            "pairs": 6,  # 3 deletions + 3 additions
            "matched": 0,
            "challenge": "Algorithms should recognize low similarity and not force matches."
        },
        "difficulty": "tests_threshold_logic"
    },

    # ========================================================================
    # CASE 7: IDENTICAL TEXT
    # ========================================================================
    "identical": {
        "v1_sentences": [
            "This is a test sentence.",
            "Nothing has changed here.",
            "Everything is the same."
        ],
        "v2_sentences": [
            "This is a test sentence.",
            "Nothing has changed here.",
            "Everything is the same."
        ],
        "expected_behavior": {
            "pairs": 3,
            "all_matched": True,
            "similarity": 1.0,
            "note": "Perfect matches. All methods should get 100% similarity."
        },
        "difficulty": "trivial"
    },

    # ========================================================================
    # CASE 8: ADDITIONS ONLY
    # ========================================================================
    "additions_only": {
        "v1_sentences": [
            "Original sentence one.",
            "Original sentence two."
        ],
        "v2_sentences": [
            "Original sentence one.",
            "New sentence inserted here.",
            "Original sentence two.",
            "Another new sentence at the end."
        ],
        "expected_behavior": {
            "matched": 2,
            "added": 2,
            "note": "Two sentences preserved, two added. Tests addition detection."
        },
        "difficulty": "easy"
    },

    # ========================================================================
    # CASE 9: DELETIONS ONLY
    # ========================================================================
    "deletions_only": {
        "v1_sentences": [
            "This sentence will be removed.",
            "This sentence stays.",
            "This one gets deleted too.",
            "This also stays."
        ],
        "v2_sentences": [
            "This sentence stays.",
            "This also stays."
        ],
        "expected_behavior": {
            "matched": 2,
            "deleted": 2,
            "note": "Two sentences removed, two preserved. Tests deletion detection."
        },
        "difficulty": "easy"
    },

    # ========================================================================
    # CASE 10: MIXED OPERATIONS (REAL-WORLD COMPLEXITY)
    # ========================================================================
    "mixed_complex": {
        "v1_sentences": [
            "We offer three pricing tiers.",
            "The basic plan costs $10 per month.",
            "The pro plan costs $30 per month.",
            "Enterprise pricing is custom.",
            "All plans include 24/7 support."
        ],
        "v2_sentences": [
            "Our pricing has three tiers to fit any budget.",  # Paraphrase of v1[0]
            "Basic is just $10/month and Pro is $30/month.",  # Merge of v1[1] and v1[2]
            "For enterprise needs, contact our sales team.",   # Paraphrase of v1[3]
            # v1[4] deleted
            "We also offer a free trial for all new users."   # Addition
        ],
        "expected_behavior": {
            "operations": {
                "paraphrase": 2,  # v1[0]→v2[0], v1[3]→v2[2]
                "merge": 1,       # v1[1]+v1[2]→v2[1]
                "deletion": 1,    # v1[4]
                "addition": 1     # v2[3]
            },
            "note": "Combines paraphrasing, merging, deletion, and addition. Most realistic test case."
        },
        "difficulty": "very_hard",
        "correct_mapping": {
            "v2[0]": ["v1[0]"],           # Paraphrase
            "v2[1]": ["v1[1]", "v1[2]"],  # Merge
            "v2[2]": ["v1[3]"],           # Paraphrase
            "v2[3]": [],                   # Addition
            "v1[4]": "deleted"
        }
    },

    # ========================================================================
    # CASE 11: UNEQUAL COUNTS (STRESS TEST PADDING)
    # ========================================================================
    "unequal_lengths": {
        "v1_sentences": [
            "Short list.",
            "Only three.",
            "Sentences here."
        ],
        "v2_sentences": [
            "This is a much longer version now.",
            "We added many more sentences.",
            "Some match the originals.",
            "Others are completely new.",
            "Testing padding logic.",
            "Does Hungarian handle this?",
            "Sentence seven.",
            "Sentence eight."
        ],
        "expected_behavior": {
            "matched": 1,  # "Only three." ≈ "Some match the originals."
            "added": 7,
            "note": "Large difference in length. Tests padding strategy."
        },
        "difficulty": "tests_padding"
    },

    # ========================================================================
    # CASE 12: EMPTY INPUTS
    # ========================================================================
    "empty_v1": {
        "v1_sentences": [],
        "v2_sentences": [
            "All new content.",
            "Nothing existed before."
        ],
        "expected_behavior": {
            "added": 2,
            "note": "Edge case: empty v1. All v2 should be additions."
        },
        "difficulty": "edge_case"
    },

    "empty_v2": {
        "v1_sentences": [
            "Everything deleted.",
            "Nothing remains."
        ],
        "v2_sentences": [],
        "expected_behavior": {
            "deleted": 2,
            "note": "Edge case: empty v2. All v1 should be deletions."
        },
        "difficulty": "edge_case"
    },

    "both_empty": {
        "v1_sentences": [],
        "v2_sentences": [],
        "expected_behavior": {
            "pairs": 0,
            "note": "Edge case: both empty. Should return empty result without crashing."
        },
        "difficulty": "edge_case"
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_test_case(name: str) -> dict:
    """Get a specific test case by name."""
    if name not in TEST_CASES:
        raise ValueError(f"Unknown test case: {name}. Available: {list(TEST_CASES.keys())}")
    return TEST_CASES[name]


def get_all_test_cases():
    """Return all test cases."""
    return TEST_CASES


def get_test_cases_by_difficulty(difficulty: str):
    """Get test cases filtered by difficulty level."""
    return {
        name: case for name, case in TEST_CASES.items()
        if case.get("difficulty") == difficulty
    }


def print_test_case_summary():
    """Print a summary of all test cases."""
    print("=" * 80)
    print("TEST CASE SUMMARY")
    print("=" * 80)

    for name, case in TEST_CASES.items():
        print(f"\n{name.upper().replace('_', ' ')}")
        print(f"  Difficulty: {case.get('difficulty', 'N/A')}")
        print(f"  V1 sentences: {len(case['v1_sentences'])}")
        print(f"  V2 sentences: {len(case['v2_sentences'])}")
        if 'expected_behavior' in case:
            print(f"  Expected: {case['expected_behavior'].get('note', 'N/A')}")
        print()


if __name__ == "__main__":
    print_test_case_summary()
