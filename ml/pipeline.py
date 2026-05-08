"""Step 6 — Pipeline orchestration.

Owner: Agent 4 (pipeline + metrics).

Top-level entry point: ``run_diff(before: str, after: str) -> DiffResponse``.
Calls the backend lead's ``align()`` (or the mock), then runs embeddings/
scoring/classification and concept extraction concurrently via
``asyncio.gather``, finally assembling the ``DiffResponse``.
"""
