#!/usr/bin/env python3
"""Windows voice bridge for Hermes on a VPS.

Flow:
1) Listen continuously for a wake phrase like "hermes".
2) When detected, record the next utterance until silence.
3) Transcribe that utterance locally with faster-whisper.
4) POST the text to the Hermes webhook on the VPS.
5) Hermes replies through Telegram.

This is an MVP. It is not a trained wake-word engine like Porcupine.
It uses lightweight local transcription on short audio windows to detect
"hermes" / "oye hermes" / "hey hermes".
"""
from __future__ import annotations

import argparse
import collections
import ctypes
import ctypes.wintypes
import hashlib
import hmac
import io
import json
import os
import queue
import re
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Iterable, List, Optional, Tuple

from src.services.audio.audio_service import AudioService
from src.storage.cache import JsonRuntimeSignalStore
from src.core.session import build_session_manager
from windows_hermes_voice_control import acquire_single_instance_mutex, release_single_instance_mutex, BRIDGE_MUTEX_NAME

try:
    import numpy as np
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: numpy. Install with: pip install numpy"
    ) from exc

try:
    import sounddevice as sd
except (ImportError, OSError):  # pragma: no cover - allow pure-function tests without PortAudio
    sd = None

try:
    from faster_whisper import WhisperModel
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: faster-whisper. Install with: pip install faster-whisper"
    ) from exc

try:
    import winsound
except ImportError:  # pragma: no cover - non-Windows fallback
    winsound = None

try:
    import pyttsx3
except ImportError:  # pragma: no cover - optional nice-to-have
    pyttsx3 = None


SAMPLE_RATE = 16000
CHANNELS = 1
DEFAULT_BLOCK_SECONDS = 0.25
DEFAULT_WAKE_WINDOW_SECONDS = 2.0
DEFAULT_SILENCE_TIMEOUT_SECONDS = 0.85
DEFAULT_MAX_COMMAND_SECONDS = 12.0
DEFAULT_WAKE_PHRASES = ["hermes", "oye hermes", "hey hermes"]
DEFAULT_HOTKEY = "ctrl+shift+h"
RUNTIME_SIGNAL_STORE = JsonRuntimeSignalStore(Path(__file__).resolve().parent.parent / "state" / "runtime_signal.json")

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
SESSION_MANAGER = build_session_manager(STATE_DIR)
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008


def load_env_file(path: Path | str) -> None:
    """Load KEY=VALUE pairs from a local env file if present."""
    path = Path(path)
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def emit_runtime_signal(kind: str, title: str, detail: str = "", **payload: object) -> None:
    try:
        RUNTIME_SIGNAL_STORE.emit(kind=kind, title=title, detail=detail, source="bridge", payload={k: v for k, v in payload.items() if v not in (None, "")})
    except Exception:
        pass


@dataclass
class Config:
    webhook_url: str
    webhook_secret: str
    model_size: str
    language: str
    wake_phrases: List[str]
    energy_threshold: float
    silence_rms: float
    device: Optional[int]
    device_name: str
    device_hostapi: Optional[int]
    hotkey: str
    feedback_mode: str
    feedback_voice: str
    block_seconds: float
    wake_window_seconds: float
    silence_timeout_seconds: float
    max_command_seconds: float


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def float_env(name: str, default: float) -> float:
    raw = env(name, str(default))
    try:
        return float(raw)
    except ValueError:
        return default


