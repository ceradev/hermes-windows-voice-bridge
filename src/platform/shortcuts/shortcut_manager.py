import threading
import ctypes
import ctypes.wintypes
import time
from typing import Callable, Optional, Tuple, Dict, Set, List

# ── Windows Message Constants ────────────────────────────────────────────────
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

WH_KEYBOARD_LL = 13

# ── Virtual-Key Codes ────────────────────────────────────────────────────────
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_PAUSE = 0x13
VK_CAPITAL = 0x14
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_SNAPSHOT = 0x2C
VK_INSERT = 0x2D
VK_DELETE = 0x2E
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_NUMPAD0 = 0x60
VK_NUMPAD1 = 0x61
VK_NUMPAD2 = 0x62
VK_NUMPAD3 = 0x63
VK_NUMPAD4 = 0x64
VK_NUMPAD5 = 0x65
VK_NUMPAD6 = 0x66
VK_NUMPAD7 = 0x67
VK_NUMPAD8 = 0x68
VK_NUMPAD9 = 0x69
VK_MULTIPLY = 0x6A
VK_ADD = 0x6B
VK_SEPARATOR = 0x6C
VK_SUBTRACT = 0x6D
VK_DECIMAL = 0x6E
VK_DIVIDE = 0x6F
VK_F1 = 0x70
VK_NUMLOCK = 0x90
VK_SCROLL = 0x91
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_UP = 0xAE
VK_VOLUME_DOWN = 0xAF

_MODIFIER_VKS: Set[int] = {
    VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN,
    0xA0, 0xA1,  # LSHIFT, RSHIFT
    0xA2, 0xA3,  # LCONTROL, RCONTROL
    0xA4, 0xA5,  # LMENU, RMENU
}

# ── Name → VK mapping (input parsing) ────────────────────────────────────────
_TOKEN_MAP: Dict[str, int] = {
    "space": VK_SPACE,
    "tab": VK_TAB,
    "enter": VK_RETURN,
    "return": VK_RETURN,
    "esc": VK_ESCAPE,
    "escape": VK_ESCAPE,
    "backspace": VK_BACK,
    "insert": VK_INSERT,
    "delete": VK_DELETE,
    "home": VK_HOME,
    "end": VK_END,
    "pageup": VK_PRIOR,
    "pagedown": VK_NEXT,
    "left": VK_LEFT,
    "up": VK_UP,
    "right": VK_RIGHT,
    "down": VK_DOWN,
    # Numpad
    "num0": VK_NUMPAD0,
    "num1": VK_NUMPAD1,
    "num2": VK_NUMPAD2,
    "num3": VK_NUMPAD3,
    "num4": VK_NUMPAD4,
    "num5": VK_NUMPAD5,
    "num6": VK_NUMPAD6,
    "num7": VK_NUMPAD7,
    "num8": VK_NUMPAD8,
    "num9": VK_NUMPAD9,
    "numadd": VK_ADD,
    "numsub": VK_SUBTRACT,
    "nummul": VK_MULTIPLY,
    "numdiv": VK_DIVIDE,
    "numdec": VK_DECIMAL,
    "numenter": VK_RETURN,
    # Media
    "play": VK_MEDIA_PLAY_PAUSE,
    "pause": VK_MEDIA_PLAY_PAUSE,
    "stop": VK_MEDIA_STOP,
    "next": VK_MEDIA_NEXT_TRACK,
    "prev": VK_MEDIA_PREV_TRACK,
    "mute": VK_VOLUME_MUTE,
    "volup": VK_VOLUME_UP,
    "voldown": VK_VOLUME_DOWN,
    # Special
    "print": VK_SNAPSHOT,
    "scroll": VK_SCROLL,
    "break": VK_PAUSE,
    "caps": VK_CAPITAL,
    "numlock": VK_NUMLOCK,
}

