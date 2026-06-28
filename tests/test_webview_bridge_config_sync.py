from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.api.webview_bridge import WebviewBridge


class FakeConfig:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {
            "hotkey": "ctrl+shift+h",
            "visual_hotkey": "ctrl+shift+v",
            "mic_device": None,
            "mic_device_name": "",
            "mic_device_hostapi": None,
            "overlay_enabled": True,
            "overlay_mode": "mini",
            "overlay_x": None,
            "overlay_y": None,
            "feedback_mode": "both",
            "feedback_voice": "",
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def get_all(self) -> dict[str, Any]:
        return dict(self.values)

    def update(self, updates: dict[str, Any]) -> None:
        self.values.update(updates)


class FakeSessionManager:
    def get_active_session_id(self) -> str:
        return "session-1"

    def get_active_session(self) -> Optional[dict[str, Any]]:
        return None

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        return None

    def create_session(self, name: str, remote_session_id: Optional[str] = None) -> str:
        return "new-id"

    def switch_session(self, session_id: str) -> bool:
        return True

    def delete_session(self, session_id: str) -> None:
        return None

    def rename_session(self, session_id: str, new_name: str) -> bool:
        return True

    def get_sessions(self) -> list[dict[str, Any]]:
        return []

    def add_message(self, *args: Any, **kwargs: Any) -> str:
        return "msg-id"

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        return []

    def save_vps_token(self, *args: Any) -> None:
        return None

    def get_vps_token(self, *args: Any) -> Optional[str]:
        return None


class FakeHermes:
    def health(self) -> bool:
        return True

    def create_session(self, name: str) -> dict[str, Any]:
        return {"session": {"id": "remote-x", "name": name}}

    def send_message(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"response": "ok", "speak": False, "latencyMs": 0}

    def rename_session(self, remote_id: str, new_name: str) -> bool:
        return True

    def delete_session(self, remote_id: str) -> None:
        return None


class FakeTts:
    def update_settings(self, mode: str, voice: str) -> None:
        return None

    def say(self, text: str) -> None:
        return None


class FakeAudio:
    def __init__(self) -> None:
        self.devices: list[dict[str, Any]] = [
            {"index": 2, "name": "USB Mic", "hostapi": 7, "usable": True},
            {"index": 3, "name": "Headset Mic", "hostapi": 9, "usable": True},
        ]

    def get_devices(self) -> list[dict[str, Any]]:
        return list(self.devices)


class FakeTray:
    def __init__(self) -> None:
        self.audio_devices: list[dict[str, Any]] = []
        self.current_mic: Optional[Tuple[Any, str]] = None
        self.refresh_count = 0
        self.shortcut_display = ""
        self.recent_activity: list[str] = []

    def set_audio_devices(self, devices: list[dict[str, Any]]) -> None:
        self.audio_devices = list(devices)

    def set_current_mic(self, index: Any, name: str = "Default") -> None:
        self.current_mic = (index, name)

    def set_status(self, connected: bool) -> None:
        return None

    def notify(self, title: str, message: str) -> None:
        return None

    def set_shortcut_display(self, shortcut: str) -> None:
        self.shortcut_display = shortcut

    def update_quick_commands(self, commands: list[dict[str, Any]]) -> None:
        return None

    def set_recent_activity(self, items: list[str]) -> None:
        self.recent_activity = list(items)

    def _refresh(self) -> None:
        self.refresh_count += 1


class FakeVoiceLoop:
    def __init__(self) -> None:
        self.restart_requests = 0
        self.is_paused = False

    def request_stream_restart(self) -> None:
        self.restart_requests += 1


class FakeShortcutManager:
    def __init__(self) -> None:
        self.stop_calls = 0
        self.start_calls: list[tuple[str, Optional[str]]] = []
        self.error_handler = None

    def set_registration_error_handler(self, handler: Any) -> None:
        self.error_handler = handler

    def stop(self) -> None:
        self.stop_calls += 1

    def start(self, hotkey: str, visual_hotkey: Optional[str] = None) -> None:
        self.start_calls.append((hotkey, visual_hotkey))


class FakeOverlay:
    def __init__(self) -> None:
        self.mode = "mini"
        self.enabled = True
        self.position: tuple[Any, Any] = (None, None)
        self.visible = False

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def set_position(self, x: Any, y: Any) -> None:
        self.position = (x, y)

    def is_visible(self) -> bool:
        return self.visible


class FakeWindow:
    def __init__(self) -> None:
        self.scripts: list[str] = []

    def evaluate_js(self, script: str) -> None:
        self.scripts.append(script)


def build_bridge() -> tuple[WebviewBridge, FakeConfig, FakeTray, FakeVoiceLoop, FakeWindow, FakeShortcutManager]:
    config = FakeConfig()
    tray = FakeTray()
    voice_loop = FakeVoiceLoop()
    window = FakeWindow()
    shortcuts = FakeShortcutManager()
    bridge = WebviewBridge(
        config,
        FakeSessionManager(),
        FakeHermes(),
        FakeAudio(),
        wakeword=None,
        tts=FakeTts(),
        shortcut_manager=shortcuts,
    )
    bridge.set_tray(tray)
    bridge.set_voice_loop(voice_loop)
    bridge.set_window(window)
    return bridge, config, tray, voice_loop, window, shortcuts


def test_update_config_refreshes_mic_runtime_and_tray() -> None:
    bridge, config, tray, voice_loop, window, _shortcuts = build_bridge()

    updated = bridge.update_config({"mic_device": 2})