def int_env(name: str, default: int) -> int:
    raw = env(name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def optional_int_env(name: str) -> Optional[int]:
    raw = env(name)
    if raw in {"", "-1"}:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def load_config() -> Config:
    root_dir = Path(__file__).resolve().parent.parent
    load_env_file(root_dir / "state" / "voice.env")
    webhook_url = env("HERMES_WEBHOOK_URL", "http://YOUR_VPS_IP:8644/webhooks/voice")
    webhook_secret = env("HERMES_WEBHOOK_SECRET")
    if not webhook_secret:
        raise SystemExit(
            "Set HERMES_WEBHOOK_SECRET to the route secret shown by `hermes webhook subscribe`."
        )

    wake_phrases = [p.strip().lower() for p in env("HERMES_WAKE_PHRASES", ",".join(DEFAULT_WAKE_PHRASES)).split(",") if p.strip()]
    return Config(
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        model_size=env("HERMES_STT_MODEL", "base"),
        language=env("HERMES_STT_LANGUAGE", "").strip() or None,
        wake_phrases=wake_phrases,
        energy_threshold=float(env("HERMES_WAKE_ENERGY", "0.008")),
        silence_rms=float(env("HERMES_SILENCE_RMS", "0.008")),
        device=optional_int_env("HERMES_MIC_DEVICE"),
        device_name=env("HERMES_MIC_DEVICE_NAME", ""),
        device_hostapi=optional_int_env("HERMES_MIC_DEVICE_HOSTAPI"),
        hotkey=env("HERMES_HOTKEY", DEFAULT_HOTKEY).lower(),
        feedback_mode=env("HERMES_FEEDBACK_MODE", "both").lower(),
        feedback_voice=env("HERMES_FEEDBACK_VOICE", "").strip(),
        block_seconds=float_env("HERMES_BLOCK_SECONDS", DEFAULT_BLOCK_SECONDS),
        wake_window_seconds=float_env("HERMES_WAKE_WINDOW_SECONDS", DEFAULT_WAKE_WINDOW_SECONDS),
        silence_timeout_seconds=float_env("HERMES_SILENCE_TIMEOUT_SECONDS", DEFAULT_SILENCE_TIMEOUT_SECONDS),
        max_command_seconds=float_env("HERMES_MAX_COMMAND_SECONDS", DEFAULT_MAX_COMMAND_SECONDS),
    )


def sign_payload(secret: str, body: bytes) -> str:
    # Hermes webhook expects the generic header to be the raw hex digest.
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


class FeedbackPlayer:
    def __init__(self, mode: str, voice_name: str = "") -> None:
        self.mode = mode if mode in {"off", "beep", "voice", "both"} else "both"
        self.voice_name = voice_name
        self.queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self.voice_failed = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def beep(self) -> None:
        if self.mode not in {"beep", "both"}:
            return
        try:
            if winsound is not None:
                winsound.Beep(880, 85)
            else:
                print("\a", end="", flush=True)
        except Exception as exc:
            print(f"[feedback] beep failed: {exc}")

    def say(self, text: str) -> None:
        if self.mode not in {"voice", "both"} or not text or self.voice_failed:
            return
        for chunk in chunk_tts_text(text):
            self.queue.put(chunk)

    def pulse(self, text: str) -> None:
        self.beep()
        self.say(text)

    def _speak_once(self, text: str) -> None:
        if pyttsx3 is None:
            raise RuntimeError("pyttsx3 is not installed")
        engine = pyttsx3.init()
        try:
            if self.voice_name:
                voice_hint = self.voice_name.lower()
                for voice in engine.getProperty("voices"):
                    if voice_hint in getattr(voice, "id", "").lower() or voice_hint in getattr(voice, "name", "").lower():
                        engine.setProperty("voice", voice.id)
                        break
            engine.setProperty("rate", 182)
            engine.setProperty("volume", 1.0)
            engine.say(text)
            engine.runAndWait()
        finally:
            try:
                engine.stop()
            except Exception:
                pass

    def _run(self) -> None:
        if self.mode not in {"voice", "both"}:
            return
        if pyttsx3 is None:
            self.voice_failed = True
            print("[feedback] voice disabled: pyttsx3 missing")
            return

        while True:
            text = self.queue.get()
            if text is None:
                return
            try:
                self._speak_once(text)
                if not self.queue.empty():
                    time.sleep(0.12)
            except Exception as exc:
                self.voice_failed = True
                print(f"[feedback] voice failed: {exc}")
                return


def build_webhook_url(base_url: str, sync_reply: bool) -> str:
    if not sync_reply:
        return base_url
    parsed = urllib.parse.urlsplit(base_url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if ("sync", "1") not in query:
        query.append(("sync", "1"))
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment))


