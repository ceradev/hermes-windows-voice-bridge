from __future__ import annotations

import logging
import time
from typing import Any, List, Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.last_selected_device: Optional[dict[str, Any]] = None
        self.last_selection_reason: str = ""

    def shutdown(self) -> None:
        """Release sounddevice playback/recording resources during app shutdown."""
        try:
            sd.stop()
        except Exception as exc:
            logger.debug("Could not stop sounddevice streams during shutdown: %s", exc)

    def _get_default_input_index(self) -> Optional[int]:
        try:
            default = sd.default.device
        except Exception:
            return None
        if isinstance(default, (list, tuple)) and default:
            return default[0]
        if isinstance(default, int):
            return default
        return None

    @staticmethod
    def _normalize_name(name: Any) -> str:
        return str(name or "").strip().casefold()

    def _probe_input_device(self, index: int) -> tuple[bool, str]:
        try:
            sd.check_input_settings(
                device=index,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
            )
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def _build_device_entry(self, idx: int, dev: dict[str, Any], default_input: Optional[int]) -> dict[str, Any]:
        usable, last_error = self._probe_input_device(idx)
        max_input = int(dev.get("max_input_channels", 0) or 0)
        return {
            "index": idx,
            "name": dev.get("name", f"Device {idx}"),
            "max_input_channels": max_input,
            "default_samplerate": float(dev.get("default_samplerate") or 0),
            "hostapi": dev.get("hostapi"),
            "selected": idx == default_input,
            "usable": usable,
            "selection_reason": "system_default" if idx == default_input else "",
            "last_error": last_error,
        }

    def describe_device(self, device: Optional[dict[str, Any]]) -> str:
        if not device:
            return "default input"
        hostapi = device.get("hostapi")
        suffix = f" (hostapi {hostapi})" if hostapi is not None else ""
        return f"{device.get('name', 'Unknown')} [#{device.get('index', '?')}]" + suffix

    def select_input_device(
        self,
        preferred_index: Optional[int],
        preferred_name: Optional[str] = None,
        preferred_hostapi: Optional[int] = None,
    ) -> dict[str, Any]:
        try:
            devices = sd.query_devices()
        except Exception as exc:
            return {
                "device": None,
                "reason": "query_failed",
                "error": str(exc),
                "devices": [],
            }

        default_input = self._get_default_input_index()
        entries = [
            self._build_device_entry(idx, dev, default_input)
            for idx, dev in enumerate(devices)
            if int(dev.get("max_input_channels", 0) or 0) > 0
        ]

        if not entries:
            return {
                "device": None,
                "reason": "no_input_devices",
                "error": "No input devices available",
                "devices": [],
            }

        usable_entries = [entry for entry in entries if entry.get("usable")]
        normalized_name = self._normalize_name(preferred_name)

        if preferred_index is not None:
            for entry in usable_entries:
                if entry["index"] == preferred_index:
                    return {"device": {**entry, "selected": True, "selection_reason": "configured_index"}, "reason": "configured_index", "error": "", "devices": entries}

        if normalized_name:
            preferred_hostapi_value = None if preferred_hostapi in (None, "") else int(preferred_hostapi)
            for entry in usable_entries:
                if self._normalize_name(entry.get("name")) != normalized_name:
                    continue
                if preferred_hostapi_value is not None and entry.get("hostapi") != preferred_hostapi_value:
                    continue
                return {"device": {**entry, "selected": True, "selection_reason": "remembered_name"}, "reason": "remembered_name", "error": "", "devices": entries}
            for entry in usable_entries:
                if self._normalize_name(entry.get("name")) == normalized_name:
                    return {"device": {**entry, "selected": True, "selection_reason": "remembered_name"}, "reason": "remembered_name", "error": "", "devices": entries}

        if default_input is not None:
            for entry in usable_entries:
                if entry["index"] == default_input:
                    return {"device": {**entry, "selected": True, "selection_reason": "system_default"}, "reason": "system_default", "error": "", "devices": entries}

        if usable_entries:
            return {"device": {**usable_entries[0], "selected": True, "selection_reason": "fallback_first_usable"}, "reason": "fallback_first_usable", "error": "", "devices": entries}

        first_error = next((entry.get("last_error") for entry in entries if entry.get("last_error")), "No usable microphone detected")
        return {
            "device": None,
            "reason": "no_usable_input_devices",
            "error": first_error,
            "devices": entries,
        }

    def get_devices(self) -> List[dict[str, Any]]:
        return self.select_input_device(None).get("devices", [])

    def _earcon_envelope(self, length: int, *, attack_ms: float = 8.0, decay: float = 5.5) -> np.ndarray:
        """Soft attack + exponential decay for unobtrusive UI feedback."""
        fs = 44100
        attack = max(1, int(fs * attack_ms / 1000.0))
        env = np.ones(length, dtype=np.float32)
        if attack < length:
            env[:attack] = np.linspace(0.0, 1.0, attack, dtype=np.float32)
            tail = np.arange(length - attack, dtype=np.float32) / fs
            env[attack:] = np.exp(-tail * decay)
        else:
            env = np.linspace(0.0, 1.0, length, dtype=np.float32)
        return env

    def _synthesize_earcon(self, kind: str) -> np.ndarray:
        """Generate subtle, modern earcon waveforms (mono float32, -1..1)."""
        fs = 44100

        def tone(freq: float, duration: float, amp: float, attack_ms: float = 8.0, decay: float = 5.5) -> np.ndarray:
            length = max(1, int(fs * duration))
            t = np.arange(length, dtype=np.float32) / fs
            wave = np.sin(2.0 * np.pi * freq * t, dtype=np.float32)
            return wave * self._earcon_envelope(length, attack_ms=attack_ms, decay=decay) * amp

        def chirp(f0: float, f1: float, duration: float, amp: float) -> np.ndarray:
            length = max(1, int(fs * duration))
            t = np.arange(length, dtype=np.float32) / fs
            freq = np.linspace(f0, f1, length, dtype=np.float32)
            phase = 2.0 * np.pi * np.cumsum(freq) / fs
            wave = np.sin(phase, dtype=np.float32)
            wave += 0.12 * np.sin(phase * 2.0, dtype=np.float32)
            return wave * self._earcon_envelope(length, attack_ms=6.0, decay=6.5) * amp

        if kind == "wake":
            # Soft upward "ready" ping — short and airy.
            return chirp(520.0, 720.0, 0.10, 0.16)

        if kind == "done":
            # Gentle two-note confirmation, barely there.
            note_a = tone(740.0, 0.07, 0.11, attack_ms=5.0, decay=7.0)
            note_b = tone(880.0, 0.09, 0.10, attack_ms=5.0, decay=6.0)
            gap = int(fs * 0.025)
            return np.concatenate([note_a, np.zeros(gap, dtype=np.float32), note_b])

        if kind == "error":
            # Muted low tap — noticeable but not alarming.
            return tone(320.0, 0.14, 0.12, attack_ms=4.0, decay=4.5)

        return np.zeros(0, dtype=np.float32)

    def _earcon_to_wav_bytes(self, samples: np.ndarray) -> bytes:
        import io
        import struct
        import wave

        clipped = np.clip(samples, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype(np.int16)
        data = io.BytesIO()
        with wave.open(data, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(struct.pack("<" + "h" * len(pcm), *pcm.tolist()))
        return data.getvalue()

    def play_earcon(self, kind: str = "wake"):
        try:
            import threading
            import winsound

            samples = self._synthesize_earcon(kind)
            if samples.size == 0:
                return

            wav_bytes = self._earcon_to_wav_bytes(samples)

            def _play():
                winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)

            threading.Thread(target=_play, daemon=True).start()

        except Exception as e:
            print(f"Error playing earcon with winsound: {e}")

    def get_rms(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(audio.astype(np.float32)))))

    def create_stream(
        self,
        device_index: Optional[int],
        block_seconds: float,
        preferred_name: Optional[str] = None,
        preferred_hostapi: Optional[int] = None,
    ) -> sd.InputStream:
        selection = self.select_input_device(device_index, preferred_name=preferred_name, preferred_hostapi=preferred_hostapi)
        selected_device = selection.get("device")
        if not selected_device:
            raise RuntimeError(selection.get("error") or "No usable microphone detected")

        self.last_selected_device = selected_device
        self.last_selection_reason = str(selection.get("reason") or "")
        blocksize = max(1, int(self.sample_rate * block_seconds))
        return sd.InputStream(
            device=selected_device["index"],
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=blocksize,
        )

    def record_command(self, stream: sd.InputStream, blocksize: int, silence_rms: float, silence_timeout_seconds: float, max_command_seconds: float, initial_timeout_seconds: float = 0.0, level_callback=None, cancel_check=None) -> np.ndarray:
        # Flush any leftover audio in the buffer (like the beep sound)
        if stream.read_available > 0:
            stream.read(stream.read_available)

        frames: List[np.ndarray] = []
        silence_start: Optional[float] = None
        started = False
        start_time = time.monotonic()

        while True:
            if cancel_check and cancel_check():
                return np.zeros((0,), dtype=np.float32)

            block, _overflow = stream.read(blocksize)
            audio = block[:, 0].astype(np.float32).copy()
            level = self.get_rms(audio)
            
            if level_callback:
                level_callback(level)

            if level > silence_rms:
                started = True
                silence_start = None
            elif started and silence_start is None:
                silence_start = time.monotonic()
            elif started and silence_start is not None and (time.monotonic() - silence_start) >= silence_timeout_seconds:
                break
            elif not started and initial_timeout_seconds > 0.0 and (time.monotonic() - start_time) >= initial_timeout_seconds:
                # User never started speaking
                break

            if started:
                frames.append(audio)

            if started and (time.monotonic() - start_time) >= max_command_seconds:
                break

        if not frames:
            return np.zeros((0,), dtype=np.float32)
        return np.concatenate(frames)
