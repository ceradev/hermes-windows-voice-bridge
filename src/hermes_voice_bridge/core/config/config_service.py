from __future__ import annotations

from pathlib import Path
from typing import Any

from windows_hermes_voice_control import load_env_file, save_env_file


class ConfigService:
    """Centralized config access backed by state/voice.env."""

    def __init__(self, env_path: Path) -> None:
        self.env_path = env_path
        self.env_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, str]:
        return load_env_file(self.env_path, update_os_environ=False)

    def save(self, updates: dict[str, Any]) -> dict[str, str]:
        normalized = {key: "" if value is None else str(value).strip() for key, value in updates.items()}
        return save_env_file(self.env_path, normalized)

    def get(self, key: str, default: str = "") -> str:
        return self.load().get(key, default)
