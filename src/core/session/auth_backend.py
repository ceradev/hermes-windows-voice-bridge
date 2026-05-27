from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from typing import Any
import urllib.request


def _future_timestamp(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


class LocalRefreshBackend:
    def __init__(self, ttl_hours: float = 12.0) -> None:
        self.ttl_hours = ttl_hours

    def refresh(self, record: Any) -> Any:
        metadata = dict(record.metadata)
        metadata.update({"refreshed": True, "refresh_backend": "local"})
        access_token = record.access_token or record.refresh_token or "local-session"
        return replace(record, access_token=access_token, expires_at=_future_timestamp(self.ttl_hours), metadata=metadata)


class HttpRefreshBackend:
    def __init__(
        self,
        refresh_url: str,
        timeout_seconds: float = 10.0,
        auth_header: str = "Authorization",
        extra_secret: str = "",
        secret_header: str = "X-Hermes-Auth-Secret",
    ) -> None:
        self.refresh_url = refresh_url
        self.timeout_seconds = timeout_seconds
        self.auth_header = auth_header
        self.extra_secret = extra_secret
        self.secret_header = secret_header

    def refresh(self, record: Any) -> Any:
        payload = {
            "refresh_token": record.refresh_token,
            "user_id": record.user_id,
            "display_name": record.display_name,
            "metadata": record.metadata,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            self.auth_header: f"{record.token_type} {record.access_token}".strip(),
        }
        if self.extra_secret:
            headers[self.secret_header] = self.extra_secret

        request = urllib.request.Request(self.refresh_url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw) if raw else {}
        if not isinstance(data, dict):
            raise ValueError("Refresh endpoint returned a non-object payload")

        metadata = dict(record.metadata)
        remote_metadata = data.get("metadata", {})
        if isinstance(remote_metadata, dict):
            metadata.update(remote_metadata)
        metadata.update({"refreshed": True, "refresh_backend": "http"})

        return replace(
            record,
            access_token=str(data.get("access_token") or record.access_token),
            refresh_token=str(data.get("refresh_token") or record.refresh_token),
            expires_at=str(data.get("expires_at") or record.expires_at),
            display_name=str(data.get("display_name") or record.display_name),
            metadata=metadata,
        )
