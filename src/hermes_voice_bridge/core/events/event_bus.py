from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, DefaultDict


EventHandler = Callable[["Event"], None]


@dataclass(slots=True)
class Event:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EventBus:
    """In-process event bus for bridge lifecycle and UI synchronization.

    Event names should stay semantic and stable, for example:
    - audio.started
    - audio.stopped
    - transcription.completed
    - hermes.response
    - tts.started
    - session.restored
    - shortcut.updated
    """

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, list[EventHandler]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, event_name: str, handler: EventHandler) -> Callable[[], None]:
        with self._lock:
            self._handlers[event_name].append(handler)

        def _unsubscribe() -> None:
            self.unsubscribe(event_name, handler)

        return _unsubscribe

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        with self._lock:
            handlers = self._handlers.get(event_name, [])
            if handler in handlers:
                handlers.remove(handler)
            if not handlers and event_name in self._handlers:
                del self._handlers[event_name]

    def publish(self, event_name: str, **payload: Any) -> Event:
        event = Event(name=event_name, payload=payload)
        with self._lock:
            handlers = list(self._handlers.get(event_name, []))
            wildcard = list(self._handlers.get("*", []))
        for handler in [*handlers, *wildcard]:
            handler(event)
        return event
