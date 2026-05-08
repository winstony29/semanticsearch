"""pytest configuration: ensure project root is importable.

This mirrors the sys.path injection in ``backend/main.py`` so that test
modules can use absolute imports like ``from ml.scoring import ...`` and
``from backend.models.schemas import ...`` regardless of where pytest is
invoked from.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
