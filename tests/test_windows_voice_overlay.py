from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_voice_bridge.ui.overlays import derive_overlay_signal


def _status(mode="unknown", last_event="", last_good="", runtime_signal=None):
    return {
        "summary": {"mode": mode, "last_event": last_event, "runtime_signal": runtime_signal or {}},
        "log_state": {"last_good": last_good},
        "runtime_signal": runtime_signal or {},
    }


def test_overlay_signal_prefers_explicit_runtime_signal():
    signal = derive_overlay_signal(
        _status(mode="listening", runtime_signal={"sequence": 1, "kind": "listening", "title": "● Listening…"}),
        _status(mode="listening", runtime_signal={"sequence": 2, "kind": "transcribing", "title": "Transcribing…", "detail": "Local Whisper processing"}),
    )

    assert signal is not None
    assert signal.kind == "transcribing"
    assert signal.title == "Transcribing…"


def test_overlay_signal_shows_listening_on_mode_transition():
    signal = derive_overlay_signal(_status(mode="starting"), _status(mode="listening"))

    assert signal is not None
    assert signal.kind == "listening"
    assert signal.title == "● Listening…"


def test_overlay_signal_shows_transcribing_from_voice_post_event():
    signal = derive_overlay_signal(
        _status(mode="listening", last_event="old"),
        _status(mode="listening", last_event="POST event=voice route=voice"),
    )

    assert signal is not None
    assert signal.kind == "transcribing"


def test_overlay_signal_shows_responding_for_inbound_webhook_message():
    signal = derive_overlay_signal(
        _status(mode="listening", last_event="old"),
        _status(mode="listening", last_event="Inbound message: platform=webhook user=voice"),
    )

    assert signal is not None
    assert signal.kind == "responding"


def test_overlay_signal_shows_speaking_when_new_response_arrives():
    signal = derive_overlay_signal(
        _status(mode="listening", last_good=""),
        _status(mode="listening", last_good="Response ready: platform=webhook"),
    )

    assert signal is not None
    assert signal.kind == "speaking"


def test_overlay_signal_stays_hidden_when_paused():
    signal = derive_overlay_signal(_status(mode="listening"), _status(mode="paused"))

    assert signal is None
