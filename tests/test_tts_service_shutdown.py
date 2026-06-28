import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.tts import tts_service


class FakeMusic:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class FakeMixer:
    def __init__(self) -> None:
        self.music = FakeMusic()
        self.initialized = False

    def init(self) -> None:
        self.initialized = True


class FakePygame:
    def __init__(self) -> None:
        self.mixer = FakeMixer()


def test_tts_shutdown_sends_sentinel_and_joins_worker(monkeypatch):
    fake_pygame = FakePygame()
    spoken: list[str] = []

    def fake_speak_once(self, text: str) -> None:
        spoken.append(text)
        time.sleep(0.01)

    monkeypatch.setattr(tts_service, "edge_tts", object())
    monkeypatch.setattr(tts_service, "pygame", fake_pygame)
    monkeypatch.setattr(tts_service.TTSService, "_speak_once", fake_speak_once)

    service = tts_service.TTSService(mode="voice")
    service.say("Hermes shutdown smoke test.")

    deadline = time.monotonic() + 1.0
    while not spoken and time.monotonic() < deadline:
        time.sleep(0.01)

    service.shutdown(timeout=1.0)

    assert spoken == ["Hermes shutdown smoke test."]
    assert fake_pygame.mixer.initialized is True
    assert fake_pygame.mixer.music.stopped is True
    assert service.thread.is_alive() is False
    assert not any(thread.name == "HermesTTS" for thread in threading.enumerate())


def test_tts_shutdown_is_idempotent(monkeypatch):
    monkeypatch.setattr(tts_service, "edge_tts", object())
    monkeypatch.setattr(tts_service, "pygame", FakePygame())
    monkeypatch.setattr(tts_service.TTSService, "_speak_once", lambda self, text: None)

    service = tts_service.TTSService(mode="voice")
    service.shutdown(timeout=1.0)
    service.shutdown(timeout=1.0)

    assert service.thread.is_alive() is False