def post_json(
    url: str,
    secret: str,
    payload: dict,
    timeout_seconds: int = 120,
    attempts: int = 3,
    retry_base_delay: float = 0.5,
    extra_headers: dict | None = None,
) -> tuple[int, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": sign_payload(secret, body),
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )

    attempts = max(1, attempts)
    retry_base_delay = max(0.0, retry_base_delay)
    retryable_statuses = {429, 500, 502, 503, 504}

    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            if exc.code in retryable_statuses and attempt < attempts:
                time.sleep(retry_base_delay * (2 ** (attempt - 1)))
                continue
            return exc.code, body_text
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt < attempts:
                time.sleep(retry_base_delay * (2 ** (attempt - 1)))
                continue
            return 0, f"{exc.__class__.__name__}: {exc}"

    return 0, "unreachable"


def submit_command(cfg: Config, command_text: str) -> tuple[int, str]:
    sync_reply = env("HERMES_WEBHOOK_SYNC", "1").lower() not in {"", "0", "false", "no", "off"}
    timeout_seconds = int_env("HERMES_WEBHOOK_TIMEOUT", 120 if sync_reply else 30)

    session_record = SESSION_MANAGER.restore()
    user_id = session_record.user_id if session_record else ""

    payload = {
        "text": command_text,
        "source": "windows_voice_bridge",
        "event_type": "voice",
    }
    if user_id:
        payload["user_id"] = user_id

    extra_headers = {}
    if user_id:
        extra_headers["X-Request-ID"] = user_id

    return post_json(
        build_webhook_url(cfg.webhook_url, sync_reply),
        cfg.webhook_secret,
        payload,
        timeout_seconds=timeout_seconds,
        extra_headers=extra_headers if extra_headers else None,
    )


def handle_transcribed_command(cfg: Config, feedback: FeedbackPlayer, command_text: str) -> bool:
    try:
        print(f"Command: {command_text}")
        emit_runtime_signal("responding", "Hermes responding…", command_text[:120], command_text=command_text[:240])
        feedback.pulse("Mensaje recibido")
        status, response = submit_command(cfg, command_text)
        print(f"Hermes: HTTP {status}")
        if response:
            print(response)
        spoken = clean_speech_text(extract_final_response(response))
        if spoken and 200 <= status < 300:
            emit_runtime_signal("speaking", "Speaking…", spoken[:160], status=status)
            feedback.say(spoken)
        elif 200 <= status < 300:
            emit_runtime_signal("speaking", "Speaking…", "Enviado", status=status)
            feedback.say("Enviado")
        else:
            emit_runtime_signal("error", "Send failed", response[:160] if response else f"HTTP {status}", status=status)
            feedback.say("No se pudo enviar")
        emit_runtime_signal("idle", "Ready", f"HTTP {status}", status=status)
        return 200 <= status < 300
    except Exception as exc:
        print(f"[bridge] command handling failed: {exc}")
        print(traceback.format_exc().rstrip())
        emit_runtime_signal("error", "Command handling failed", str(exc))
        feedback.say("No se pudo enviar")
        return False


