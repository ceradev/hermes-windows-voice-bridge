import math
import threading
import tkinter as tk
from typing import Any


class OverlayService:
    def __init__(self) -> None:
        self.root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self.rect_id: int | None = None
        self.text_id: int | None = None
        self.canvas: tk.Canvas | None = None
        self.waveform_id: int | None = None
        self.led_id: int | None = None
        self.led_glow_id: int | None = None
        self.dots: list[int] = []
        self.animating: bool = False
        self.anim_step: int = 0
        self.state: str = "listening"

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # Remove windows borders
        self.root.attributes("-topmost", True)  # Always on top
        self.root.attributes("-transparentcolor", "black")  # Make black pixels transparent
        self.root.config(bg="black")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        width = 220
        height = 74
        x = (screen_width // 2) - (width // 2)
        y = screen_height - height - 120  # Float above taskbar

        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack()

        panel_bg = "#0a0a0a"
        border = "#333"
        text = "#e0e0e0"
        dim_text = "#777777"
        accent = "#4ade80"
        mono = ("Consolas", 8)

        self.rect_id = self.canvas.create_rectangle(
            2,
            2,
            width - 2,
            height - 2,
            fill=panel_bg,
            outline=border,
            width=1,
        )
        self.canvas.create_line(3, 3, width - 3, 3, fill="#1a1a1a")
        self.canvas.create_line(3, 3, 3, height - 3, fill="#1a1a1a")
        self.canvas.create_line(3, height - 3, width - 3, height - 3, fill="#050505")
        self.canvas.create_line(width - 3, 3, width - 3, height - 3, fill="#050505")

        scope_x1 = 12
        scope_y1 = 17
        scope_x2 = 112
        scope_y2 = 57
        self.canvas.create_rectangle(
            scope_x1,
            scope_y1,
            scope_x2,
            scope_y2,
            fill="#050505",
            outline=border,
            width=1,
        )
        self.canvas.create_line(scope_x1 + 1, 37, scope_x2 - 1, 37, fill="#182018")
        for grid_x in range(scope_x1 + 20, scope_x2, 20):
            self.canvas.create_line(
                grid_x,
                scope_y1 + 1,
                grid_x,
                scope_y2 - 1,
                fill="#111811",
            )
        for grid_y in (27, 47):
            self.canvas.create_line(
                scope_x1 + 1,
                grid_y,
                scope_x2 - 1,
                grid_y,
                fill="#111811",
            )

        self.waveform_id = self.canvas.create_line(
            self._wave_points(scope_x1, scope_y1, scope_x2, scope_y2),
            fill=accent,
            width=2,
            smooth=True,
        )

        self.canvas.create_text(
            12,
            9,
            text="VOICE SCOPE",
            fill=dim_text,
            font=("Consolas", 7),
            anchor="w",
        )
        self.canvas.create_text(126, 16, text="STATE", fill=dim_text, font=mono, anchor="w")
        self.text_id = self.canvas.create_text(
            126,
            31,
            text="Listening",
            fill=text,
            font=("Consolas", 11, "bold"),
            anchor="w",
        )

        self.led_glow_id = self.canvas.create_oval(
            190,
            19,
            208,
            37,
            fill="#14331f",
            outline="",
        )
        self.led_id = self.canvas.create_oval(
            195,
            24,
            203,
            32,
            fill=accent,
            outline="#9fffc2",
        )

        self.canvas.create_text(126, 49, text="MIC: ACTIVE", fill=accent, font=mono, anchor="w")
        self.canvas.create_text(126, 62, text="STT: ON", fill="#60a5fa", font=mono, anchor="w")

        self.root.withdraw()
        self._animate()
        self.root.mainloop()

    def _animate(self) -> None:
        root = self.root
        canvas = self.canvas
        waveform_id = self.waveform_id
        if root is None:
            return

        if self.animating and canvas is not None and waveform_id is not None:
            self.anim_step = (self.anim_step + 1) % 360
            canvas.coords(waveform_id, *self._wave_points(12, 17, 112, 57))

        root.after(50, self._animate)

    def _wave_points(self, x1: int, y1: int, x2: int, y2: int) -> list[float]:
        mid_y = (y1 + y2) // 2
        phase = self.anim_step * 0.22
        state_boost = 1.25 if self.state == "listening" else 0.75
        amplitude = (8 + (math.sin(self.anim_step * 0.08) * 3)) * state_boost
        points: list[float] = []

        for x in range(x1 + 4, x2 - 3, 4):
            t = (x - x1) / (x2 - x1)
            carrier = math.sin((t * math.tau * 3.0) + phase)
            harmonic = math.sin((t * math.tau * 8.0) - (phase * 0.45)) * 0.35
            envelope = math.sin(t * math.pi)
            y = mid_y + (carrier + harmonic) * amplitude * envelope
            points.extend((float(x), y))

        return points

    def _round_rect(
        self,
        canvas: tk.Canvas,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int = 25,
        **kwargs: Any,
    ) -> int:
        points = [x1+radius, y1,
                  x1+radius, y1,
                  x2-radius, y1,
                  x2-radius, y1,
                  x2, y1,
                  x2, y1+radius,
                  x2, y1+radius,
                  x2, y2-radius,
                  x2, y2-radius,
                  x2, y2,
                  x2-radius, y2,
                  x2-radius, y2,
                  x1+radius, y2,
                  x1+radius, y2,
                  x1, y2,
                  x1, y2-radius,
                  x1, y2-radius,
                  x1, y1+radius,
                  x1, y1+radius,
                  x1, y1]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def show(self, state: str = "listening") -> None:
        if not self.root:
            return
        root = self.root

        def _show() -> None:
            canvas = self.canvas
            text_id = self.text_id
            led_glow_id = self.led_glow_id
            led_id = self.led_id
            if canvas is None or text_id is None or led_glow_id is None or led_id is None:
                return

            self.animating = True
            self.state = state
            if state == "listening":
                canvas.itemconfig(text_id, text="Listening")
                canvas.itemconfig(led_glow_id, fill="#14331f")
                canvas.itemconfig(led_id, fill="#4ade80", outline="#9fffc2")
            elif state == "processing":
                canvas.itemconfig(text_id, text="Thinking")
                canvas.itemconfig(led_glow_id, fill="#3a2608")
                canvas.itemconfig(led_id, fill="#f59e0b", outline="#ffd166")

            root.deiconify()
            root.lift()
        root.after(0, _show)

    def hide(self) -> None:
        if not self.root:
            return
        root = self.root

        def _hide() -> None:
            self.animating = False
            root.withdraw()
        root.after(0, _hide)
