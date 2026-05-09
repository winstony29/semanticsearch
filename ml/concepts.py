"""Step 5 — Concept extraction.

Owner: Agent 3 (concepts).

Runs concurrently with steps 1–4 via ``asyncio.gather``. Calls
``gpt-4o-mini`` via ``client.chat.completions.parse`` with the ``ConceptDiff``
schema for guaranteed structured output. Wrapped in try/except — on any
failure the pipeline returns ``concepts=[]`` and ``concept_extraction="failed"``.
"""

import sys

from openai import AsyncOpenAI

from backend.models.schemas import ConceptDiff, ConceptExtractionStatus
from ml.thresholds import CHAT_MODEL, MAX_CONCEPT_INPUT_CHARS


_SYSTEM_PROMPT = """\
You are a document analysis expert specializing in identifying high-level concepts,
obligations, rights, and themes in contracts and policy documents.

Read the BEFORE and AFTER texts carefully. Identify 3-8 key concepts in each document.

For each concept, classify its status relative to the two versions:
- "new": appears only in AFTER
- "removed": appears only in BEFORE (dropped in AFTER)
- "weakened": exists in both but is less strict/obligatory in AFTER
- "strengthened": exists in both but is more strict/obligatory in AFTER
- "unchanged": exists in both with essentially the same meaning and strength

Provide a verbatim quote (≤240 characters) from the relevant text as evidence.
Return a one-sentence summary of the overall document-level change.

Focus on concepts that matter legally or semantically, not trivial wording changes.
Output must conform to the provided JSON schema."""


async def extract_concepts(
    before_text: str,
    after_text: str,
) -> tuple[ConceptDiff, ConceptExtractionStatus]:
    """Extract document-level concepts from before and after text.

    Returns:
        ``(ConceptDiff, status)`` where status is ``"ok"`` or ``"failed"``.
        On ``"failed"``, ``ConceptDiff`` is empty (summary="", concepts=[])
        — concept extraction is best-effort and never breaks the pipeline.
    """
    # Truncate if necessary, with a clear marker.
    before_truncated = before_text
    after_truncated = after_text

    if len(before_text) > MAX_CONCEPT_INPUT_CHARS:
        before_truncated = (
            before_text[:MAX_CONCEPT_INPUT_CHARS] + "\n[TRUNCATED at 60,000 chars]"
        )

    if len(after_text) > MAX_CONCEPT_INPUT_CHARS:
        after_truncated = (
            after_text[:MAX_CONCEPT_INPUT_CHARS] + "\n[TRUNCATED at 60,000 chars]"
        )

    user_message = f"BEFORE:\n{before_truncated}\n\nAFTER:\n{after_truncated}"

    try:
        client = AsyncOpenAI()
        response = await client.chat.completions.parse(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format=ConceptDiff,
            temperature=0,
            max_completion_tokens=2000,
        )

        if response.choices[0].message.parsed is None:
            refusal = response.choices[0].message.refusal
            print(
                f"API refusal on concept extraction: {refusal}",
                file=sys.stderr,
            )
            return ConceptDiff(summary="", concepts=[]), "failed"

        return response.choices[0].message.parsed, "ok"

    except Exception as exc:
        print(
            f"extract_concepts failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return ConceptDiff(summary="", concepts=[]), "failed"
