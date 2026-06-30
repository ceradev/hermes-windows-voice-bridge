from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config.config_service import ConfigService
from src.services.hermes.hermes_client import HermesClient, HermesClientError


class FakeConfig:
    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)


def test_webhook_send_message_signs_payload_and_parses_response() -> None:
    config = FakeConfig(
        {
            "webhook_url": "http://localhost:8644/webhooks/voice",
            "webhook_secret": "test-secret",
            "webhook_sync": True,
            "webhook_timeout": 30,
            "webhook_user_id": "cesar",
        }
    )
    client = HermesClient(config)

    captured: dict[str, Any] = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"response": "Hola desde Hermes"}).encode("utf-8")

    def fake_urlopen(req, timeout=30, context=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = req.data
        return FakeResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = client.send_message("ignored", "hola hermes", source="voice")

    body = captured["body"]
    assert captured["url"] == "http://localhost:8644/webhooks/voice"
    expected_sig = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    assert captured["headers"]["X-webhook-signature"] == expected_sig
    assert captured["headers"]["X-request-id"] == "cesar"

    payload = json.loads(body.decode("utf-8"))
    assert payload["text"] == "hola hermes"
    assert payload["event_type"] == "voice"
    assert payload["user_id"] == "cesar"

    assert result["response"] == "Hola desde Hermes"
    assert result["speak"] is True


def test_webhook_health_accepts_non_server_errors() -> None:
    config = FakeConfig(
        {
            "webhook_url": "http://localhost:8644/webhooks/voice",
            "webhook_secret": "test-secret",
        }
    )
    client = HermesClient(config)

    import urllib.error

    def fake_urlopen(req, timeout=3, context=None):
        raise urllib.error.HTTPError(req.full_url, 405, "Method Not Allowed", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        assert client.health() is True


def test_webhook_ignored_event_raises_clear_error() -> None:
    config = FakeConfig(
        {
            "webhook_url": "http://localhost:8644/webhooks/voice",
            "webhook_secret": "test-secret",
            "webhook_sync": True,
        }
    )
    client = HermesClient(config)

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"status": "ignored", "event": "voice"}).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        try:
            client.send_message("ignored", "hola", source="voice")
            raise AssertionError("expected HermesClientError")
        except HermesClientError as exc:
            assert exc.status == 422
            assert "ignored" in exc.message.lower()


def test_webhook_accepted_without_body_recovers_session_reply() -> None:
    config = FakeConfig(
        {
            "webhook_url": "http://localhost:8644/webhooks/voice",
            "webhook_secret": "test-secret",
            "webhook_sync": True,
        }
    )
    client = HermesClient(config)

    class FakeResponse:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"status": "accepted", "route": "voice", "event": "voice", "sessionId": "remote-x"}
            ).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=FakeResponse()), patch.object(
        HermesClient,
        "get_session_messages",
        return_value=[
            {"role": "user", "content": "hola"},
            {"role": "assistant", "content": "Hola desde Hermes"},
        ],
    ):
        result = client.send_message("remote-x", "hola", source="voice")

    assert result["speak"] is True
    assert result["response"] == "Hola desde Hermes"


def test_webhook_accepted_without_body_falls_back_to_api_chat() -> None:
    config = FakeConfig(
        {
            "webhook_url": "http://localhost:8644/webhooks/voice",
            "webhook_secret": "test-secret",
            "api_base_url": "http://localhost:8642",
            "api_token": "real-api-token",
            "webhook_sync": True,
        }
    )
    client = HermesClient(config)

    class FakeWebhookResponse:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"status": "accepted", "event": "voice"}).encode("utf-8")

    class FakeApiResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {"message": {"role": "assistant", "content": "Respuesta por API"}},
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout=30, context=None):
        if "webhooks" in req.full_url:
            return FakeWebhookResponse()
        return FakeApiResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen), patch.object(
        HermesClient,
        "get_session_messages",
        return_value=[],
    ):
        result = client.send_message("remote-x", "hola", source="voice")

    assert result["response"] == "Respuesta por API"
    assert result["speak"] is True


def test_webhook_create_session_uses_user_id(tmp_path: Path) -> None:
    config = FakeConfig(
        {
            "webhook_url": "http://localhost:8644/webhooks/voice",
            "webhook_secret": "test-secret",
            "webhook_user_id": "cesar",
        }
    )
    client = HermesClient(config)
    session = client.create_session("Default Session")
    assert session["session"]["id"] == "cesar"
