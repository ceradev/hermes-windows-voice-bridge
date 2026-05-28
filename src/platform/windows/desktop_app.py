import os
import sys
import webview
from pathlib import Path
import threading

# Add src to python path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from src.core.config.config_service import ConfigService
from src.core.session.session_manager import SessionManager
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

def main():
    # Paths
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")

    app_dir = Path(appdata) / "HermesVoiceBridge"
    app_dir.mkdir(parents=True, exist_ok=True)

    db_path = app_dir / "database.sqlite"
    log_path = app_dir / "app.log"
    dist_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "ui" / "app" / "dist"
    
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Redirect prints to logger and mirror to original console
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
    
    # Init Core & Storage
    config = ConfigService()
    db = Database(db_path)
    session_manager = SessionManager(db)
    
    # Init Services
    hermes = HermesClient(config)
    audio = AudioService()
    wakeword = WakePhraseManager(
        model_size=config.get("stt_model", "base")
    )
    tts = TTSService(
        mode=config.get("feedback_mode", "both"),
        voice_name=config.get("feedback_voice", ""),
        rate=config.get("tts_rate", 235)
    )
    shortcut_manager = ShortcutManager()
    
    # Init Autostart
    autostart = AutostartService()
    if config.get("autostart", True):
        autostart.enable()
    else:
        autostart.disable()
        
    # Init API Bridge
    bridge = WebviewBridge(config, session_manager, hermes, audio, wakeword, tts, autostart, shortcut_manager=shortcut_manager)
    
    # Init Overlay
    overlay = OverlayService()
    overlay.start()
    
    # Init Voice Loop
    voice_loop = VoiceLoop(config, audio, wakeword, bridge, shortcut_manager, tts, overlay)
    voice_loop.start()
    
    # Init Proactive Loop
    from src.services.agent.proactive_service import ProactiveService
    proactive = ProactiveService(bridge)
    proactive.start()
    
    # Fallback to dev server if dist not built yet
    url = str(dist_path / "index.html") if dist_path.exists() else "http://localhost:5173"
    
    # Create Window
    window = webview.create_window(
        'Hermes Voice Bridge', 
        url=url, 
        js_api=bridge,
        width=1320,
        height=900,
        min_size=(350, 150),
        background_color='#000000' if config.get("theme", "dark") == "dark" else '#FFFFFF'
    )
    
    bridge.set_window(window)
    
    def on_quit(icon=None, item=None):
        proactive.stop()
        voice_loop.stop()
        shortcut_manager.stop()
        tray.stop()
        try:
            window.destroy()
        except: pass
        os._exit(0)

    def on_closing():
        window.hide()
        return False
        
    window.events.closing += on_closing
    
    def on_open_app(icon, item):
        window.show()
        
    def on_pause_toggle(paused: bool):
        voice_loop.is_paused = paused
        if paused:
            shortcut_manager.stop()
        else:
            hotkey = config.get("hotkey", "")
            if hotkey:
                shortcut_manager.start(hotkey)

    def on_restart(icon, item):
        import subprocess
        proactive.stop()
        voice_loop.stop()
        shortcut_manager.stop()
        tray.stop()
        try:
            window.destroy()
        except: pass
        subprocess.Popen([sys.executable] + sys.argv)
        os._exit(0)
        
    bridge.set_callbacks(
        on_pause=on_pause_toggle,
        on_restart=lambda: on_restart(None, None),
        on_quit=lambda: on_quit(None, None)
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
        on_open_settings=on_open_app
    )
    tray.start()
    bridge.set_tray(tray)
    voice_loop.set_tray(tray)

    # Set initial tray info
    tray.set_shortcut_display(config.get("hotkey", "CTRL+SHIFT+H"))
    try:
        cmds = bridge.get_quick_commands()
        tray.update_quick_commands(cmds)
    except Exception:
        pass

    # Background connection polling loop
    def poll_health():
        import time
        while True:
            try:
                is_connected = hermes.health()
            except Exception:
                is_connected = False
            tray.set_status(is_connected)
            time.sleep(10)
            
    threading.Thread(target=poll_health, daemon=True).start()
    
    # Start app
    webview.start(debug=False)

if __name__ == '__main__':
    main()
