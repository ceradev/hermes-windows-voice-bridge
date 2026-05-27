from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import windows_hermes_voice as bridge


def test_float_env_falls_back_on_invalid_value(monkeypatch):
    monkeypatch.setenv("HERMES_BLOCK_SECONDS", "bad")
    assert bridge.float_env("HERMES_BLOCK_SECONDS", 0.25) == 0.25


def test_int_env_falls_back_on_invalid_value(monkeypatch):
    monkeypatch.setenv("HERMES_MAX_COMMAND_SECONDS", "bad")
    assert bridge.int_env("HERMES_MAX_COMMAND_SECONDS", 12) == 12


def test_startup_status_lines_report_hotkey_and_feedback():
    cfg = bridge.Config(
        webhook_url="http://example.com",
        webhook_secret="secret",
        model_size="base",
        language="es",
        wake_phrases=["hermes", "oye hermes"],
        energy_threshold=0.008,
        silence_rms=0.008,
        device=None,
        device_name="",
        device_hostapi=None,
        hotkey="ctrl+shift+h",
        feedback_mode="both",
        feedback_voice="en-US-GuyNeural",
        block_seconds=0.25,
        wake_window_seconds=2.0,
        silence_timeout_seconds=0.85,
        max_command_seconds=12.0,
    )

    lines = bridge.startup_status_lines(cfg, hotkey_enabled=True)

    assert any("Hotkey: ctrl+shift+h (active)" in line for line in lines)
    assert any("Feedback: both" in line for line in lines)
    assert any("Wake control:" in line for line in lines)


def test_extract_final_response_prefers_common_json_fields():
    body = '{"response":"Hola!","text":"ignored","final_response":"also ignored"}'
    assert bridge.extract_final_response(body) == "also ignored"


def test_extract_final_response_falls_back_to_plain_text():
    assert bridge.extract_final_response("Respuesta directa") == "Respuesta directa"


def test_prepare_tts_text_preserves_sentence_pauses():
    text = "**Hola**\n- Primero\n- Segundo\n\n[link](https://example.com)"
    assert bridge.prepare_tts_text(text) == "Hola. Primero. Segundo. link"


def test_chunk_tts_text_splits_long_response_on_sentence_boundaries():
    text = (
        "Primera frase bastante larga para probar el troceo. "
        "Segunda frase también larga para ver cómo se parte el texto. "
        "Tercera frase para cerrar."
    )
    chunks = bridge.chunk_tts_text(text, max_chars=60)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 60 for chunk in chunks)
    assert " ".join(chunks).startswith("Primera frase")


def test_post_json_retries_transient_errors_before_succeeding(monkeypatch):
    attempts = []
    sleeps = []

    class FakeResponse:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"ok"

    def fake_urlopen(req, timeout=None):
        attempts.append(timeout)
        if len(attempts) < 3:
            raise bridge.urllib.error.URLError("temporary network issue")
        return FakeResponse()

    monkeypatch.setattr(bridge.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(bridge.time, "sleep", lambda seconds: sleeps.append(seconds))

    status, body = bridge.post_json(
        "http://example.com/webhook",
        "secret",
        {"text": "hola"},
        timeout_seconds=1,
        attempts=3,
        retry_base_delay=0.1,
    )

    assert status == 202
    assert body == "ok"
    assert len(attempts) == 3
    assert sleeps == [0.1, 0.2]


def test_handle_transcribed_command_recovers_from_submission_error(monkeypatch):
    calls = []

    class FakeFeedback:
        def pulse(self, text):
            calls.append(("pulse", text))

        def say(self, text):
            calls.append(("say", text))

    def boom_submit(cfg, command_text):
        raise RuntimeError("boom")

    monkeypatch.setattr(bridge, "submit_command", boom_submit)

    result = bridge.handle_transcribed_command(object(), FakeFeedback(), "abre el navegador")

    assert result is False
    assert ("pulse", "Mensaje recibido") in calls
    assert ("say", "No se pudo enviar") in calls


def test_post_json_propagates_extra_headers(monkeypatch):
    captured = []

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self): return b'"ok"'

    def fake_urlopen(req, timeout=None):
        captured.append(req.headers)
        return FakeResponse()

    monkeypatch.setattr(bridge.urllib.request, "urlopen", fake_urlopen)

    bridge.post_json(
        "http://example.com/webhook",
        "secret",
        {"text": "hola"},
        extra_headers={"X-Request-ID": "cesar", "X-Custom": "value"},
    )

    headers = captured[0]
    assert headers["X-request-id"] == "cesar"
    assert headers["X-custom"] == "value"


