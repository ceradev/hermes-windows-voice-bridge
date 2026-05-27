from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LogPaths:
    user_log: Path
    debug_log: Path
    crash_log: Path


class BridgeLogger:
    """Three-channel logger: user, debug, crash."""

    def __init__(self, paths: LogPaths) -> None:
        self.paths = paths
        for path in (paths.user_log, paths.debug_log, paths.crash_log):
            path.parent.mkdir(parents=True, exist_ok=True)
        self.user = self._build_logger("src.user", paths.user_log)
        self.debug = self._build_logger("src.debug", paths.debug_log)
        self.crash = self._build_logger("src.crash", paths.crash_log)

    def _build_logger(self, name: str, path: Path) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if logger.handlers:
            return logger
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
        logger.addHandler(handler)
        return logger
