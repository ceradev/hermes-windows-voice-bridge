import pystray
from PIL import Image, ImageDraw, ImageFont
import threading
import queue
import time
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional, Callable, List, Dict, Any

# ────────────────────────────────────────────────────────────────────────────────
# Windows constants (may not be imported by pystray)
_WM_LBUTTONUP = 0x0202
_WM_RBUTTONUP = 0x0205


class TrayManager:
    """System tray icon with a fully custom dark tkinter popup menu.

    Replaces pystray's native Windows context menu (always light-themed on
    light-mode systems) with a machined dark panel rendered via tkinter.
    """

    def __init__(
        self,
        app_name: str,
        on_open_app: Callable,
        on_pause_toggle: Callable[[bool], None],
        on_restart: Callable,
        on_quit: Callable,
        on_quick_command: Optional[Callable[[str], None]] = None,
        on_open_settings: Optional[Callable] = None,
    ):
        self.app_name = app_name
        self.on_open_app = on_open_app
        self.on_pause_toggle = on_pause_toggle
        self.on_restart = on_restart
        self.on_quit = on_quit
        self.on_quick_command = on_quick_command
        self.on_open_settings = on_open_settings or on_open_app

        self.icon: Optional[pystray.Icon] = None
        self._lock = threading.Lock()

        # tkinter thread
        self._menu_queue: queue.Queue[Any] = queue.Queue()
        self._menu_thread: Optional[threading.Thread] = None
        self._tk_root: Optional[tk.Tk] = None
        self._popup: Optional[tk.Toplevel] = None
        self._stop_flag = threading.Event()

        # State
        self.is_connected = False
        self.is_paused = False
        self.is_mic_active = False
        self._shortcut_display = ""
        self._quick_commands: List[Dict[str, Any]] = []
        self._recent_activity: List[str] = []

    # ── Icon generation ────────────────────────────────────────────────────────

    def _make_icon_image(self):
        """Draw a machined "H" tray icon with a small status LED."""
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark machined panel background
        draw.rounded_rectangle(
            [(2, 2), (size - 2, size - 2)],
            radius=10,
            fill="#141414",
            outline="#2a2a2a",
            width=2,
        )

        # Elegant H — slightly thicker for visibility
        h_color = "#e0e0e0"
        line_width = 5
        mid_y = size // 2
        left_x = 20
        right_x = size - 20
        top_y = 16
        bottom_y = size - 16

        # Left vertical
        draw.line([(left_x, top_y), (left_x, bottom_y)], fill=h_color, width=line_width)
        # Right vertical
        draw.line([(right_x, top_y), (right_x, bottom_y)], fill=h_color, width=line_width)
        # Middle horizontal
        draw.line([(left_x, mid_y), (right_x, mid_y)], fill=h_color, width=line_width)

        # Status dot bottom-right
        if self.is_paused:
            dot_color = (245, 158, 11)    # amber
        elif self.is_connected:
            dot_color = (16, 185, 129)    # green
        else:
            dot_color = (239, 68, 68)     # red

        draw.ellipse([(46, 46), (58, 58)], fill=dot_color, outline="#141414", width=2)

        return img

    # ── Tooltip ────────────────────────────────────────────────────────────────

    def _build_tooltip(self) -> str:
        if self.is_connected:
            return f"{self.app_name}  ●"
        return f"{self.app_name}  ○"

    # ── Menu helpers ───────────────────────────────────────────────────────────

    def _noop(self, icon=None, item=None) -> None:
        pass

    def _handle_pause(self, icon=None, item=None) -> None:
        self.is_paused = not self.is_paused
        self.on_pause_toggle(self.is_paused)
        self._refresh()

    def _on_quick_cmd(self, command_id: str) -> Callable:
        def handler(icon=None, item=None) -> None:
            if self.on_quick_command:
                self.on_quick_command(command_id)
        return handler

    # ── tkinter thread ─────────────────────────────────────────────────────────

    def _tk_mainloop(self) -> None:
        """Dedicated thread that owns the tkinter root and processes queue tasks."""
        root = tk.Tk()
        root.withdraw()
        self._tk_root = root

        def process() -> None:
            if self._stop_flag.is_set():
                try:
                    root.destroy()
                except Exception:
                    pass
                return
            try:
                while True:
                    task = self._menu_queue.get_nowait()
                    task()
            except queue.Empty:
                pass
            root.after(50, process)

        process()
        root.mainloop()

    # ── Custom popup builder ───────────────────────────────────────────────────

    def _show_popup(self) -> None:
        """Build and show a Windows-native-style dark popup menu above the tray icon."""
        root = self._tk_root
        if root is None:
            return

        # Toggle: close if already open
        if self._popup is not None:
            try:
                if self._popup.winfo_exists():
                    self._popup.destroy()
            except Exception:
                pass
            self._popup = None
            return

        popup = tk.Toplevel(root)
        popup.overrideredirect(True)
        popup.configure(bg="#2b2b2b")
        popup.attributes("-topmost", True)

        # Card frame — single flat surface with subtle border via highlight
        card = tk.Frame(popup, bg="#2b2b2b", highlightbackground="#3d3d3d", highlightthickness=1)
        card.pack(fill="both", expand=True)

        # Font: clean sans-serif, small & light
        font_header = tkfont.Font(family="Segoe UI", size=10, weight="normal")
        font_item = tkfont.Font(family="Segoe UI", size=10, weight="normal")
        font_status = tkfont.Font(family="Segoe UI", size=9, weight="normal")

        # ── Helpers ────────────────────────────────────────────────────────────

        def add_header(text: str) -> None:
            row = tk.Frame(card, bg="#2b2b2b", height=28)
            row.pack(fill="x")
            row.pack_propagate(False)
            lbl = tk.Label(
                row,
                text=text,
                bg="#2b2b2b",
                fg="#a0a0a0",
                font=font_header,
                padx=36,
                pady=0,
                anchor="w",
            )
            lbl.pack(side="left", fill="both", expand=True)

        def add_row(text: str, cmd: Optional[Callable] = None, status_dot: Optional[str] = None) -> tk.Label:
            """A single menu row."""
            row = tk.Frame(card, bg="#2b2b2b", height=30)
            row.pack(fill="x")
            row.pack_propagate(False)

            # Optional status dot (colored circle) on the far left
            if status_dot:
                dot_color = "#10b981" if status_dot == "connected" else "#ef4444"
                dot = tk.Canvas(row, bg="#2b2b2b", highlightthickness=0, width=28, height=30)
                dot.pack(side="left", fill="y")
                dot.create_oval(10, 12, 18, 20, fill=dot_color, outline="")

            lbl = tk.Label(
                row,
                text=text,
                bg="#2b2b2b",
                fg="#ffffff",
                font=font_item if status_dot is None else font_status,
                padx=36 if status_dot is None else 0,
                pady=0,
                anchor="w",
                cursor="hand2" if cmd else "arrow",
            )
            lbl.pack(side="left", fill="both", expand=True)

            if cmd:
                def on_enter(e, widget=lbl, container=row):
                    widget.configure(bg="#3a3a3a")
                    container.configure(bg="#3a3a3a")

                def on_leave(e, widget=lbl, container=row):
                    widget.configure(bg="#2b2b2b")
                    container.configure(bg="#2b2b2b")

                def on_click(e, c=cmd):
                    try:
                        c()
                    except Exception:
                        pass
                    self._close_popup()

                lbl.bind("<Enter>", on_enter)
                lbl.bind("<Leave>", on_leave)
                lbl.bind("<Button-1>", on_click)
                row.bind("<Enter>", on_enter)
                row.bind("<Leave>", on_leave)
                row.bind("<Button-1>", on_click)

            return lbl

        def add_sep() -> None:
            sep = tk.Frame(card, bg="#3d3d3d", height=1)
            sep.pack(fill="x", padx=8, pady=0)

        # ── Build content ──────────────────────────────────────────────────────
        with self._lock:
            connected = self.is_connected
            paused = self.is_paused
            qcmds = list(self._quick_commands)
            recent = list(self._recent_activity)

        # App name header
        add_header(self.app_name)
        add_sep()

        # Status row (connected / offline)
        status_text = "Connected" if connected else "Offline"
        add_row(status_text, status_dot="connected" if connected else "offline")

        # Quick commands
        if qcmds:
            add_sep()
            for cmd in qcmds[:6]:
                add_row(cmd.get("label", cmd["id"]), self._on_quick_cmd(cmd["id"]))

        # Recent activity
        if recent:
            add_sep()
            for text in recent[-3:]:
                truncated = text[:32] + "…" if len(text) > 32 else text
                add_row(truncated)

        # Core actions
        add_sep()
        add_row("Resume" if paused else "Pause", self._handle_pause)
        add_row("Settings", self.on_open_settings)
        add_row("Restart", self.on_restart)
        add_sep()
        add_row("Quit", self.on_quit)

        # ── Position: above the tray icon ────────────────────────────────────
        popup.update_idletasks()
        w = max(popup.winfo_reqwidth(), 240)
        h = popup.winfo_reqheight()
        popup.geometry(f"{w}x{h}")
        popup.update_idletasks()

        # Get cursor position — the tray icon is right under the cursor on right-click
        px = popup.winfo_pointerx()
        py = popup.winfo_pointery()
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()

        # Place the menu above the icon so the bottom edge sits near the cursor
        x = min(px - 20, sw - w - 12)
        y = py - h - 4
        # If too close to top edge, flip below
        if y < 8:
            y = py + 8

        popup.geometry(f"{w}x{h}+{x}+{y}")
        popup.deiconify()
        popup.focus_force()

        # Auto-close when focus leaves
        def check_focus() -> None:
            if not popup.winfo_exists():
                return
            if popup.focus_get() is None:
                popup.after(200, close_if_still_unfocused)
            else:
                popup.after(150, check_focus)

        def close_if_still_unfocused() -> None:
            if popup.winfo_exists() and popup.focus_get() is None:
                try:
                    popup.destroy()
                except Exception:
                    pass
                self._popup = None
            elif popup.winfo_exists():
                popup.after(150, check_focus)

        popup.after(150, check_focus)
        self._popup = popup

    def _close_popup(self) -> None:
        if self._popup is not None:
            try:
                if self._popup.winfo_exists():
                    self._popup.destroy()
            except Exception:
                pass
            self._popup = None

    # ── Public lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        if self.icon is not None:
            return

        self._stop_flag.clear()
        self._menu_thread = threading.Thread(target=self._tk_mainloop, daemon=True)
        self._menu_thread.start()

        # Wait briefly for tkinter thread to start
        time.sleep(0.05)

        self.icon = pystray.Icon(
            self.app_name,
            self._make_icon_image(),
            self._build_tooltip(),
            menu=None,  # disable native menu entirely
        )

        # Monkey-patch _on_notify to intercept clicks instead of native menu
        try:
            from pystray._util import win32 as pystray_win32
            _WM_LBUTTONUP = pystray_win32.WM_LBUTTONUP
            _WM_RBUTTONUP = pystray_win32.WM_RBUTTONUP
        except Exception:
            _WM_LBUTTONUP = 0x0202
            _WM_RBUTTONUP = 0x0205

        original_on_notify = self.icon._on_notify

        def custom_on_notify(wparam, lparam) -> None:
            if lparam == _WM_LBUTTONUP:
                try:
                    self.on_open_app()
                except Exception:
                    pass
            elif lparam == _WM_RBUTTONUP:
                self._menu_queue.put(self._show_popup)
            else:
                original_on_notify(wparam, lparam)

        self.icon._on_notify = custom_on_notify
        # pystray caches handlers in _message_handlers during __init__, so we must
        # update the dict too for the WNDPROC to see the new handler.
        try:
            from pystray._util import win32 as pystray_win32
            wm_notify = getattr(pystray_win32, 'WM_NOTIFY', 0x004E)
        except Exception:
            wm_notify = 0x004E
        if hasattr(self.icon, '_message_handlers'):
            self.icon._message_handlers[wm_notify] = self.icon._on_notify

        self.icon.run_detached()

    def stop(self) -> None:
        self._stop_flag.set()
        self._close_popup()

        if self._tk_root is not None:
            try:
                self._tk_root.destroy()
            except Exception:
                pass
            self._tk_root = None

        if self.icon is not None:
            self.icon.stop()
            self.icon = None

    # ── Dynamic updates ────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        if self.icon:
            self.icon.icon = self._make_icon_image()
            self.icon.title = self._build_tooltip()

    def set_status(self, connected: bool) -> None:
        with self._lock:
            if self.is_connected != connected:
                self.is_connected = connected
                self._refresh()

    def set_mic_active(self, active: bool) -> None:
        with self._lock:
            if self.is_mic_active != active:
                self.is_mic_active = active
                self._refresh()

    def set_shortcut_display(self, shortcut: str) -> None:
        with self._lock:
            self._shortcut_display = shortcut

    def update_quick_commands(self, commands: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._quick_commands = list(commands)

    def set_recent_activity(self, items: List[str]) -> None:
        with self._lock:
            self._recent_activity = list(items)

    # ── Notifications ──────────────────────────────────────────────────────────

    def notify(self, title: str, message: str, duration: int = 3) -> None:
        try:
            from win10toast import ToastNotifier

            ToastNotifier().show_toast(title, message, duration=duration, threaded=True)
        except Exception:
            if self.icon:
                try:
                    self.icon.notify(message, title)
                except Exception:
                    pass
