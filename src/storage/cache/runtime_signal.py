from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json


class JsonRuntimeSignalStore:
    """Small shared store for explicit runtime/overlay events across bridge, tray, API and desktop."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            raw = self.path.read_text(encoding="utf-8").strip()
            if not raw:
                return None
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def emit(self, *, kind: str, title: str, detail: str = "", source: str = "runtime", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        current = self.load() or {}
        signal = {
            "sequence": int(current.get("sequence", 0) or 0) + 1,
            "kind": kind,
            "title": title,
            "detail": detail,
            "source": source,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
        }
        self.path.write_text(json.dumps(signal, indent=2, ensure_ascii=False), encoding="utf-8")
        return signal

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
