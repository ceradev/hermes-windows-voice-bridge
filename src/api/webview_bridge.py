from collections import deque
from datetime import datetime, timezone
from importlib import import_module
from typing import Any

ActivityEntry = dict[str, str]

class WebviewBridge:
    def __init__(self, config, session_manager, hermes, audio, wakeword, tts, autostart=None):
        self._config = config
        self._session_manager = session_manager
        self._hermes = hermes
        self._audio = audio
        self._wakeword = wakeword
        self._tts = tts
        custom_command_module = import_module("src.services.custom_commands.custom_command_service")
        self._custom_commands = custom_command_module.CustomCommandService(config, tts)
        self._autostart = autostart
        self._window = None
        self._on_pause = None
        self._on_restart = None
        self._on_quit = None
        self._recent_activity: deque[ActivityEntry] = deque(maxlen=50)

    def set_window(self, window):
        self._window = window

    def set_callbacks(self, on_pause, on_restart, on_quit):
        self._on_pause = on_pause
        self._on_restart = on_restart
        self._on_quit = on_quit

    # --- Config ---
    def get_config(self) -> dict[str, Any]:
        return self._config.get_all()

    def update_config(self, updates: dict[str, Any]) -> bool:
        try:
            self._config.update(updates)
            
            # Apply immediate settings if needed
            if "tts_enabled" in updates or "feedback_mode" in updates or "feedback_voice" in updates:
                self._tts.update_settings(
                    self._config.get("feedback_mode", "both"), 
                    self._config.get("feedback_voice", "")
                )
                
            if "autostart" in updates and self._autostart:
                if updates["autostart"]:
                    self._autostart.enable()
                else:
                    self._autostart.disable()
                    
            return True
        except Exception as e:
            return False

    # --- Session ---
    def get_sessions(self) -> list[dict[str, Any]]:
        return self._session_manager.get_sessions()

    def create_session(self, name: str) -> str:
        try:
            res = self._hermes.create_session(name)
            remote_id = res.get("session", {}).get("id")
            return self._session_manager.create_session(name, remote_id)
        except Exception as e:
            print(f"Failed to create remote session: {e}")
            return self._session_manager.create_session(name) # fallback local

    def switch_session(self, session_id: str) -> bool:
        return self._session_manager.switch_session(session_id)

    def delete_session(self, session_id: str) -> None:
        sessions = self.get_sessions()
        session = next((s for s in sessions if s['id'] == session_id), None)
        if session and session.get('remote_session_id'):
            try:
                self._hermes.delete_session(session['remote_session_id'])
            except Exception as e:
                print(f"Failed to delete remote session: {e}")
        self._session_manager.delete_session(session_id)

    def rename_session(self, session_id: str, new_name: str) -> bool:
        sessions = self.get_sessions()
        session = next((s for s in sessions if s['id'] == session_id), None)
        if session and session.get('remote_session_id'):
            try:
                self._hermes.rename_session(session['remote_session_id'], new_name)
            except Exception as e:
                print(f"Failed to rename remote session: {e}")
        return self._session_manager.rename_session(session_id, new_name)

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        # For now, return local history. If we wanted, we could sync remote history here.
        return self._session_manager.get_messages(session_id)

    def get_recent_activity(self) -> list[ActivityEntry]:
        return list(self._recent_activity)

    def save_vps_token(self, token: str) -> bool:
        self._session_manager.save_vps_token("default_user", token)
        return True

    def get_vps_token(self) -> str:
        return self._session_manager.get_vps_token("default_user") or ""

    # --- Custom Commands ---
    def get_custom_commands(self) -> list[dict[str, Any]]:
        return self._custom_commands.get_all()

    def add_custom_command(self, cmd: dict[str, Any]) -> dict[str, Any]:
        return self._custom_commands.add(cmd)

    def update_custom_command(self, id: str, cmd: dict[str, Any]) -> bool:
        return self._custom_commands.update(id, cmd) is not None

    def delete_custom_command(self, id: str) -> bool:
        return self._custom_commands.delete(id)

    def test_custom_command(self, id: str) -> bool:
        return self._custom_commands.execute(id)

    # --- Audio & Device ---
    def get_audio_devices(self) -> list[dict[str, Any]]:
        return self._audio.get_devices()

    # --- Hermes ---
    def check_health(self) -> bool:
        return self._hermes.health()

    def send_message(self, text: str, image_base64: str | None = None, source: str = "voice") -> dict[str, Any]:
        active_session = self._session_manager.get_active_session()
        if not active_session:
            return {"success": False, "error": "No active session"}
            
        session_id = active_session['id']
        remote_id = active_session.get('remote_session_id')
        
        if not remote_id:
            # Try to upgrade to remote session if missing
            try:
                res = self._hermes.create_session(active_session['name'])
                remote_id = res.get("session", {}).get("id")
                # Update DB (hacky but works for now)
                conn = self._session_manager.db.get_connection()
                conn.execute('UPDATE sessions SET remote_session_id = ? WHERE id = ?', (remote_id, session_id))
                conn.commit()
                conn.close()
            except Exception as e:
                return {"success": False, "error": f"Session not synced with VPS. Try creating a new one. {e}"}

        should_track_user_text = source != "system" and not text.startswith("[SYSTEM:")

        # No guardar en historial si es evento de sistema o arranca con la etiqueta oculta
        if should_track_user_text:
            self._session_manager.add_message(session_id, "user", text, source, "success")
            self._record_activity("voice", text, "success")

        outbound_text = self._with_active_window_context(text)
        
        try:
            data = self._hermes.send_message(remote_id, outbound_text, source, image_base64=image_base64)
            response_text = data.get("response", "")
            speak = data.get("speak", False)
            latency = data.get("latencyMs", 0)
            
            msg_id = self._session_manager.add_message(session_id, "hermes", response_text, source, "success", latency)
            self._record_activity("command", response_text, "success")
            
            if speak and self._config.get("tts_enabled", True):
                self._tts.say(response_text)
                
            if self._window:
                self._window.evaluate_js("window.dispatchEvent(new CustomEvent('hermes_new_message'))")
                
            return {
                "success": True, 
                "response": response_text, 
                "message_id": msg_id, 
                "latencyMs": latency,
                "remoteSessionId": data.get("sessionId")
            }
        except Exception as e:
            print(f"[BRIDGE ERROR] Excepción al enviar mensaje: {e}")
            msg_id = self._session_manager.add_message(session_id, "hermes", str(e), "manual", "error")
            self._record_activity("command", str(e), "error")
            if self._window:
                self._window.evaluate_js("window.dispatchEvent(new CustomEvent('hermes_new_message'))")
            return {"success": False, "error": str(e), "message_id": msg_id}

    def speak_text(self, text: str) -> bool:
        if self._tts:
            self._tts.say(text)
            return True
        return False

    def log_local_action(self, request_text: str, response_text: str) -> bool:
        active_session = self._session_manager.get_active_session()
        if not active_session:
            return False
            
        session_id = active_session['id']
        self._session_manager.add_message(session_id, "user", request_text, "voice", "success")
        self._session_manager.add_message(session_id, "hermes", f"⚡ {response_text}", "local", "success", 0)
        self._record_activity("voice", request_text, "success")
        self._record_activity("command", response_text, "success")
        
        if self._window:
            self._window.evaluate_js("window.dispatchEvent(new CustomEvent('hermes_new_message'))")
        return True

    def _record_activity(self, activity_type: str, text: str, status: str) -> None:
        if not text:
            return

        self._recent_activity.appendleft({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": activity_type,
            "text": text,
            "status": status,
        })

    def _with_active_window_context(self, text: str) -> str:
        from src.platform.windows.active_window import get_active_window_title

        window_title = get_active_window_title()
        if not window_title or self._is_app_window(window_title):
            return text
        return f"[Context: Usuario está en '{window_title}'] {text}"

    def _is_app_window(self, window_title: str) -> bool:
        title = window_title.lower()
        app_titles = [
            "hermes voice bridge",
            "hermes windows voice bridge",
        ]
        pywebview_title = str(getattr(self._window, "title", "") or "").lower()
        return any(app_title in title for app_title in app_titles) or bool(pywebview_title and pywebview_title in title)

    # --- Platform ---
    def toggle_mini_mode(self, enable: bool) -> bool:
        if not self._window:
            return False
        
        try:
            if enable:
                # Remove fullscreen if active before shrinking
                if getattr(self._window, 'fullscreen', False):
                    self._window.toggle_fullscreen()
                    
                self._window.resize(380, 200)
                
                # Mover a la esquina inferior derecha
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    screen_width = user32.GetSystemMetrics(0)
                    screen_height = user32.GetSystemMetrics(1)
                    # X: ancho pantalla - 380 (ventana) - 20 (margen) = screen_width - 400
                    # Y: alto pantalla - 200 (ventana) - 60 (barra de tareas)
                    self._window.move(screen_width - 400, screen_height - 260)
                except Exception as e:
                    print(f"No se pudo mover la ventana: {e}")
                
                try:
                    self._window.resizable = False
                except Exception: pass
                self._window.on_top = True
            else:
                try:
                    self._window.resizable = True
                except Exception: pass
                
                self._window.resize(1000, 700)
                self._window.on_top = False
                
                # Make the dashboard fullscreen
                if not getattr(self._window, 'fullscreen', False):
                    self._window.toggle_fullscreen()
            return True
        except Exception as e:
            print(f"Error toggling mini mode: {e}")
            return False

    def minimize_to_tray(self):
        if self._window:
            self._window.hide()

    def maximize_window(self):
        if self._window:
            self._window.toggle_fullscreen()

    def close_app(self):
        if self._on_quit:
            self._on_quit()
        elif self._window:
            self._window.destroy()

    def exit_app(self):
        self.close_app()
        
    def pause_app(self, paused: bool):
        if self._on_pause:
            self._on_pause(paused)
            return True
        return False

    def restart_app(self):
        if self._on_restart:
            self._on_restart()
            return True
        return False