    assert updated is True
    assert config.values["mic_device"] == 2
    assert config.values["mic_device_name"] == "USB Mic"
    assert config.values["mic_device_hostapi"] == 7
    assert tray.current_mic == (2, "USB Mic")
    assert tray.refresh_count == 1
    assert voice_loop.restart_requests == 1
    assert window.scripts == [
        "window.dispatchEvent(new CustomEvent('hermes_config_updated'))"
    ]


def test_update_config_keeps_selected_metadata_when_mic_changes_with_name() -> None:
    bridge, config, tray, voice_loop, _window, _shortcuts = build_bridge()

    updated = bridge.update_config(
        {"mic_device": 3, "mic_device_name": "Headset Mic", "mic_device_hostapi": 9}
    )

    assert updated is True
    assert config.values["mic_device"] == 3
    assert config.values["mic_device_name"] == "Headset Mic"
    assert config.values["mic_device_hostapi"] == 9
    assert tray.current_mic == (3, "Headset Mic")
    assert tray.refresh_count == 1
    assert voice_loop.restart_requests == 1


def test_update_config_handles_default_mic_selection() -> None:
    """When mic_device is set to None (default), the tray should still be refreshed."""
    bridge, config, tray, voice_loop, _window, _shortcuts = build_bridge()

    # First set to a specific device
    bridge.update_config({"mic_device": 2})
    assert config.values["mic_device_name"] == "USB Mic"
    assert tray.refresh_count == 1

    # Now reset to default
    updated = bridge.update_config({"mic_device": None})

    assert updated is True
    assert config.values["mic_device"] is None
    assert tray.current_mic == (None, "Default")
    assert tray.refresh_count == 2
    assert voice_loop.restart_requests == 2


def test_update_config_restarts_shortcuts_and_updates_tray_hotkey() -> None:
    bridge, config, tray, _voice_loop, _window, shortcuts = build_bridge()

    updated = bridge.update_config({"hotkey": "ctrl+alt+h"})

    assert updated is True
    assert config.values["hotkey"] == "ctrl+alt+h"
    assert tray.shortcut_display == "ctrl+alt+h"
    assert shortcuts.stop_calls == 1
    assert shortcuts.start_calls == [("ctrl+alt+h", "ctrl+shift+v")]


def test_shortcut_registration_error_dispatches_error_toast() -> None:
    _bridge, _config, _tray, _voice_loop, window, shortcuts = build_bridge()

    assert shortcuts.error_handler is not None
    shortcuts.error_handler(
        "trigger",
        "CTRL+ALT+H",
        "RegisterHotKey failed for 'CTRL+ALT+H' (Win32 error 1409)",
    )

    assert len(window.scripts) == 1
    assert "hermes_toast" in window.scripts[0]
    assert "Hotkey registration failed" in window.scripts[0]
    assert "CTRL+ALT+H" in window.scripts[0]


def test_record_activity_syncs_recent_items_to_tray() -> None:
    bridge, _config, tray, _voice_loop, _window, _shortcuts = build_bridge()

    bridge._record_activity("voice", "Primera actividad", "success")
    bridge._record_activity("command", "Segunda actividad", "success")

    assert tray.recent_activity == ["Segunda actividad", "Primera actividad"]


def test_set_overlay_syncs_initial_overlay_config_into_runtime() -> None:
    bridge, _config, _tray, _voice_loop, _window, _shortcuts = build_bridge()
    overlay = FakeOverlay()

    bridge.set_overlay(overlay)

    runtime = bridge.get_runtime_state()["runtime"]
    assert overlay.mode == "mini"
    assert overlay.enabled is True
    assert overlay.position == (None, None)
    assert runtime["overlay_mode"] == "mini"
    assert runtime["overlay_enabled"] is True
    assert runtime["overlay_visible"] is False


def test_update_config_updates_overlay_state_and_runtime_snapshot() -> None:
    bridge, config, _tray, _voice_loop, _window, _shortcuts = build_bridge()
    overlay = FakeOverlay()
    bridge.set_overlay(overlay)

    updated = bridge.update_config({
        "overlay_mode": "normal",
        "overlay_enabled": False,
        "overlay_x": 640,
        "overlay_y": 380,
    })

    runtime = bridge.get_runtime_state()["runtime"]
    assert updated is True
    assert config.values["overlay_mode"] == "normal"
    assert config.values["overlay_enabled"] is False
    assert config.values["overlay_x"] == 640
    assert config.values["overlay_y"] == 380
    assert overlay.mode == "normal"
    assert overlay.enabled is False
    assert overlay.position == (640, 380)
    assert runtime["overlay_mode"] == "normal"
    assert runtime["overlay_enabled"] is False
    assert runtime["overlay_x"] == 640
    assert runtime["overlay_y"] == 380


def test_runtime_overlay_visibility_respects_overlay_enabled_flag() -> None:
    bridge, _config, _tray, _voice_loop, _window, _shortcuts = build_bridge()

    bridge.set_runtime_listening_state("listening", "Wake detected")
    runtime = bridge.get_runtime_state()["runtime"]
    assert runtime["overlay_visible"] is True
    assert runtime["overlay_detail"] == "Wake detected"

    bridge.update_config({"overlay_enabled": False})
    bridge.set_runtime_listening_state("speaking", "Respuesta lista")
    runtime = bridge.get_runtime_state()["runtime"]
    assert runtime["overlay_enabled"] is False
    assert runtime["overlay_visible"] is False
    assert runtime["overlay_detail"] == "Respuesta lista"
