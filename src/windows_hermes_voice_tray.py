#!/usr/bin/env python3
"""Tray-owned runtime shell for Hermes Voice Bridge.

This process is now the lifecycle owner for the Windows client runtime:
- owns bridge + panel API process supervision
- owns central app state + event bus + logging
- persists a live runtime snapshot for desktop/API consumers
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.core.config import ConfigService
from src.core.events import EventBus
from src.core.lifecycle import AppLifecycle
from src.core.logging import BridgeLogger, LogPaths
from src.core.session import build_session_manager
from src.core.state import AppStateStore
from src.storage.cache import JsonRuntimeSignalStore, JsonRuntimeStateStore
from windows_hermes_voice_control import (
    TRAY_MUTEX_NAME,
    acquire_single_instance_mutex,
    load_control_state,
    release_single_instance_mutex,
    save_control_state,
)

try:
    import pystray
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: pystray. Install with: pip install pystray pillow"
    ) from exc

try:
    from PIL import Image, ImageDraw
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: pillow. Install with: pip install pystray pillow"
    ) from exc

SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent
STATE_DIR = BASE_DIR / "state"
BRIDGE_SCRIPT = SRC_DIR / "windows_hermes_voice.py"
DESKTOP_APP_SCRIPT = SRC_DIR / "windows_hermes_voice_desktop.py"
PANEL_API_SCRIPT = BASE_DIR / "src" / "windows_hermes_voice_panel_api.py"
VOICE_ENV = STATE_DIR / "voice.env"
CONTROL_FILE = STATE_DIR / "voice.control.json"
RUNTIME_STATE_FILE = STATE_DIR / "runtime_state.json"
RUNTIME_SIGNAL_FILE = STATE_DIR / "runtime_signal.json"
SESSION_FILE = STATE_DIR / "session.json"
SESSION_SECRETS_FILE = STATE_DIR / "session.secrets"
LOG_DIR = STATE_DIR / "logs" / "HermesVoiceBridge"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TRAY_LOG = LOG_DIR / "tray.log"
DEBUG_LOG = LOG_DIR / "debug.log"
CRASH_LOG = LOG_DIR / "crash.log"
BRIDGE_LOG = LOG_DIR / "bridge.log"
PANEL_API_LOG = LOG_DIR / "panel-api.log"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PANEL_API_PORT = int(os.environ.get("HERMES_PANEL_PORT", "8765"))
TASK_NAME = "Hermes Voice Bridge"
STARTUP_SHORTCUT = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Hermes Voice Bridge.lnk"
PROGRAMS_DIR = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
DESKTOP_SHORTCUT = PROGRAMS_DIR / "Hermes Voice Bridge (Desktop).lnk"
LEGACY_WEB_SHORTCUT = PROGRAMS_DIR / "Hermes Voice Panel (Web).lnk"
APP_VERSION = "0.3.0"

LOGGERS = BridgeLogger(LogPaths(user_log=TRAY_LOG, debug_log=DEBUG_LOG, crash_log=CRASH_LOG))
EVENTS = EventBus()
APP_STATE = AppStateStore()
LIFECYCLE = AppLifecycle(APP_STATE, EVENTS, LOGGERS)
CONFIG = ConfigService(VOICE_ENV)
RUNTIME_STORE = JsonRuntimeStateStore(RUNTIME_STATE_FILE)
SIGNAL_STORE = JsonRuntimeSignalStore(RUNTIME_SIGNAL_FILE)
SESSION_MANAGER = build_session_manager(STATE_DIR, EVENTS, APP_STATE)


@dataclass
class State:
    paused: bool = False
    stopping: bool = False
    bridge: Optional[subprocess.Popen] = None
    api: Optional[subprocess.Popen] = None
    restart_backoff: int = 3
    api_backoff: int = 3
    last_error: str = ""
    last_event: str = ""


STATE = State()
STATE_LOCK = threading.Lock()
ICON = None
TRAY_MUTEX_HANDLE = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str, *, channel: str = "user", level: str = "info") -> None:
    logger = getattr(LOGGERS, channel)
    getattr(logger, level)(message)


def set_last_error(message: str) -> None:
    STATE.last_error = message
    APP_STATE.update(last_error=message)
    if message:
        EVENTS.publish("runtime.error", message=message)


def _as_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"", "0", "false", "no", "off"}


def sync_session_state() -> None:
    persist_enabled = _as_bool(CONFIG.load().get("HERMES_PERSIST_SESSION", "1"), True)
    if not persist_enabled:
        if SESSION_FILE.exists() or SESSION_SECRETS_FILE.exists():
            SESSION_MANAGER.logout(reason="disabled")
        else:
            APP_STATE.patch_session(authenticated=False, remember_me=False, restoration_source="disabled")
        return

    record = SESSION_MANAGER.restore()
    if record is None:
        APP_STATE.patch_session(authenticated=False, remember_me=True, restoration_source="empty")


def current_runtime_signal() -> dict:
    return SIGNAL_STORE.load() or {}


def make_icon_image(running: bool = True):
    size = 64
    color = (42, 145, 255) if running else (120, 120, 120)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((6, 6, size - 6, size - 6), radius=14, fill=color)
    draw.ellipse((18, 18, 46, 46), outline=(255, 255, 255, 255), width=4)
    draw.line((46, 32, 56, 32), fill=(255, 255, 255, 255), width=4)
    draw.line((52, 28, 56, 32), fill=(255, 255, 255, 255), width=4)
    draw.line((52, 36, 56, 32), fill=(255, 255, 255, 255), width=4)
    return img


def bridge_env() -> dict[str, str]:
    CONFIG.load()
    return os.environ.copy()


def is_bridge_running() -> bool:
    bridge = STATE.bridge
    return bool(bridge and bridge.poll() is None)


def is_panel_api_running() -> bool:
    api = STATE.api
    if api and api.poll() is None:
        return True
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{PANEL_API_PORT}/api/status", timeout=0.5):
            return True
    except Exception:
        return False


def runtime_health() -> tuple[str, str, str, str]:
    paused = STATE.paused
    bridge_running = is_bridge_running()
    api_running = is_panel_api_running()
    if STATE.stopping:
        return "stopping", "STOPPING", "Shutting down Hermes Voice Bridge", "#94A3B8"
    if paused:
        return "paused", "PAUSED", "Listening stopped by user", "#F59E0B"
    if bridge_running and api_running and not STATE.last_error:
        return "ready", "READY", "Tray, bridge and local API are healthy", "#10B981"
    if bridge_running and api_running:
        return "warn", "ATTENTION", STATE.last_error or "Bridge is running with warnings", "#F59E0B"
    if api_running or bridge_running:
        return "starting", "STARTING", "Runtime is recovering services", "#3B82F6"
    return "stopped", "STOPPED", STATE.last_error or "Runtime is down", "#EF4444"


def sync_runtime_state() -> None:
    sync_session_state()
    bridge_running = is_bridge_running()
    api_running = is_panel_api_running()
    health_state, badge_label, hint, color = runtime_health()
    mode = "paused" if STATE.paused else ("listening" if bridge_running else "starting")
    ts = now_iso()
    runtime_signal = current_runtime_signal()

    APP_STATE.patch_service("tray", state="running" if not STATE.stopping else "stopping", detail=badge_label, last_updated_at=ts)
    APP_STATE.patch_service(
        "bridge",
        state="running" if bridge_running else ("paused" if STATE.paused else "stopped"),
        detail=mode,
        pid=STATE.bridge.pid if bridge_running and STATE.bridge else None,
        last_updated_at=ts,
    )
    APP_STATE.patch_service(
        "api",
        state="running" if api_running else "stopped",
        detail="local-api",
        pid=STATE.api.pid if STATE.api and STATE.api.poll() is None else None,
        last_updated_at=ts,
    )
    APP_STATE.update(last_error=STATE.last_error, overlay_state=runtime_signal.get("kind", ""))

    payload = {
        "generated_at": ts,
        "version": APP_VERSION,
        "lifecycle": APP_STATE.state.lifecycle,
        "badge": {
            "state": health_state,
            "label": badge_label,
            "hint": hint,
            "color": color,
        },
        "badge_label": badge_label.title(),
        "summary": {
            "tray_running": not STATE.stopping,
            "bridge_running": bridge_running,
            "api_running": api_running,
            "mode": mode,
            "health": health_state,
            "paused": STATE.paused,
            "last_error": STATE.last_error,
            "last_event": STATE.last_event,
            "runtime_signal": runtime_signal,
        },
        "control": {"paused": STATE.paused},
        "runtime_signal": runtime_signal,
        "runtime": APP_STATE.snapshot(),
        "processes": {
            "tray": [{"pid": os.getpid(), "name": Path(sys.executable).name, "cmd": "windows_hermes_voice_tray.py"}],
            "bridge": ([{"pid": str(STATE.bridge.pid), "name": Path(sys.executable).name, "cmd": "windows_hermes_voice.py"}] if bridge_running and STATE.bridge else []),
            "api": ([{"pid": str(STATE.api.pid), "name": Path(sys.executable).name, "cmd": "windows_hermes_voice_panel_api.py"}] if STATE.api and STATE.api.poll() is None else []),
        },
    }
    RUNTIME_STORE.save(payload)


def start_panel_api() -> None:
    if not PANEL_API_SCRIPT.exists():
        raise FileNotFoundError(f"Panel API script not found: {PANEL_API_SCRIPT}")
    if is_panel_api_running():
        sync_runtime_state()
        return

    stdout = open(PANEL_API_LOG, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-B", str(PANEL_API_SCRIPT)],
        cwd=str(BASE_DIR),
        env=bridge_env(),
        stdout=stdout,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )
    STATE.api = proc
    STATE.api_backoff = 3
    STATE.last_event = f"panel api started pid={proc.pid}"
    log(STATE.last_event)
    EVENTS.publish("api.started", pid=proc.pid)
    sync_runtime_state()


def stop_panel_api() -> None:
    proc = STATE.api
    if not proc:
        sync_runtime_state()
        return
    if proc.poll() is not None:
        STATE.api = None
        sync_runtime_state()
        return
    message = f"stopping panel api pid={proc.pid}"
    log(message)
    try:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    STATE.api = None
    EVENTS.publish("api.stopped")
    sync_runtime_state()


def start_bridge() -> None:
    if not BRIDGE_SCRIPT.exists():
        raise FileNotFoundError(f"Bridge script not found: {BRIDGE_SCRIPT}")
    if is_bridge_running():
        sync_runtime_state()
        return

    stdout = open(BRIDGE_LOG, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-B", str(BRIDGE_SCRIPT)],
        cwd=str(BASE_DIR),
        env=bridge_env(),
        stdout=stdout,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )
    STATE.bridge = proc
    STATE.restart_backoff = 3
    STATE.last_error = ""
    STATE.last_event = f"bridge started pid={proc.pid}"
    log(STATE.last_event)
    EVENTS.publish("audio.started", pid=proc.pid)
    sync_runtime_state()


def stop_bridge() -> None:
    proc = STATE.bridge
    if not proc:
        sync_runtime_state()
        return
    if proc.poll() is not None:
        STATE.bridge = None
        sync_runtime_state()
        return
    message = f"stopping bridge pid={proc.pid}"
    log(message)
    try:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    STATE.bridge = None
    EVENTS.publish("audio.stopped")
    sync_runtime_state()


def set_paused(value: bool) -> None:
    save_control_state(CONTROL_FILE, value)
    with STATE_LOCK:
        STATE.paused = value
    if value:
        stop_bridge()
        STATE.last_event = "paused"
        log("paused")
        EVENTS.publish("runtime.paused")
    else:
        STATE.last_event = "resumed"
        log("resumed")
        EVENTS.publish("runtime.resumed")
        start_bridge()
    sync_runtime_state()
    update_icon()


def restart_services() -> None:
    stop_bridge()
    stop_panel_api()
    save_control_state(CONTROL_FILE, False)
    with STATE_LOCK:
        STATE.paused = False
    set_last_error("")
    start_panel_api()
    start_bridge()
    STATE.last_event = "services restarted"
    EVENTS.publish("runtime.restarted")
    sync_runtime_state()
    update_icon()


def current_menu_status() -> str:
    _state, label, _hint, _color = runtime_health()
    return f"● {label.title()}"


def update_icon() -> None:
    if ICON is None:
        return
    try:
        health_state, label, hint, _color = runtime_health()
        running = health_state in {"ready", "warn", "starting"}
        ICON.icon = make_icon_image(running=running)
        ICON.title = f"Hermes Voice Bridge - {label.lower()} · {hint}"
        ICON.update_menu()
    except Exception as exc:
        log(f"icon update failed: {exc}", channel="debug")


def monitor_loop() -> None:
    while not STATE.stopping:
        paused = load_control_state(CONTROL_FILE)
        with STATE_LOCK:
            STATE.paused = paused

        if not is_panel_api_running():
            try:
                start_panel_api()
                time.sleep(1.0)
            except Exception as exc:
                message = f"failed to start panel api: {exc}"
                set_last_error(message)
                log(message)
                log(f"retrying panel api in {STATE.api_backoff}s")
                sync_runtime_state()
                time.sleep(STATE.api_backoff)
                STATE.api_backoff = min(STATE.api_backoff * 2, 60)
        else:
            STATE.api_backoff = 3

        if paused:
            if is_bridge_running():
                stop_bridge()
            sync_runtime_state()
            update_icon()
            time.sleep(1.0)
            continue

        if not is_bridge_running():
            try:
                start_bridge()
                update_icon()
                time.sleep(1.0)
                continue
            except Exception as exc:
                message = f"failed to start bridge: {exc}"
                set_last_error(message)
                log(message)
                log(f"retrying in {STATE.restart_backoff}s")
                sync_runtime_state()
                time.sleep(STATE.restart_backoff)
                STATE.restart_backoff = min(STATE.restart_backoff * 2, 60)
                continue

        proc = STATE.bridge
        if proc is not None:
            code = proc.poll()
            if code is not None:
                message = f"bridge exited code={code}"
                log(message)
                set_last_error(message)
                STATE.bridge = None
                update_icon()
                sync_runtime_state()
                time.sleep(STATE.restart_backoff)
                STATE.restart_backoff = min(STATE.restart_backoff * 2, 60)
                continue

        sync_runtime_state()
        update_icon()
        time.sleep(1.0)


def on_pause(icon, item):
    set_paused(True)


def on_resume(icon, item):
    set_paused(False)


def on_restart(icon, item):
    restart_services()


def on_open_logs(icon, item):
    os.startfile(str(LOG_DIR))


def cleanup_shortcuts_and_task() -> None:
    for path in (STARTUP_SHORTCUT, DESKTOP_SHORTCUT, LEGACY_WEB_SHORTCUT):
        try:
            if path.exists():
                path.unlink()
                log(f"removed shortcut {path}")
        except Exception as exc:
            log(f"could not remove shortcut {path}: {exc}")

    try:
        subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception as exc:
        log(f"could not remove scheduled task {TASK_NAME}: {exc}")


def on_open_panel(icon, item):
    if DESKTOP_APP_SCRIPT.exists():
        subprocess.Popen(
            [sys.executable, "-B", str(DESKTOP_APP_SCRIPT)],
            cwd=str(BASE_DIR),
            env=bridge_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
    else:
        os.startfile(str(BASE_DIR))


def on_exit(icon, item):
    global ICON, TRAY_MUTEX_HANDLE
    STATE.stopping = True
    sync_runtime_state()
    cleanup_shortcuts_and_task()
    try:
        LIFECYCLE.stop()
        icon.stop()
    finally:
        if TRAY_MUTEX_HANDLE is not None:
            release_single_instance_mutex(TRAY_MUTEX_HANDLE)
            TRAY_MUTEX_HANDLE = None
        ICON = None
        RUNTIME_STORE.delete()
        SIGNAL_STORE.clear()
        log("exited")


def build_menu() -> pystray.Menu:
    return pystray.Menu(
        pystray.MenuItem(lambda item: current_menu_status(), lambda icon, item: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start Listening", on_resume),
        pystray.MenuItem("Stop Listening", on_pause),
        pystray.MenuItem("Open Hermes", on_open_panel),
        pystray.MenuItem("View Logs", on_open_logs),
        pystray.MenuItem("Settings", on_open_panel),
        pystray.MenuItem("Restart Services", on_restart),
        pystray.MenuItem("Quit", on_exit),
    )


def main() -> int:
    global ICON, TRAY_MUTEX_HANDLE
    TRAY_MUTEX_HANDLE = acquire_single_instance_mutex(TRAY_MUTEX_NAME)
    if TRAY_MUTEX_HANDLE is None:
        log("tray already running; exiting")
        return 0

    log("tray starting")
    with STATE_LOCK:
        STATE.paused = load_control_state(CONTROL_FILE)

    LIFECYCLE.on_shutdown(stop_bridge)
    LIFECYCLE.on_shutdown(stop_panel_api)
    LIFECYCLE.start()
    sync_runtime_state()

    start_panel_api()
    if not STATE.paused:
        start_bridge()

    ICON = pystray.Icon(
        "HermesVoiceBridge",
        make_icon_image(running=not STATE.paused),
        f"Hermes Voice Bridge - {current_menu_status()}",
        build_menu(),
    )
    monitor = threading.Thread(target=monitor_loop, daemon=True)
    monitor.start()
    sync_runtime_state()
    ICON.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
