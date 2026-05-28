#!/usr/bin/env python3
"""Local HTTP API for the Hermes Windows voice bridge desktop app."""
from __future__ import annotations

import json
import mimetypes
import os
import secrets
import subprocess
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from src.services.audio.audio_service import AudioService
from src.core.session import SessionRecord, build_session_manager
from src.storage.cache import JsonRuntimeSignalStore, JsonRuntimeStateStore
from windows_hermes_voice_control import (
    BRIDGE_MUTEX_NAME,
    TRAY_MUTEX_NAME,
    PANEL_API_MUTEX_NAME,
    acquire_single_instance_mutex,
    build_status_snapshot,
    load_control_state,
    load_env_file,
    probe_single_instance_mutex,
    query_windows_voice_processes,
    release_single_instance_mutex,
    save_control_state,
    save_env_file,
)

try:
    import sounddevice as sd
except (ImportError, OSError):  # pragma: no cover
    sd = None

SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent
STATE_DIR = BASE_DIR / "state"
VOICE_ENV = STATE_DIR / "voice.env"
CONTROL_FILE = STATE_DIR / "voice.control.json"
RUNTIME_STATE_FILE = STATE_DIR / "runtime_state.json"
RUNTIME_SIGNAL_FILE = STATE_DIR / "runtime_signal.json"
LOG_DIR = STATE_DIR / "logs" / "HermesVoiceBridge"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TRAY_SCRIPT = SRC_DIR / "windows_hermes_voice_tray.py"
PROBE_SCRIPT = SRC_DIR / "voice_end2end_test.py"
DIST_DIR = BASE_DIR / "panel-web" / "dist"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DEFAULT_PORT = int(os.environ.get("HERMES_PANEL_PORT", "8765"))
APP_VERSION = "0.2.0"
RUNTIME_STATE_STORE = JsonRuntimeStateStore(RUNTIME_STATE_FILE)
RUNTIME_SIGNAL_STORE = JsonRuntimeSignalStore(RUNTIME_SIGNAL_FILE)
SESSION_MANAGER = build_session_manager(STATE_DIR)
AUDIO_SERVICE = AudioService()

_panel_token_value = os.environ.get("HERMES_PANEL_TOKEN", "").strip()
if not _panel_token_value:
    token_path = STATE_DIR / ".panel_token"
    if token_path.exists():
        _panel_token_value = token_path.read_text(encoding="utf-8").strip()
    else:
        _panel_token_value = secrets.token_urlsafe(32)
        token_path.write_text(_panel_token_value, encoding="utf-8")
_PANEL_TOKEN = _panel_token_value

# Simple per-IP rate limiter: ip -> (count, window_start)
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 120    # requests per window
_rate_limit_store: Dict[str, Tuple[int, float]] = {}


def _check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    count, window_start = _rate_limit_store.get(client_ip, (0, now))
    if now - window_start > _RATE_LIMIT_WINDOW:
        _rate_limit_store[client_ip] = (1, now)
        return True
    if count >= _RATE_LIMIT_MAX:
        return False
    _rate_limit_store[client_ip] = (count + 1, window_start)
    return True


def _check_panel_token(handler: BaseHTTPRequestHandler) -> bool:
    token = handler.headers.get("X-Hermes-Panel-Token", "").strip()
    return token == _PANEL_TOKEN


def _local_origin(origin: str) -> bool:
    if not origin:
        return True
    return origin.startswith(("http://localhost:", "http://127.0.0.1:", "https://localhost:", "https://127.0.0.1:", "app://", "file://", "null"))


