from __future__ import annotations

from pathlib import Path

from hermes_voice_bridge.core.events import EventBus
from hermes_voice_bridge.core.state import AppStateStore
from hermes_voice_bridge.core.session.auth_backend import build_refresh_backend_from_env
from hermes_voice_bridge.core.session.session_manager import SessionManager
from hermes_voice_bridge.platform.windows import SecureValueStore
from hermes_voice_bridge.storage.repositories import JsonSessionRepository


def build_session_manager(state_dir: Path, events: EventBus | None = None, state: AppStateStore | None = None) -> SessionManager:
    state_dir.mkdir(parents=True, exist_ok=True)
    return SessionManager(
        JsonSessionRepository(state_dir / "session.json"),
        SecureValueStore(state_dir / "session.secrets"),
        events or EventBus(),
        state or AppStateStore(),
        build_refresh_backend_from_env(),
    )
