#!/usr/bin/env python3
"""Shared helpers for the Hermes Windows voice bridge UI.

This module stays dependency-light so it can be imported by both the tray
launcher and the optional control panel without pulling in audio or GUI
libraries.
"""
from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ERROR_ALREADY_EXISTS = 183
TRAY_MUTEX_NAME = r"Local\HermesVoiceBridgeTray"
BRIDGE_MUTEX_NAME = r"Local\HermesVoiceBridgeBridge"
PANEL_API_MUTEX_NAME = r"Local\HermesVoicePanelApi"


def load_env_file(path: Path, *, update_os_environ: bool = True) -> Dict[str, str]:
    """Load KEY=VALUE pairs from a local env file.

    Returns the parsed values so callers can inspect them directly.
    """
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        values[key] = value
        if update_os_environ and key not in os.environ:
            os.environ[key] = value
    return values


def save_env_file(path: Path, updates: Dict[str, str]) -> Dict[str, str]:
    """Persist KEY=VALUE pairs into a simple env file and return the final mapping."""
    current = load_env_file(path, update_os_environ=False)
    for key, value in updates.items():
        if value is None:
            continue
        current[key] = str(value)
    lines = [f"{key}={value}" for key, value in sorted(current.items()) if value != ""]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return current


def read_json_file(path: Path, default: Optional[dict] = None) -> dict:
    default = {} if default is None else dict(default)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_file(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_control_state(path: Path) -> bool:
    data = read_json_file(path, default={"paused": False})
    return bool(data.get("paused", False))


def save_control_state(path: Path, paused: bool) -> None:
    write_json_file(path, {"paused": bool(paused)})


def acquire_single_instance_mutex(name: str):
    """Acquire a named Windows mutex and return the handle, or None if held."""
    if os.name != "nt":
        return object()
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        return None
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


def probe_single_instance_mutex(name: str) -> bool:
    """Return True when another process is currently holding the mutex."""
    if os.name != "nt":
        return False
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        return False
    held_elsewhere = kernel32.GetLastError() == ERROR_ALREADY_EXISTS
    kernel32.CloseHandle(handle)
    return held_elsewhere


def release_single_instance_mutex(handle) -> None:
    if os.name != "nt" or not handle:
        return
    kernel32 = ctypes.windll.kernel32
    try:
        kernel32.ReleaseMutex(handle)
    finally:
        kernel32.CloseHandle(handle)


def read_tail(path: Path, max_lines: int = 80) -> List[str]:
    if max_lines <= 0 or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-max_lines:]


def parse_process_lines(lines: Iterable[str]) -> Dict[str, Any]:
    """Parse pipe-delimited process lines emitted by PowerShell.

    Expected format per line:
    PID=123|NAME=pythonw.exe|CMD=C:\\path\\script.py
    """
    result = {
        "tray": [],
        "bridge": [],
    }
    for raw in lines:
        line = raw.strip()
        if not line.startswith("PID="):
            continue
        parts = {}
        for chunk in line.split("|"):
            if "=" not in chunk:
                continue
            key, value = chunk.split("=", 1)
            parts[key.strip().lower()] = value.strip()
        pid = parts.get("pid")
        name = parts.get("name", "")
        cmd = parts.get("cmd", "")
        if not pid:
            continue
        entry = {"pid": pid, "name": name, "cmd": cmd}
        lowered = cmd.lower()
        if "windows_hermes_voice_tray.py" in lowered:
            result["tray"].append(entry)
        if "windows_hermes_voice.py" in lowered and "windows_hermes_voice_tray.py" not in lowered:
            result["bridge"].append(entry)
    return result


