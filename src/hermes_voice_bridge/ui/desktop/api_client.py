from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class ApiError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 2.5) -> Dict[str, Any]:
        data = None
        headers = {"Accept": "application/json", "Cache-Control": "no-cache"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(f"{self.base_url}{path}", data=data, method=method.upper(), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            raise ApiError(body or str(exc)) from exc
        except Exception as exc:
            raise ApiError(str(exc)) from exc

    def get(self, path: str, timeout: float = 2.5) -> Dict[str, Any]:
        return self.request("GET", path, timeout=timeout)

    def post(self, path: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 8.0) -> Dict[str, Any]:
        return self.request("POST", path, payload=payload, timeout=timeout)
