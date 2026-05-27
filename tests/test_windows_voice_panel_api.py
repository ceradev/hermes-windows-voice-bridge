from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from hermes_voice_bridge.core.session import build_session_manager
from hermes_voice_bridge.storage.cache import JsonRuntimeSignalStore, JsonRuntimeStateStore
import windows_hermes_voice_panel_api as panel_api


def _patch_state_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(panel_api, "VOICE_ENV", tmp_path / "voice.env")
    monkeypatch.setattr(panel_api, "CONTROL_FILE", tmp_path / "voice.control.json")
    monkeypatch.setattr(panel_api, "LOG_DIR", tmp_path)
    monkeypatch.setattr(panel_api, "RUNTIME_STATE_FILE", tmp_path / "runtime_state.json")
    monkeypatch.setattr(panel_api, "RUNTIME_SIGNAL_FILE", tmp_path / "runtime_signal.json")
    monkeypatch.setattr(panel_api, "RUNTIME_STATE_STORE", JsonRuntimeStateStore(panel_api.RUNTIME_STATE_FILE))
    monkeypatch.setattr(panel_api, "RUNTIME_SIGNAL_STORE", JsonRuntimeSignalStore(panel_api.RUNTIME_SIGNAL_FILE))
    monkeypatch.setattr(panel_api, "SESSION_MANAGER", build_session_manager(tmp_path))


def test_safe_env_hides_missing_values():
    env = panel_api._safe_env({"HERMES_HOTKEY": "ctrl+shift+h"})

    assert env["hotkey"] == "ctrl+shift+h"
    assert env["feedback_mode"] == "(default)"
    assert env["wake_phrases"] == "(default)"
    assert env["persist_session"] == "1"
    assert env["endpoint"] == ""
    assert env["auth_refresh_url"] == ""
    assert env["auth_timeout"] == "10"


def test_semantic_state_matches_expected_priority():
    assert panel_api._semantic_state(True, True, True, "") == (
        "paused",
        "Paused",
        "Control state shared between tray and panel",
    )
    assert panel_api._semantic_state(False, False, True, "error") == (
        "warn",
        "Listening",
        "Bridge is up, but the latest log entry suggests attention",
    )
    assert panel_api._semantic_state(False, False, False, "") == (
        "stopped",
        "Stopped",
        "Start the tray or relaunch the bridge",
    )


def test_build_snapshot_returns_expected_top_level_keys(tmp_path, monkeypatch):
    _patch_state_paths(tmp_path, monkeypatch)

    snapshot = panel_api._build_snapshot()

    assert "badge" in snapshot
    assert "summary" in snapshot
    assert "status_lines" in snapshot
    assert isinstance(snapshot["status_lines"], list)
    assert snapshot["summary"]["paused"] is False


def test_apply_runtime_snapshot_promotes_tray_owned_state():
    base = {
        "generated_at": "older",
        "version": "0.2.0",
        "badge": {"state": "stopped"},
        "badge_label": "Stopped",
        "summary": {"tray_running": False, "bridge_running": False},
        "control": {"paused": False},
        "processes": {"tray": [], "bridge": []},
    }
    runtime = {
        "generated_at": "newer",
        "version": "0.3.0",
        "badge": {"state": "ready", "label": "READY"},
        "badge_label": "Ready",
        "summary": {"tray_running": True, "bridge_running": True, "mode": "listening"},
        "control": {"paused": False},
        "runtime_signal": {"sequence": 2, "kind": "transcribing"},
        "processes": {"tray": [{"pid": 1}], "bridge": [{"pid": 2}], "api": [{"pid": 3}]},
        "runtime": {"lifecycle": "running"},
        "lifecycle": "running",
    }

    merged = panel_api._apply_runtime_snapshot(base, runtime)

    assert merged["generated_at"] == "newer"
    assert merged["badge"]["state"] == "ready"
    assert merged["summary"]["bridge_running"] is True
    assert merged["processes"]["api"][0]["pid"] == 3
    assert merged["runtime_signal"]["kind"] == "transcribing"
    assert merged["lifecycle"] == "running"