CONFIG_KEYS = {
    "mic_device": "HERMES_MIC_DEVICE",
    "mic_device_name": "HERMES_MIC_DEVICE_NAME",
    "mic_device_hostapi": "HERMES_MIC_DEVICE_HOSTAPI",
    "hotkey": "HERMES_HOTKEY",
    "feedback_mode": "HERMES_FEEDBACK_MODE",
    "feedback_voice": "HERMES_FEEDBACK_VOICE",
    "wake_phrases": "HERMES_WAKE_PHRASES",
    "stt_language": "HERMES_STT_LANGUAGE",
    "stt_model": "HERMES_STT_MODEL",
    "wake_energy": "HERMES_WAKE_ENERGY",
    "silence_rms": "HERMES_SILENCE_RMS",
    "block_seconds": "HERMES_BLOCK_SECONDS",
    "wake_window_seconds": "HERMES_WAKE_WINDOW_SECONDS",
    "silence_timeout_seconds": "HERMES_SILENCE_TIMEOUT_SECONDS",
    "max_command_seconds": "HERMES_MAX_COMMAND_SECONDS",
    "webhook_sync": "HERMES_WEBHOOK_SYNC",
    "webhook_timeout": "HERMES_WEBHOOK_TIMEOUT",
    "persist_session": "HERMES_PERSIST_SESSION",
    "overlay_enabled": "HERMES_OVERLAY_ENABLED",
    "notifications_enabled": "HERMES_NOTIFICATIONS_ENABLED",
    "tts_enabled": "HERMES_TTS_ENABLED",
    "endpoint": "HERMES_WEBHOOK_URL",
    "auth_refresh_url": "HERMES_AUTH_REFRESH_URL",
    "auth_timeout": "HERMES_AUTH_TIMEOUT",
    "auth_header": "HERMES_AUTH_HEADER",
    "auth_secret_header": "HERMES_AUTH_SECRET_HEADER",
}


def _semantic_state(paused: bool, tray_running: bool, bridge_running: bool, last_error: str) -> Tuple[str, str, str]:
    if paused:
        return "paused", "Paused", "Control state shared between tray and panel"
    if bridge_running and last_error:
        return "warn", "Listening", "Bridge is up, but the latest log entry suggests attention"
    if bridge_running:
        return "listening", "Listening", "Bridge and tray can be controlled from here"
    if tray_running:
        return "warn", "Tray only", "Tray is alive, bridge needs to be started"
    return "stopped", "Stopped", "Start the tray or relaunch the bridge"


def _safe_env(env: Dict[str, str]) -> Dict[str, str]:
    return {
        "mic_device": env.get("HERMES_MIC_DEVICE", "") or "",
        "mic_device_name": env.get("HERMES_MIC_DEVICE_NAME", "") or "",
        "mic_device_hostapi": env.get("HERMES_MIC_DEVICE_HOSTAPI", "") or "",
        "hotkey": env.get("HERMES_HOTKEY", "(default)") or "(default)",
        "feedback_mode": env.get("HERMES_FEEDBACK_MODE", "(default)") or "(default)",
        "feedback_voice": env.get("HERMES_FEEDBACK_VOICE", "") or "",
        "wake_phrases": env.get("HERMES_WAKE_PHRASES", "(default)") or "(default)",
        "stt_language": env.get("HERMES_STT_LANGUAGE", "(default)") or "(default)",
        "stt_model": env.get("HERMES_STT_MODEL", "(default)") or "(default)",
        "wake_energy": env.get("HERMES_WAKE_ENERGY", "") or "",
        "silence_rms": env.get("HERMES_SILENCE_RMS", "") or "",
        "block_seconds": env.get("HERMES_BLOCK_SECONDS", "") or "",
        "wake_window_seconds": env.get("HERMES_WAKE_WINDOW_SECONDS", "") or "",
        "silence_timeout_seconds": env.get("HERMES_SILENCE_TIMEOUT_SECONDS", "") or "",
        "max_command_seconds": env.get("HERMES_MAX_COMMAND_SECONDS", "") or "",
        "webhook_sync": env.get("HERMES_WEBHOOK_SYNC", "") or "",
        "webhook_timeout": env.get("HERMES_WEBHOOK_TIMEOUT", "") or "",
        "persist_session": env.get("HERMES_PERSIST_SESSION", "1") or "1",
        "overlay_enabled": env.get("HERMES_OVERLAY_ENABLED", "1") or "1",
        "notifications_enabled": env.get("HERMES_NOTIFICATIONS_ENABLED", "1") or "1",
        "tts_enabled": env.get("HERMES_TTS_ENABLED", "1") or "1",
        "endpoint": env.get("HERMES_WEBHOOK_URL", "") or "",
        "auth_refresh_url": env.get("HERMES_AUTH_REFRESH_URL", "") or "",
        "auth_timeout": env.get("HERMES_AUTH_TIMEOUT", "10") or "10",
        "auth_header": env.get("HERMES_AUTH_HEADER", "Authorization") or "Authorization",
        "auth_secret_header": env.get("HERMES_AUTH_SECRET_HEADER", "X-Hermes-Auth-Secret") or "X-Hermes-Auth-Secret",
    }