# ── VK → Name mapping (capture output) ───────────────────────────────────────
_VK_TO_NAME: Dict[int, str] = {
    VK_SPACE: "SPACE",
    VK_TAB: "TAB",
    VK_RETURN: "ENTER",
    VK_BACK: "BACKSPACE",
    VK_INSERT: "INSERT",
    VK_DELETE: "DELETE",
    VK_HOME: "HOME",
    VK_END: "END",
    VK_PRIOR: "PAGEUP",
    VK_NEXT: "PAGEDOWN",
    VK_LEFT: "LEFT",
    VK_UP: "UP",
    VK_RIGHT: "RIGHT",
    VK_DOWN: "DOWN",
    VK_ESCAPE: "ESC",
    VK_SNAPSHOT: "PRINT",
    VK_SCROLL: "SCROLL",
    VK_PAUSE: "PAUSE",
    VK_CAPITAL: "CAPS",
    VK_NUMLOCK: "NUMLOCK",
    VK_NUMPAD0: "NUM0",
    VK_NUMPAD1: "NUM1",
    VK_NUMPAD2: "NUM2",
    VK_NUMPAD3: "NUM3",
    VK_NUMPAD4: "NUM4",
    VK_NUMPAD5: "NUM5",
    VK_NUMPAD6: "NUM6",
    VK_NUMPAD7: "NUM7",
    VK_NUMPAD8: "NUM8",
    VK_NUMPAD9: "NUM9",
    VK_ADD: "NUMADD",
    VK_SUBTRACT: "NUMSUB",
    VK_MULTIPLY: "NUMMUL",
    VK_DIVIDE: "NUMDIV",
    VK_DECIMAL: "NUMDEC",
    VK_MEDIA_PLAY_PAUSE: "PLAY",
    VK_MEDIA_STOP: "STOP",
    VK_MEDIA_NEXT_TRACK: "NEXT",
    VK_MEDIA_PREV_TRACK: "PREV",
    VK_VOLUME_MUTE: "MUTE",
    VK_VOLUME_UP: "VOLUP",
    VK_VOLUME_DOWN: "VOLDOWN",
}

# ── CTypes Structures ────────────────────────────────────────────────────────
class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.wintypes.LONG), ("y", ctypes.wintypes.LONG)]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.wintypes.HWND),
        ("message", ctypes.wintypes.UINT),
        ("wParam", ctypes.wintypes.WPARAM),
        ("lParam", ctypes.wintypes.LPARAM),
        ("time", ctypes.wintypes.DWORD),
        ("pt", _POINT),
    ]


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


# ── Hook callback type ─────────────────────────────────────────────────────────
_LOWLEVELKEYBOARDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,  # LRESULT == LONG_PTR
    ctypes.c_int,
    ctypes.c_size_t,   # WPARAM == UINT_PTR
    ctypes.c_ssize_t,  # LPARAM == LONG_PTR
)


