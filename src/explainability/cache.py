"""File-based cache for LLM explanations, keyed by (nct_id, error_type)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional


class ExplanationCache:
    """Persist and retrieve LLM explanations to avoid redundant API calls."""

    def __init__(self, cache_dir: Path) -> None:
        self._dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, nct_id: str, error_type: str) -> Path:
        digest = hashlib.sha256(f"{nct_id}:{error_type}".encode()).hexdigest()[:16]
        return self._dir / f"{digest}.json"

    def get(self, nct_id: str, error_type: str) -> Optional[str]:
        """Return a cached explanation, or None on a cache miss."""
        path = self._key_path(nct_id, error_type)
        if path.exists():
            return json.loads(path.read_text())["explanation"]
        return None

    def set(self, nct_id: str, error_type: str, explanation: str) -> None:
        """Write an explanation to cache."""
        path = self._key_path(nct_id, error_type)
        path.write_text(
            json.dumps(
                {"nct_id": nct_id, "error_type": error_type, "explanation": explanation}
            )
        )
