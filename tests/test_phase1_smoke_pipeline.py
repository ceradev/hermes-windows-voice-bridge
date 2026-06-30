from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportPrivateUsage=false, reportUnannotatedClassAttribute=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnusedParameter=false

import threading
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from src.platform.windows.voice_loop import VoiceLoop
from src.services.tts import tts_service


class FakeConfig:
    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.values = values or {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)


class FakeShortcutManager:
    def __init__(self) -> None:
        self.started: list[tuple[str, str | None]] = []

    def start(self, hotkey: str | None = None, visual_hotkey: str | None = None) -> None:
        self.started.append((hotkey or "", visual_hotkey))

    def is_triggered(self) -> bool:
        return False

    def is_visual_triggered(self) -> bool:
        return False

    def clear_trigger(self) -> None:
        return None

    def clear_visual_trigger(self) -> None:
        return None


class FakeTts:
    is_speaking = False


class FakeOverlay:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def show(self, state: str, detail: str = "") -> None:
        self.calls.append(("show", state, detail))

    def show_result(self, request_text: str, response_text: str) -> None:
        self.calls.append(("show_result", request_text, response_text))

    def hide(self) -> None:
        self.calls.append(("hide", "idle", ""))

    def cancel_active(self) -> None:
        self.calls.append(("cancel", "idle", ""))


class FakeBridge:
    def __init__(self) -> None:
        self.voice_loop: VoiceLoop | None = None
        self.runtime_states: list[tuple[str, str]] = [("idle", "")]
        self.overlay_text: list[tuple[str, str]] = []
        self.messages: list[str] = []

    def set_voice_loop(self, voice_loop: VoiceLoop) -> None:
        self.voice_loop = voice_loop

    def set_runtime_listening_state(self, state: str, detail: str = "") -> None:
        self.runtime_states.append((state, detail))

    def set_runtime_overlay_text(self, request_text: str = "", response_text: str = "") -> None:
        self.overlay_text.append((request_text, response_text))

    def send_message(self, text: str, image_base64: str | None = None) -> dict[str, Any]:
        self.messages.append(text)
        return {"success": True, "response": "Respuesta de Hermes", "latencyMs": 1}

    def log_local_action(self, request_text: str, response_text: str) -> bool:
        return True


class FakeWakeword:
    def __init__(self, transcripts: list[str] | None = None) -> None:
        self.transcripts = transcripts or []
        self.transcribe_calls: list[tuple[np.ndarray, bool]] = []
        self.contains_calls: list[tuple[str, list[str]]] = []

    def normalize_text(self, text: str) -> str:
        return " ".join(text.lower().split())

    def build_stt_prompt(self, phrases: list[str]) -> str:
        return ", ".join(phrases)

    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "es",
        *,
        vad_filter: bool = False,
        beam_size: int = 1,
        initial_prompt: str | None = None,
    ) -> str:
        self.transcribe_calls.append((audio, vad_filter))
        if self.transcripts:
            return self.transcripts.pop(0)
        return ""

    def contains_wake_phrase(self, text: str, phrases: list[str]) -> bool:
        self.contains_calls.append((text, phrases))
        return any(phrase in text.lower() for phrase in phrases)

    def split_wake_and_command(self, text: str, phrases: list[str], **kwargs: Any) -> tuple[bool, str]:
        normalized = self.normalize_text(text)
        for phrase in sorted(phrases, key=lambda p: len(p.split()), reverse=True):
            needle = phrase.lower()
            if normalized.startswith(needle):
                return True, normalized[len(needle) :].strip()
        return False, ""


class FakeStream:
    def __init__(self, blocks: list[np.ndarray], on_exhaust: Callable[[], None] | None = None) -> None:
        self.blocks = list(blocks)
        self.on_exhaust = on_exhaust
        self.read_available = 0

    def read(self, blocksize: int) -> tuple[np.ndarray, bool]:
        if not self.blocks:
            if self.on_exhaust:
                self.on_exhaust()
            raise RuntimeError("fake stream exhausted")
        block = self.blocks.pop(0).astype(np.float32)
        if block.ndim == 1:
            block = block.reshape((-1, 1))
        return block, False


