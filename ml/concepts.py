"""Step 5 — Concept extraction.

Owner: Agent 3 (concepts).

Runs concurrently with steps 1–4 via ``asyncio.gather``. Calls
``gpt-4o-mini`` via ``client.chat.completions.parse`` with the ``ConceptDiff``
schema for guaranteed structured output. Wrapped in try/except — on any
failure the pipeline returns ``concepts=[]`` and ``concept_extraction="failed"``.
"""
