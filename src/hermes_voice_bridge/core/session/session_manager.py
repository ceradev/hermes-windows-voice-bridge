from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from hermes_voice_bridge.core.events import EventBus
from hermes_voice_bridge.core.state import AppStateStore
from hermes_voice_bridge.platform.windows import SecureValueStore
from hermes_voice_bridge.storage.repositories import JsonSessionRepository
from hermes_voice_bridge.core.session.auth_backend import SessionRefreshBackend


@dataclass(slots=True)
class SessionRecord:
    access_token: str
    refresh_token: str = ""
    token_type: str = "Bearer"
    user_id: str = ""
    display_name: str = ""
    remember_me: bool = True
    expires_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, *, now: datetime | None = None, skew_seconds: int = 30) -> bool:
        if not self.expires_at:
            return False
        current = now or datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(self.expires_at)
        return current + timedelta(seconds=skew_seconds) >= expires_at


class SessionManager:
    """Owns persistent sign-in, restore, logout and token refresh hooks."""

    def __init__(
        self,
        repository: JsonSessionRepository,
        secure_store: SecureValueStore,
        events: EventBus,
        state: AppStateStore,
        refresh_backend: SessionRefreshBackend,
    ) -> None:
        self._repository = repository
        self._secure_store = secure_store
        self._events = events
        self._state = state
        self._refresh_backend = refresh_backend

    def save(self, record: SessionRecord) -> SessionRecord:
        payload = {
            "refresh_token": record.refresh_token,
            "token_type": record.token_type,
            "user_id": record.user_id,
            "display_name": record.display_name,
            "remember_me": record.remember_me,
            "expires_at": record.expires_at,
            "metadata": record.metadata,
        }
        self._repository.save(payload)
        self._secure_store.set_secret("access_token", record.access_token)
        self._state.patch_session(
            authenticated=True,
            user_id=record.user_id,
            display_name=record.display_name,
            token_expires_at=record.expires_at,
            remember_me=record.remember_me,
            restoration_source="login",
            last_error="",
        )
        self._events.publish("session.saved", user_id=record.user_id, remember_me=record.remember_me)
        return record

    def restore(self) -> SessionRecord | None:
        payload = self._repository.load()
        token = self._secure_store.get_secret("access_token")
        if not payload or not token:
            self._state.patch_session(authenticated=False, restoration_source="empty")
            return None
        record = SessionRecord(access_token=token, **payload)
        if record.is_expired() and not record.refresh_token:
            self.logout(reason="expired")
            self._state.patch_session(last_error="Session expired")
            self._events.publish("session.expired")
            return None
        if record.is_expired() and record.refresh_token:
            record = self.refresh(record)
        self._state.patch_session(
            authenticated=True,
            user_id=record.user_id,
            display_name=record.display_name,
            token_expires_at=record.expires_at,
            remember_me=record.remember_me,
            restoration_source="restore",
            last_error="",
        )
        self._events.publish("session.restored", user_id=record.user_id)
        return record

    def refresh(self, record: SessionRecord) -> SessionRecord:
        if not record.refresh_token:
            raise RuntimeError("Cannot refresh session without refresh token")
        refreshed = self._refresh_backend.refresh(record)
        self.save(refreshed)
        self._events.publish("session.refreshed", user_id=refreshed.user_id)
        return refreshed

    def logout(self, *, reason: str = "manual") -> None:
        self._repository.delete()
        self._secure_store.delete_secret("access_token")
        self._state.patch_session(
            authenticated=False,
            user_id="",
            display_name="",
            token_expires_at="",
            restoration_source=reason,
            last_error="" if reason == "manual" else reason,
        )
        self._events.publish("session.logged_out", reason=reason)
