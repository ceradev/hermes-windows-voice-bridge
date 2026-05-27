from __future__ import annotations

from contextlib import ExitStack
from typing import Callable

from src.core.events import EventBus
from src.core.logging import BridgeLogger
from src.core.state import AppStateStore


class AppLifecycle:
    """Coordinates clean boot/shutdown for desktop, tray and local API."""

    def __init__(self, state: AppStateStore, events: EventBus, logger: BridgeLogger) -> None:
        self._state = state
        self._events = events
        self._logger = logger
        self._cleanup = ExitStack()
        self._started = False

    def on_shutdown(self, callback: Callable[[], None]) -> None:
        self._cleanup.callback(callback)

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._state.update(lifecycle="running")
        self._logger.user.info("Lifecycle started")
        self._events.publish("lifecycle.started")

    def stop(self) -> None:
        if not self._started:
            return
        self._state.update(lifecycle="stopping")
        self._events.publish("lifecycle.stopping")
        try:
            self._cleanup.close()
        finally:
            self._state.update(lifecycle="stopped")
            self._logger.user.info("Lifecycle stopped")
            self._events.publish("lifecycle.stopped")
            self._started = False