def _list_audio_devices() -> Dict[str, Any]:
    if sd is None:
        return {"devices": [], "default_input": None, "error": "sounddevice/PortAudio not available"}
    devices = AUDIO_SERVICE.get_devices()
    default_input = next((device["index"] for device in devices if device.get("selection_reason") == "system_default"), None)
    error = ""
    if not any(device.get("usable") for device in devices):
        error = next((device.get("last_error") for device in devices if device.get("last_error")), "No usable microphone detected")
    return {"devices": devices, "default_input": default_input, "error": error}


def _load_runtime_snapshot() -> Dict[str, Any] | None:
    return RUNTIME_STATE_STORE.load()


def _load_runtime_signal() -> Dict[str, Any] | None:
    return RUNTIME_SIGNAL_STORE.load()


def _logout_persisted_session(reason: str = "manual") -> None:
    SESSION_MANAGER.logout(reason=reason)


def _save_persisted_session(payload: Dict[str, Any]) -> SessionRecord:
    access_token = str(payload.get("access_token", "") or "").strip()
    if not access_token:
        raise ValueError("access_token is required")
    remember_me = str(payload.get("remember_me", "1") or "1").strip().lower() not in {"", "0", "false", "no", "off"}
    record = SessionRecord(
        access_token=access_token,
        refresh_token=str(payload.get("refresh_token", "") or "").strip(),
        token_type=str(payload.get("token_type", "Bearer") or "Bearer").strip() or "Bearer",
        user_id=str(payload.get("user_id", "") or "").strip(),
        display_name=str(payload.get("display_name", "") or "").strip(),
        remember_me=remember_me,
        expires_at=str(payload.get("expires_at", "") or "").strip(),
        metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {},
    )
    return SESSION_MANAGER.save(record)


def _refresh_persisted_session() -> SessionRecord:
    record = SESSION_MANAGER.restore()
    if record is None:
        raise ValueError("No persisted session to refresh")
    return SESSION_MANAGER.refresh(record)


def _apply_runtime_snapshot(base_snapshot: Dict[str, Any], runtime_snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    if not runtime_snapshot:
        return base_snapshot

    merged = dict(base_snapshot)
    merged["generated_at"] = runtime_snapshot.get("generated_at", merged.get("generated_at", ""))
    merged["version"] = runtime_snapshot.get("version", APP_VERSION)
    merged["badge"] = runtime_snapshot.get("badge", merged.get("badge", {}))
    merged["badge_label"] = runtime_snapshot.get("badge_label", merged.get("badge_label", ""))
    merged["summary"] = {**merged.get("summary", {}), **runtime_snapshot.get("summary", {})}
    merged["control"] = {**merged.get("control", {}), **runtime_snapshot.get("control", {})}
    merged["runtime_signal"] = runtime_snapshot.get("runtime_signal", merged.get("runtime_signal", {}))

    runtime_processes = runtime_snapshot.get("processes", {})
    merged_processes = dict(merged.get("processes", {}))
    for key in ("tray", "bridge", "api"):
        if key in runtime_processes:
            merged_processes[key] = runtime_processes[key]
    merged["processes"] = merged_processes
    merged["runtime"] = runtime_snapshot.get("runtime", {})
    merged["lifecycle"] = runtime_snapshot.get("lifecycle", merged.get("lifecycle", "unknown"))
    return merged


def _build_snapshot() -> Dict[str, Any]:
    runtime_snapshot = _load_runtime_snapshot()
    runtime_signal = _load_runtime_signal()
    snapshot = build_status_snapshot(
        base_dir=BASE_DIR,
        env_path=VOICE_ENV,
        control_path=CONTROL_FILE,
        log_paths=[LOG_DIR / "tray.log", LOG_DIR / "bridge.log"],
    )
    control = snapshot.get("control", {})
    processes = snapshot.get("processes", {})
    log_state = snapshot.get("log_state", {})
    env = snapshot.get("env", {})

    tray_running = bool(processes.get("tray")) or probe_single_instance_mutex(TRAY_MUTEX_NAME)
    bridge_running = bool(processes.get("bridge")) or probe_single_instance_mutex(BRIDGE_MUTEX_NAME)
    paused = bool(control.get("paused"))
    last_error = log_state.get("last_error", "") or ""

    semantic_state, label, hint = _semantic_state(paused, tray_running, bridge_running, last_error)
    badge_color = {
        "running": "#10B981",
        "listening": "#10B981",
        "paused": "#F59E0B",
        "warn": "#3B82F6" if tray_running and not bridge_running else "#F59E0B",
        "stopped": "#EF4444",
        "unknown": "#94A3B8",
    }.get(semantic_state, "#94A3B8")

    base_snapshot = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "version": APP_VERSION,
        "badge": {
            "state": semantic_state,
            "label": semantic_state.upper() if semantic_state != "warn" else "ATTENTION",
            "hint": hint,
            "color": badge_color,
        },
        "badge_label": label,
        "summary": {
            "tray_running": tray_running,
            "bridge_running": bridge_running,
            "mode": log_state.get("mode", "unknown") if not paused else "paused",
            "health": semantic_state,
            "paused": paused,
            "last_error": last_error,
            "last_event": log_state.get("last_event", "") or "",
            "runtime_signal": runtime_signal or {},
        },
        "control": control,
        "config": _safe_env(env),
        "processes": {
            "tray": processes.get("tray", []),
            "bridge": processes.get("bridge", []),
        },
        "runtime_signal": runtime_signal or {},
        "logs": snapshot.get("logs", []),
        "status_lines": snapshot.get("status_lines", []),
        "log_state": log_state,
    }
    return _apply_runtime_snapshot(base_snapshot, runtime_snapshot)


