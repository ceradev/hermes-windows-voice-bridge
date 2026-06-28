import logging
import os
import sys
import threading
import time
import webview
from pathlib import Path

# Add repo root to python path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.core.config.config_service import ConfigService
from src.core.session.session_manager import SessionManager
from src.core.state import AppStateStore
from src.storage.database import Database
from src.services.hermes.hermes_client import HermesClient
from src.services.audio.audio_service import AudioService
from src.services.wakeword.wake_phrase_manager import WakePhraseManager
from src.services.tts.tts_service import TTSService
from src.api.webview_bridge import WebviewBridge
from src.platform.shortcuts.shortcut_manager import ShortcutManager
from src.platform.tray.tray_manager import TrayManager
from src.platform.windows.voice_loop import VoiceLoop
from src.platform.windows.overlay_service import OverlayService
from src.platform.windows.autostart_service import AutostartService

UI_DIST_DIR = REPO_ROOT / "src" / "ui" / "app" / "dist"
UI_SRC_DIR = REPO_ROOT / "src" / "ui" / "app" / "src"


def _newest_source_mtime() -> float:
    if not UI_SRC_DIR.is_dir():
        return 0.0
    newest = 0.0
    for path in UI_SRC_DIR.rglob("*"):
        if path.suffix in {".tsx", ".ts", ".css"} and path.is_file():
            newest = max(newest, path.stat().st_mtime)
    return newest


def resolve_ui_url() -> str:
    index_html = UI_DIST_DIR / "index.html"

    if os.environ.get("HERMES_UI_DEV") == "1":
        url = "http://127.0.0.1:5173"
        print(f"[Hermes UI] Dev mode: {url}")
        print("[Hermes UI] Start Vite with: cd src\\ui\\app && npm run dev")
        return url

    if not index_html.is_file():
        print(f"[Hermes UI] Missing build: {index_html}")
        print("[Hermes UI] Run: cd src\\ui\\app && npm install && npm run build")
        print("[Hermes UI] Or: .\\scripts\\run_desktop_app.ps1")
        print("[Hermes UI] Dev fallback: set HERMES_UI_DEV=1 and npm run dev")
        sys.exit(1)

    dist_mtime = index_html.stat().st_mtime
    src_mtime = _newest_source_mtime()
    if src_mtime > dist_mtime + 1:
        print("[Hermes UI] WARNING: src/ui/app/src is newer than dist.")
        print("[Hermes UI] Rebuild with: cd src\\ui\\app && npm run build")

    print(f"[Hermes UI] Loading: {index_html.resolve()}")
    print(
        "[Hermes UI] dist built:",
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(dist_mtime)),
    )
    return str(index_html.resolve())


