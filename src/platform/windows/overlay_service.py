import math
import logging
import math
import threading
import tkinter as tk
from typing import Any, Callable

logger = logging.getLogger(__name__)


class OverlayService:
    NORMAL_WIDTH = 160
    NORMAL_HEIGHT = 40
    EXPANDED_WIDTH = 360
    EXPANDED_HEIGHT = 154
    VALID_MODES = {"mini", "full"}

    def __init__(
        self,
        initial_mode: str = "mini",
        enabled: bool = True,
        initial_x: int | None = None,
        initial_y: int | None = None,
        on_position_change: Callable[[int, int], None] | None = None,
        on_visibility_change: Callable[[bool], None] | None = None,
        on_mode_change: Callable[[str], None] | None = None,
        on_open_dashboard: Callable[[], None] | None = None,
        on_start_mic: Callable[[], None] | None = None,
    ) -> None:
        self.root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self.canvas: tk.Canvas | None = None
        self.text_id = 0
        self.dot_ids: list[int] = []
        self.animating = False
        self.anim_step = 0
        self.state = "idle"
        self.mode = self._normalize_mode(initial_mode)
        self.enabled = bool(enabled)
        self._visible = False
        self._position_x = initial_x
        self._position_y = initial_y
        self._drag_origin: tuple[int, int] | None = None
        self._window_origin: tuple[int, int] | None = None

        self.current_w = 40.0 if self.mode == "mini" else float(self.NORMAL_WIDTH)
        self.is_hovered = False
        self._expanded = False
        self._expanded_pinned = False
        self._canvas_width = self.NORMAL_WIDTH
        self._canvas_height = self.NORMAL_HEIGHT
        self._pill_x_offset = 0

        self.latest_request_text = ""
        self.latest_response_text = ""
        self.latest_detail = ""

        self.bg_color = "#171717"
        self.border_color = "#2a2a2a"
        self.hover_color = "#333333"
        self.panel_bg = 0
        self.panel_title = 0
        self.panel_request_label = 0
        self.panel_request = 0
        self.panel_response_label = 0
        self.panel_response = 0
        self.pill_left = 0
        self.pill_right = 0
        self.pill_center = 0
        self.pill_line_top = 0
        self.pill_line_bot = 0
        self.idle_icon = 0
        self.btn_dashboard_bg = 0
        self.btn_dashboard = 0
        self.btn_mic_bg = 0
        self.btn_mic = 0
        self.btn_close_bg = 0
        self.btn_close = 0

        self._on_position_change = on_position_change
        self._on_visibility_change = on_visibility_change
        self._on_mode_change = on_mode_change
        self._on_open_dashboard = on_open_dashboard
        self._on_start_mic = on_start_mic
        self._stopping = False

    def start(self) -> None:
        self._stopping = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        """Stop the overlay Tk loop and wait briefly for its thread to exit."""
        self._stopping = True
        self.animating = False
        root = self.root

        if root is not None:
            def _shutdown() -> None:
                self._notify_visibility(False)
                try:
                    root.quit()
                    root.destroy()
                except tk.TclError as exc:
                    logger.debug("Overlay window was already closed: %s", exc)

            try:
                root.after(0, _shutdown)
            except tk.TclError as exc:
                logger.debug("Could not schedule overlay shutdown: %s", exc)

        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=timeout)
        if self._thread and self._thread.is_alive():
            logger.warning("Overlay thread did not stop within %.1f seconds", timeout)
        else:
            self._thread = None

    def is_visible(self) -> bool:
        return self._visible

    def set_mode(self, mode: str) -> None:
        normalized = self._normalize_mode(mode)
        changed = normalized != self.mode
        self.mode = normalized

        def _apply() -> None:
            if self.mode == "mini" and not self._expanded_pinned:
                self.hide_expanded()
            if self.mode == "full" and self.root and self.enabled:
                self.root.deiconify()
                self._notify_visibility(True)
            if self._on_mode_change and changed:
                self._on_mode_change(self.mode)

        if self.root:
            self.root.after(0, _apply)
        elif self._on_mode_change and changed:
            self._on_mode_change(self.mode)

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
            x, y = self._default_position(self.NORMAL_WIDTH, self.NORMAL_HEIGHT)
            self.root.geometry(f"+{x}+{y}")

    def _normalize_mode(self, mode: str) -> str:
        normalized = str(mode or "mini").strip().lower()
        return normalized if normalized in self.VALID_MODES else "mini"

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
        if not self.root:
            return 0, 0
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        return (sw // 2) - (width // 2), sh - height - 80

    def _run(self) -> None:
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "magenta")
        self.root.config(bg="magenta")

        width, height = self.NORMAL_WIDTH, self.NORMAL_HEIGHT
        x, y = self._position_x, self._position_y
        if x is None or y is None:
            x, y = self._default_position(width, height)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.canvas = tk.Canvas(self.root, width=width, height=height, bg="magenta", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_color = "#171717"
        self.border_color = "#2a2a2a"
        self.hover_color = "#333333"

        self.panel_bg = self.canvas.create_rectangle(0, 0, 0, 0, fill="#141414", outline="#303030", width=1, state="hidden")
        self.panel_title = self.canvas.create_text(0, 0, text="", fill="#a3a3a3", font=("Segoe UI", 9, "bold"), anchor="w", state="hidden")
        self.panel_request_label = self.canvas.create_text(0, 0, text="You", fill="#737373", font=("Segoe UI", 8, "bold"), anchor="w", state="hidden")
        self.panel_request = self.canvas.create_text(0, 0, text="", fill="#f5f5f5", font=("Segoe UI", 9), anchor="nw", width=308, state="hidden")
        self.panel_response_label = self.canvas.create_text(0, 0, text="Hermes", fill="#737373", font=("Segoe UI", 8, "bold"), anchor="w", state="hidden")
        self.panel_response = self.canvas.create_text(0, 0, text="", fill="#d4d4d4", font=("Segoe UI", 9), anchor="nw", width=308, state="hidden")

        # Shapes
        self.pill_left = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline=self.border_color, width=1)
        self.pill_right = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline=self.border_color, width=1)
        self.pill_center = self.canvas.create_rectangle(0, 0, 0, 0, fill=self.bg_color, outline="")
        self.pill_line_top = self.canvas.create_line(0, 0, 0, 0, fill=self.border_color, width=1)
        self.pill_line_bot = self.canvas.create_line(0, 0, 0, 0, fill=self.border_color, width=1)

        # UI Elements
        self.idle_icon = self.canvas.create_text(width // 2, height // 2, text="H", fill="#737373", font=("Segoe UI", 11, "bold"), state="hidden")

        self.btn_dashboard_bg = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline="", state="hidden")
        self.btn_dashboard = self.canvas.create_text(0, 0, text="⛶", fill="#a3a3a3", font=("Segoe UI", 12), state="hidden")

        self.btn_mic_bg = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline="", state="hidden")
        self.btn_mic = self.canvas.create_text(0, 0, text="🎙", fill="#a3a3a3", font=("Segoe UI", 11), state="hidden")

        self.btn_close_bg = self.canvas.create_oval(0, 0, 0, 0, fill=self.bg_color, outline="", state="hidden")
        self.btn_close = self.canvas.create_text(0, 0, text="✕", fill="#a3a3a3", font=("Segoe UI", 10), state="hidden")

        self.text_id = self.canvas.create_text(width // 2, height // 2, text="", fill="#F5F5F5", font=("Segoe UI", 10, "bold"), justify="center", state="hidden")

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

        self.state = "idle"
        if self.enabled:
            self._notify_visibility(True)
        else:
            self.root.withdraw()
            self._notify_visibility(False)

        self._animate()
        try:
            self.root.mainloop()
        finally:
            self.canvas = None
            self.root = None

    def _on_enter(self, event: Any) -> None:
        self.is_hovered = True
        if self.mode == "full" and (self.latest_request_text or self.latest_response_text):
            self.show_expanded(pinned=False)

    def _on_leave(self, event: Any) -> None:
        self.is_hovered = False
        self._update_btn_hover(-1, -1)
        if self._expanded and not self._expanded_pinned:
            self.hide_expanded()

    def _on_mouse_motion(self, event: Any) -> None:
        if self.is_hovered and self.current_w > 140:
            self._update_btn_hover(event.x, event.y)

    def _button_slot_at(self, x: int, y: int) -> str | None:
        if not (8 <= y <= 36):
            return None
        start = self._pill_x_offset
        if start + 20 < x < start + 60:
            return "dashboard"
        if start + 60 < x < start + 100:
            return "mic"
        if start + 100 < x < start + 140:
            return "close"
        return None

    def _update_btn_hover(self, x: int, y: int) -> None:
        if not self.canvas:
            return
        slot = self._button_slot_at(x, y)
        self.canvas.itemconfig(self.btn_dashboard_bg, fill=self.hover_color if slot == "dashboard" else self.bg_color)
        self.canvas.itemconfig(self.btn_dashboard, fill="#ffffff" if slot == "dashboard" else "#a3a3a3")

        mic_base_color = "#f87171" if self.state == "listening" else "#a3a3a3"
        self.canvas.itemconfig(self.btn_mic_bg, fill=self.hover_color if slot == "mic" else self.bg_color)
        self.canvas.itemconfig(self.btn_mic, fill="#ffffff" if slot == "mic" else mic_base_color)

        self.canvas.itemconfig(self.btn_close_bg, fill=self.hover_color if slot == "close" else self.bg_color)
        self.canvas.itemconfig(self.btn_close, fill="#ffffff" if slot == "close" else "#a3a3a3")

    def _on_click(self, event: Any) -> None:
        if not self.root:
            return
        self._drag_origin = (event.x_root, event.y_root)
        self._window_origin = (self.root.winfo_x(), self.root.winfo_y())

        if self.current_w > 140:
            slot = self._button_slot_at(event.x, event.y)
            if slot == "dashboard":
                if self._on_open_dashboard:
                    self._on_open_dashboard()
                return
            if slot == "mic":
                if self._on_start_mic:
                    self._on_start_mic()
                return
            if slot == "close":
                self.dismiss()
                return

        if self.latest_request_text or self.latest_response_text or self.mode == "full":
            if self._expanded and self._expanded_pinned:
                self.hide_expanded()
            else:
                self.show_expanded(pinned=True)

    def _target_width(self) -> int:
        if self._expanded or self.mode == "full":
            return self.NORMAL_WIDTH
        if self.state != "idle" or self.is_hovered:
            return self.NORMAL_WIDTH
        return 40

    def _state_color(self) -> str:
        if self.state == "listening":
            return "#f87171"
        if self.state in {"processing", "thinking", "transcribing"}:
            return "#fbbf24"
        if self.state in {"speaking", "responding"}:
            return "#60a5fa"
        return self.border_color

    def _animate(self) -> None:
        if self._stopping or self.root is None or not self.canvas:
            return

        target_w = self._target_width()
        diff = target_w - self.current_w
        if abs(diff) > 0.5:
            self.current_w += diff * 0.25
        else:
            self.current_w = target_w

        w = int(self.current_w)
        h = self.NORMAL_HEIGHT
        x_offset = (self._canvas_width - w) // 2
        self._pill_x_offset = x_offset
        r = 18
        accent = self._state_color()

        self.canvas.itemconfig(self.pill_left, outline=accent)
        self.canvas.itemconfig(self.pill_right, outline=accent)
        self.canvas.itemconfig(self.pill_line_top, fill=accent)
        self.canvas.itemconfig(self.pill_line_bot, fill=accent)

        self.canvas.coords(self.pill_left, x_offset + 2, 2, x_offset + 2 + r * 2, 2 + r * 2)
        self.canvas.coords(self.pill_right, x_offset + w - 2 - r * 2, 2, x_offset + w - 2, 2 + r * 2)
        self.canvas.coords(self.pill_center, x_offset + 2 + r, 2, x_offset + w - 2 - r, h - 2)
        self.canvas.coords(self.pill_line_top, x_offset + 2 + r, 2, x_offset + w - 2 - r, 2)
        self.canvas.coords(self.pill_line_bot, x_offset + 2 + r, h - 2, x_offset + w - 2 - r, h - 2)
        self.canvas.coords(self.idle_icon, x_offset + w // 2, h // 2)
        if self.text_id:
            self.canvas.coords(self.text_id, x_offset + w // 2, h // 2)

        is_active = self.state != "idle"
        show_controls = self.is_hovered and w > 140 and not self._expanded
        if show_controls:
            self.canvas.itemconfig(self.idle_icon, state="hidden")
            self._hide_active()
            self._show_buttons(x_offset)
            self.canvas.itemconfig(self.btn_mic, text="■" if self.state == "listening" else "🎙")
        elif w < 50 and not is_active:
            self.canvas.itemconfig(self.idle_icon, state="normal")
            self._hide_buttons()
            self._hide_active()
        elif is_active or self.mode == "full":
            self.canvas.itemconfig(self.idle_icon, state="hidden")
            self._hide_buttons()
            self._show_active(x_offset)

        if self.animating and self.state == "listening":
            self.anim_step += 1
            for i, did in enumerate(self.dot_ids):
                phase = (self.anim_step * 0.15) - (i * 0.5)
                val = (math.sin(phase) + 1) / 2
                gray = int(80 + (val * 175))
                color = f"#{gray:02x}{gray:02x}{gray:02x}"
                self.canvas.itemconfig(did, fill=color)

        if not self._stopping and self.root is not None:
            self.root.after(16, self._animate)

    def _hide_buttons(self) -> None:
        if not self.canvas:
            return
        self.canvas.itemconfig(self.btn_dashboard_bg, state="hidden")
        self.canvas.itemconfig(self.btn_dashboard, state="hidden")
        self.canvas.itemconfig(self.btn_mic_bg, state="hidden")
        self.canvas.itemconfig(self.btn_mic, state="hidden")
        self.canvas.itemconfig(self.btn_close_bg, state="hidden")
        self.canvas.itemconfig(self.btn_close, state="hidden")

    def _show_buttons(self, x_offset: int) -> None:
        if not self.canvas:
            return
        cy = 20
        self.canvas.coords(self.btn_dashboard_bg, x_offset + 40 - 14, cy - 14, x_offset + 40 + 14, cy + 14)
        self.canvas.coords(self.btn_dashboard, x_offset + 40, cy)
        self.canvas.itemconfig(self.btn_dashboard_bg, state="normal")
        self.canvas.itemconfig(self.btn_dashboard, state="normal")

        self.canvas.coords(self.btn_mic_bg, x_offset + 80 - 14, cy - 14, x_offset + 80 + 14, cy + 14)
        self.canvas.coords(self.btn_mic, x_offset + 80, cy)
        self.canvas.itemconfig(self.btn_mic_bg, state="normal")
        self.canvas.itemconfig(self.btn_mic, state="normal")

        self.canvas.coords(self.btn_close_bg, x_offset + 120 - 14, cy - 14, x_offset + 120 + 14, cy + 14)
        self.canvas.coords(self.btn_close, x_offset + 120, cy)
        self.canvas.itemconfig(self.btn_close_bg, state="normal")
        self.canvas.itemconfig(self.btn_close, state="normal")

    def _hide_active(self) -> None:
        if not self.canvas:
            return
        self.canvas.itemconfig(self.text_id, state="hidden")
        for did in self.dot_ids:
            self.canvas.itemconfig(did, state="hidden")

    def _show_active(self, x_offset: int) -> None:
        if not self.canvas:
            return
        if self.state == "listening":
            self.canvas.itemconfig(self.text_id, state="hidden")
            dot_spacing = 12
            start_x = x_offset + 80 - (dot_spacing * 1.5)
            for i, did in enumerate(self.dot_ids):
                dx = start_x + (i * dot_spacing)
                self.canvas.coords(did, dx - 3, 20 - 3, dx + 3, 20 + 3)
                self.canvas.itemconfig(did, state="normal")
        else:
            for did in self.dot_ids:
                self.canvas.itemconfig(did, state="hidden")
            self.canvas.itemconfig(self.text_id, state="normal")

    def _on_drag_motion(self, event: Any) -> None:
        if not self.root or not self._drag_origin or not self._window_origin:
            return
        if self.current_w > 140:
            local_x = self._drag_origin[0] - self.root.winfo_x()
            local_y = self._drag_origin[1] - self.root.winfo_y()
            if self._button_slot_at(local_x, local_y):
                return
        self.root.geometry(f"+{self._window_origin[0] + (event.x_root - self._drag_origin[0])}+{self._window_origin[1] + (event.y_root - self._drag_origin[1])}")

    def _on_drag_end(self, event: Any) -> None:
        self._drag_origin = None
        self._window_origin = None
        self._persist_position()

    def _short_text(self, value: str, limit: int) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= limit:
            return text
        return f"{text[: max(0, limit - 1)].rstrip()}…"

    def _state_label(self) -> str:
        labels = {
            "idle": "Idle",
            "listening": "Listening",
            "processing": "Thinking",
            "thinking": "Thinking",
            "transcribing": "Thinking",
            "speaking": "Speaking",
            "responding": "Speaking",
        }
        return labels.get(self.state, self.state.title())

    def _set_status_text(self, state: str, detail: str = "") -> None:
        self.latest_detail = str(detail or "")
        if not self.canvas or not self.text_id:
            return
        if state == "listening":
            self.canvas.itemconfig(self.text_id, text="")
        elif state in {"processing", "thinking", "transcribing"}:
            self.canvas.itemconfig(self.text_id, text=self._short_text(detail or "Thinking...", 18))
        elif state in {"speaking", "responding"}:
            preview = self.latest_response_text or detail or "Speaking..."
            self.canvas.itemconfig(self.text_id, text=self._short_text(preview, 18))
        else:
            self.canvas.itemconfig(self.text_id, text=self._short_text(detail or "Ready", 18))

    def show(self, state: str = "listening", detail: str = "") -> None:
        if not self.root or not self.enabled:
            return
        root = self.root

        def _show() -> None:
            self.state = str(state or "idle").strip().lower()
            self.animating = self.state == "listening"
            self._set_status_text(self.state, detail)
            if self._expanded:
                self._render_expanded_panel()
            root.deiconify()
            root.lift()
            self._notify_visibility(True)

        root.after(0, _show)

    def show_result(self, request_text: str, response_text: str) -> None:
        self.latest_request_text = str(request_text or "")
        self.latest_response_text = str(response_text or "")

        def _show_result() -> None:
            root = self.root
            if not self.enabled or not root:
                return
            self.state = "speaking"
            self.animating = False
            self._set_status_text("speaking", self.latest_response_text or "Speaking...")
            if self.mode == "full":
                self._expanded_pinned = False
                self._show_expanded_now()
            elif self._expanded:
                self._render_expanded_panel()
            root.deiconify()
            root.lift()
            self._notify_visibility(True)

        if self.root:
            self.root.after(0, _show_result)

    def show_expanded(self, pinned: bool = True) -> None:
        if not self.root:
            return

        def _show_expanded() -> None:
            self._expanded_pinned = bool(pinned)
            self._show_expanded_now()

        self.root.after(0, _show_expanded)

    def _show_expanded_now(self) -> None:
        if not self.root or not self.canvas:
            return
        self._expanded = True
        self._resize_window(self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)
        self._render_expanded_panel()
        if self.enabled:
            self.root.deiconify()
            self.root.lift()
            self._notify_visibility(True)

    def hide_expanded(self) -> None:
        if not self.root:
            return

        def _hide_expanded() -> None:
            if not self.canvas:
                return
            self._expanded = False
            self._expanded_pinned = False
            self.canvas.itemconfig(self.panel_bg, state="hidden")
            self.canvas.itemconfig(self.panel_title, state="hidden")
            self.canvas.itemconfig(self.panel_request_label, state="hidden")
            self.canvas.itemconfig(self.panel_request, state="hidden")
            self.canvas.itemconfig(self.panel_response_label, state="hidden")
            self.canvas.itemconfig(self.panel_response, state="hidden")
            self._resize_window(self.NORMAL_WIDTH, self.NORMAL_HEIGHT)

        self.root.after(0, _hide_expanded)

    def _render_expanded_panel(self) -> None:
        if not self.canvas:
            return
        self.canvas.coords(self.panel_bg, 8, 44, self.EXPANDED_WIDTH - 8, self.EXPANDED_HEIGHT - 8)
        self.canvas.coords(self.panel_title, 22, 58)
        self.canvas.coords(self.panel_request_label, 22, 78)
        self.canvas.coords(self.panel_request, 22, 90)
        self.canvas.coords(self.panel_response_label, 22, 112)
        self.canvas.coords(self.panel_response, 22, 124)
        self.canvas.itemconfig(self.panel_title, text=f"Overlay · {self._state_label()}")
        self.canvas.itemconfig(self.panel_request, text=self._short_text(self.latest_request_text or self.latest_detail or "No request yet.", 120))
        self.canvas.itemconfig(self.panel_response, text=self._short_text(self.latest_response_text or "No response yet.", 120))
        for item in (
            self.panel_bg,
            self.panel_title,
            self.panel_request_label,
            self.panel_request,
            self.panel_response_label,
            self.panel_response,
        ):
            self.canvas.itemconfig(item, state="normal")

    def _resize_window(self, width: int, height: int) -> None:
        if not self.root or not self.canvas:
            return
        if width == self._canvas_width and height == self._canvas_height:
            return
        self._canvas_width = width
        self._canvas_height = height
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.canvas.config(width=width, height=height)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def cancel_active(self) -> None:
        self.hide()

    def hide(self) -> None:
        if not self.root:
            return
        root = self.root

        def _hide() -> None:
            self.animating = False
            self.state = "idle"
            self.is_hovered = False
            self._expanded = False
            self._expanded_pinned = False
            if self.canvas:
                for item in (
                    self.panel_bg,
                    self.panel_title,
                    self.panel_request_label,
                    self.panel_request,
                    self.panel_response_label,
                    self.panel_response,
                ):
                    self.canvas.itemconfig(item, state="hidden")
            self._resize_window(self.NORMAL_WIDTH, self.NORMAL_HEIGHT)
            root.withdraw()
            self._notify_visibility(False)

        root.after(0, _hide)

    def dismiss(self) -> None:
        self.hide()