class FakeStreamContext:
    def __init__(self, stream: FakeStream) -> None:
        self.stream = stream

    def __enter__(self) -> FakeStream:
        return self.stream

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


class FakeAudio:
    def __init__(self, stream: FakeStream | None = None, command_audio: np.ndarray | None = None) -> None:
        self.stream = stream
        self.command_audio = command_audio if command_audio is not None else np.ones(1600, dtype=np.float32) * 0.05
        self.earcons: list[str] = []
        self.last_selected_device = {"index": 0, "name": "Fake microphone", "hostapi": 0}
        self.last_selection_reason = "test_fake"

    def create_stream(self, *args: Any, **kwargs: Any) -> FakeStreamContext:
        if self.stream is None:
            raise RuntimeError("No fake stream configured")
        return FakeStreamContext(self.stream)

    def describe_device(self, device: dict[str, Any] | None) -> str:
        return "Fake microphone [#0]"

    def get_rms(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(audio.astype(np.float32)))))

    def play_earcon(self, kind: str = "wake") -> None:
        self.earcons.append(kind)

    def record_command(self, *args: Any, level_callback: Callable[[float], None] | None = None, **kwargs: Any) -> np.ndarray:
        if level_callback:
            level_callback(self.get_rms(self.command_audio))
        return self.command_audio


def build_voice_loop(
    *,
    config_values: dict[str, Any] | None = None,
    audio: FakeAudio | None = None,
    wakeword: FakeWakeword | None = None,
    bridge: FakeBridge | None = None,
    overlay: FakeOverlay | None = None,
) -> VoiceLoop:
    return VoiceLoop(
        FakeConfig(config_values),
        audio=audio or FakeAudio(),
        wakeword=wakeword or FakeWakeword(),
        bridge=bridge or FakeBridge(),
        shortcut_manager=FakeShortcutManager(),
        tts=FakeTts(),
        overlay=overlay or FakeOverlay(),
    )


def test_wake_detection_does_not_trigger_on_silence_or_non_wake_noise() -> None:
    blocksize = 160
    silence = np.zeros((blocksize, 1), dtype=np.float32)
    noise = np.ones((blocksize, 1), dtype=np.float32) * 0.02

    for blocks, expected_transcribes in (([silence] * 8, 0), ([noise] * 4, 1)):
        wakeword = FakeWakeword(transcripts=["ruido sin frase"])
        handled: list[bool] = []
        loop_ref: dict[str, VoiceLoop] = {}

        def stop_loop() -> None:
            loop_ref["loop"]._running = False

        stream = FakeStream(blocks, on_exhaust=stop_loop)
        loop = build_voice_loop(
            config_values={
                "block_seconds": 0.01,
                "wake_window_seconds": 0.03,
                "wake_min_speech_seconds": 0.02,
                "wake_hangover_seconds": 0.01,
                "wake_speech_ratio_min": 0.4,
                "wake_energy": 0.008,
                "wake_cooldown_seconds": 0.0,
                "stt_beam_size": 3,
                "wake_phrases": ["hermes"],
                "hotkey": "",
                "visual_hotkey": "",
            },
            audio=FakeAudio(stream=stream),
            wakeword=wakeword,
        )
        loop_ref["loop"] = loop
        loop._handle_command = lambda *args, **kwargs: handled.append(True) or True  # type: ignore[method-assign]
        loop._running = True

        worker = threading.Thread(target=loop._loop, daemon=True)
        worker.start()
        worker.join(timeout=1.0)

        assert worker.is_alive() is False
        assert handled == []
        assert len(wakeword.transcribe_calls) == expected_transcribes
        if expected_transcribes:
            assert wakeword.transcribe_calls[0][1] is True


