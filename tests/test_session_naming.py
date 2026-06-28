from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.session.session_manager import SessionManager
from src.storage.database import Database


class FakeConfig:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {
            "feedback_mode": "both",
            "feedback_voice": "",
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def get_all(self) -> dict[str, Any]:
        return dict(self.values)

    def update(self, updates: dict[str, Any]) -> None:
        self.values.update(updates)


class FakeHermes:
    def __init__(self) -> None:
        self.sessions: list[dict[str, Any]] = []
        self.renamed: list[Tuple[str, str]] = []

    def create_session(self, name: str) -> dict[str, Any]:
        remote_id = f"remote-{len(self.sessions) + 1}"
        self.sessions.append({"session": {"id": remote_id, "name": name}})
        return self.sessions[-1]

    def rename_session(self, remote_id: str, new_name: str) -> bool:
        self.renamed.append((remote_id, new_name))
        return True

    def send_message(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"response": "ok", "speak": False, "latencyMs": 0, "sessionId": "x"}

    def health(self) -> bool:
        return True


class FakeTts:
    def update_settings(self, *args: Any, **kwargs: Any) -> None:
        return None

    def say(self, text: str) -> None:
        return None

    def is_speaking(self) -> bool:
        return False


class FakeAudio:
    def get_devices(self) -> list[dict[str, Any]]:
        return []

    def create_stream(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def record_command(self, *args: Any, **kwargs: Any) -> Any:
        import numpy as np
        return np.zeros((0,), dtype="float32")

    def play_earcon(self, *args: Any, **kwargs: Any) -> None:
        return None

    def get_rms(self, audio: Any) -> float:
        return 0.0


def build_manager(tmp_path: Path) -> SessionManager:
    db = Database(tmp_path / "test.sqlite")
    return SessionManager(db)


def build_bridge(tmp_path: Path) -> tuple[Any, SessionManager, FakeHermes]:
    from src.api.webview_bridge import WebviewBridge

    db = Database(tmp_path / "test.sqlite")
    manager = SessionManager(db)
    hermes = FakeHermes()
    config = FakeConfig()
    audio = FakeAudio()
    tts = FakeTts()
    bridge = WebviewBridge(config, manager, hermes, audio, wakeword=None, tts=tts)
    return bridge, manager, hermes


def test_create_session_normalizes_name_and_marks_generic_as_system(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    session_id = manager.create_session("  new   session  ", remote_session_id="remote-x")
    session = manager.get_session(session_id)
    assert session is not None
    assert session["name"] == "new session"
    assert session["title_source"] == "system"


def test_rename_session_locks_title_as_manual(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    session_id = manager.create_session("New Session", remote_session_id="remote-x")
    assert manager.rename_session(session_id, "My Custom Title") is True
    session = manager.get_session(session_id)
    assert session is not None
    assert session["name"] == "My Custom Title"
    assert session["title_source"] == "manual"


def test_rename_session_rejects_empty_name(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    session_id = manager.create_session("New Session", remote_session_id="remote-x")
    assert manager.rename_session(session_id, "   ") is False


def test_auto_title_generates_from_first_message(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    session_id = manager.create_session("New Session", remote_session_id="remote-x")
    title = manager.auto_title_session(session_id, "Can you help me debug the wake word issue on Windows?")
    assert title == "Debug the wake word issue on Windows"
    session = manager.get_session(session_id)
    assert session is not None
    assert session["name"] == "Debug the wake word issue on Windows"
    assert session["title_source"] == "auto"


def test_auto_title_strips_conversational_prefixes_in_english(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    title = manager.build_auto_title("Can you help me debug the wake word issue on Windows?")
    assert title == "Debug the wake word issue on Windows"


def test_auto_title_strips_conversational_prefixes_in_spanish(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    title = manager.build_auto_title("Por favor ayúdame a configurar los atajos globales para Discord")
    assert title == "Configurar los atajos globales para Discord"


def test_auto_title_strips_prefixes_with_commas(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    english_title = manager.build_auto_title("Can you help me, debug the wake word issue?")
    spanish_title = manager.build_auto_title("Por favor, ayúdame a revisar la configuración de audio")
    assert english_title == "Debug the wake word issue"
    assert spanish_title == "Revisar la configuración de audio"


def test_auto_title_keeps_spanish_intent_when_not_requesting_help(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    title = manager.build_auto_title("Quiero que me expliques OAuth paso a paso")
    assert title == "Quiero que me expliques OAuth paso a paso"


def test_auto_title_does_not_overwrite_existing_messages(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    session_id = manager.create_session("New Session", remote_session_id="remote-x")
    # Add an existing user message
    manager.add_message(session_id, "user", "previous question", "voice", "success")
    title = manager.auto_title_session(session_id, "Help me debug the wake word")
    assert title is None
    session = manager.get_session(session_id)
    assert session is not None
    assert session["name"] == "New Session"
    assert session["title_source"] == "system"


def test_auto_title_does_not_overwrite_manual_rename(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    session_id = manager.create_session("New Session", remote_session_id="remote-x")
    assert manager.rename_session(session_id, "My Custom Title") is True
    # Even after a new message arrives, auto-title should be blocked
    title = manager.auto_title_session(session_id, "Help me debug the wake word")
    assert title is None
    session = manager.get_session(session_id)
    assert session is not None
    assert session["name"] == "My Custom Title"
    assert session["title_source"] == "manual"


def test_send_message_renames_existing_remote_session_on_first_real_message(tmp_path: Path) -> None:
    bridge, manager, hermes = build_bridge(tmp_path)
    # Pre-create a session with a remote_id
    session_id = manager.create_session("New Session", remote_session_id="remote-1")

    # Send a real voice message
    result = bridge.send_message("Help me debug the wake word", source="voice")

    assert result.get("success") is True
    # The local session should now have the auto-title
    session = manager.get_session(session_id)
    assert session is not None
    assert session["name"] == "Debug the wake word"
    # The remote session should have been renamed
    assert ("remote-1", "Debug the wake word") in hermes.renamed


def test_send_message_uses_generated_title_when_remote_session_missing(tmp_path: Path) -> None:
    bridge, manager, hermes = build_bridge(tmp_path)
    # Create a session WITHOUT a remote_session_id
    session_id = manager.create_session("New Session")

    # Send a real voice message
    result = bridge.send_message("Help me debug the wake word", source="voice")

    assert result.get("success") is True
    session = manager.get_session(session_id)
    assert session is not None
    assert session["name"] == "Debug the wake word"
    # The local session should now have a remote_session_id
    assert session.get("remote_session_id") is not None


def test_send_message_ignores_system_messages_for_auto_title(tmp_path: Path) -> None:
    bridge, manager, hermes = build_bridge(tmp_path)
    session_id = manager.create_session("New Session", remote_session_id="remote-1")

    # Send a system message - should NOT trigger auto-title
    result = bridge.send_message("system health check", source="system")

    assert result.get("success") is True
    session = manager.get_session(session_id)
    assert session is not None
    assert session["name"] == "New Session"
    assert session["title_source"] == "system"
    assert hermes.renamed == []


def test_send_message_ignores_hidden_system_prefix(tmp_path: Path) -> None:
    bridge, manager, hermes = build_bridge(tmp_path)
    session_id = manager.create_session("New Session", remote_session_id="remote-1")

    # Send a message with [SYSTEM: prefix - should NOT trigger auto-title
    result = bridge.send_message("[SYSTEM: internal event]", source="voice")

    assert result.get("success") is True
    session = manager.get_session(session_id)
    assert session is not None
    assert session["name"] == "New Session"
    assert session["title_source"] == "system"
