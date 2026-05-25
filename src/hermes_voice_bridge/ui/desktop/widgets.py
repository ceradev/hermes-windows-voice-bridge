from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import PALETTE


class PillRow(tk.Frame):
    def __init__(self, master: tk.Misc, bg: str | None = None) -> None:
        super().__init__(master, bg=bg or PALETTE["surface_bg"])
        self.bg = bg or PALETTE["surface_bg"]
        self._labels: list[tk.Label] = []

    def set_keys(self, keys: list[tuple[str, bool]]) -> None:
        for label in self._labels:
            label.destroy()
        self._labels.clear()
        for idx, (key, pressed) in enumerate(keys):
            if idx:
                plus = tk.Label(self, text="+", bg=self.bg, fg=PALETTE["muted_fg"], font=("Segoe UI", 13, "bold"))
                plus.pack(side="left", padx=(8, 8))
                self._labels.append(plus)
            label = tk.Label(
                self,
                text=f" {key} ",
                bg=PALETTE["pill_active"] if pressed else PALETTE["pill_idle"],
                fg="white",
                padx=10,
                pady=6,
                font=("Segoe UI", 10, "bold"),
                relief="flat",
            )
            label.pack(side="left")
            self._labels.append(label)


class LabeledSwitch(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str, description: str) -> None:
        super().__init__(master)
        self.var = tk.BooleanVar(value=False)
        copy = ttk.Frame(self)
        copy.pack(side="left", fill="x", expand=True)
        ttk.Label(copy, text=title, style="Section.TLabel").pack(anchor="w")
        ttk.Label(copy, text=description, style="Muted.TLabel", wraplength=420).pack(anchor="w", pady=(2, 0))
        self.button = ttk.Checkbutton(self, variable=self.var)
        self.button.pack(side="right", padx=(12, 0))
