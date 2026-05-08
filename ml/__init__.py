"""ML slice — embeddings, scoring, classification, metrics, concepts, pipeline.

Public entry point: ``ml.pipeline.run_diff``.

Receives an ``AlignmentResult`` from the backend lead's ``align()`` (or from
``ml._mock_align`` during pre-integration development) and produces the full
``DiffResponse`` defined in ``backend/models/schemas.py``.
"""
