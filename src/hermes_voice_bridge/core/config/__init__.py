from __future__ import annotations

from pathlib import Path


class ConfigService:
    def __init__(self, env_path: Path) -> None:
        self.env_path = Path(env_path)
        self.env_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, str]:
        if not self.env_path.exists():
            return {}
        data: dict[str, str] = {}
        for line in self.env_path.read_text(encoding="utf-8").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
        return data

    def save(self, updates: dict[str, str]) -> None:
        current = self.load()
        current.update(updates)
        lines = [f"{key}={value}" for key, value in current.items()]
        self.env_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


__all__ = ["ConfigService"]