class ShortcutManager:
    """Global hotkey manager using the Windows RegisterHotKey API.

    Supports multiple named hotkeys, efficient blocking message loops,
    conflict detection, and an interactive key-capture mode.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._thread_id: int = 0

        # Named hotkey storage
        self._hotkeys: Dict[str, str] = {}
        self._next_id: int = 1
        self._id_to_name: Dict[int, str] = {}
        self._name_to_id: Dict[str, int] = {}
        self._triggered: Set[str] = set()
        self._errors: Dict[str, str] = {}
        self._registration_error_handler: Optional[Callable[[str, str, str], None]] = None

        # Legacy attribute compatibility
        self.trigger = threading.Event()
        self.visual_trigger = threading.Event()

    def set_registration_error_handler(
        self,
        handler: Optional[Callable[[str, str, str], None]],
    ) -> None:
        """Install a callback for async RegisterHotKey failures.

        The callback receives ``(name, hotkey_combo, error_message)`` and is
        invoked from the shortcut worker thread immediately after registration
        attempts complete.
        """
        with self._lock:
            self._registration_error_handler = handler

    # ── Public API: named hotkeys ────────────────────────────────────────────

    def start(self, hotkeys, visual_hotkey=None) -> bool:
        """Start listening for hotkeys.

        Backward-compatible overloads:
          • start(hotkey: str, visual_hotkey: str = "")  – legacy
          • start(hotkeys: dict[str, str])               – new
        """
        if isinstance(hotkeys, str):
            # Legacy single/ dual-hotkey mode
            mapping: Dict[str, str] = {}
            if hotkeys:
                mapping["trigger"] = hotkeys
            if visual_hotkey:
                mapping["visual_trigger"] = visual_hotkey
            return self._start_named(mapping)

        if hotkeys is None or not isinstance(hotkeys, dict):
            return False

        return self._start_named(hotkeys)

    def _start_named(self, hotkeys: Dict[str, str]) -> bool:
        """Internal implementation that expects a name → hotkey-string dict."""
        self.stop()

        valid = {k: v for k, v in hotkeys.items() if v and v.strip()}
        if not valid:
            return False

        with self._lock:
            self._hotkeys = valid
            self._next_id = 1
            self._errors.clear()
            self._triggered.clear()
            self.trigger.clear()
            self.visual_trigger.clear()

        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Unregister every hotkey and stop the background thread."""
        self._running = False

        if self._thread_id:
            user32 = ctypes.windll.user32
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

        if self._thread:
            self._thread.join(timeout=2.0)

        self._thread = None
        self._thread_id = 0

        with self._lock:
            self._id_to_name.clear()
            self._name_to_id.clear()
            self._triggered.clear()
            self._errors.clear()
            self.trigger.clear()
            self.visual_trigger.clear()

    def is_triggered(self, name: Optional[str] = None) -> bool:
        """Check whether a specific (or the legacy default) hotkey fired."""
        target = name if name is not None else "trigger"
        with self._lock:
            return target in self._triggered

    def is_visual_triggered(self) -> bool:
        """Legacy convenience wrapper."""
        return self.is_triggered("visual_trigger")

    def clear_trigger(self) -> None:
        """Legacy helper: clear the default trigger."""
        self.clear_triggered("trigger")

    def clear_visual_trigger(self) -> None:
        """Legacy helper: clear the visual trigger."""
        self.clear_triggered("visual_trigger")

    def clear_triggered(self, name: str) -> None:
        """Clear a specific named trigger flag."""
        with self._lock:
            self._triggered.discard(name)
            if name == "trigger":
                self.trigger.clear()
            elif name == "visual_trigger":
                self.visual_trigger.clear()

    def get_triggered(self) -> List[str]:
        """Return all triggered hotkey names and atomically clear them."""
        with self._lock:
            triggered = list(self._triggered)
            self._triggered.clear()
            self.trigger.clear()
            self.visual_trigger.clear()
            return triggered

    def get_registration_errors(self) -> Dict[str, str]:
        """Return a map of hotkey-name → error-message for the last start()."""
        with self._lock:
            return dict(self._errors)

    def _emit_registration_error(self, name: str, hotkey: str, message: str) -> None:
        with self._lock:
            handler = self._registration_error_handler
        if handler is None:
            return
        try:
            handler(name, hotkey, message)
        except Exception as exc:
            print(f"Shortcut registration error handler failed: {exc}")

    # ── Conflict detection ───────────────────────────────────────────────────

    def check_conflict(self, hotkey: str) -> bool:
        """Return True if *hotkey* can be registered right now."""
        parsed = self.parse_hotkey(hotkey)
        if not parsed:
            return False

        mod, vk = parsed
        temp_id = 0x7FFF
        user32 = ctypes.windll.user32

        if user32.RegisterHotKey(None, temp_id, mod, vk):
            user32.UnregisterHotKey(None, temp_id)
            return True
        return False

    # ── Key capture mode ─────────────────────────────────────────────────────

    def capture_next_hotkey(self, timeout: float = 5.0) -> Optional[str]:
        """Block until the user presses a key combination (or time runs out).

        Returns a canonical string such as ``"CTRL+SHIFT+H"`` or ``"F12"``.
        """
        captured: List[Optional[str]] = [None]
        event = threading.Event()
        thread_id: List[int] = [0]
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        @_LOWLEVELKEYBOARDPROC
        def hook_proc(nCode, wParam, lParam):
            if nCode < 0:
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            if wParam not in (WM_KEYDOWN, WM_SYSKEYDOWN):
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            kb = ctypes.cast(lParam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents

            # Ignore injected keystrokes (e.g. from SendInput)
            if kb.flags & 0x10:
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            # Ignore pure-modifier presses
            if kb.vkCode in _MODIFIER_VKS:
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            # Assemble modifiers
            mods: List[str] = []
            if user32.GetAsyncKeyState(VK_CONTROL) & 0x8000:
                mods.append("CTRL")
            if user32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
                mods.append("SHIFT")
            if user32.GetAsyncKeyState(VK_MENU) & 0x8000:
                mods.append("ALT")
            if (user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or (
                user32.GetAsyncKeyState(VK_RWIN) & 0x8000
            ):
                mods.append("WIN")

            # Resolve key name
            key_name = _VK_TO_NAME.get(kb.vkCode)
            if not key_name:
                if 0x30 <= kb.vkCode <= 0x39:
                    key_name = chr(kb.vkCode)
                elif 0x41 <= kb.vkCode <= 0x5A:
                    key_name = chr(kb.vkCode)
                elif VK_F1 <= kb.vkCode <= 0x87:
                    key_name = f"F{kb.vkCode - VK_F1 + 1}"
                else:
                    key_name = f"VK_{kb.vkCode:02X}"

            if mods:
                captured[0] = "+".join(mods + [key_name])
            else:
                captured[0] = key_name

            event.set()
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        def hook_thread() -> None:
            thread_id[0] = kernel32.GetCurrentThreadId()

            # Force creation of a message queue for this thread
            msg = _MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

            hook_handle = user32.SetWindowsHookExW(WH_KEYBOARD_LL, hook_proc, None, 0)
            if not hook_handle:
                event.set()
                return

            try:
                while not event.is_set():
                    ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    if ret == 0 or ret == -1:
                        break
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            finally:
                user32.UnhookWindowsHookEx(hook_handle)

        t = threading.Thread(target=hook_thread, daemon=True)
        t.start()

        event.wait(timeout=timeout)

        if not event.is_set() and thread_id[0]:
            user32.PostThreadMessageW(thread_id[0], WM_QUIT, 0, 0)

        t.join(timeout=2.0)
        return captured[0]

    # ── Parsing ────────────────────────────────────────────────────────────────

    def parse_hotkey(self, hotkey: str) -> Optional[Tuple[int, int]]:
        """Convert a human-readable hotkey string into (modifiers, vk_code).

        Examples: ``"ctrl+shift+h"``, ``"alt+f4"``, ``"numadd"``, ``"volup"``.
        """
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
            elif part == "shift":
                mod |= MOD_SHIFT
            elif part in {"win", "windows", "meta"}:
                mod |= MOD_WIN
            else:
                return None

        if len(key) == 1 and key.isalnum():
            vk = ord(key.upper())
        elif key in _TOKEN_MAP:
            vk = _TOKEN_MAP[key]
        elif key.startswith("f") and key[1:].isdigit():
            n = int(key[1:])
            if 1 <= n <= 24:
                vk = VK_F1 + n - 1
            else:
                return None
        else:
            return None

        return mod, vk

    # ── Internal worker thread ───────────────────────────────────────────────

    def _worker(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        self._thread_id = kernel32.GetCurrentThreadId()

        # Create a message queue before registering hotkeys
        msg = _MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        # Register all configured hotkeys
        registration_errors: List[Tuple[str, str, str]] = []
        with self._lock:
            for name, hotkey_str in self._hotkeys.items():
                parsed = self.parse_hotkey(hotkey_str)
                if not parsed:
                    message = f"Invalid hotkey syntax: {hotkey_str!r}"
                    self._errors[name] = message
                    registration_errors.append((name, hotkey_str, message))
                    continue

                mod, vk = parsed
                hotkey_id = self._next_id
                self._next_id += 1

                if user32.RegisterHotKey(None, hotkey_id, mod, vk):
                    self._id_to_name[hotkey_id] = name
                    self._name_to_id[name] = hotkey_id
                else:
                    err = kernel32.GetLastError()
                    message = f"RegisterHotKey failed for {hotkey_str!r} (Win32 error {err})"
                    self._errors[name] = message
                    registration_errors.append((name, hotkey_str, message))

        for name, hotkey_str, message in registration_errors:
            self._emit_registration_error(name, hotkey_str, message)

        try:
            while self._running:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret == 0:   # WM_QUIT
                    break
                if ret == -1:  # Error
                    break

                if msg.message == WM_HOTKEY:
                    hotkey_id = msg.wParam
                    with self._lock:
                        name = self._id_to_name.get(hotkey_id)
                        if name:
                            self._triggered.add(name)
                            # Keep legacy Events in sync
                            if name == "trigger":
                                self.trigger.set()
                            elif name == "visual_trigger":
                                self.visual_trigger.set()

                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            with self._lock:
                for hid in list(self._id_to_name.keys()):
                    user32.UnregisterHotKey(None, hid)
                self._id_to_name.clear()
                self._name_to_id.clear()
            self._thread_id = 0
