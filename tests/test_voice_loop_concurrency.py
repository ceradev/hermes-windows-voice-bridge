from pathlib import Path
import sys
import threading
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.platform.windows.voice_loop import VoiceLoop


class FakeConfig:
    def get(self, key: str, default: Any = None) -> Any:
        return default


class FakeBridge:
    def __init__(self) -> None:
        self.voice_loop: VoiceLoop | None = None

    def set_voice_loop(self, voice_loop: VoiceLoop) -> None:
        self.voice_loop = voice_loop


class FakeShortcutManager:
    def is_triggered(self) -> bool:
        return False

    def is_visual_triggered(self) -> bool:
        return False

    def clear_trigger(self) -> None:
        return None

    def clear_visual_trigger(self) -> None:
        return None


def build_loop() -> VoiceLoop:
    return VoiceLoop(
        FakeConfig(),
        audio=object(),
        wakeword=object(),
        bridge=FakeBridge(),
        shortcut_manager=FakeShortcutManager(),
        tts=object(),
        overlay=object(),
    )


def test_concurrent_listening_requests_queue_only_one_session() -> None:
    voice_loop = build_loop()
    barrier = threading.Barrier(3)
    results: list[str] = []
    results_lock = threading.Lock()

    def request(source: str) -> None:
        barrier.wait(timeout=2.0)
        result = voice_loop.request_listening(source)
        with results_lock:
            results.append(result)

    threads = [
        threading.Thread(target=request, args=(source,))
        for source in ("overlay", "hotkey", "tray")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2.0)

    assert results.count("queued") == 1
    assert results.count("ignored") == 2
    assert voice_loop._consume_listen_request() in {"overlay", "hotkey", "tray"}
    assert voice_loop._consume_listen_request() is None


def test_active_listening_request_signals_cancel_without_queueing_second_session() -> None:
    voice_loop = build_loop()

    assert voice_loop._begin_listening("hotkey") is True
    assert voice_loop.request_listening("overlay") == "cancelled"
    assert voice_loop._consume_listen_request() is None
    assert voice_loop._check_cancel() is True

    voice_loop._finish_listening()
    assert voice_loop.request_listening("tray") == "queued"
