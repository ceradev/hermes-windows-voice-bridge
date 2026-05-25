from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonRuntimeStateStore:
    """Persists the live tray-owned runtime snapshot for desktop/API consumers."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save(self, payload: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def delete(self) -> None:
        if self.path.exists():
            self.path.unlink()
