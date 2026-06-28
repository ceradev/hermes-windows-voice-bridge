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
        self.window.configure(bg="#09090b")
        self.window.wm_attributes("-alpha", 0.95)

        self.shell = tk.Frame(self.window, bg="#111111", padx=16, pady=12, highlightbackground="#262626", highlightthickness=1)
        self.shell.pack(fill="both", expand=True)

        header_frame = tk.Frame(self.shell, bg="#111111")
        header_frame.pack(fill="x", anchor="w")

        self.indicator_canvas = tk.Canvas(header_frame, width=8, height=8, bg="#111111", highlightthickness=0)
        self.indicator_canvas.pack(side="left", padx=(0, 8))
        self.indicator_oval = self.indicator_canvas.create_oval(0, 0, 8, 8, fill="#525252", outline="")

        self.title_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="")
        tk.Label(header_frame, textvariable=self.title_var, bg="#111111", fg="#f5f5f5", font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(self.shell, textvariable=self.detail_var, bg="#111111", fg="#a3a3a3", font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0), padx=(16, 0))
        self._hide_after: str | None = None

    def show_signal(self, signal: OverlaySignal) -> None:
        self.title_var.set(signal.title)
        self.detail_var.set(signal.detail)

        title_lower = signal.title.lower()
        if "listen" in title_lower:
            color = "#16a34a"  # state-ready
        elif "process" in title_lower:
            color = "#3D2BFF"  # accent-primary
        elif "speak" in title_lower:
            color = "#5B4AFF"  # accent-secondary
        elif "error" in title_lower:
            color = "#dc2626"  # state-error
        elif "warn" in title_lower:
            color = "#d97706"  # state-warn
        else:
            color = "#525252"  # text-muted

        self.indicator_canvas.itemconfig(self.indicator_oval, fill=color)
        self.shell.configure(highlightbackground=color if color != "#525252" else "#262626")

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
