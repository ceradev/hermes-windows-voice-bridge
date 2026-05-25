#!/usr/bin/env python3
"""Native desktop settings app for the Hermes Windows voice bridge.

Phase 3 goal:
- utility-like window, not control-panel sprawl
- sidebar navigation instead of notebook tabs
- settings-first layout
- visual shortcut editor
- session persistence UX
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

import tkinter as tk
from tkinter import messagebox, ttk

from hermes_voice_bridge.ui.desktop import ApiClient, PALETTE, PillRow, LabeledSwitch, apply_desktop_theme
from hermes_voice_bridge.ui.overlays import StatusOverlayWindow, derive_overlay_signal
from hermes_voice_bridge.ui.settings import SessionPreferenceState, ShortcutEditorState
from windows_hermes_voice_control import (
    PANEL_API_MUTEX_NAME,
    acquire_single_instance_mutex,
    release_single_instance_mutex,
)

SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent
STATE_DIR = BASE_DIR / "state"
LOG_DIR = STATE_DIR / "logs" / "HermesVoiceBridge"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PANEL_API_SCRIPT = SRC_DIR / "windows_hermes_voice_panel_api.py"
PANEL_API_LOG = LOG_DIR / "panel-api.log"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PANEL_PORT = int(os.environ.get("HERMES_PANEL_PORT", "8765"))
PANEL_BASE_URL = f"http://127.0.0.1:{PANEL_PORT}"
DESKTOP_MUTEX_NAME = r"Local\HermesVoiceBridgeDesktop"

CONFIG_FIELDS = {
    "feedback_mode": ["(default)", "off", "beep", "voice", "both"],
}

CONFLICT_SHORTCUTS = {
    "alt+f4": "Windows close window",
    "ctrl+c": "Reserved copy/cancel",
    "ctrl+v": "Reserved paste",
}


API = ApiClient(PANEL_BASE_URL)


def _is_api_alive() -> bool:
    try:
        API.get("/api/status", timeout=0.8)
        return True
    except Exception:
        return False


def _start_panel_api() -> None:
    if not PANEL_API_SCRIPT.exists():
        raise FileNotFoundError(f"Panel API script not found: {PANEL_API_SCRIPT}")
    if _is_api_alive():
        return
    stdout = open(PANEL_API_LOG, "a", encoding="utf-8")
    subprocess.Popen(
        [sys.executable, "-B", str(PANEL_API_SCRIPT)],
        cwd=str(BASE_DIR),
        stdout=stdout,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
    )


def _wait_for_api(timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_api_alive():
            return True
        time.sleep(0.25)
    return False


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


class VoiceBridgeDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Hermes Voice Bridge")
        self.geometry("1320x900")
        self.minsize(1120, 760)
        self.configure(bg=PALETTE["app_bg"])
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._mutex = acquire_single_instance_mutex(DESKTOP_MUTEX_NAME)
        if self._mutex is None:
            messagebox.showinfo("Hermes Voice Bridge", "La app ya está abierta.")
            raise SystemExit(0)

        self._pending_refresh = False
        self._pending_action = False
        self._last_status: Dict[str, Any] = {}
        self._last_devices: Dict[str, Any] = {}
        self._section_frames: Dict[str, ttk.Frame] = {}
        self._nav_buttons: Dict[str, ttk.Button] = {}
        self._current_section = "general"
        self._pressed_keys: list[str] = []
        self.shortcut_state = ShortcutEditorState()
        self.session_state = SessionPreferenceState()
        self.overlay = StatusOverlayWindow(self)

        self._build_style()
        self._build_ui()
        self.after(250, self._bootstrap)

    def _build_style(self) -> None:
        apply_desktop_theme(self)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=18)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="App.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Hermes Voice Bridge", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Windows utility. Tray-first. Settings-first. Native-feeling control surface.",
            style="Hero.TLabel",
        ).pack(anchor="w", pady=(4, 12))

        topbar = ttk.Frame(root, style="App.TFrame")
        topbar.pack(fill="x", pady=(0, 14))
        self.badge = tk.Label(topbar, text="BOOTING", bg="#475569", fg="white", padx=12, pady=7, font=("Segoe UI", 10, "bold"))
        self.badge.pack(side="left")
        self.status_var = tk.StringVar(value="Starting…")
        tk.Label(topbar, textvariable=self.status_var, bg=PALETTE["app_bg"], fg=PALETTE["muted_fg"], font=("Segoe UI", 10)).pack(side="left", padx=(12, 0))
        ttk.Button(topbar, text="Refresh", style="Secondary.TButton", command=self.refresh_now).pack(side="right")
        ttk.Button(topbar, text="Restart Services", style="Primary.TButton", command=lambda: self.post_action("restart-tray")).pack(side="right", padx=(0, 10))

        body = ttk.Frame(root, style="App.TFrame")
        body.pack(fill="both", expand=True)

        sidebar = ttk.Frame(body, style="Sidebar.TFrame", padding=12)
        sidebar.pack(side="left", fill="y")
        ttk.Label(sidebar, text="SECTIONS", style="SidebarTitle.TLabel").pack(anchor="w", pady=(4, 12))

        self.content = ttk.Frame(body, style="App.TFrame")
        self.content.pack(side="left", fill="both", expand=True, padx=(16, 0))

        sections = [
            ("general", "General"),
            ("audio", "Audio"),
            ("shortcuts", "Shortcuts"),
            ("session", "Session"),
            ("hermes", "Hermes"),
            ("tts", "TTS"),
            ("logs", "Logs"),
        ]
        for key, label in sections:
            button = ttk.Button(sidebar, text=label, style="Sidebar.TButton", command=lambda name=key: self.show_section(name))
            button.pack(fill="x", pady=4)
            self._nav_buttons[key] = button

        self._build_general_section()
        self._build_audio_section()
        self._build_shortcuts_section()
        self._build_session_section()
        self._build_hermes_section()
        self._build_tts_section()
        self._build_logs_section()
        self.show_section("general")

    def _new_section(self, key: str) -> ttk.Frame:
        frame = ttk.Frame(self.content, style="Surface.TFrame", padding=18)
        self._section_frames[key] = frame
        return frame

    def _section_header(self, parent: ttk.Frame, title: str, description: str) -> None:
        ttk.Label(parent, text=title, style="Section.TLabel").pack(anchor="w")
        ttk.Label(parent, text=description, style="Muted.TLabel", wraplength=880).pack(anchor="w", pady=(4, 16))

    def _build_general_section(self) -> None:
        frame = self._new_section("general")
        self._section_header(frame, "General", "Tray utility defaults, startup behavior, and lightweight UX toggles.")

        self.general_cards = {}
        self.general_cards["overlay"] = LabeledSwitch(frame, "Show overlay feedback", "Small non-invasive overlay during listening, transcribing, and responding.")
        self.general_cards["overlay"].pack(fill="x", pady=(0, 14))
        self.general_cards["notifications"] = LabeledSwitch(frame, "Desktop notifications", "Native notices for errors, reconnects, and completed voice turns.")
        self.general_cards["notifications"].pack(fill="x", pady=(0, 14))

        actions = ttk.Frame(frame, style="Surface.TFrame")
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Pause Listening", command=lambda: self.post_action("pause")).pack(side="left")
        ttk.Button(actions, text="Resume Listening", command=lambda: self.post_action("resume")).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Repair Autostart", command=lambda: self.post_action("repair-autostart")).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Save General", command=self.save_general_settings).pack(side="right")

        self.general_status = tk.StringVar(value="Waiting for runtime…")
        ttk.Label(frame, textvariable=self.general_status, style="Muted.TLabel", wraplength=860).pack(anchor="w", pady=(18, 0))

    def _build_audio_section(self) -> None:
        frame = self._new_section("audio")
        self._section_header(frame, "Audio", "Microphone, wake sensitivity, and command-capture timing.")

        self.audio_vars = {key: tk.StringVar() for key in [
            "mic_device",
            "wake_phrases",
            "wake_energy",
            "silence_rms",
            "wake_window_seconds",
            "silence_timeout_seconds",
            "max_command_seconds",
        ]}

        form = ttk.Frame(frame, style="Surface.TFrame")
        form.pack(fill="x")
        fields = [
            ("mic_device", "Input device index"),
            ("wake_phrases", "Wake phrases"),
            ("wake_energy", "Wake energy"),
            ("silence_rms", "Silence RMS"),
            ("wake_window_seconds", "Wake window (s)"),
            ("silence_timeout_seconds", "Silence timeout (s)"),
            ("max_command_seconds", "Max command length (s)"),
        ]
        for row, (key, label) in enumerate(fields):
            ttk.Label(form, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))
            ttk.Entry(form, textvariable=self.audio_vars[key]).grid(row=row, column=1, sticky="ew", pady=6)
        form.columnconfigure(1, weight=1)

        devices_card = ttk.Frame(frame, style="Card.TFrame")
        devices_card.pack(fill="both", expand=True, pady=(16, 0))
        ttk.Label(devices_card, text="Available microphones", style="Section.TLabel").pack(anchor="w")
        ttk.Label(devices_card, text="Click a device to prefill the input device field.", style="Muted.TLabel").pack(anchor="w", pady=(4, 10))
        self.device_list = tk.Listbox(devices_card, height=12, activestyle="dotbox", bg=PALETTE["log_bg"], fg=PALETTE["body_fg"], selectbackground=PALETTE["accent"])
        self.device_list.pack(fill="both", expand=True)
        self.device_list.bind("<<ListboxSelect>>", self.on_device_select)

        ttk.Button(frame, text="Save Audio", command=self.save_audio_settings).pack(anchor="e", pady=(14, 0))

    def _build_shortcuts_section(self) -> None:
        frame = self._new_section("shortcuts")
        self._section_header(frame, "Shortcuts", "Modern hotkey capture with live pills, conflict warnings, and quick reset.")

        card = ttk.Frame(frame, style="Card.TFrame")
        card.pack(fill="x")
        ttk.Label(card, text="Global capture shortcut", style="Section.TLabel").pack(anchor="w")
        ttk.Label(card, text="Click record, press the combination, then save it.", style="Muted.TLabel").pack(anchor="w", pady=(4, 10))

        self.shortcut_caption = tk.StringVar(value=self.shortcut_state.caption)
        ttk.Label(card, textvariable=self.shortcut_caption, style="Body.TLabel").pack(anchor="w")

        self.shortcut_pills = PillRow(card, bg="#111827")
        self.shortcut_pills.pack(anchor="w", pady=(12, 12))

        self.shortcut_conflict = tk.StringVar(value="")
        ttk.Label(card, textvariable=self.shortcut_conflict, style="Muted.TLabel", wraplength=860).pack(anchor="w")

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", pady=(14, 0))
        ttk.Button(actions, text="Record Shortcut", command=self.start_shortcut_capture).pack(side="left")
        ttk.Button(actions, text="Clear", command=self.clear_shortcut_capture).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Save Shortcut", command=self.save_shortcut_setting).pack(side="right")

        self.shortcut_hint = tk.StringVar(value="Suggested premium default: CTRL + SHIFT + SPACE")
        ttk.Label(frame, textvariable=self.shortcut_hint, style="Muted.TLabel", wraplength=860).pack(anchor="w", pady=(16, 0))

    def _build_session_section(self) -> None:
        frame = self._new_section("session")
        self._section_header(frame, "Session", "Persistent sign-in, restore expectations, and session lifecycle visibility.")

        self.session_switch = LabeledSwitch(frame, "Mantener sesión iniciada", "Restore Hermes session when the app restarts, unless the user signs out or the token expires.")
        self.session_switch.pack(fill="x", pady=(0, 16))

        status_card = ttk.Frame(frame, style="Card.TFrame")
        status_card.pack(fill="x")
        self.session_status = tk.StringVar(value=self.session_state.status_label)
        self.session_detail = tk.StringVar(value=self.session_state.detail)
        ttk.Label(status_card, textvariable=self.session_status, style="Section.TLabel").pack(anchor="w")
        ttk.Label(status_card, textvariable=self.session_detail, style="Muted.TLabel", wraplength=860).pack(anchor="w", pady=(4, 12))

        self.session_vars = {
            "access_token": tk.StringVar(),
            "refresh_token": tk.StringVar(),
            "display_name": tk.StringVar(),
            "user_id": tk.StringVar(),
            "expires_at": tk.StringVar(),
        }
        form = ttk.Frame(status_card, style="Card.TFrame")
        form.pack(fill="x", pady=(0, 8))
        fields = [
            ("display_name", "Display name"),
            ("user_id", "User ID"),
            ("expires_at", "Expires at (ISO)"),
            ("access_token", "Access token"),
            ("refresh_token", "Refresh token"),
        ]
        for row, (key, label) in enumerate(fields):
            ttk.Label(form, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))
            entry = ttk.Entry(form, textvariable=self.session_vars[key], show="*" if "token" in key else "")
            entry.grid(row=row, column=1, sticky="ew", pady=6)
        form.columnconfigure(1, weight=1)

        actions = ttk.Frame(status_card, style="Card.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="Save Session Preferences", command=self.save_session_settings).pack(side="left")
        ttk.Button(actions, text="Store Session", command=self.save_session_login).pack(side="right")
        ttk.Button(actions, text="Refresh Session", command=self.refresh_persisted_session).pack(side="right", padx=(0, 8))
        ttk.Button(actions, text="Sign Out", command=self.logout_session).pack(side="right", padx=(0, 8))

    def _build_hermes_section(self) -> None:
        frame = self._new_section("hermes")
        self._section_header(frame, "Hermes", "Endpoint health, webhook mode, latency-facing settings, and runtime inspection.")

        self.hermes_vars = {
            "endpoint": tk.StringVar(),
            "auth_refresh_url": tk.StringVar(),
            "auth_timeout": tk.StringVar(),
            "auth_header": tk.StringVar(),
            "auth_secret_header": tk.StringVar(),
            "stt_language": tk.StringVar(),
            "stt_model": tk.StringVar(),
            "webhook_sync": tk.StringVar(),
            "webhook_timeout": tk.StringVar(),
            "block_seconds": tk.StringVar(),
        }

        form = ttk.Frame(frame, style="Surface.TFrame")
        form.pack(fill="x")
        fields = [
            ("endpoint", "Endpoint"),
            ("auth_refresh_url", "Auth refresh URL"),
            ("auth_timeout", "Auth timeout"),
            ("auth_header", "Auth header"),
            ("auth_secret_header", "Auth secret header"),
            ("stt_language", "STT language"),
            ("stt_model", "STT model"),
            ("webhook_sync", "Webhook sync"),
            ("webhook_timeout", "Webhook timeout"),
            ("block_seconds", "Post-command block seconds"),
        ]
        for row, (key, label) in enumerate(fields):
            ttk.Label(form, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))
            ttk.Entry(form, textvariable=self.hermes_vars[key]).grid(row=row, column=1, sticky="ew", pady=6)
        form.columnconfigure(1, weight=1)

        self.hermes_runtime = tk.StringVar(value="Waiting for status…")
        ttk.Label(frame, textvariable=self.hermes_runtime, style="Muted.TLabel", wraplength=860).pack(anchor="w", pady=(14, 0))
        buttons = ttk.Frame(frame, style="Surface.TFrame")
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Run Probe", command=lambda: self.post_action("probe")).pack(side="left")
        ttk.Button(buttons, text="Start Tray", command=lambda: self.post_action("start-tray")).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Save Hermes", command=self.save_hermes_settings).pack(side="right")

    def _build_tts_section(self) -> None:
        frame = self._new_section("tts")
        self._section_header(frame, "TTS", "Speech feedback mode and output behavior.")

        self.tts_vars = {
            "feedback_mode": tk.StringVar(),
            "feedback_voice": tk.StringVar(),
        }
        self.tts_switch = LabeledSwitch(frame, "Speak Hermes responses", "Read the assistant response aloud locally when enabled.")
        self.tts_switch.pack(fill="x", pady=(0, 14))

        form = ttk.Frame(frame, style="Surface.TFrame")
        form.pack(fill="x")
        ttk.Label(form, text="Feedback mode", style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Combobox(form, textvariable=self.tts_vars["feedback_mode"], values=CONFIG_FIELDS["feedback_mode"], state="normal").grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Label(form, text="Feedback voice", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Entry(form, textvariable=self.tts_vars["feedback_voice"]).grid(row=1, column=1, sticky="ew", pady=6)
        form.columnconfigure(1, weight=1)

        ttk.Button(frame, text="Save TTS", command=self.save_tts_settings).pack(anchor="e", pady=(14, 0))

    def _build_logs_section(self) -> None:
        frame = self._new_section("logs")
        self._section_header(frame, "Logs", "Focused runtime logs for tray, bridge, and the local API.")

        actions = ttk.Frame(frame, style="Surface.TFrame")
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Open Logs Folder", command=lambda: self.post_action("open-logs")).pack(side="left")
        ttk.Button(actions, text="Open voice.env", command=lambda: self.post_action("open-env")).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Open Project Folder", command=lambda: self.post_action("open-folder")).pack(side="left", padx=(8, 0))

        self.logs_text = tk.Text(frame, wrap="none", height=30, bg=PALETTE["log_bg"], fg=PALETTE["body_fg"], insertbackground="white", padx=10, pady=10)
        self.logs_text.pack(fill="both", expand=True)
        self.logs_text.configure(state="disabled")

    def show_section(self, name: str) -> None:
        self._current_section = name
        for key, frame in self._section_frames.items():
            if key == name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        for key, button in self._nav_buttons.items():
            button.configure(text=("● " if key == name else "") + button.cget("text").replace("● ", ""))

    def _bootstrap(self) -> None:
        if not _is_api_alive():
            self.status_var.set("Starting local API…")
            try:
                _start_panel_api()
            except Exception as exc:
                self.status_var.set(f"Could not start local API: {exc}")
        if not _wait_for_api(timeout=8.0):
            self.status_var.set("Local API is not responding yet. Open the tray or review logs.")
        self.refresh_now()
        self.after(1500, self._auto_refresh)

    def _auto_refresh(self) -> None:
        self.refresh_now()
        self.after(1500, self._auto_refresh)

    def refresh_now(self) -> None:
        if self._pending_refresh:
            return
        self._pending_refresh = True
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            status = API.get("/api/status", timeout=2.5)
            devices = API.get("/api/devices", timeout=2.5)
        except Exception as exc:
            self.after(0, lambda: self._apply_error(str(exc)))
            return
        self.after(0, lambda: self._apply_snapshot(status, devices))

    def _apply_error(self, message: str) -> None:
        self._pending_refresh = False
        self.status_var.set(f"Error: {message}")
        self.badge.configure(text="SIN API", bg=PALETTE["danger"])

    def _apply_snapshot(self, status: Dict[str, Any], devices: Dict[str, Any]) -> None:
        self._pending_refresh = False
        previous_status = self._last_status
        self._last_status = status
        self._last_devices = devices

        badge = status.get("badge", {})
        color = badge.get("color", "#64748B")
        label = badge.get("label", "UNKNOWN")
        hint = badge.get("hint", "")
        self.badge.configure(text=f"{label}", bg=color)
        self.status_var.set(hint or f"Updated: {status.get('generated_at', '')}")

        config = status.get("config", {}) or {}
        summary = status.get("summary", {}) or {}
        runtime = status.get("runtime", {}) or {}
        session = runtime.get("session", {}) or {}

        self.general_cards["overlay"].var.set(_as_bool(config.get("overlay_enabled"), True))
        self.general_cards["notifications"].var.set(_as_bool(config.get("notifications_enabled"), True))
        self.general_status.set(
            f"Status: {summary.get('health', 'unknown')} · Mode: {summary.get('mode', 'unknown')} · "
            f"Tray={'on' if summary.get('tray_running') else 'off'} · Bridge={'on' if summary.get('bridge_running') else 'off'}"
        )

        for key in self.audio_vars:
            self.audio_vars[key].set("" if config.get(key) in (None, "(default)") else str(config.get(key, "")))
        for key in self.hermes_vars:
            self.hermes_vars[key].set("" if config.get(key) in (None, "(default)") else str(config.get(key, "")))
        for key in self.tts_vars:
            self.tts_vars[key].set("" if config.get(key) in (None, "(default)") else str(config.get(key, "")))

        self.tts_switch.var.set(_as_bool(config.get("tts_enabled"), True))
        self.session_switch.var.set(_as_bool(config.get("persist_session"), True))
        self.session_status.set("Signed in" if session.get("authenticated") else "Signed out")
        detail_bits = []
        if session.get("display_name"):
            detail_bits.append(str(session.get("display_name")))
        if session.get("user_id"):
            detail_bits.append(f"id {session.get('user_id')}")
        if session.get("token_expires_at"):
            detail_bits.append(f"expires {session.get('token_expires_at')}")
        if session.get("last_error"):
            detail_bits.append(f"error: {session.get('last_error')}")
        self.session_detail.set(" · ".join(detail_bits) if detail_bits else "No persisted Hermes session is available on this machine right now.")
        self.session_vars["display_name"].set(str(session.get("display_name") or ""))
        self.session_vars["user_id"].set(str(session.get("user_id") or ""))
        self.session_vars["expires_at"].set(str(session.get("token_expires_at") or ""))

        hotkey = str(config.get("hotkey", "") or "")
        if hotkey and hotkey != self.shortcut_state.accelerator and not self.shortcut_state.listening:
            self.shortcut_state.load_accelerator(hotkey)
            self._render_shortcut_state()

        self.hermes_runtime.set(
            f"Endpoint: {config.get('endpoint') or '(missing)'} · "
            f"Last event: {summary.get('last_event') or '—'} · Last error: {summary.get('last_error') or '—'}"
        )

        devices_list = devices.get("devices", []) or []
        self.device_list.delete(0, tk.END)
        for dev in devices_list:
            idx = dev.get("index", "?")
            name = dev.get("name", "Unknown")
            chans = dev.get("max_input_channels", 0)
            rate = dev.get("default_samplerate", 0)
            mark = " *" if dev.get("selected") else ""
            self.device_list.insert(tk.END, f"{idx}: {name} ({chans} ch, {rate:.0f} Hz){mark}")

        logs = "\n".join(status.get("logs", []) or [])
        self._set_text(self.logs_text, logs)

        if _as_bool(config.get("overlay_enabled"), True):
            signal = derive_overlay_signal(previous_status, status)
            if signal is not None:
                self.overlay.show_signal(signal)
        else:
            self.overlay.hide()

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def start_shortcut_capture(self) -> None:
        self.shortcut_state.begin_capture()
        self._pressed_keys = []
        self.bind_all("<KeyPress>", self._on_key_press, add="+")
        self.bind_all("<KeyRelease>", self._on_key_release, add="+")
        self.focus_force()
        self._render_shortcut_state()

    def clear_shortcut_capture(self) -> None:
        self.shortcut_state.clear()
        self._pressed_keys = []
        self._stop_shortcut_capture()
        self._render_shortcut_state()

    def _stop_shortcut_capture(self) -> None:
        self.unbind_all("<KeyPress>")
        self.unbind_all("<KeyRelease>")

    def _on_key_press(self, event: tk.Event) -> None:
        if not self.shortcut_state.listening:
            return
        keysym = str(getattr(event, "keysym", "") or "")
        if keysym and keysym not in self._pressed_keys:
            self._pressed_keys.append(keysym)
        self.shortcut_state.update_pressed(self._pressed_keys)
        self._render_shortcut_state()

    def _on_key_release(self, event: tk.Event) -> None:
        if not self.shortcut_state.listening:
            return
        accelerator = self.shortcut_state.accelerator
        conflict = CONFLICT_SHORTCUTS.get(accelerator, "")
        self.shortcut_state.finish_capture(conflict_with=conflict)
        self._stop_shortcut_capture()
        self._render_shortcut_state()

    def _render_shortcut_state(self) -> None:
        self.shortcut_caption.set(self.shortcut_state.caption)
        self.shortcut_conflict.set(self.shortcut_state.conflict)
        self.shortcut_pills.set_keys([(pill.key, pill.pressed) for pill in self.shortcut_state.pills])
        if self.shortcut_state.accelerator:
            self.shortcut_hint.set(f"Current capture: {self.shortcut_state.accelerator}")
        elif self.shortcut_state.listening:
            self.shortcut_hint.set("Press the full combination now…")
        else:
            self.shortcut_hint.set("Suggested premium default: CTRL + SHIFT + SPACE")

    def on_device_select(self, _event: tk.Event) -> None:
        selection = self.device_list.curselection()
        if not selection:
            return
        raw = self.device_list.get(selection[0])
        idx = raw.split(":", 1)[0].strip()
        self.audio_vars["mic_device"].set(idx)
        self.status_var.set(f"Mic device set to {idx}. Save Audio to persist it.")

    def _save_config_subset(self, payload: Dict[str, Any]) -> None:
        clean = {key: value for key, value in payload.items() if value not in (None, "")}
        if not clean:
            messagebox.showinfo("Hermes Voice Bridge", "Nada que guardar.")
            return
        self.post_action("save-config", clean)

    def save_general_settings(self) -> None:
        self._save_config_subset(
            {
                "overlay_enabled": "1" if self.general_cards["overlay"].var.get() else "0",
                "notifications_enabled": "1" if self.general_cards["notifications"].var.get() else "0",
            }
        )

    def save_audio_settings(self) -> None:
        self._save_config_subset({key: self.audio_vars[key].get().strip() for key in self.audio_vars})

    def save_shortcut_setting(self) -> None:
        if not self.shortcut_state.accelerator:
            messagebox.showinfo("Hermes Voice Bridge", "Primero graba un shortcut.")
            return
        if self.shortcut_state.conflict:
            messagebox.showwarning("Hermes Voice Bridge", self.shortcut_state.conflict)
            return
        self._save_config_subset({"hotkey": self.shortcut_state.accelerator})

    def save_session_settings(self) -> None:
        self._save_config_subset({"persist_session": "1" if self.session_switch.var.get() else "0"})

    def save_session_login(self) -> None:
        access_token = self.session_vars["access_token"].get().strip()
        if not access_token:
            messagebox.showinfo("Hermes Voice Bridge", "Access token required.")
            return
        payload = {key: self.session_vars[key].get().strip() for key in self.session_vars}
        payload["remember_me"] = "1" if self.session_switch.var.get() else "0"
        self.post_action("save-session", payload)

    def refresh_persisted_session(self) -> None:
        self.post_action("refresh-session", {"remember_me": "1" if self.session_switch.var.get() else "0"})

    def logout_session(self) -> None:
        self.session_vars["access_token"].set("")
        self.session_vars["refresh_token"].set("")
        self.post_action("logout-session", {"reason": "manual"})

    def save_hermes_settings(self) -> None:
        self._save_config_subset({key: self.hermes_vars[key].get().strip() for key in self.hermes_vars})

    def save_tts_settings(self) -> None:
        payload = {key: self.tts_vars[key].get().strip() for key in self.tts_vars}
        payload["tts_enabled"] = "1" if self.tts_switch.var.get() else "0"
        self._save_config_subset(payload)

    def post_action(self, action: str, payload: Optional[Dict[str, Any]] = None) -> None:
        if self._pending_action:
            return
        self._pending_action = True

        def worker() -> None:
            try:
                result = API.post(f"/api/action/{action}", payload=payload, timeout=20.0)
                message = result.get("action", {}).get("message", action)
                self.after(0, lambda: self._apply_action_result(message, result))
            except Exception as exc:
                self.after(0, lambda: self._apply_action_error(action, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_action_result(self, message: str, result: Dict[str, Any]) -> None:
        self._pending_action = False
        if result.get("action", {}).get("needs_restart"):
            self.status_var.set(f"{message} · restart recommended")
        else:
            self.status_var.set(message)
        self.refresh_now()

    def _apply_action_error(self, action: str, error: str) -> None:
        self._pending_action = False
        self.status_var.set(f"{action} failed: {error}")
        self.badge.configure(text="ERROR", bg=PALETTE["danger"])

    def on_close(self) -> None:
        self.overlay.hide()
        self._stop_shortcut_capture()
        if self._mutex is not None:
            release_single_instance_mutex(self._mutex)
            self._mutex = None
        self.destroy()


def main() -> int:
    try:
        app = VoiceBridgeDesktopApp()
    except SystemExit as exc:
        return int(exc.code or 0)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
