from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_voice_bridge.core.config import ConfigService
from hermes_voice_bridge.core.events import EventBus
from hermes_voice_bridge.core.session import HttpRefreshBackend, LocalRefreshBackend, SessionManager, SessionRecord
from hermes_voice_bridge.core.state import AppStateStore
from hermes_voice_bridge.platform.windows import SecureValueStore
from hermes_voice_bridge.storage.cache import JsonRuntimeSignalStore, JsonRuntimeStateStore
from hermes_voice_bridge.storage.repositories import JsonSessionRepository


def test_event_bus_publish_and_subscribe():
    bus = EventBus()
    received = []

    bus.subscribe("shortcut.updated", lambda event: received.append((event.name, event.payload["value"])))
    bus.publish("shortcut.updated", value="ctrl+shift+space")

    assert received == [("shortcut.updated", "ctrl+shift+space")]


def test_session_manager_restores_saved_session(tmp_path):
    repo = JsonSessionRepository(tmp_path / "session.json")
    store = SecureValueStore(tmp_path / "session.secrets")
    bus = EventBus()
    app_state = AppStateStore()
    manager = SessionManager(repo, store, bus, app_state, LocalRefreshBackend())

    events = []
    bus.subscribe("session.restored", lambda event: events.append(event.name))

    record = SessionRecord(
        access_token="abc123",
        refresh_token="refresh-me",
        user_id="cesar",
        display_name="César",
        expires_at="2999-01-01T00:00:00+00:00",
        remember_me=True,
    )
    manager.save(record)
    restored = manager.restore()

    assert restored is not None
    assert restored.user_id == "cesar"
    assert app_state.state.session.authenticated is True
    assert app_state.state.session.display_name == "César"
    assert "session.restored" in events


def test_session_manager_logout_clears_persisted_state(tmp_path):
    repo = JsonSessionRepository(tmp_path / "session.json")
    store = SecureValueStore(tmp_path / "session.secrets")
    bus = EventBus()
    app_state = AppStateStore()
    manager = SessionManager(repo, store, bus, app_state, LocalRefreshBackend())

    manager.save(SessionRecord(access_token="token", user_id="u1", expires_at="2999-01-01T00:00:00+00:00"))
    manager.logout()

    assert repo.load() is None
    assert store.get_secret("access_token") == ""
    assert app_state.state.session.authenticated is False


def test_session_manager_refreshes_expired_session_with_backend(tmp_path):
    repo = JsonSessionRepository(tmp_path / "session.json")
    store = SecureValueStore(tmp_path / "session.secrets")
    bus = EventBus()
    app_state = AppStateStore()
    manager = SessionManager(repo, store, bus, app_state, LocalRefreshBackend(ttl_hours=4))

    manager.save(
        SessionRecord(
            access_token="old-token",
            refresh_token="refresh-me",
            user_id="cesar",
            display_name="César",
            expires_at="2000-01-01T00:00:00+00:00",
            remember_me=True,
        )
    )

    restored = manager.restore()

    assert restored is not None
    assert restored.metadata["refresh_backend"] == "local"
    assert restored.metadata["refreshed"] is True
    assert app_state.state.session.authenticated is True


def test_http_refresh_backend_uses_remote_payload(monkeypatch):
    backend = HttpRefreshBackend("https://example.com/refresh", timeout_seconds=3.0, extra_secret="secret")
    record = SessionRecord(
        access_token="old-token",
        refresh_token="refresh-token",
        token_type="Bearer",
        user_id="cesar",
        display_name="César",
        remember_me=True,
        expires_at="2000-01-01T00:00:00+00:00",
        metadata={"origin": "test"},
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "access_token": "new-token",
                    "refresh_token": "new-refresh",
                    "expires_at": "2999-01-01T00:00:00+00:00",
                    "display_name": "César Updated",
                    "metadata": {"source": "remote"},
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout=0):
        assert request.full_url == "https://example.com/refresh"
        assert request.headers["Authorization"] == "Bearer old-token"
        assert request.headers["X-hermes-auth-secret"] == "secret"
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["refresh_token"] == "refresh-token"
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    refreshed = backend.refresh(record)

    assert refreshed.access_token == "new-token"
    assert refreshed.refresh_token == "new-refresh"
    assert refreshed.display_name == "César Updated"
    assert refreshed.metadata["source"] == "remote"
    assert refreshed.metadata["refresh_backend"] == "http"


def test_config_service_roundtrip(tmp_path):
    env_path = tmp_path / "voice.env"
    service = ConfigService(env_path)

    service.save({"HERMES_HOTKEY": "ctrl+shift+space", "HERMES_FEEDBACK_MODE": "both"})
    data = service.load()

    assert data["HERMES_HOTKEY"] == "ctrl+shift+space"
    assert data["HERMES_FEEDBACK_MODE"] == "both"


def test_runtime_state_store_roundtrip(tmp_path):
    store = JsonRuntimeStateStore(tmp_path / "runtime_state.json")
    payload = {
        "badge": {"state": "ready"},
        "summary": {"tray_running": True, "bridge_running": True},
    }

    store.save(payload)

    assert store.load() == payload


def test_runtime_signal_store_increments_sequence(tmp_path):
    store = JsonRuntimeSignalStore(tmp_path / "runtime_signal.json")

    first = store.emit(kind="listening", title="● Listening…")
    second = store.emit(kind="transcribing", title="Transcribing…", detail="Local Whisper processing")

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert store.load()["kind"] == "transcribing"
