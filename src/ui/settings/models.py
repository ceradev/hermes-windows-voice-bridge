from __future__ import annotations

from dataclasses import dataclass, field

from src.core.state import ShortcutKeyState

DISPLAY_NAMES = {
    "control_l": "CTRL",
    "control_r": "CTRL",
    "ctrl": "CTRL",
    "shift_l": "SHIFT",
    "shift_r": "SHIFT",
    "shift": "SHIFT",
    "alt_l": "ALT",
    "alt_r": "ALT",
    "alt": "ALT",
    "option": "ALT",
    "super_l": "WIN",
    "super_r": "WIN",
    "win": "WIN",
    "space": "SPACE",
    "return": "ENTER",
    "escape": "ESC",
    "prior": "PAGEUP",
    "next": "PAGEDOWN",
}

KEY_PRIORITY = {
    "CTRL": 0,
    "SHIFT": 1,
    "ALT": 2,
    "WIN": 3,
}


def normalize_key_name(raw: str) -> str:
    key = (raw or "").strip().lower()
    if not key:
        return ""
    return DISPLAY_NAMES.get(key, key.upper())


@dataclass(slots=True)
class SessionPreferenceState:
    remember_me: bool = True
    status_label: str = "Signed out"
    detail: str = "Hermes will ask you to sign in when needed."


@dataclass(slots=True)
class ShortcutEditorState:
    caption: str = "Click to record shortcut"
    listening: bool = False
    conflict: str = ""
    accelerator: str = ""
    pills: list[ShortcutKeyState] = field(default_factory=list)

    def begin_capture(self) -> "ShortcutEditorState":
        self.caption = "Listening…"
        self.listening = True
        self.conflict = ""
        self.pills = []
        return self

    def update_pressed(self, keys: list[str]) -> "ShortcutEditorState":
        normalized = [normalize_key_name(key) for key in keys if normalize_key_name(key)]
        normalized.sort(key=lambda item: (KEY_PRIORITY.get(item, 50), item))
        self.pills = [ShortcutKeyState(key=item, pressed=True) for item in normalized]
        self.accelerator = "+".join(item.lower() for item in normalized)
        if normalized:
            self.caption = " + ".join(normalized)
        return self

    def finish_capture(self, conflict_with: str = "") -> "ShortcutEditorState":
        self.listening = False
        self.conflict = conflict_with
        self.caption = "Shortcut saved" if self.accelerator and not conflict_with else (conflict_with or "Click to record shortcut")
        for pill in self.pills:
            pill.pressed = False
        return self

    def clear(self) -> "ShortcutEditorState":
        self.caption = "Click to record shortcut"
        self.listening = False
        self.conflict = ""
        self.accelerator = ""
        self.pills = []
        return self

    def load_accelerator(self, accelerator: str) -> "ShortcutEditorState":
        self.clear()
        keys = [normalize_key_name(part) for part in accelerator.split("+") if normalize_key_name(part)]
        self.accelerator = "+".join(item.lower() for item in keys)
        self.pills = [ShortcutKeyState(key=item, pressed=False) for item in keys]
        if keys:
            self.caption = " + ".join(keys)
        return self