def test_submit_command_includes_session_user_id_and_request_header(monkeypatch, tmp_path):
    from hermes_voice_bridge.core.events import EventBus
    from hermes_voice_bridge.core.session import SessionRecord, SessionManager
    from hermes_voice_bridge.core.session.auth_backend import LocalRefreshBackend
    from hermes_voice_bridge.core.state import AppStateStore
    from hermes_voice_bridge.platform.windows import SecureValueStore
    from hermes_voice_bridge.storage.repositories import JsonSessionRepository

    # Set up a temporary session manager with a persisted record
    repo = JsonSessionRepository(tmp_path / "session.json")
    store = SecureValueStore(tmp_path / "session.secrets")
    temp_manager = SessionManager(repo, store, EventBus(), AppStateStore(), LocalRefreshBackend())
    temp_manager.save(SessionRecord(
        access_token="token",
        refresh_token="refresh",
        user_id="cesar",
        display_name="César",
        expires_at="2999-01-01T00:00:00+00:00",
        remember_me=True,
    ))
    monkeypatch.setattr(bridge, "SESSION_MANAGER", temp_manager)

    captured = []

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self): return b'"ok"'

    def fake_urlopen(req, timeout=None):
        captured.append({"url": req.full_url, "headers": dict(req.headers), "body": req.data})
        return FakeResponse()

    monkeypatch.setattr(bridge.urllib.request, "urlopen", fake_urlopen)

    cfg = bridge.Config(
        webhook_url="http://example.com/webhooks/voice",
        webhook_secret="secret",
        model_size="base",
        language="es",
        wake_phrases=["hermes"],
        energy_threshold=0.008,
        silence_rms=0.008,
        device=None,
        device_name="",
        device_hostapi=None,
        hotkey="ctrl+shift+h",
        feedback_mode="both",
        feedback_voice="",
        block_seconds=0.25,
        wake_window_seconds=2.0,
        silence_timeout_seconds=0.85,
        max_command_seconds=12.0,
    )

    status, body = bridge.submit_command(cfg, "hola hermes")

    assert status == 200
    body_json = json.loads(captured[0]["body"].decode("utf-8"))
    assert body_json["user_id"] == "cesar"
    assert captured[0]["headers"]["X-request-id"] == "cesar"
    assert body_json["text"] == "hola hermes"
    assert body_json["source"] == "windows_voice_bridge"


def test_submit_command_omits_user_id_when_no_session(monkeypatch, tmp_path):
    from hermes_voice_bridge.core.events import EventBus
    from hermes_voice_bridge.core.session import SessionManager
    from hermes_voice_bridge.core.session.auth_backend import LocalRefreshBackend
    from hermes_voice_bridge.core.state import AppStateStore
    from hermes_voice_bridge.platform.windows import SecureValueStore
    from hermes_voice_bridge.storage.repositories import JsonSessionRepository

    repo = JsonSessionRepository(tmp_path / "empty_session.json")
    store = SecureValueStore(tmp_path / "session.secrets")
    temp_manager = SessionManager(repo, store, EventBus(), AppStateStore(), LocalRefreshBackend())
    monkeypatch.setattr(bridge, "SESSION_MANAGER", temp_manager)

    captured = []

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self): return b'"ok"'

    def fake_urlopen(req, timeout=None):
        captured.append({"headers": dict(req.headers), "body": req.data})
        return FakeResponse()

    monkeypatch.setattr(bridge.urllib.request, "urlopen", fake_urlopen)

    cfg = bridge.Config(
        webhook_url="http://example.com/webhooks/voice",
        webhook_secret="secret",
        model_size="base",
        language="es",
        wake_phrases=["hermes"],
        energy_threshold=0.008,
        silence_rms=0.008,
        device=None,
        device_name="",
        device_hostapi=None,
        hotkey="ctrl+shift+h",
        feedback_mode="both",
        feedback_voice="",
        block_seconds=0.25,
        wake_window_seconds=2.0,
        silence_timeout_seconds=0.85,
        max_command_seconds=12.0,
    )

    status, body = bridge.submit_command(cfg, "hola")

    assert status == 200
    body_json = json.loads(captured[0]["body"].decode("utf-8"))
    assert "user_id" not in body_json
    assert "X-request-id" not in captured[0]["headers"]
