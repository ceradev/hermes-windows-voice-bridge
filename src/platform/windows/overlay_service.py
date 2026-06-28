import math
import threading
import tkinter as tk
from typing import Any, Callable

class OverlayService:
    def __init__(
        self,
        initial_mode: str = "mini",
        enabled: bool = True,
        initial_x: int | None = None,
        initial_y: int | None = None,
        on_position_change: Callable[[int, int], None] | None = None,
        on_visibility_change: Callable[[bool], None] | None = None,
        on_open_dashboard: Callable[[], None] | None = None,
        on_start_mic: Callable[[], None] | None = None,
    ) -> None:
        self.root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self.canvas: tk.Canvas | None = None
        self.text_id: int | None = None
        self.dot_ids: list[int] = []
        self.animating = False
        self.anim_step = 0
        self.state = "idle"
        self.enabled = bool(enabled)
        self._visible = False
        self._position_x = initial_x
        self._position_y = initial_y
        self._drag_origin: tuple[int, int] | None = None
        self._window_origin: tuple[int, int] | None = None
        
        self.current_w = 40.0
        self.is_hovered = False
        
        self._on_position_change = on_position_change
        self._on_visibility_change = on_visibility_change
        self._on_open_dashboard = on_open_dashboard
        self._on_start_mic = on_start_mic

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def is_visible(self) -> bool:
        return self._visible

    def set_mode(self, mode: str) -> None:
        pass

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if not self.enabled:
            self.hide()

    def set_position(self, x: int | None, y: int | None) -> None:
        if x is None or y is None:
            self._position_x = None
            self._position_y = None
            return
        self._position_x = int(x)
        self._position_y = int(y)
        if self.root:
            self.root.geometry(f"+{self._position_x}+{self._position_y}")

    def reset_position(self) -> None:
        self._position_x = None
        self._position_y = None
        if self.root:
            x, y = self._default_position(160, 40)
            self.root.geometry(f"+{x}+{y}")

    def _notify_visibility(self, visible: bool) -> None:
        self._visible = visible
        if self._on_visibility_change:
            self._on_visibility_change(visible)

    def _persist_position(self) -> None:
        if self.root:
            self._position_x = self.root.winfo_x()
            self._position_y = self.root.winfo_y()
            if self._on_position_change and self._position_x is not None and self._position_y is not None:
                self._on_position_change(self._position_x, self._position_y)

    def _default_position(self, width: int, height: int) -> tuple[int, int]:
        if not self.root: return 0, 0
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        return (sw // 2) - (width // 2), sh - height - 80

    def _run(self) -> None:
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "magenta")
        self.root.config(bg="magenta")

        width, height = 160, 40
        x, y = self._position_x, self._position_y
        if x is None or y is None:
            x, y = self._default_position(width, height)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.canvas = tk.Canvas(self.root, width=width, height=height, bg="magenta", highlightthickness=0)
        self.canvas.pack()
        
        self.bg_color = "#171717"
        self.border_color = "#2a2a2a"
        self.hover_color = "#333333"
        
        # Shapes
        self.pill_left = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline=self.border_color, width=1)
        self.pill_right = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline=self.border_color, width=1)
        self.pill_center = self.canvas.create_rectangle(0, 0, 0, 0, fill=self.bg_color, outline="")
        self.pill_line_top = self.canvas.create_line(0, 0, 0, 0, fill=self.border_color, width=1)
        self.pill_line_bot = self.canvas.create_line(0, 0, 0, 0, fill=self.border_color, width=1)

        # UI Elements
        # Idle Icon (Hermes Logo / Circle)
        self.idle_icon = self.canvas.create_text(width//2, height//2, text="H", fill="#737373", font=("Segoe UI", 11, "bold"), state="hidden")
        
        # Buttons
        self.btn_dashboard_bg = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline="", state="hidden")
        self.btn_dashboard = self.canvas.create_text(0, 0, text="⛶", fill="#a3a3a3", font=("Segoe UI", 12), state="hidden")
        
        self.btn_mic_bg = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline="", state="hidden")
        self.btn_mic = self.canvas.create_text(0, 0, text="🎙", fill="#a3a3a3", font=("Segoe UI", 11), state="hidden")
        
        self.btn_close_bg = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline="", state="hidden")
        self.btn_close = self.canvas.create_text(0, 0, text="✕", fill="#a3a3a3", font=("Segoe UI", 10), state="hidden")

        # Active elements
        self.text_id = self.canvas.create_text(width//2, height//2, text="", fill="#F5F5F5", font=("Segoe UI", 10, "bold"), justify="center", state="hidden")
        
        for _ in range(4):
            did = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline="", state="hidden")
            self.dot_ids.append(did)

        # Events
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<ButtonPress-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.canvas.bind("<Motion>", self._on_mouse_motion)

        # Start always visible as idle
        self.state = "idle"
        self._notify_visibility(True)
        
        self._animate()
        self.root.mainloop()

    def _on_enter(self, event: Any) -> None:
        self.is_hovered = True

    def _on_leave(self, event: Any) -> None:
        self.is_hovered = False
        self._update_btn_hover(-1, -1)

    def _on_mouse_motion(self, event: Any) -> None:
        if self.is_hovered and self.current_w > 140:
            self._update_btn_hover(event.x, event.y)

    def _update_btn_hover(self, x: int, y: int) -> None:
        if not self.canvas: return
        # Check which button is hovered
        self.canvas.itemconfig(self.btn_dashboard_bg, fill=self.hover_color if (20 < x < 60) else self.bg_color)
        self.canvas.itemconfig(self.btn_dashboard, fill="#ffffff" if (20 < x < 60) else "#a3a3a3")
        
        mic_base_color = "#f87171" if self.state == "listening" else "#a3a3a3"
        self.canvas.itemconfig(self.btn_mic_bg, fill=self.hover_color if (60 < x < 100) else self.bg_color)
        self.canvas.itemconfig(self.btn_mic, fill="#ffffff" if (60 < x < 100) else mic_base_color)
        
        self.canvas.itemconfig(self.btn_close_bg, fill=self.hover_color if (100 < x < 140) else self.bg_color)
        self.canvas.itemconfig(self.btn_close, fill="#ffffff" if (100 < x < 140) else "#a3a3a3")

    def _on_click(self, event: Any) -> None:
        if not self.root: return
        self._drag_origin = (event.x_root, event.y_root)
        self._window_origin = (self.root.winfo_x(), self.root.winfo_y())
        
        # Handle button clicks
        if self.current_w > 140:
            if 20 < event.x < 60:
                if self._on_open_dashboard: self._on_open_dashboard()
            elif 60 < event.x < 100:
                if self._on_start_mic: self._on_start_mic()
            elif 100 < event.x < 140:
                self.dismiss()

    def _animate(self) -> None:
        if self.root is None or not self.canvas: return
        
        is_active = self.state != "idle"
        target_w = 160 if (self.is_hovered or is_active) else 40
        
        diff = target_w - self.current_w
        if abs(diff) > 0.5:
            self.current_w += diff * 0.25
        else:
            self.current_w = target_w
            
        w = int(self.current_w)
        h = 40
        max_w = 160
        x_offset = (max_w - w) // 2
        r = 18
        
        # Update shapes
        self.canvas.coords(self.pill_left, x_offset+2, 2, x_offset+2+r*2, 2+r*2)
        self.canvas.coords(self.pill_right, x_offset+w-2-r*2, 2, x_offset+w-2, 2+r*2)
        self.canvas.coords(self.pill_center, x_offset+2+r, 2, x_offset+w-2-r, h-2)
        self.canvas.coords(self.pill_line_top, x_offset+2+r, 2, x_offset+w-2-r, 2)
        self.canvas.coords(self.pill_line_bot, x_offset+2+r, h-2, x_offset+w-2-r, h-2)

        # Visibility logic
        if self.is_hovered and w > 140:
            self.canvas.itemconfig(self.idle_icon, state="hidden")
            self._hide_active()
            self._show_buttons()
            if self.state == "listening":
                self.canvas.itemconfig(self.btn_mic, text="■")
            else:
                self.canvas.itemconfig(self.btn_mic, text="🎙")
        elif w < 50 and not is_active:
            self.canvas.itemconfig(self.idle_icon, state="normal")
            self._hide_buttons()
            self._hide_active()
        elif is_active:
            self.canvas.itemconfig(self.idle_icon, state="hidden")
            self._hide_buttons()
            self._show_active()

        if self.animating and self.state == "listening":
            self.anim_step += 1
            for i, did in enumerate(self.dot_ids):
                phase = (self.anim_step * 0.15) - (i * 0.5)
                val = (math.sin(phase) + 1) / 2
                gray = int(80 + (val * 175))
                color = f"#{gray:02x}{gray:02x}{gray:02x}"
                self.canvas.itemconfig(did, fill=color)

        self.root.after(16, self._animate)

    def _hide_buttons(self) -> None:
        if not self.canvas: return
        self.canvas.itemconfig(self.btn_dashboard_bg, state="hidden")
        self.canvas.itemconfig(self.btn_dashboard, state="hidden")
        self.canvas.itemconfig(self.btn_mic_bg, state="hidden")
        self.canvas.itemconfig(self.btn_mic, state="hidden")
        self.canvas.itemconfig(self.btn_close_bg, state="hidden")
        self.canvas.itemconfig(self.btn_close, state="hidden")

    def _show_buttons(self) -> None:
        if not self.canvas: return
        cy = 20
        self.canvas.coords(self.btn_dashboard_bg, 40-14, cy-14, 40+14, cy+14)
        self.canvas.coords(self.btn_dashboard, 40, cy)
        self.canvas.itemconfig(self.btn_dashboard_bg, state="normal")
        self.canvas.itemconfig(self.btn_dashboard, state="normal")
        
        self.canvas.coords(self.btn_mic_bg, 80-14, cy-14, 80+14, cy+14)
        self.canvas.coords(self.btn_mic, 80, cy)
        self.canvas.itemconfig(self.btn_mic_bg, state="normal")
        self.canvas.itemconfig(self.btn_mic, state="normal")
        
        self.canvas.coords(self.btn_close_bg, 120-14, cy-14, 120+14, cy+14)
        self.canvas.coords(self.btn_close, 120, cy)
        self.canvas.itemconfig(self.btn_close_bg, state="normal")
        self.canvas.itemconfig(self.btn_close, state="normal")

    def _hide_active(self) -> None:
        if not self.canvas: return
        self.canvas.itemconfig(self.text_id, state="hidden")
        for did in self.dot_ids:
            self.canvas.itemconfig(did, state="hidden")

    def _show_active(self) -> None:
        if not self.canvas: return
        if self.state == "listening":
            self.canvas.itemconfig(self.text_id, state="hidden")
            dot_spacing = 12
            start_x = 80 - (dot_spacing * 1.5)
            for i, did in enumerate(self.dot_ids):
                dx = start_x + (i * dot_spacing)
                self.canvas.coords(did, dx-3, 20-3, dx+3, 20+3)
                self.canvas.itemconfig(did, state="normal")
        else:
            for did in self.dot_ids:
                self.canvas.itemconfig(did, state="hidden")
            self.canvas.itemconfig(self.text_id, state="normal")

    def _on_drag_motion(self, event: Any) -> None:
        if not self.root or not self._drag_origin or not self._window_origin: return
        # Don't drag if we clicked a button
        if self.current_w > 140:
            if 20 < self._drag_origin[0] - self.root.winfo_x() < 140:
                return
        self.root.geometry(f"+{self._window_origin[0] + (event.x_root - self._drag_origin[0])}+{self._window_origin[1] + (event.y_root - self._drag_origin[1])}")

    def _on_drag_end(self, event: Any) -> None:
        self._drag_origin = None
        self._window_origin = None
        self._persist_position()

    def show(self, state: str = "listening", detail: str = "") -> None:
        if not self.root or not self.enabled: return
        def _show():
            self.state = state
            self.animating = state == "listening"
            if self.canvas and self.text_id:
                if state == "listening":
                    self.canvas.itemconfig(self.text_id, text="")
                elif state == "processing" or state == "thinking" or state == "transcribing":
                    self.canvas.itemconfig(self.text_id, text="Thinking...")
                elif state == "speaking" or state == "responding":
                    self.canvas.itemconfig(self.text_id, text="Speaking...")
                else:
                    self.canvas.itemconfig(self.text_id, text="...")
            self.root.deiconify()
            self.root.lift()
            self._notify_visibility(True)
        self.root.after(0, _show)

    def show_result(self, request_text: str, response_text: str) -> None:
        self.show("speaking", "Speaking...")

    def cancel_active(self) -> None:
        self.hide()

    def hide(self) -> None:
        if not self.root: return
        def _hide():
            self.animating = False
            self.state = "idle"
            self.is_hovered = False
            # Pill becomes tiny, doesn't disappear unless dismiss() is called
        self.root.after(0, _hide)

    def dismiss(self) -> None:
        if not self.root: return
        def _dismiss():
            self.animating = False
            self.state = "idle"
            self.root.withdraw()
            self._notify_visibility(False)
        self.root.after(0, _dismiss)
