from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from hermes_voice_bridge.core.session.session_manager import SessionRecord


class SessionRefreshBackend(Protocol):
    def refresh(self, record: SessionRecord) -> SessionRecord: ...


@dataclass(slots=True)
class LocalRefreshBackend:
    ttl_hours: int = 8

    def refresh(self, record: SessionRecord) -> SessionRecord:
        from hermes_voice_bridge.core.session.session_manager import SessionRecord

        if not record.refresh_token:
            raise RuntimeError("Cannot refresh session without refresh token")
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.ttl_hours)
        return SessionRecord(
            access_token=record.access_token,
            refresh_token=record.refresh_token,
            token_type=record.token_type,
            user_id=record.user_id,
            display_name=record.display_name,
            remember_me=record.remember_me,
            expires_at=expires_at.isoformat(),
            metadata={**record.metadata, "refreshed": True, "refresh_backend": "local"},
        )


@dataclass(slots=True)
class HttpRefreshBackend:
    refresh_url: str
    timeout_seconds: float = 10.0
    auth_header_name: str = "Authorization"
    extra_secret: str = ""
    extra_secret_header: str = "X-Hermes-Auth-Secret"

    def refresh(self, record: SessionRecord) -> SessionRecord:
        from hermes_voice_bridge.core.session.session_manager import SessionRecord

        if not record.refresh_token:
            raise RuntimeError("Cannot refresh session without refresh token")
        payload = {
            "refresh_token": record.refresh_token,
            "access_token": record.access_token,
            "token_type": record.token_type,
            "user_id": record.user_id,
            "display_name": record.display_name,
            "remember_me": record.remember_me,
            "metadata": record.metadata,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            self.auth_header_name: f"Bearer {record.access_token}",
        }
        if self.extra_secret:
            headers[self.extra_secret_header] = self.extra_secret
        request = urllib.request.Request(self.refresh_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            raise RuntimeError(body or f"Refresh request failed with HTTP {exc.code}") from exc
        except Exception as exc:
            raise RuntimeError(f"Refresh request failed: {exc}") from exc

        try:
            result = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("Refresh endpoint returned invalid JSON") from exc

        access_token = str(result.get("access_token") or record.access_token or "").strip()
        refresh_token = str(result.get("refresh_token") or record.refresh_token or "").strip()
        expires_at = str(result.get("expires_at") or "").strip()
        if not access_token:
            raise RuntimeError("Refresh endpoint did not return an access token")
        if not refresh_token:
            raise RuntimeError("Refresh endpoint did not return a refresh token")
        return SessionRecord(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=str(result.get("token_type") or record.token_type or "Bearer").strip() or "Bearer",
            user_id=str(result.get("user_id") or record.user_id or "").strip(),
            display_name=str(result.get("display_name") or record.display_name or "").strip(),
            remember_me=bool(result.get("remember_me", record.remember_me)),
            expires_at=expires_at,
            metadata={**record.metadata, **(result.get("metadata") if isinstance(result.get("metadata"), dict) else {}), "refresh_backend": "http"},
        )


def build_refresh_backend_from_env(env: dict[str, str] | None = None) -> SessionRefreshBackend:
    source = env or os.environ
    refresh_url = str(source.get("HERMES_AUTH_REFRESH_URL", "") or "").strip()
    if not refresh_url:
        ttl_raw = str(source.get("HERMES_AUTH_LOCAL_TTL_HOURS", "8") or "8").strip()
        try:
            ttl = max(1, int(ttl_raw))
        except ValueError:
            ttl = 8
        return LocalRefreshBackend(ttl_hours=ttl)
    timeout_raw = str(source.get("HERMES_AUTH_TIMEOUT", "10") or "10").strip()
    try:
        timeout_seconds = max(1.0, float(timeout_raw))
    except ValueError:
        timeout_seconds = 10.0
    return HttpRefreshBackend(
        refresh_url=refresh_url,
        timeout_seconds=timeout_seconds,
        auth_header_name=str(source.get("HERMES_AUTH_HEADER", "Authorization") or "Authorization").strip() or "Authorization",
        extra_secret=str(source.get("HERMES_AUTH_SECRET", "") or "").strip(),
        extra_secret_header=str(source.get("HERMES_AUTH_SECRET_HEADER", "X-Hermes-Auth-Secret") or "X-Hermes-Auth-Secret").strip() or "X-Hermes-Auth-Secret",
    )
