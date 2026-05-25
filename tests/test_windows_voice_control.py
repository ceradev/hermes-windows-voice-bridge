from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import windows_hermes_voice_control as control


def test_load_env_file_parses_trimmed_pairs(tmp_path, monkeypatch):
    env_file = tmp_path / "voice.env"
    env_file.write_text(
        "# comment\n"
        "HERMES_WEBHOOK_URL = http://example.com/webhooks/voice\n"
        "HERMES_HOTKEY='ctrl+shift+h'\n"
        "EMPTY=\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("HERMES_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("HERMES_HOTKEY", raising=False)

    values = control.load_env_file(env_file)

    assert values["HERMES_WEBHOOK_URL"] == "http://example.com/webhooks/voice"
    assert values["HERMES_HOTKEY"] == "ctrl+shift+h"
    assert os.environ["HERMES_WEBHOOK_URL"] == "http://example.com/webhooks/voice"


def test_control_state_round_trip(tmp_path):
    control_file = tmp_path / "voice.control.json"
    control.save_control_state(control_file, True)
    assert control.load_control_state(control_file) is True
    control.save_control_state(control_file, False)
    assert control.load_control_state(control_file) is False


def test_save_env_file_updates_and_removes_blank_values(tmp_path):
    env_file = tmp_path / "voice.env"
    env_file.write_text("HERMES_HOTKEY=ctrl+shift+h\nHERMES_MIC_DEVICE=2\n", encoding="utf-8")

    values = control.save_env_file(env_file, {"HERMES_MIC_DEVICE": "", "HERMES_FEEDBACK_MODE": "both"})

    text = env_file.read_text(encoding="utf-8")
    assert "HERMES_MIC_DEVICE" not in text
    assert "HERMES_FEEDBACK_MODE=both" in text
    assert values["HERMES_FEEDBACK_MODE"] == "both"


def test_parse_process_lines_separates_tray_and_bridge():
    lines = [
        "PID=123|NAME=pythonw.exe|CMD=C:\\Users\\cesar\\Downloads\\hermes-windows-voice-bridge\\src\\windows_hermes_voice_tray.py",
        "PID=456|NAME=pythonw.exe|CMD=C:\\Users\\cesar\\Downloads\\hermes-windows-voice-bridge\\src\\windows_hermes_voice.py",
        "PID=789|NAME=python.exe|CMD=other.py",
    ]

    parsed = control.parse_process_lines(lines)

    assert parsed["tray"][0]["pid"] == "123"
    assert parsed["bridge"][0]["pid"] == "456"


def test_parse_log_state_tracks_latest_useful_lines():
    lines = [
        "[tray.log] tray starting",
        "[tray.log] paused",
        "[bridge.log] bridge started pid=11",
        "[bridge.log] POST event=voice route=voice prompt_len=8 delivery=123",
        "[bridge.log] inbound message: platform=webhook user=voice chat=webhook:voice:123 msg='hola'",
        "[bridge.log] response ready: platform=webhook chat=webhook:voice:123 time=2.2s api_calls=1 response=12 chars",
    ]

    state = control.parse_log_state(lines)

    assert state["tray_state"] == "running"
    assert state["bridge_state"] == "running"
    assert state["mode"] == "paused"
    assert "response ready" in state["last_good"]
    assert "inbound message" in state["last_event"]
