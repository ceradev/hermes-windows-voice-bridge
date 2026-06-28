from __future__ import annotations

from importlib import import_module
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item
import threading
from typing import Any, Callable, Dict, List, Optional


class TrayManager:
    """Native Windows tray manager backed by pystray menus."""

    def __init__(
        self,
        app_name: str,
        on_open_app: Callable[..., None],
        on_pause_toggle: Callable[[bool], None],
        on_restart: Callable[..., None],
        on_quit: Callable[..., None],
        on_quick_command: Optional[Callable[[str], None]] = None,
        on_open_settings: Optional[Callable[..., None]] = None,
        on_change_microphone: Optional[Callable[[int | None], None]] = None,
        on_start_listening: Optional[Callable[[], None]] = None,
    ) -> None:
        self.app_name = app_name
        self.on_open_app = on_open_app
        self.on_pause_toggle = on_pause_toggle
        self.on_restart = on_restart
        self.on_quit = on_quit
        self.on_quick_command = on_quick_command
        self.on_open_settings = on_open_settings or on_open_app
        self.on_change_microphone = on_change_microphone
        self.on_start_listening = on_start_listening

        self.icon: Any | None = None
        self._lock = threading.Lock()

        self.is_connected = False
        self.is_paused = False
        self.is_mic_active = False
        self._shortcut_display = ""
        self._quick_commands: List[Dict[str, Any]] = []
        self._recent_activity: List[str] = []
        self._audio_devices: List[Dict[str, Any]] = []
        self._current_mic_index: int | None = None
        self._current_mic_name = "Default"

    def _make_icon_image(self) -> Image.Image:
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle(
            [(2, 2), (size - 2, size - 2)],
            radius=10,
            fill="#141414",
            outline="#2a2a2a",
            width=2,
        )

        h_color = "#e0e0e0"
        line_width = 5
        mid_y = size // 2
        left_x = 20
        right_x = size - 20
        top_y = 16
        bottom_y = size - 16

        draw.line([(left_x, top_y), (left_x, bottom_y)], fill=h_color, width=line_width)
        draw.line([(right_x, top_y), (right_x, bottom_y)], fill=h_color, width=line_width)
        draw.line([(left_x, mid_y), (right_x, mid_y)], fill=h_color, width=line_width)

        if self.is_paused:
            dot_color = (245, 158, 11)
        elif self.is_connected:
            dot_color = (16, 185, 129)
        else:
            dot_color = (239, 68, 68)

        draw.ellipse([(46, 46), (58, 58)], fill=dot_color, outline="#141414", width=2)
        return img

    def _build_tooltip(self) -> str:
        status = "Paused" if self.is_paused else "Connected" if self.is_connected else "Offline"
        hotkey = self._shortcut_display or "Not configured"
        mic = self._current_mic_name or "Default"
        return f"{self.app_name}\n{status}\nHotkey: {hotkey}\nMic: {mic}"

    def _noop(self, icon: Any = None, item: Any = None) -> None:
        return None

    def _handle_open(self, icon: Any = None, item: Any = None) -> None:
        self.on_open_app(icon, item)

    def _handle_settings(self, icon: Any = None, item: Any = None) -> None:
        self.on_open_settings(icon, item)

    def _handle_pause(self, icon: Any = None, item: Any = None) -> None:
        next_state = not self.is_paused
        self.on_pause_toggle(next_state)
        self.set_paused(next_state)

    def _handle_restart(self, icon: Any = None, item: Any = None) -> None:
        self.on_restart(icon, item)

    def _handle_quit(self, icon: Any = None, item: Any = None) -> None:
        self.on_quit(icon, item)

    def _handle_listen(self, icon: Any = None, item: Any = None) -> None:
        if self.on_start_listening:
            self.on_start_listening()

    def _on_quick_cmd(self, command_id: str) -> Callable[..., None]:
        def handler(icon: Any = None, item: Any = None) -> None:
            if self.on_quick_command:
                self.on_quick_command(command_id)

        return handler

    def _on_mic_select(self, index: int | None) -> Callable[..., None]:
        def handler(icon: Any = None, item: Any = None) -> None:
            if self.on_change_microphone:
                self.on_change_microphone(index)

        return handler

    def _build_microphone_items(self) -> tuple[Any, ...]:
        devices = [device for device in self._audio_devices if device.get("usable", True)]
        items: list[Any] = [
            Item(
                "System Default",
                self._on_mic_select(None),
                checked=lambda item: self._current_mic_index is None,
            )
        ]

        if not devices:
            items.append(Item("No microphones available", self._noop, enabled=False))
            return tuple(items)

        for device in devices:
            index = device.get("index")
            name = str(device.get("name") or f"Microphone {index}")
            items.append(
                Item(
                    name,
                    self._on_mic_select(index),
                    checked=lambda item, idx=index: self._current_mic_index == idx,
                )
            )

        return tuple(items)

    def _build_recent_activity_items(self) -> tuple[Any, ...]:
        if not self._recent_activity:
            return (Item("No recent activity", self._noop, enabled=False),)
        return tuple(Item(text, self._noop, enabled=False) for text in self._recent_activity[:5])

    def _build_quick_command_items(self) -> tuple[Any, ...]:
        if not self._quick_commands:
            return (Item("No quick commands", self._noop, enabled=False),)
        return tuple(
            Item(str(cmd.get("label") or cmd.get("id") or "Unnamed"), self._on_quick_cmd(str(cmd["id"])))
            for cmd in self._quick_commands
            if cmd.get("id")
        )

    def _build_menu(self) -> pystray.Menu:
        status_text = "Connected" if self.is_connected else "Offline"
        hotkey_text = self._shortcut_display or "Not configured"
        mic_text = self._current_mic_name or "Default"
        mic_live = " · Listening" if self.is_mic_active else ""

        return pystray.Menu(
            Item(self.app_name, self._noop, enabled=False),
            Item(f"Status: {status_text}", self._noop, enabled=False),
            Item(f"Hotkey: {hotkey_text}", self._noop, enabled=False),
            Item(f"Microphone: {mic_text}{mic_live}", self._noop, enabled=False),
            pystray.Menu.SEPARATOR,
            Item("Open Dashboard", self._handle_open, default=True),
            Item("Cancel Listening" if self.is_mic_active else "Listen", self._handle_listen),
            Item("Microphone", pystray.Menu(*self._build_microphone_items())),
            Item("Quick Commands", pystray.Menu(*self._build_quick_command_items())),
            Item("Recent Activity", pystray.Menu(*self._build_recent_activity_items())),
            pystray.Menu.SEPARATOR,
            Item("Resume Listening" if self.is_paused else "Pause Listening", self._handle_pause),
            Item("Settings", self._handle_settings),
            Item("Restart", self._handle_restart),
            pystray.Menu.SEPARATOR,
            Item("Quit", self._handle_quit),
        )

    def start(self) -> None:
        if self.icon is not None:
            return

        self.icon = pystray.Icon(
            self.app_name,
            self._make_icon_image(),
            self._build_tooltip(),
            menu=self._build_menu(),
        )

        try:
            from pystray._util import win32 as pystray_win32

            wm_lbuttonup = pystray_win32.WM_LBUTTONUP
            wm_notify = getattr(pystray_win32, "WM_NOTIFY", 0x004E)
        except Exception:
            wm_lbuttonup = 0x0202
            wm_notify = 0x004E

        icon = self.icon
        if icon is None:
            return
        original_on_notify = icon._on_notify

        def custom_on_notify(wparam: Any, lparam: Any) -> None:
            if lparam == wm_lbuttonup:
                self._handle_open()
            else:
                original_on_notify(wparam, lparam)

        icon._on_notify = custom_on_notify
        if hasattr(icon, "_message_handlers"):
            icon._message_handlers[wm_notify] = icon._on_notify

        icon.run_detached()

    def stop(self) -> None:
        if self.icon is not None:
            self.icon.stop()
            self.icon = None

    def _refresh(self) -> None:
        if self.icon is None:
            return
        self.icon.icon = self._make_icon_image()
        self.icon.title = self._build_tooltip()
        self.icon.menu = self._build_menu()
        try:
            self.icon.update_menu()
        except Exception:
            pass

    def set_status(self, connected: bool) -> None:
        with self._lock:
            self.is_connected = connected
        self._refresh()

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self.is_paused = paused
        self._refresh()

    def set_mic_active(self, active: bool) -> None:
        with self._lock:
            self.is_mic_active = active
        self._refresh()

    def set_shortcut_display(self, shortcut: str) -> None:
        with self._lock:
            self._shortcut_display = str(shortcut or "")
        self._refresh()

    def set_audio_devices(self, devices: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._audio_devices = list(devices)
        self._refresh()

    def set_current_mic(self, index: int | None, name: str = "Default") -> None:
        with self._lock:
            self._current_mic_index = index
            self._current_mic_name = name or "Default"
        self._refresh()

    def update_quick_commands(self, commands: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._quick_commands = list(commands)
        self._refresh()

    def set_recent_activity(self, items: List[str]) -> None:
        with self._lock:
            self._recent_activity = list(items)
        self._refresh()

    def notify(self, title: str, message: str, duration: int = 3) -> None:
        try:
            toast_module = import_module("win10toast")
            toast_module.ToastNotifier().show_toast(title, message, duration=duration, threaded=True)
        except Exception:
            if self.icon is not None:
                try:
                    self.icon.notify(message, title)
                except Exception:
                    pass
