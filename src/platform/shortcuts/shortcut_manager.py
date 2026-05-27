import threading
import ctypes
import ctypes.wintypes
from typing import Optional, Tuple

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

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

class ShortcutManager:
    def __init__(self):
        self.trigger = threading.Event()
        self.visual_trigger = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self._running = False
        self.current_hotkey: str = ""
        self.current_visual_hotkey: str = ""

    def parse_hotkey(self, hotkey: str) -> Optional[Tuple[int, int]]:
        token_map = {
            "space": 0x20, "tab": 0x09, "enter": 0x0D, "return": 0x0D,
            "esc": 0x1B, "escape": 0x1B, "backspace": 0x08, "insert": 0x2D,
            "delete": 0x2E, "home": 0x24, "end": 0x23, "pageup": 0x21,
            "pagedown": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
        }
        mod = 0
        parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
        if not parts:
            return None
            
        key = parts[-1]
        for part in parts[:-1]:
            if part in {"ctrl", "control"}: mod |= MOD_CONTROL
            elif part in {"alt", "menu"}: mod |= MOD_ALT
            elif part in {"shift"}: mod |= MOD_SHIFT
            elif part in {"win", "windows", "meta"}: mod |= MOD_WIN
            else: return None
            
        if len(key) == 1 and key.isalnum():
            vk = ord(key.upper())
        elif key in token_map:
            vk = token_map[key]
        elif key.startswith("f") and key[1:].isdigit():
            n = int(key[1:])
            if 1 <= n <= 24:
                vk = 0x6F + n
            else: return None
        else:
            return None
        return mod, vk

    def start(self, hotkey: str, visual_hotkey: str = "") -> bool:
        self.stop()
        
        parsed = self.parse_hotkey(hotkey) if hotkey else None
        parsed_visual = self.parse_hotkey(visual_hotkey) if visual_hotkey else None
        
        if not parsed and not parsed_visual:
            return False

        self._running = True
        self.current_hotkey = hotkey
        self.current_visual_hotkey = visual_hotkey

        def _worker() -> None:
            user32 = ctypes.windll.user32
            if parsed:
                user32.RegisterHotKey(None, 1, parsed[0], parsed[1])
            if parsed_visual:
                user32.RegisterHotKey(None, 2, parsed_visual[0], parsed_visual[1])
                
            try:
                msg = _HotkeyMessage()
                while self._running:
                    if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1) != 0:
                        if msg.message == WM_HOTKEY:
                            if msg.wParam == 1:
                                self.trigger.set()
                            elif msg.wParam == 2:
                                self.visual_trigger.set()
                    else:
                        import time
                        time.sleep(0.05)
            finally:
                if parsed:
                    user32.UnregisterHotKey(None, 1)
                if parsed_visual:
                    user32.UnregisterHotKey(None, 2)

        self.thread = threading.Thread(target=_worker, daemon=True)
        self.thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.thread = None
        self.current_hotkey = ""
        self.current_visual_hotkey = ""

    def clear_trigger(self) -> None:
        self.trigger.clear()
        
    def clear_visual_trigger(self) -> None:
        self.visual_trigger.clear()

    def is_triggered(self) -> bool:
        return self.trigger.is_set()
        
    def is_visual_triggered(self) -> bool:
        return self.visual_trigger.is_set()
