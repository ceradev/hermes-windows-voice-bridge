from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from threading import RLock
from typing import Any, Callable


@dataclass(slots=True)
class SessionState:
    authenticated: bool = False
    user_id: str = ""
    display_name: str = ""
    token_expires_at: str = ""
    remember_me: bool = True
    restoration_source: str = ""
    last_error: str = ""


@dataclass(slots=True)
class ShortcutKeyState:
    key: str
    pressed: bool = False


@dataclass(slots=True)
class ShortcutBinding:
    accelerator: str = ""
    is_listening: bool = False
    has_conflict: bool = False
    conflict_with: str = ""
    last_pressed: list[str] = field(default_factory=list)
    preview_keys: list[ShortcutKeyState] = field(default_factory=list)


@dataclass(slots=True)
class ServiceStatus:
    state: str = "stopped"
    detail: str = ""
    pid: int | None = None
    latency_ms: float | None = None
    last_updated_at: str = ""


@dataclass(slots=True)
class ServiceHealth:
    tray: ServiceStatus = field(default_factory=ServiceStatus)
    bridge: ServiceStatus = field(default_factory=lambda: ServiceStatus(state="starting"))
    api: ServiceStatus = field(default_factory=ServiceStatus)
    hermes: ServiceStatus = field(default_factory=ServiceStatus)
    tts: ServiceStatus = field(default_factory=ServiceStatus)


@dataclass(slots=True)
class AppState:
    lifecycle: str = "booting"
    overlay_state: str = "idle"
    last_transcript: str = ""
    last_response_preview: str = ""
    last_error: str = ""
    session: SessionState = field(default_factory=SessionState)
    shortcut: ShortcutBinding = field(default_factory=ShortcutBinding)
    services: ServiceHealth = field(default_factory=ServiceHealth)


StateListener = Callable[[AppState], None]


class AppStateStore:
    """Single source of truth for bridge runtime state."""

    def __init__(self, initial: AppState | None = None) -> None:
        self._state = initial or AppState()
        self._listeners: list[StateListener] = []
        self._lock = RLock()

    @property
    def state(self) -> AppState:
        return self._state

    def subscribe(self, listener: StateListener) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def _unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return _unsubscribe

    def snapshot(self) -> dict[str, Any]:
        return asdict(self._state)

    def update(self, **fields: Any) -> AppState:
        with self._lock:
            self._state = replace(self._state, **fields)
            listeners = list(self._listeners)
            state = self._state
        for listener in listeners:
            listener(state)
        return state

    def patch_session(self, **fields: Any) -> AppState:
        session = replace(self._state.session, **fields)
        return self.update(session=session)

    def patch_shortcut(self, **fields: Any) -> AppState:
        shortcut = replace(self._state.shortcut, **fields)
        return self.update(shortcut=shortcut)

    def patch_service(self, service_name: str, **fields: Any) -> AppState:
        services = self._state.services
        current = getattr(services, service_name)
        updated = replace(current, **fields)
        next_services = replace(services, **{service_name: updated})
        return self.update(services=next_services)