def test_build_snapshot_uses_runtime_file_when_present(tmp_path, monkeypatch):
    _patch_state_paths(tmp_path, monkeypatch)
    panel_api.RUNTIME_STATE_FILE.write_text(
        '{"generated_at":"2026-05-24T21:00:00+00:00","badge":{"state":"ready","label":"READY"},"badge_label":"Ready","summary":{"tray_running":true,"bridge_running":true,"api_running":true,"health":"ready","mode":"listening"},"control":{"paused":false},"runtime_signal":{"sequence":4,"kind":"responding"},"processes":{"tray":[{"pid":11}],"bridge":[{"pid":22}],"api":[{"pid":33}]},"runtime":{"services":{"bridge":{"state":"running"}}},"lifecycle":"running"}',
        encoding="utf-8",
    )

    snapshot = panel_api._build_snapshot()

    assert snapshot["badge"]["state"] == "ready"
    assert snapshot["summary"]["api_running"] is True
    assert snapshot["processes"]["api"][0]["pid"] == 33
    assert snapshot["runtime_signal"]["kind"] == "responding"
    assert snapshot["runtime"]["services"]["bridge"]["state"] == "running"


def test_normalize_config_updates_maps_known_fields():
    updates = panel_api._normalize_config_updates({
        "mic_device": "3",
        "wake_phrases": "hermes, oye hermes",
        "feedback_mode": "both",
        "persist_session": "1",
        "endpoint": "http://127.0.0.1:8644/webhooks/voice",
        "auth_refresh_url": "https://example.com/auth/refresh",
        "auth_timeout": "12",
        "unknown": "ignore me",
    })

    assert updates["HERMES_MIC_DEVICE"] == "3"
    assert updates["HERMES_WAKE_PHRASES"] == "hermes, oye hermes"
    assert updates["HERMES_FEEDBACK_MODE"] == "both"
    assert updates["HERMES_PERSIST_SESSION"] == "1"
    assert updates["HERMES_WEBHOOK_URL"] == "http://127.0.0.1:8644/webhooks/voice"
    assert updates["HERMES_AUTH_REFRESH_URL"] == "https://example.com/auth/refresh"
    assert updates["HERMES_AUTH_TIMEOUT"] == "12"
    assert "unknown" not in updates


def test_normalize_config_updates_persists_selected_mic_identity(monkeypatch):
    monkeypatch.setattr(
        panel_api.AUDIO_SERVICE,
        "get_devices",
        lambda: [
            {"index": 3, "name": "USB Headset", "hostapi": 2, "usable": True},
        ],
    )

    updates = panel_api._normalize_config_updates({"mic_device": "3"})

    assert updates["HERMES_MIC_DEVICE"] == "3"
    assert updates["HERMES_MIC_DEVICE_NAME"] == "USB Headset"
    assert updates["HERMES_MIC_DEVICE_HOSTAPI"] == "2"


def test_save_and_logout_persisted_session_roundtrip(tmp_path, monkeypatch):
    _patch_state_paths(tmp_path, monkeypatch)

    record = panel_api._save_persisted_session(
        {
            "access_token": "abc123",
            "refresh_token": "refresh456",
            "user_id": "cesar",
            "display_name": "César",
            "expires_at": "2999-01-01T00:00:00+00:00",
            "remember_me": "1",
        }
    )
    restored = panel_api.SESSION_MANAGER.restore()

    assert record.user_id == "cesar"
    assert restored is not None
    assert restored.display_name == "César"

    refreshed = panel_api._refresh_persisted_session()
    assert refreshed.metadata.get("refreshed") is True

    panel_api._logout_persisted_session(reason="manual")

    assert panel_api.SESSION_MANAGER.restore() is None


def test_repair_autostart_invokes_install_script(tmp_path, monkeypatch):
    script = tmp_path / "scripts" / "install_autostart.ps1"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("Write-Host done", encoding="utf-8")
    monkeypatch.setattr(panel_api, "BASE_DIR", tmp_path)

    calls = []

    class Result:
        returncode = 0
        stdout = "autostart repaired"
        stderr = ""

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return Result()

    monkeypatch.setattr(panel_api.subprocess, "run", fake_run)

    ok, message = panel_api._repair_autostart()

    assert ok is True
    assert "autostart repaired" in message.lower()
    assert calls[0][0][0] == "powershell.exe"
    assert calls[0][0][5] == str(script)