def _json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def _run_probe() -> Tuple[int, str]:
    if not PROBE_SCRIPT.exists():
        return 1, f"Probe script not found: {PROBE_SCRIPT}"
    proc = subprocess.run(
        [sys.executable, str(PROBE_SCRIPT)],
        cwd=str(BASE_DIR),
        capture_output=True,
        timeout=180,
        creationflags=CREATE_NO_WINDOW,
    )
    output = proc.stdout.decode("utf-8", errors="replace")
    if proc.stderr:
        output += "\n--- STDERR ---\n" + proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode, output.strip() or "(no output)"


def _start_tray() -> Tuple[bool, str]:
    if not TRAY_SCRIPT.exists():
        return False, f"Tray script not found: {TRAY_SCRIPT}"
    try:
        subprocess.Popen(
            [sys.executable, "-B", str(TRAY_SCRIPT)],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        return True, "Tray launched"
    except Exception as exc:
        return False, f"Could not launch tray: {exc}"


def _kill_matching_processes(needle: str) -> List[str]:
    if os.name != "nt":
        return []
    state = query_windows_voice_processes(BASE_DIR)
    killed: List[str] = []
    for group in (state.get("tray", []), state.get("bridge", [])):
        for proc in group:
            cmd = str(proc.get("cmd", ""))
            if needle not in cmd.lower():
                continue
            pid = str(proc.get("pid", ""))
            if not pid:
                continue
            subprocess.run(
                ["taskkill", "/PID", pid, "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            killed.append(pid)
    return killed


def _restart_tray() -> Tuple[bool, str]:
    killed = _kill_matching_processes("windows_hermes_voice_tray.py")
    ok, message = _start_tray()
    if killed:
        return ok, f"Restarted tray; killed PIDs {', '.join(killed)}"
    return ok, message


def _restart_bridge() -> Tuple[bool, str]:
    killed = _kill_matching_processes("windows_hermes_voice.py")
    save_control_state(CONTROL_FILE, False)
    if not killed:
        return True, "Bridge restart requested"
    return True, f"Restarted bridge; killed PIDs {', '.join(killed)}"


def _repair_autostart() -> Tuple[bool, str]:
    script = BASE_DIR / "scripts" / "install_autostart.ps1"
    if not script.exists():
        return False, f"Autostart script not found: {script}"

    launchers = ["powershell.exe", "pwsh"]
    last_error = ""
    for launcher in launchers:
        try:
            proc = subprocess.run(
                [launcher, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=CREATE_NO_WINDOW,
            )
            output = (proc.stdout or "").strip()
            error = (proc.stderr or "").strip()
            if proc.returncode == 0:
                message = output or "Autostart repaired"
                if error:
                    message = f"{message}\n{error}"
                return True, message
            last_error = output or error or f"exit code {proc.returncode}"
        except FileNotFoundError as exc:
            last_error = str(exc)
        except Exception as exc:  # pragma: no cover - platform specific
            last_error = str(exc)
    return False, f"Could not repair autostart: {last_error}"


def _serve_file(handler: BaseHTTPRequestHandler, path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    data = path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)
    return True


def _parse_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    raw = handler.rfile.read(int(handler.headers.get("Content-Length", "0") or 0))
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _normalize_config_updates(payload: Dict[str, Any]) -> Dict[str, str]:
    updates: Dict[str, str] = {}
    for form_key, env_key in CONFIG_KEYS.items():
        if form_key not in payload:
            continue
        value = payload.get(form_key)
        if value is None:
            continue
        if env_key == "HERMES_MIC_DEVICE":
            text = str(value).strip()
            updates[env_key] = "" if text in {"", "default", "none", "-1"} else str(int(text))
        else:
            updates[env_key] = str(value).strip()

    if "HERMES_MIC_DEVICE" in updates:
        selected_value = updates["HERMES_MIC_DEVICE"]
        if not selected_value:
            updates["HERMES_MIC_DEVICE_NAME"] = ""
            updates["HERMES_MIC_DEVICE_HOSTAPI"] = ""
        else:
            selected_index = int(selected_value)
            selected_device = next((device for device in AUDIO_SERVICE.get_devices() if device.get("index") == selected_index), None)
            if selected_device:
                updates["HERMES_MIC_DEVICE_NAME"] = str(selected_device.get("name", ""))
                hostapi = selected_device.get("hostapi")
                updates["HERMES_MIC_DEVICE_HOSTAPI"] = "" if hostapi is None else str(hostapi)
    return updates


class PanelApiHandler(BaseHTTPRequestHandler):
    server_version = "HermesVoicePanelAPI/0.2"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _client_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        return forwarded or self.client_address[0]

    def _check_rate_limit(self) -> bool:
        return _check_rate_limit(self._client_ip())

    def _require_token(self) -> bool:
        return _check_panel_token(self)

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        origin = self.headers.get("Origin", "")
        if _local_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin or "http://127.0.0.1")
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, text: str, status: HTTPStatus = HTTPStatus.OK, content_type: str = "text/plain; charset=utf-8") -> None:
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        origin = self.headers.get("Origin", "")
        if _local_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin or "http://127.0.0.1")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin", "")
        if not _local_origin(origin):
            self.send_response(HTTPStatus.FORBIDDEN)
            self.end_headers()
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", origin or "http://127.0.0.1")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Hermes-Panel-Token")
        self.end_headers()

    def do_GET(self) -> None:
        if not self._check_rate_limit():
            self._send_json({"ok": False, "error": "rate limit exceeded"}, status=HTTPStatus.TOO_MANY_REQUESTS)
            return
        path = urlparse(self.path).path
        if path == "/api/status":
            self._send_json(_build_snapshot())
            return
        if path == "/api/config":
            self._send_json({"config": _safe_env(load_env_file(VOICE_ENV, update_os_environ=False)), "devices": _list_audio_devices()})
            return
        if path == "/api/session":
            self._send_json({"session": _build_snapshot().get("runtime", {}).get("session", {})})
            return
        if path == "/api/devices":
            self._send_json(_list_audio_devices())
            return
        if path == "/api/logs":
            self._send_json({"logs": _build_snapshot()["logs"]})
            return
        if path == "/api/stream":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            origin = self.headers.get("Origin", "")
            if _local_origin(origin):
                self.send_header("Access-Control-Allow-Origin", origin or "http://127.0.0.1")
            self.end_headers()
            try:
                while True:
                    snap = _build_snapshot()
                    payload = json.dumps({"snapshot": snap, "logs": snap["logs"]}, ensure_ascii=False)
                    self.wfile.write(b"event: snapshot\n")
                    for line in (payload.splitlines() or ["{}"]):
                        self.wfile.write(f"data: {line}\n".encode("utf-8"))
                    self.wfile.write(b"\n")
                    self.wfile.flush()
                    time.sleep(1.5)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return
        if DIST_DIR.exists():
            rel = path.lstrip("/")
            candidate = (DIST_DIR / rel) if rel else (DIST_DIR / "index.html")
            try:
                candidate = candidate.resolve()
                dist_root = DIST_DIR.resolve()
                if candidate != dist_root and dist_root not in candidate.parents:
                    raise ValueError("outside dist")
            except Exception:
                candidate = DIST_DIR / "index.html"
            if candidate.is_dir():
                candidate = candidate / "index.html"
            if _serve_file(self, candidate):
                return
            if _serve_file(self, DIST_DIR / "index.html"):
                return
        self._send_text("Hermes Voice Bridge control API is running. Open the desktop app to view it.")

    def do_POST(self) -> None:
        if not self._check_rate_limit():
            self._send_json({"ok": False, "error": "rate limit exceeded"}, status=HTTPStatus.TOO_MANY_REQUESTS)
            return
        if not self._require_token():
            self._send_json({"ok": False, "error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
            return
        path = urlparse(self.path).path
        action = path.removeprefix("/api/action/")
        if not action:
            self._send_json({"ok": False, "error": "missing action"}, status=HTTPStatus.NOT_FOUND)
            return

        if action == "pause":
            save_control_state(CONTROL_FILE, True)
        elif action == "resume":
            save_control_state(CONTROL_FILE, False)
        elif action == "toggle":
            save_control_state(CONTROL_FILE, not load_control_state(CONTROL_FILE))
        elif action == "start-tray":
            ok, message = _start_tray()
            payload = _build_snapshot()
            payload["action"] = {"ok": ok, "message": message}
            self._send_json(payload)
            return
        elif action == "restart-tray":
            ok, message = _restart_tray()
            payload = _build_snapshot()
            payload["action"] = {"ok": ok, "message": message}
            self._send_json(payload)
            return
        elif action == "restart-bridge":
            ok, message = _restart_bridge()
            payload = _build_snapshot()
            payload["action"] = {"ok": ok, "message": message}
            self._send_json(payload)
            return
        elif action == "repair-autostart":
            ok, message = _repair_autostart()
            payload = _build_snapshot()
            payload["action"] = {"ok": ok, "message": message}
            self._send_json(payload)
            return
        elif action == "save-config":
            payload = _parse_json_body(self)
            updates = _normalize_config_updates(payload)
            final_env = save_env_file(VOICE_ENV, updates)
            if updates.get("HERMES_PERSIST_SESSION") == "0":
                _logout_persisted_session(reason="disabled")
            snapshot = _build_snapshot()
            snapshot["action"] = {
                "ok": True,
                "message": "Config saved",
                "needs_restart": True,
                "updated_keys": sorted(updates.keys()),
                "voice_env": final_env,
            }
            self._send_json(snapshot)
            return
        elif action == "save-session":
            payload = _parse_json_body(self)
            try:
                record = _save_persisted_session(payload)
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            snapshot = _build_snapshot()
            snapshot["action"] = {
                "ok": True,
                "message": "Session saved",
                "remember_me": record.remember_me,
                "user_id": record.user_id,
            }
            self._send_json(snapshot)
            return
        elif action == "logout-session":
            payload = _parse_json_body(self)
            _logout_persisted_session(reason=str(payload.get("reason", "manual") or "manual"))
            snapshot = _build_snapshot()
            snapshot["action"] = {"ok": True, "message": "Session cleared"}
            self._send_json(snapshot)
            return
        elif action == "refresh-session":
            try:
                record = _refresh_persisted_session()
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            except RuntimeError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.CONFLICT)
                return
            snapshot = _build_snapshot()
            snapshot["action"] = {
                "ok": True,
                "message": "Session refreshed",
                "expires_at": record.expires_at,
            }
            self._send_json(snapshot)
            return
        elif action == "open-folder":
            if os.name == "nt":
                os.startfile(str(BASE_DIR))
        elif action == "open-logs":
            if os.name == "nt":
                os.startfile(str(LOG_DIR))
        elif action == "open-env":
            if os.name == "nt":
                os.startfile(str(VOICE_ENV))
        elif action == "probe":
            code, output = _run_probe()
            payload = _build_snapshot()
            payload["probe"] = {"exit_code": code, "output": output}
            self._send_json(payload)
            return
        else:
            self._send_json({"ok": False, "error": f"unknown action: {action}"}, status=HTTPStatus.NOT_FOUND)
            return

        payload = _build_snapshot()
        payload["action"] = {"ok": True, "message": action}
        self._send_json(payload)


def serve(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer((host, port), PanelApiHandler)
    print(f"Hermes voice panel API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    api_mutex = acquire_single_instance_mutex(PANEL_API_MUTEX_NAME)
    if api_mutex is None:
        print("Hermes voice panel API already running")
        raise SystemExit(0)
    try:
        serve()
    finally:
        release_single_instance_mutex(api_mutex)
