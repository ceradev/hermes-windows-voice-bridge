from __future__ import annotations

import tkinter as tk

from .signals import OverlaySignal


class StatusOverlayWindow:
    def __init__(self, owner: tk.Tk) -> None:
        self.owner = owner
        self.window = tk.Toplevel(owner)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg="#0B1020")
        self.window.wm_attributes("-alpha", 0.95)

        shell = tk.Frame(self.window, bg="#111827", padx=18, pady=14, highlightbackground="#1F2937", highlightthickness=1)
        shell.pack(fill="both", expand=True)
        self.title_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="")
        tk.Label(shell, textvariable=self.title_var, bg="#111827", fg="white", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(shell, textvariable=self.detail_var, bg="#111827", fg="#94A3B8", font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
        self._hide_after: str | None = None

    def show_signal(self, signal: OverlaySignal) -> None:
        self.title_var.set(signal.title)
        self.detail_var.set(signal.detail)
        self.window.update_idletasks()
        self._position()
        self.window.deiconify()
        if self._hide_after is not None:
            self.window.after_cancel(self._hide_after)
        self._hide_after = self.window.after(signal.duration_ms, self.hide)

    def hide(self) -> None:
        self.window.withdraw()
        self._hide_after = None

    def _position(self) -> None:
        self.owner.update_idletasks()
        owner_x = self.owner.winfo_rootx()
        owner_y = self.owner.winfo_rooty()
        owner_w = self.owner.winfo_width()
        overlay_w = max(self.window.winfo_reqwidth(), 260)
        x = owner_x + owner_w - overlay_w - 24
        y = owner_y + 24
        self.window.geometry(f"+{max(x, 12)}+{max(y, 12)}")