def test_wake_phrase_detection_dispatches_voice_command_once() -> None:
    blocksize = 160
    noise = np.ones((blocksize, 1), dtype=np.float32) * 0.02
    wakeword = FakeWakeword(transcripts=["hermes"])
    handled_sources: list[str] = []
    loop_ref: dict[str, VoiceLoop] = {}

    def stop_loop() -> None:
        loop_ref["loop"]._running = False

    stream = FakeStream([noise] * 4, on_exhaust=stop_loop)
    loop = build_voice_loop(
        config_values={
            "block_seconds": 0.01,
            "wake_window_seconds": 0.03,
            "wake_min_speech_seconds": 0.02,
            "wake_hangover_seconds": 0.01,
            "wake_speech_ratio_min": 0.4,
            "wake_energy": 0.008,
            "wake_cooldown_seconds": 0.0,
            "stt_beam_size": 3,
            "wake_phrases": ["hermes"],
            "hotkey": "",
            "visual_hotkey": "",
        },
        audio=FakeAudio(stream=stream),
        wakeword=wakeword,
    )
    loop_ref["loop"] = loop

    def handle_command(*args: Any, **kwargs: Any) -> bool:
        handled_sources.append(str(kwargs.get("source")))
        loop._running = False
        return True

    loop._handle_command = handle_command  # type: ignore[method-assign]
    loop._running = True

    worker = threading.Thread(target=loop._loop, daemon=True)
    worker.start()
    worker.join(timeout=1.0)

    assert worker.is_alive() is False
    assert handled_sources == ["voice"]
    assert len(wakeword.transcribe_calls) == 1
    assert wakeword.transcribe_calls[0][1] is True


def test_headless_voice_command_flow_exercises_stt_hermes_tts_and_overlay_states() -> None:
    bridge = FakeBridge()
    overlay = FakeOverlay()
    wakeword = FakeWakeword(transcripts=["consulta el estado"])
    audio = FakeAudio(command_audio=np.ones(1600, dtype=np.float32) * 0.05)
    loop = build_voice_loop(audio=audio, wakeword=wakeword, bridge=bridge, overlay=overlay)
    loop._running = True

    result = loop._handle_command(FakeStream([]), 160, 0.01, source="hotkey")

    assert result is True
    assert bridge.messages == ["consulta el estado"]
    assert [state for state, _detail in bridge.runtime_states] == [
        "idle",
        "listening",
        "thinking",
        "thinking",
        "speaking",
        "idle",
    ]
    assert overlay.calls[0][0:2] == ("show", "listening")
    assert ("show", "processing", "Transcribing your command...") in overlay.calls
    assert ("show", "thinking", "consulta el estado") in overlay.calls
    assert ("show_result", "consulta el estado", "Respuesta de Hermes") in overlay.calls
    assert overlay.calls[-1] == ("hide", "idle", "")
    assert audio.earcons == ["wake", "done"]


class BlockingMusic:
    def __init__(self, stop_event: threading.Event) -> None:
        self.stop_event = stop_event
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True
        self.stop_event.set()


class BlockingMixer:
    def __init__(self, stop_event: threading.Event) -> None:
        self.music = BlockingMusic(stop_event)

    def init(self) -> None:
        return None


class BlockingPygame:
    def __init__(self, stop_event: threading.Event) -> None:
        self.mixer = BlockingMixer(stop_event)


def test_tts_can_queue_speech_and_stop_playback_on_shutdown(monkeypatch: Any) -> None:
    stop_event = threading.Event()
    spoken: list[str] = []

    def fake_speak_once(self: tts_service.TTSService, text: str) -> None:
        spoken.append(text)
        while not self._stop_event.is_set() and not stop_event.is_set():
            time.sleep(0.01)

    fake_pygame = BlockingPygame(stop_event)
    monkeypatch.setattr(tts_service, "edge_tts", object())
    monkeypatch.setattr(tts_service, "pygame", fake_pygame)
    monkeypatch.setattr(tts_service.TTSService, "_speak_once", fake_speak_once)

    service = tts_service.TTSService(mode="voice")
    service.say("Hermes smoke test playback should start and then stop cleanly.")

    deadline = time.monotonic() + 1.0
    while not spoken and time.monotonic() < deadline:
        time.sleep(0.01)

    assert spoken == ["Hermes smoke test playback should start and then stop cleanly."]
    assert service.is_speaking is True

    service.shutdown(timeout=1.0)

    assert fake_pygame.mixer.music.stopped is True
    assert service.thread.is_alive() is False