def main():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")

    app_dir = Path(appdata) / "HermesVoiceBridge"
    app_dir.mkdir(parents=True, exist_ok=True)

    db_path = app_dir / "database.sqlite"
    log_path = app_dir / "app.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    class PrintLogger:
        def write(self, message):
            original_stdout.write(message)
            original_stdout.flush()
            if message.strip():
                logging.getLogger("stdout").info(message.strip())

        def flush(self):
            original_stdout.flush()

    class ErrorLogger:
        def write(self, message):
            original_stderr.write(message)
            original_stderr.flush()
            if message.strip():
                logging.getLogger("stderr").error(message.strip())

        def flush(self):
            original_stderr.flush()

    sys.stdout = PrintLogger()
    sys.stderr = ErrorLogger()

    config = ConfigService()
    db = Database(db_path)
    app_state = AppStateStore()
    app_state.patch_runtime(
        hotkey=str(config.get("hotkey", "") or ""),
        mic_device=config.get("mic_device", None),
        mic_device_name=str(config.get("mic_device_name", "") or ""),
        mic_device_hostapi=config.get("mic_device_hostapi", None),
        overlay_enabled=bool(config.get("overlay_enabled", True)),
        overlay_mode=str(config.get("overlay_mode", "mini") or "mini").lower(),
        overlay_x=config.get("overlay_x", None),
        overlay_y=config.get("overlay_y", None),
        overlay_visible=False,
        listening_state="idle",
    )
    app_state.patch_service("bridge", state="starting", detail="desktop_app_boot", last_updated_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    session_manager = SessionManager(db, app_state=app_state)

    hermes = HermesClient(config)
    audio = AudioService()
    wakeword = WakePhraseManager(model_size=config.get("stt_model", "base"))
    tts = TTSService(
        mode=config.get("feedback_mode", "both"),
        voice_name=config.get("feedback_voice", ""),
        rate=config.get("tts_rate", 235),
    )
    shortcut_manager = ShortcutManager()

    autostart = AutostartService()
    if config.get("autostart", True):
        autostart.enable()
    else:
        autostart.disable()

    bridge = WebviewBridge(
        config,
        session_manager,
        hermes,
        audio,
        wakeword,
        tts,
        autostart,
        shortcut_manager=shortcut_manager,
        app_state=app_state,
    )

    def on_overlay_position_change(x: int, y: int) -> None:
        config.update({"overlay_x": x, "overlay_y": y})
        bridge.set_runtime_overlay_position(x, y)

    def on_overlay_visibility_change(visible: bool) -> None:
        bridge.set_runtime_overlay_visibility(visible)

    def on_overlay_dashboard_click() -> None:
        window.show()
        
    def on_overlay_mic_click() -> None:
        shortcut_manager._triggered.add("trigger")

    overlay = OverlayService(
        initial_mode=str(config.get("overlay_mode", "mini") or "mini").lower(),
        enabled=bool(config.get("overlay_enabled", True)),
        initial_x=config.get("overlay_x", None),
        initial_y=config.get("overlay_y", None),
        on_position_change=on_overlay_position_change,
        on_visibility_change=on_overlay_visibility_change,
        on_open_dashboard=on_overlay_dashboard_click,
        on_start_mic=on_overlay_mic_click,
    )
    overlay.start()
    bridge.set_overlay(overlay)

    voice_loop = VoiceLoop(config, audio, wakeword, bridge, shortcut_manager, tts, overlay)
    voice_loop.start()
    bridge.set_voice_loop(voice_loop)

    from src.services.agent.proactive_service import ProactiveService

    proactive = ProactiveService(bridge)
    proactive.start()

    url = resolve_ui_url()

    window = webview.create_window(
        "Hermes Voice Bridge",
        url=url,
        js_api=bridge,
        width=1320,
        height=900,
        min_size=(350, 150),
        background_color="#000000" if config.get("theme", "dark") == "dark" else "#FFFFFF",
    )

    bridge.set_window(window)

    def on_quit(icon=None, item=None):
        proactive.stop()
        voice_loop.stop()
        shortcut_manager.stop()
        tray.stop()
        try:
            window.destroy()
        except Exception:
            pass
        os._exit(0)

    def on_closing():
        window.hide()
        return False

    window.events.closing += on_closing

    def on_open_app(icon, item):
        window.show()

    def on_pause_toggle(paused: bool):
        voice_loop.is_paused = paused
        bridge.set_runtime_paused(paused)
        tray.set_paused(paused)
        if paused:
            shortcut_manager.stop()
        else:
            hotkey = config.get("hotkey", "")
            visual_hotkey = config.get("visual_hotkey", "")
            if hotkey or visual_hotkey:
                shortcut_manager.start(hotkey, visual_hotkey or None)

    def on_change_microphone(device_index: int | None):
        devices = audio.get_devices()
        selected = next((device for device in devices if device.get("index") == device_index), None)
        updates = {
            "mic_device": device_index,
            "mic_device_name": str(selected.get("name") or "") if selected else "",
            "mic_device_hostapi": selected.get("hostapi") if selected else None,
        }
        updated = bridge.update_config(updates)
        if updated:
            label = str(selected.get("name") or "Default microphone") if selected else "Default microphone"
            tray.notify("Microphone Updated", f"Active microphone: {label}")
        else:
            tray.notify("Microphone Error", "Could not update microphone selection")

    def on_restart(icon, item):
        import subprocess

        proactive.stop()
        voice_loop.stop()
        shortcut_manager.stop()
        tray.stop()
        try:
            window.destroy()
        except Exception:
            pass
        subprocess.Popen([sys.executable] + sys.argv)
        os._exit(0)

    bridge.set_callbacks(
        on_pause=on_pause_toggle,
        on_restart=lambda: on_restart(None, None),
        on_quit=lambda: on_quit(None, None),
    )

    def on_quick_command(command_id: str):
        try:
            bridge.run_quick_command(command_id)
            tray.notify("Command Executed", f"Ran quick command: {command_id}")
        except Exception as e:
            print(f"Quick command error: {e}")

    tray = TrayManager(
        app_name="Hermes Voice Bridge",
        on_open_app=on_open_app,
        on_pause_toggle=on_pause_toggle,
        on_restart=on_restart,
        on_quit=on_quit,
        on_quick_command=on_quick_command,
        on_open_settings=on_open_app,
        on_change_microphone=on_change_microphone,
    )
    tray.start()
    bridge.set_tray(tray)
    voice_loop.set_tray(tray)

    tray.set_shortcut_display(config.get("hotkey", "CTRL+SHIFT+H"))
    try:
        cmds = bridge.get_quick_commands()
        tray.update_quick_commands(cmds)
    except Exception:
        pass

    def poll_health():
        while True:
            try:
                is_connected = bridge.check_health()
            except Exception:
                is_connected = False
            tray.set_status(is_connected)
            time.sleep(10)

    threading.Thread(target=poll_health, daemon=True).start()

    webview.start(debug=False)


if __name__ == "__main__":
    main()
