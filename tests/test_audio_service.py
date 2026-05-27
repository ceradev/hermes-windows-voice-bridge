from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from src.services.audio import audio_service as audio_module
from src.services.audio.audio_service import AudioService


class _FakeSoundDevice:
    def __init__(self, devices, default_device, failing_indexes=None):
        self._devices = devices
        self.default = type("Default", (), {"device": default_device})()
        self._failing_indexes = set(failing_indexes or set())
        self.stream_calls = []

    def query_devices(self):
        return self._devices

    def check_input_settings(self, device, samplerate, channels, dtype):
        if device in self._failing_indexes:
            raise RuntimeError(f"device {device} failed")

    def InputStream(self, **kwargs):
        self.stream_calls.append(kwargs)
        return kwargs


def test_select_input_device_prefers_configured_index(monkeypatch):
    fake_sd = _FakeSoundDevice(
        devices=[
            {"name": "Mic A", "max_input_channels": 1, "default_samplerate": 16000, "hostapi": 0},
            {"name": "Mic B", "max_input_channels": 1, "default_samplerate": 16000, "hostapi": 0},
        ],
        default_device=(1, None),
    )
    monkeypatch.setattr(audio_module, "sd", fake_sd)

    service = AudioService()
    selected = service.select_input_device(1)

    assert selected["device"]["index"] == 1
    assert selected["reason"] == "configured_index"


def test_select_input_device_falls_back_to_remembered_name(monkeypatch):
    fake_sd = _FakeSoundDevice(
        devices=[
            {"name": "Another Mic", "max_input_channels": 1, "default_samplerate": 16000, "hostapi": 0},
            {"name": "USB Headset", "max_input_channels": 1, "default_samplerate": 16000, "hostapi": 2},
        ],
        default_device=(0, None),
        failing_indexes={0},
    )
    monkeypatch.setattr(audio_module, "sd", fake_sd)

    service = AudioService()
    selected = service.select_input_device(9, preferred_name="USB Headset", preferred_hostapi=2)

    assert selected["device"]["index"] == 1
    assert selected["reason"] == "remembered_name"


def test_create_stream_uses_fallback_first_usable_device(monkeypatch):
    fake_sd = _FakeSoundDevice(
        devices=[
            {"name": "Broken Mic", "max_input_channels": 1, "default_samplerate": 16000, "hostapi": 0},
            {"name": "Working Mic", "max_input_channels": 1, "default_samplerate": 16000, "hostapi": 1},
        ],
        default_device=(0, None),
        failing_indexes={0},
    )
    monkeypatch.setattr(audio_module, "sd", fake_sd)

    service = AudioService(sample_rate=16000, channels=1)
    service.create_stream(0, 0.25)

    assert fake_sd.stream_calls[0]["device"] == 1
    assert service.last_selected_device is not None
    assert service.last_selected_device["index"] == 1
    assert service.last_selection_reason == "fallback_first_usable"


def test_get_devices_reports_usable_and_last_error(monkeypatch):
    fake_sd = _FakeSoundDevice(
        devices=[
            {"name": "Broken Mic", "max_input_channels": 1, "default_samplerate": 16000, "hostapi": 0},
            {"name": "Working Mic", "max_input_channels": 1, "default_samplerate": 16000, "hostapi": 1},
        ],
        default_device=(0, None),
        failing_indexes={0},
    )
    monkeypatch.setattr(audio_module, "sd", fake_sd)

    service = AudioService()
    devices = service.get_devices()

    assert devices[0]["usable"] is False
    assert "failed" in devices[0]["last_error"]
    assert devices[1]["usable"] is True
