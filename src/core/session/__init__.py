from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from src.core.events import EventBus
from src.core.state import AppStateStore
from src.platform.windows import SecureValueStore
from src.storage.repositories import JsonSessionRepository

from .auth_backend import HttpRefreshBackend, LocalRefreshBackend


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


class SessionManager:
    def __init__(
        self,
        repository: JsonSessionRepository,
        secure_store: SecureValueStore,
        events: EventBus | None = None,
        app_state: AppStateStore | None = None,
        refresh_backend: LocalRefreshBackend | HttpRefreshBackend | None = None,
    ) -> None:
        self.repository = repository
        self.secure_store = secure_store
        self.events = events or EventBus()
        self.app_state = app_state or AppStateStore()
        self.refresh_backend = refresh_backend or LocalRefreshBackend()

    def save(self, record: SessionRecord) -> SessionRecord:
        payload = asdict(record)
        payload.pop("access_token", None)
        payload.pop("refresh_token", None)
        self.repository.save(payload)
        self.secure_store.set_secret("access_token", record.access_token)
        self.secure_store.set_secret("refresh_token", record.refresh_token)
        self._patch_state(record, restoration_source="save")
        self.events.publish("session.saved", user_id=record.user_id, remember_me=record.remember_me)
        return record

    def restore(self) -> SessionRecord | None:
        payload = self.repository.load()
        if not payload:
            self._clear_state("empty")
            return None

        record = self._record_from_payload(payload)
        if record.expires_at and self._is_expired(record.expires_at):
            record = self.refresh(record)

        self._patch_state(record, restoration_source="restored")
        self.events.publish("session.restored", user_id=record.user_id, remember_me=record.remember_me)
        return record

    def refresh(self, record: SessionRecord) -> SessionRecord:
        refreshed = self.refresh_backend.refresh(record)
        self.save(refreshed)
        self._patch_state(refreshed, restoration_source="refreshed")
        self.events.publish("session.refreshed", user_id=refreshed.user_id, remember_me=refreshed.remember_me)
        return refreshed

    def logout(self, reason: str = "manual") -> None:
        self.repository.delete()
        self.secure_store.delete_secret("access_token")
        self.secure_store.delete_secret("refresh_token")
        self._clear_state(reason)
        self.events.publish("session.logged_out", reason=reason)

    def _record_from_payload(self, payload: dict[str, Any]) -> SessionRecord:
        return SessionRecord(
            access_token=self.secure_store.get_secret("access_token") or str(payload.get("access_token") or ""),
            refresh_token=self.secure_store.get_secret("refresh_token") or str(payload.get("refresh_token") or ""),
            token_type=str(payload.get("token_type") or "Bearer"),
            user_id=str(payload.get("user_id") or ""),
            display_name=str(payload.get("display_name") or ""),
            remember_me=bool(payload.get("remember_me", True)),
            expires_at=str(payload.get("expires_at") or ""),
            metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {},
        )

    def _patch_state(self, record: SessionRecord, *, restoration_source: str) -> None:
        self.app_state.patch_session(
            authenticated=bool(record.access_token),
            user_id=record.user_id,
            display_name=record.display_name,
            token_expires_at=record.expires_at,
            remember_me=record.remember_me,
            restoration_source=restoration_source,
            last_error="",
        )

    def _clear_state(self, restoration_source: str) -> None:
        self.app_state.patch_session(
            authenticated=False,
            user_id="",
            display_name="",
            token_expires_at="",
            remember_me=True,
            restoration_source=restoration_source,
            last_error="",
        )

    @staticmethod
    def _is_expired(value: str) -> bool:
        try:
            expires_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= datetime.now(timezone.utc)


def build_session_manager(
    state_dir: Path,
    events: EventBus | None = None,
    app_state: AppStateStore | None = None,
) -> SessionManager:
    root = Path(state_dir)
    root.mkdir(parents=True, exist_ok=True)
    refresh_url = str(os.environ.get("HERMES_AUTH_REFRESH_URL", "") or "").strip()
    if refresh_url:
        backend = HttpRefreshBackend(
            refresh_url,
            timeout_seconds=float(os.environ.get("HERMES_AUTH_TIMEOUT", "10") or 10),
            auth_header=str(os.environ.get("HERMES_AUTH_HEADER", "Authorization") or "Authorization"),
            extra_secret=str(os.environ.get("HERMES_API_TOKEN", "") or ""),
            secret_header=str(os.environ.get("HERMES_AUTH_SECRET_HEADER", "X-Hermes-Auth-Secret") or "X-Hermes-Auth-Secret"),
        )
    else:
        backend = LocalRefreshBackend()
    return SessionManager(
        JsonSessionRepository(root / "session.json"),
        SecureValueStore(root / "session.secrets"),
        events or EventBus(),
        app_state or AppStateStore(),
        backend,
    )


__all__ = [
    "HttpRefreshBackend",
    "LocalRefreshBackend",
    "SessionManager",
    "SessionRecord",
    "build_session_manager",
]
