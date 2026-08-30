from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_KNOWLEDGE_DIR = Path(__file__).parent
_GUIDE_PATH = _KNOWLEDGE_DIR / "triage_guide.json"

_guide_cache: dict[str, Any] | None = None


def load_triage_guide() -> dict[str, Any]:
    """Carga y cachea la guía de triaje desde el JSON."""
    global _guide_cache
    if _guide_cache is None:
        with open(_GUIDE_PATH, "r", encoding="utf-8") as f:
            _guide_cache = json.load(f)
    return _guide_cache
