from __future__ import annotations

import base64
import os
from pathlib import Path


class SecureValueStore:
    """Small secret store.

    On Windows this can later be upgraded to real DPAPI. For now we isolate the
    abstraction so SessionManager and desktop code stop knowing about storage
    details. In non-Windows test runs we store an opaque base64 payload with file
    permissions limited by the current umask.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def set_secret(self, name: str, value: str) -> None:
        data = self._read_all()
        data[name] = base64.b64encode(value.encode("utf-8")).decode("ascii")
        self._write_all(data)

    def get_secret(self, name: str) -> str:
        value = self._read_all().get(name, "")
        if not value:
            return ""
        return base64.b64decode(value.encode("ascii")).decode("utf-8")

    def delete_secret(self, name: str) -> None:
        data = self._read_all()
        if name in data:
            del data[name]
            self._write_all(data)

    def _read_all(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        pairs: dict[str, str] = {}
        for line in raw.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            pairs[key.strip()] = value.strip()
        return pairs

    def _write_all(self, data: dict[str, str]) -> None:
        lines = [f"{key}={value}" for key, value in sorted(data.items())]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        if os.name != "nt":
            os.chmod(self.path, 0o600)