def query_windows_voice_processes(base_dir: Path, timeout_seconds: int = 8) -> Dict[str, Any]:
    """Query the live Windows process tree for tray/bridge python processes."""
    if os.name != "nt":
        return {"tray": [], "bridge": [], "raw": []}

    script = r'''
$ErrorActionPreference = "Stop"
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'windows_hermes_voice(_tray)?\.py' } |
  ForEach-Object { Write-Output ("PID=" + $_.ProcessId + "|NAME=" + $_.Name + "|CMD=" + $_.CommandLine) }
'''.strip()
    encoded = script.encode("utf-16le")
    import base64

    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-EncodedCommand",
        base64.b64encode(encoded).decode("ascii"),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(base_dir),
        capture_output=True,
        timeout=timeout_seconds,
        creationflags=CREATE_NO_WINDOW,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    lines = [line for line in stdout.splitlines() if line.strip()]
    parsed = parse_process_lines(lines)
    parsed["raw"] = lines
    return parsed


def parse_log_state(lines: Sequence[str]) -> Dict[str, Any]:
    state = {
        "tray_state": "unknown",
        "bridge_state": "unknown",
        "mode": "unknown",
        "last_event": "",
        "last_error": "",
        "last_good": "",
    }
    for raw in lines:
        line = raw.strip()
        lowered = line.lower()
        if "tray starting" in lowered:
            state["tray_state"] = "running"
        if "bridge started pid=" in lowered:
            state["bridge_state"] = "running"
        if "paused" in lowered:
            state["mode"] = "paused"
        if "resumed" in lowered:
            state["mode"] = "listening"
        if "bridge exited code=" in lowered:
            state["bridge_state"] = "stopped"
            state["last_error"] = line
        if "failed to start bridge:" in lowered:
            state["last_error"] = line
        if "retrying in " in lowered:
            state["last_error"] = line
        if "post event=voice route=voice" in lowered:
            state["last_event"] = line
        if "inbound message: platform=webhook user=voice" in lowered:
            state["last_event"] = line
        if "response ready: platform=webhook" in lowered:
            state["last_good"] = line
    return state


def build_status_snapshot(
    *,
    base_dir: Path,
    env_path: Path,
    control_path: Path,
    log_paths: Sequence[Path],
) -> Dict[str, Any]:
    env = load_env_file(env_path, update_os_environ=False)
    control = {"paused": load_control_state(control_path)}
    logs: List[str] = []
    for path in log_paths:
        if path.exists():
            lines = read_tail(path, 80)
            logs.extend([f"[{path.name}] {line}" for line in lines])
    log_state = parse_log_state(logs)
    process_state = query_windows_voice_processes(base_dir)

    tray_running = bool(process_state["tray"]) or probe_single_instance_mutex(TRAY_MUTEX_NAME)
    bridge_running = bool(process_state["bridge"]) or probe_single_instance_mutex(BRIDGE_MUTEX_NAME)
    if tray_running:
        log_state["tray_state"] = "running"
    if bridge_running and log_state["bridge_state"] == "unknown":
        log_state["bridge_state"] = "running"
    if control["paused"]:
        log_state["mode"] = "paused"
    elif log_state["mode"] == "unknown" and bridge_running:
        log_state["mode"] = "listening"

    status_lines = [
        f"Tray: {'running' if tray_running else 'stopped'}",
        f"Bridge: {'running' if bridge_running else 'stopped'}",
        f"Mode: {log_state['mode']}",
        f"Webhook URL: {env.get('HERMES_WEBHOOK_URL', '(missing)')}",
        f"Hotkey: {env.get('HERMES_HOTKEY', '(default)') or '(default)'}",
        f"Wake phrases: {env.get('HERMES_WAKE_PHRASES', '(default)')}",
        f"Feedback: {env.get('HERMES_FEEDBACK_MODE', '(default)')}",
        f"STT: {env.get('HERMES_STT_LANGUAGE', '(default)')} / {env.get('HERMES_STT_MODEL', '(default)')}",
    ]
    if log_state.get("last_event"):
        status_lines.append(f"Last event: {log_state['last_event']}")
    if log_state.get("last_good"):
        status_lines.append(f"Last response: {log_state['last_good']}")
    if log_state.get("last_error"):
        status_lines.append(f"Last error: {log_state['last_error']}")

    return {
        "env": env,
        "control": control,
        "logs": logs,
        "processes": process_state,
        "log_state": log_state,
        "status_lines": status_lines,
    }
