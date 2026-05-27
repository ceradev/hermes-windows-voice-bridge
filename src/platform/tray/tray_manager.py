import pystray
from PIL import Image, ImageDraw
import threading

class TrayManager:
    def __init__(self, app_name: str, on_open_app, on_pause_toggle, on_restart, on_quit):
        self.app_name = app_name
        self.on_open_app = on_open_app
        self.on_pause_toggle = on_pause_toggle
        self.on_restart = on_restart
        self.on_quit = on_quit
        self.icon = None
        self.is_connected = False
        self.is_paused = False

    def _make_icon_image(self, active: bool = True):
        size = 64
        color_dot = (16, 185, 129) if active else (239, 68, 68)
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Professional rounded dark box
        # Using ellipse for rounded corners simulation in basic PIL
        draw.rounded_rectangle((4, 4, 60, 60), radius=12, fill=(24, 24, 27), outline=(63, 63, 70), width=2)
        
        # Characteristic "H"
        draw.rectangle((20, 16, 26, 48), fill=(255, 255, 255))
        draw.rectangle((38, 16, 44, 48), fill=(255, 255, 255))
        draw.rectangle((26, 28, 38, 34), fill=(255, 255, 255))
        
        # Status indicator dot
        draw.ellipse((48, 48, 56, 56), fill=color_dot, outline=(0, 0, 0), width=1)
        return img

    def set_status(self, connected: bool):
        if self.is_connected != connected:
            self.is_connected = connected
            if self.icon:
                self.icon.icon = self._make_icon_image(connected)
                self.icon.title = f"{self.app_name} - {'Connected' if connected else 'Offline'}"
                # Update menu
                self.icon.update_menu()

    def _handle_pause(self, icon, item):
        self.is_paused = not self.is_paused
        self.on_pause_toggle(self.is_paused)
        if self.icon:
            self.icon.update_menu()

    def _noop(self, icon, item):
        pass

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(lambda _: "Hermes Voice Bridge", self._noop, default=True),
            pystray.MenuItem(lambda _: "🟢 Connected to VPS" if self.is_connected else "🔴 Offline (VPS down)", self._noop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Dashboard", self.on_open_app),
            pystray.MenuItem(lambda _: "▶ Resume Listening" if self.is_paused else "⏸ Pause Listening", self._handle_pause),
            pystray.MenuItem("Restart Service", self.on_restart),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.on_quit),
        )

    def start(self):
        if self.icon is None:
            self.icon = pystray.Icon(
                self.app_name,
                self._make_icon_image(True),
                self.app_name,
                self._build_menu()
            )
            # Run detached so it doesn't block the main thread (needed for pywebview)
            self.icon.run_detached()

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None