def prepare_tts_text(text: str, max_chars: int = 500) -> str:
    """Normalize text for local speech: keep pauses, remove markdown noise."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("```", " ").replace("`", " ")
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"(?m)^\s*#{1,6}\s+", "", text)
    text = re.sub(r"(?m)^\s*[-*•]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
    text = re.sub(r"\n+", ". ", text)
    for token in ["**", "__", "~~", "||"]:
        text = text.replace(token, "")
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def clean_speech_text(text: str) -> str:
    return prepare_tts_text(text)


def chunk_tts_text(text: str, max_chars: int = 180) -> List[str]:
    prepared = prepare_tts_text(text, max_chars=500)
    if not prepared:
        return []

    def split_long_segment(segment: str) -> List[str]:
        segment = segment.strip()
        if len(segment) <= max_chars:
            return [segment] if segment else []
        parts = re.split(r"(?<=[,;:!?])\s+", segment)
        out: List[str] = []
        buf = ""
        for part in parts:
            if not part:
                continue
            if len(part) > max_chars:
                start = 0
                while start < len(part):
                    out.append(part[start : start + max_chars].strip())
                    start += max_chars
                continue
            if buf and len(buf) + 1 + len(part) <= max_chars:
                buf = f"{buf} {part}"
            else:
                if buf:
                    out.append(buf)
                buf = part
        if buf:
            out.append(buf)
        return out

    sentences = re.split(r"(?<=[.!?;:])\s+", prepared)
    chunks: List[str] = []
    buf = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        for piece in split_long_segment(sentence):
            if buf and len(buf) + 1 + len(piece) <= max_chars:
                buf = f"{buf} {piece}"
            else:
                if buf:
                    chunks.append(buf)
                buf = piece
    if buf:
        chunks.append(buf)
    return chunks


def extract_final_response(body: str) -> str:
    raw = (body or "").strip()
    if not raw:
        return ""

    try:
        payload = json.loads(raw)
    except Exception:
        # Fallback for plain-text webhook responses.
        return raw if not raw.startswith("<") else ""

    if isinstance(payload, str):
        return payload.strip()
    if not isinstance(payload, dict):
        return raw if not raw.startswith("<") else ""

    for key in ("final_response", "response", "text", "message", "reply", "answer"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return raw if not raw.startswith("<") else ""


def parse_hotkey(hotkey: str) -> Optional[Tuple[int, int]]:
    token_map = {
        "space": 0x20,
        "tab": 0x09,
        "enter": 0x0D,
        "return": 0x0D,
        "esc": 0x1B,
        "escape": 0x1B,
        "backspace": 0x08,
        "insert": 0x2D,
        "delete": 0x2E,
        "home": 0x24,
        "end": 0x23,
        "pageup": 0x21,
        "pagedown": 0x22,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
    }
    mod = 0
    parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    if not parts:
        return None
    key = parts[-1]
    for part in parts[:-1]:
        if part in {"ctrl", "control"}:
            mod |= MOD_CONTROL
        elif part in {"alt", "menu"}:
            mod |= MOD_ALT
        elif part in {"shift"}:
            mod |= MOD_SHIFT
        elif part in {"win", "windows", "meta"}:
            mod |= MOD_WIN
        else:
            return None
    if len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    elif key in token_map:
        vk = token_map[key]
    elif key.startswith("f") and key[1:].isdigit():
        n = int(key[1:])
        if 1 <= n <= 24:
            vk = 0x6F + n
        else:
            return None
    else:
        return None
    return mod, vk


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.wintypes.LONG), ("y", ctypes.wintypes.LONG)]


class _HotkeyMessage(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.wintypes.HWND),
        ("message", ctypes.wintypes.UINT),
        ("wParam", ctypes.wintypes.WPARAM),
        ("lParam", ctypes.wintypes.LPARAM),
        ("time", ctypes.wintypes.DWORD),
        ("pt", _POINT),
    ]


def start_hotkey_listener(hotkey: str, trigger: threading.Event) -> bool:
    parsed = parse_hotkey(hotkey)
    if parsed is None:
        print(f"Hotkey disabled: invalid format {hotkey!r}")
        return False

    modifiers, vk = parsed

    def _worker() -> None:
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, 1, modifiers, vk):
            print(f"Hotkey disabled: could not register {hotkey!r}")
            return
        print(f"Hotkey active: {hotkey}")
        try:
            msg = _HotkeyMessage()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY:
                    trigger.set()
        finally:
            user32.UnregisterHotKey(None, 1)

    threading.Thread(target=_worker, daemon=True).start()
    return True



def startup_status_lines(cfg: Config, hotkey_enabled: bool) -> List[str]:
    hotkey_state = "active" if hotkey_enabled else "disabled; wake phrase only"
    device_label = "default microphone" if cfg.device is None else f"device #{cfg.device}"
    feedback_voice = cfg.feedback_voice or "default"
    return [
        f"Wake control: {', '.join(cfg.wake_phrases)}",
        f"Hotkey: {cfg.hotkey} ({hotkey_state})",
        f"Feedback: {cfg.feedback_mode}",
        f"Feedback voice: {feedback_voice}",
        f"Mic input: {device_label}",
    ]


def rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio.astype(np.float32)))))


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ\s]", " ", text)
    return " ".join(text.split())


def model_transcribe(model: WhisperModel, audio: np.ndarray, language: Optional[str], vad_filter: bool = True) -> str:
    segments, _info = model.transcribe(
        audio,
        language=language,
        beam_size=1,
        vad_filter=vad_filter,
        condition_on_previous_text=False,
        temperature=0.0,
    )
    parts = [seg.text.strip() for seg in segments if seg.text.strip()]
    return normalize_text(" ".join(parts))


def contains_wake_phrase(text: str, wake_phrases: Iterable[str]) -> bool:
    text = normalize_text(text)
    if not text:
        return False

    tokens = text.split()
    if any(phrase in text for phrase in wake_phrases):
        return True

    def close_enough(a: str, b: str) -> bool:
        if a == b:
            return True
        if not a or not b:
            return False
        if len(a) <= 4 or len(b) <= 4:
            return a == b or a in b or b in a
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a, b).ratio() >= 0.78

    wake_variants = set()
    for phrase in wake_phrases:
        phrase = normalize_text(phrase)
        if phrase:
            wake_variants.add(phrase)
            wake_variants.update(phrase.split())

    for token in tokens:
        for variant in wake_variants:
            if close_enough(token, variant):
                return True

    # Extra forgiving fallback for common Whisper miss-hearings of "hermes".
    if any(token.startswith(("herm", "erm", "jerm", "harm", "hern", "hermés")) for token in tokens):
        return True

    return False


def record_command(
    stream: sd.InputStream,
    blocksize: int,
    silence_rms: float,
    silence_timeout_seconds: float,
    max_command_seconds: float,
) -> np.ndarray:
    frames: List[np.ndarray] = []
    silence_start: Optional[float] = None
    started = False
    start_time = time.monotonic()

    while True:
        block, _overflow = stream.read(blocksize)
        audio = block[:, 0].astype(np.float32).copy()
        level = rms(audio)

        if level > silence_rms:
            started = True
            silence_start = None
        elif started and silence_start is None:
            silence_start = time.monotonic()
        elif started and silence_start is not None and (time.monotonic() - silence_start) >= silence_timeout_seconds:
            break

        if started:
            frames.append(audio)

        if started and (time.monotonic() - start_time) >= max_command_seconds:
            break

    if not frames:
        return np.zeros((0,), dtype=np.float32)
    return np.concatenate(frames)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes voice bridge for Windows")
    parser.add_argument("--list-devices", action="store_true", help="Show audio devices and exit")
    args = parser.parse_args()

    if sd is None:
        raise SystemExit(
            "Missing dependency: sounddevice/PortAudio. Install sounddevice and make sure PortAudio is available."
        )

    if args.list_devices:
        print(sd.query_devices())
        return 0

    mutex_handle = acquire_single_instance_mutex(BRIDGE_MUTEX_NAME)
    if mutex_handle is None:
        print("Bridge already running; exiting.")
        return 0

    cfg = load_config()
    model = WhisperModel(cfg.model_size, device="cpu", compute_type="int8")
    feedback = FeedbackPlayer(cfg.feedback_mode, cfg.feedback_voice)

    print("Hermes bridge on.")
    print(f"Webhook: {cfg.webhook_url}")
    print(f"Wake phrases: {', '.join(cfg.wake_phrases)}")
    print(
        "Capture tuning: "
        f"block={cfg.block_seconds:.2f}s, "
        f"wake_window={cfg.wake_window_seconds:.2f}s, "
        f"silence_timeout={cfg.silence_timeout_seconds:.2f}s, "
        f"max_command={cfg.max_command_seconds:.0f}s"
    )
    print("Say wake phrase, then command.")
    print()

    blocksize = max(1, int(SAMPLE_RATE * cfg.block_seconds))
    wake_blocks = max(1, int(round(cfg.wake_window_seconds / cfg.block_seconds)))
    rolling: Deque[np.ndarray] = collections.deque(maxlen=wake_blocks)
    busy_until = 0.0
    hotkey_event = threading.Event()
    hotkey_enabled = start_hotkey_listener(cfg.hotkey, hotkey_event)
    audio_service = AudioService(sample_rate=SAMPLE_RATE, channels=CHANNELS)
    last_device_signature = None

    for line in startup_status_lines(cfg, hotkey_enabled):
        print(line)

    while True:
        try:
            stream = audio_service.create_stream(
                cfg.device,
                cfg.block_seconds,
                preferred_name=cfg.device_name,
                preferred_hostapi=cfg.device_hostapi,
            )
            selected_device = audio_service.last_selected_device
            selection_reason = audio_service.last_selection_reason
            device_signature = (
                selected_device.get("index") if selected_device else None,
                selection_reason,
            )
            if device_signature != last_device_signature:
                last_device_signature = device_signature
                print(
                    f"[mic] using {audio_service.describe_device(selected_device)}"
                    + (f" via {selection_reason}" if selection_reason else "")
                )
        except Exception as exc:
            print(f"[bridge] microphone unavailable: {exc}")
            emit_runtime_signal("warn", "Microphone unavailable", str(exc))
            time.sleep(1.0)
            continue

        with stream:
            rolling.clear()
            while True:
                try:
                    block, _overflow = stream.read(blocksize)
                    audio = block[:, 0].astype(np.float32).copy()
                    rolling.append(audio)

                    now = time.monotonic()
                    if now < busy_until:
                        continue

                    if hotkey_event.is_set():
                        hotkey_event.clear()
                        print(f"Hotkey detected: {cfg.hotkey}")
                        emit_runtime_signal("listening", "● Listening…", f"Hotkey {cfg.hotkey}")
                        feedback.pulse("Te escucho")
                        print("Recording command...")
                        command_audio = record_command(
                            stream,
                            blocksize,
                            cfg.silence_rms,
                            cfg.silence_timeout_seconds,
                            cfg.max_command_seconds,
                        )
                        if command_audio.size == 0:
                            print("No command heard.")
                            emit_runtime_signal("idle", "Ready", "No command heard")
                            busy_until = time.monotonic() + 1.0
                            continue

                        emit_runtime_signal("transcribing", "Transcribing…", "Local Whisper processing")
                        command_text = model_transcribe(model, command_audio, cfg.language)
                        if not command_text:
                            print("Empty transcript.")
                            emit_runtime_signal("idle", "Ready", "Empty transcript")
                            busy_until = time.monotonic() + 1.0
                            continue

                        emit_runtime_signal("transcribed", "Transcript captured", command_text[:160], command_text=command_text[:240])
                        handle_transcribed_command(cfg, feedback, command_text)
                        print()
                        busy_until = time.monotonic() + 1.5
                        continue

                    level = rms(audio)
                    if level < cfg.energy_threshold:
                        continue
                    if len(rolling) < wake_blocks:
                        continue

                    window = np.concatenate(list(rolling))
                    wake_text = model_transcribe(model, window, cfg.language, vad_filter=False)
                    if not contains_wake_phrase(wake_text, cfg.wake_phrases):
                        continue

                    print(f"Wake detected: {wake_text!r}")
                    emit_runtime_signal("listening", "● Listening…", f"Wake phrase: {wake_text[:120]}")
                    feedback.pulse("Te escucho")
                    print("Recording command...")
                    command_audio = record_command(
                        stream,
                        blocksize,
                        cfg.silence_rms,
                        cfg.silence_timeout_seconds,
                        cfg.max_command_seconds,
                    )
                    if command_audio.size == 0:
                        print("No command heard.")
                        emit_runtime_signal("idle", "Ready", "No command heard")
                        busy_until = time.monotonic() + 1.0
                        continue

                    emit_runtime_signal("transcribing", "Transcribing…", "Local Whisper processing")
                    command_text = model_transcribe(model, command_audio, cfg.language)
                    if not command_text:
                        print("Empty transcript.")
                        emit_runtime_signal("idle", "Ready", "Empty transcript")
                        busy_until = time.monotonic() + 1.0
                        continue

                    emit_runtime_signal("transcribed", "Transcript captured", command_text[:160], command_text=command_text[:240])
                    handle_transcribed_command(cfg, feedback, command_text)
                    print()
                    busy_until = time.monotonic() + 1.5
                except Exception as exc:
                    print(f"[bridge] loop error: {exc}")
                    print(traceback.format_exc().rstrip())
                    emit_runtime_signal("error", "Bridge loop error", str(exc))
                    time.sleep(0.2)
                    break




if __name__ == "__main__":
    raise SystemExit(main())
