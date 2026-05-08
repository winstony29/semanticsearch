"""Step 5 — Concept extraction.

Owner: Agent 3 (concepts).

Runs concurrently with steps 1–4 via ``asyncio.gather``. Calls
``gpt-4o-mini`` via ``client.chat.completions.parse`` with the ``ConceptDiff``
schema for guaranteed structured output. Wrapped in try/except — on any
failure the pipeline returns ``concepts=[]`` and ``concept_extraction="failed"``.
"""

import sys
import os

# When run as __main__, ensure repo root is in path
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import AsyncOpenAI
from backend.models.schemas import ConceptDiff, ConceptExtractionStatus
from ml.thresholds import CHAT_MODEL, MAX_CONCEPT_INPUT_CHARS


async def extract_concepts(before_text: str, after_text: str) -> tuple[ConceptDiff, ConceptExtractionStatus]:
    """Extract document-level concepts from before and after text.

    Returns:
        (ConceptDiff, status) where status is "ok" | "skipped" | "failed".
        - "ok": call succeeded and returned valid structured output.
        - "skipped": inputs were empty or below a meaningful threshold.
        - "failed": an exception, refusal, or validation error occurred.
        On "failed" or "skipped", ConceptDiff is empty (summary="", concepts=[]).
    """

    # Check for empty or whitespace-only inputs
    if not before_text or not before_text.strip() or not after_text or not after_text.strip():
        return ConceptDiff(summary="", concepts=[]), "skipped"

    # Truncate if necessary, with a clear marker
    before_truncated = before_text
    after_truncated = after_text

    if len(before_text) > MAX_CONCEPT_INPUT_CHARS:
        before_truncated = before_text[:MAX_CONCEPT_INPUT_CHARS] + "\n[TRUNCATED at 60,000 chars]"

    if len(after_text) > MAX_CONCEPT_INPUT_CHARS:
        after_truncated = after_text[:MAX_CONCEPT_INPUT_CHARS] + "\n[TRUNCATED at 60,000 chars]"

    try:
        client = AsyncOpenAI()

        system_prompt = """You are a document analysis expert specializing in identifying high-level concepts,
obligations, rights, and themes in contracts and policy documents.

Read the BEFORE and AFTER texts carefully. Identify 3-8 key concepts in each document.

For each concept, classify its status relative to the two versions:
- "new": appears only in AFTER
- "weakened": exists in both but is less strict/obligatory in AFTER
- "strengthened": exists in both but is more strict/obligatory in AFTER
- "unchanged": exists in both with essentially the same meaning and strength

Provide a verbatim quote (≤240 characters) from the relevant text as evidence.
Return a one-sentence summary of the overall document-level change.

Focus on concepts that matter legally or semantically, not trivial wording changes.
Output must conform to the provided JSON schema."""

        user_message = f"""BEFORE:
{before_truncated}

AFTER:
{after_truncated}"""

        response = await client.chat.completions.parse(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format=ConceptDiff,
            temperature=0,
            max_completion_tokens=2000,
        )

        # Check for refusal
        if response.choices[0].message.parsed is None:
            refusal = response.choices[0].message.refusal
            print(
                f"API refusal on concept extraction: {refusal}",
                file=sys.stderr,
            )
            return ConceptDiff(summary="", concepts=[]), "failed"

        parsed_result = response.choices[0].message.parsed
        return parsed_result, "ok"

    except Exception as e:
        # Log exception to stderr, return empty result
        print(
            f"Exception in extract_concepts: {type(e).__name__}: {str(e)}",
            file=sys.stderr,
        )
        return ConceptDiff(summary="", concepts=[]), "failed"


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    import asyncio

    from ml._mock_align import SAMPLE_BEFORE, SAMPLE_AFTER

    async def test_extract_concepts():
        """Test the extract_concepts function."""
        # Test 1: Normal case with real OpenAI key
        if os.getenv("OPENAI_API_KEY"):
            print("Test 1: Extract concepts from mock samples...")
            result, status = await extract_concepts(SAMPLE_BEFORE, SAMPLE_AFTER)
            print(f"Status: {status}")
            print(f"Summary: {result.summary}")
            print(f"Concepts ({len(result.concepts)}):")
            for concept in result.concepts:
                print(
                    f"  - {concept.name}: {concept.status} "
                    f"(evidence: {concept.evidence[:60]}...)"
                )
            print()

        # Test 2: Empty input
        print("Test 2: Empty input...")
        result, status = await extract_concepts("", "")
        assert status == "skipped", f"Expected 'skipped', got '{status}'"
        assert result.summary == "", f"Expected empty summary, got '{result.summary}'"
        assert result.concepts == [], f"Expected no concepts, got {result.concepts}"
        print("  PASS: Returns skipped + empty ConceptDiff for empty input")
        print()

        # Test 3: Whitespace-only input
        print("Test 3: Whitespace-only input...")
        result, status = await extract_concepts("   \n\t  ", "   ")
        assert status == "skipped", f"Expected 'skipped', got '{status}'"
        print("  PASS: Returns skipped for whitespace-only input")
        print()

        # Test 4: Truncation behavior
        print("Test 4: Truncation of large input...")
        large_text = "x" * (MAX_CONCEPT_INPUT_CHARS + 1000)
        result, status = await extract_concepts(large_text, "short text")
        # Without a real API key, this will fail with "failed", but with a key,
        # it should succeed and handle the truncation
        print(f"  Status with oversized input: {status}")
        print()

        # Test 5: Missing API key scenario
        print("Test 5: API key check...")
        if not os.getenv("OPENAI_API_KEY"):
            print("  (Skipping live API test — no OPENAI_API_KEY set)")
            # But verify exception handling works by testing error path
            result, status = await extract_concepts("test before", "test after")
            assert status == "failed", f"Expected 'failed', got '{status}'"
            assert result.summary == "", f"Expected empty summary on failure"
            assert result.concepts == [], f"Expected no concepts on failure"
            print("  PASS: Returns failed + empty ConceptDiff on exception")
        else:
            print("  API key found; live tests will execute above")
        print()

        print("All tests completed!")

    asyncio.run(test_extract_concepts())
