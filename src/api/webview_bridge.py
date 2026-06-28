from collections import deque
from collections import deque
from datetime import datetime, timezone
from importlib import import_module
from typing import Any
from src.core.state import AppStateStore

ActivityEntry = dict[str, str]

class WebviewBridge:
    def __init__(self, config, session_manager, hermes, audio, wakeword, tts, autostart=None, shortcut_manager=None, tray=None, app_state: AppStateStore | None = None):
        self._config = config
        self._session_manager = session_manager
        self._hermes = hermes
        self._audio = audio
        self._wakeword = wakeword
        self._tts = tts
        custom_command_module = import_module("src.services.custom_commands.custom_command_service")
        self._custom_commands = custom_command_module.CustomCommandService(config, tts)
        self._autostart = autostart
        self._shortcut_manager = shortcut_manager
        self._tray = tray
        self._voice_loop = None
        self._overlay = None
        self._window = None
        self._on_pause = None
        self._on_restart = None
        self._on_quit = None
        self._recent_activity: deque[ActivityEntry] = deque(maxlen=50)
        self._app_state = app_state or AppStateStore()
        self._sync_runtime_from_config()

    def set_window(self, window):
        self._window = window

    def set_overlay(self, overlay):
        self._overlay = overlay
        config = self._config
        if hasattr(overlay, "set_mode"):
            overlay.set_mode(str(config.get("overlay_mode", "mini") or "mini").lower())
        if hasattr(overlay, "set_enabled"):
            overlay.set_enabled(bool(config.get("overlay_enabled", True)))
        if hasattr(overlay, "set_position"):
            overlay.set_position(config.get("overlay_x", None), config.get("overlay_y", None))
        is_visible = False
        if hasattr(overlay, "is_visible"):
            try:
                is_visible = bool(overlay.is_visible())
            except Exception:
                is_visible = False
        self._app_state.patch_runtime(overlay_visible=is_visible)
        self._sync_runtime_from_config()

    def set_tray(self, tray):
        self._tray = tray
        self._sync_tray_state()

    def set_voice_loop(self, voice_loop):
        self._voice_loop = voice_loop

    def get_runtime_state(self) -> dict[str, Any]:
        return self._app_state.snapshot()

    def navigate_to(self, path: str) -> None:
        """Navigate the webview to a hash route."""
        if not self._window:
            return
        try:
            self._window.evaluate_js(f"window.location.hash = '#{path}';")
        except Exception:
            pass

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

            if any(key in updates for key in ("mic_device", "mic_device_name", "mic_device_hostapi")):
                self._apply_microphone_config(updates)

            self._sync_runtime_from_config()

            if self._window:
                self._safe_evaluate_js(
                    "window.dispatchEvent(new CustomEvent('hermes_config_updated'))"
                )

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

            if "overlay_mode" in updates:
                overlay_mode = str(updates["overlay_mode"] or "mini").lower()
                if self._overlay and hasattr(self._overlay, "set_mode"):
                    self._overlay.set_mode(overlay_mode)
                self.set_runtime_overlay_mode(overlay_mode)

            if "overlay_enabled" in updates and self._overlay and hasattr(self._overlay, "set_enabled"):
                self._overlay.set_enabled(bool(updates["overlay_enabled"]))
            if "overlay_enabled" in updates:
                self.set_runtime_overlay_enabled(bool(updates["overlay_enabled"]))

            if any(key in updates for key in ("overlay_x", "overlay_y")) and self._overlay and hasattr(self._overlay, "set_position"):
                self._overlay.set_position(
                    self._config.get("overlay_x", None),
                    self._config.get("overlay_y", None),
                )

            if "hotkey" in updates:
                hotkey = str(self._config.get("hotkey", "") or "")
                self._app_state.patch_shortcut(accelerator=hotkey)
                if self._tray:
                    self._tray.set_shortcut_display(hotkey)
                self._restart_shortcuts_from_config()

            if "visual_hotkey" in updates and "hotkey" not in updates:
                self._restart_shortcuts_from_config()

            self._sync_tray_state()

            return True
        except Exception as e:
            return False

    def _apply_microphone_config(self, updates: dict[str, Any], restart_stream: bool = True) -> None:
        try:
            devices = self._audio.get_devices()
        except Exception:
            devices = []

        selected_index = self._config.get("mic_device", None)
        selected = next((d for d in devices if d.get("index") == selected_index), None)

        if selected and (
            updates.get("mic_device_name") != selected.get("name")
            or updates.get("mic_device_hostapi") != selected.get("hostapi")
        ):
            self._config.update({
                "mic_device_name": selected.get("name", ""),
                "mic_device_hostapi": selected.get("hostapi"),
            })

        self._sync_runtime_from_config()

        if self._tray:
            try:
                self._tray.set_audio_devices(devices)
            except Exception:
                pass
            try:
                if selected:
                    self._tray.set_current_mic(selected_index, selected.get("name", "Unknown"))
                else:
                    self._tray.set_current_mic(selected_index, "Default")
                if hasattr(self._tray, "_refresh"):
                    self._tray._refresh()
            except Exception:
                pass

        if restart_stream and self._voice_loop:
            try:
                self._voice_loop.request_stream_restart()
            except Exception:
                pass

    def _sync_tray_microphone_state(self) -> None:
        tray = self._tray
        if tray is None:
            return

        try:
            devices = self._audio.get_devices()
        except Exception:
            devices = []

        selected_index = self._config.get("mic_device", None)
        selected = next((d for d in devices if d.get("index") == selected_index), None)

        try:
            tray.set_audio_devices(devices)
            if selected:
                tray.set_current_mic(selected_index, str(selected.get("name") or "Unknown"))
            else:
                tray.set_current_mic(selected_index, "Default")
        except Exception:
            pass

    def _restart_shortcuts_from_config(self) -> None:
        if not self._shortcut_manager:
            return

        try:
            self._shortcut_manager.stop()
        except Exception:
            pass

        if getattr(self._voice_loop, "is_paused", False):
            return

        hotkey = str(self._config.get("hotkey", "") or "").strip()
        visual_hotkey = str(self._config.get("visual_hotkey", "") or "").strip()
        if hotkey or visual_hotkey:
            self._shortcut_manager.start(hotkey, visual_hotkey or None)

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
        normalized_name = self._session_manager._normalize_name(new_name)
        if not normalized_name:
            return False

        sessions = self.get_sessions()
        session = next((s for s in sessions if s['id'] == session_id), None)
        if session and session.get('remote_session_id'):
            try:
                self._hermes.rename_session(session['remote_session_id'], normalized_name)
            except Exception as e:
                print(f"Failed to rename remote session: {e}")
        return self._session_manager.rename_session(session_id, normalized_name)

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
        is_healthy = self._hermes.health()
        self._app_state.patch_runtime(connection_status="connected" if is_healthy else "offline")
        self._app_state.patch_service(
            "hermes",
            state="running" if is_healthy else "error",
            detail="connected" if is_healthy else "offline",
            last_updated_at=datetime.now(timezone.utc).isoformat(),
        )
        if self._tray:
            self._tray.set_status(is_healthy)
        return is_healthy

    def send_message(self, text: str, image_base64: str | None = None, source: str = "voice") -> dict[str, Any]:
        active_session = self._session_manager.get_active_session()
        if not active_session:
            return {"success": False, "error": "No active session"}

        session_id = active_session['id']
        remote_id = active_session.get('remote_session_id')
        should_track_user_text = source != "system" and not text.startswith("[SYSTEM:")

        generated_title = None
        if should_track_user_text:
            generated_title = self._session_manager.auto_title_session(session_id, text)
            if generated_title:
                active_session = self._session_manager.get_session(session_id) or active_session
                remote_id = active_session.get('remote_session_id')
                if remote_id:
                    try:
                        self._hermes.rename_session(remote_id, generated_title)
                    except Exception as e:
                        print(f"Failed to rename remote session: {e}")

        if not remote_id:
            # Try to upgrade to remote session if missing
            try:
                res = self._hermes.create_session(active_session['name'])
                remote_id = res.get("session", {}).get("id")
                self._session_manager.set_remote_session_id(session_id, remote_id)
            except Exception as e:
                return {"success": False, "error": f"Session not synced with VPS. Try creating a new one. {e}"}

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

            self._app_state.patch_runtime(connection_status="connected", listening_state="idle")
            self._app_state.patch_service(
                "hermes",
                state="running",
                detail="message_ok",
                latency_ms=float(latency) if latency is not None else None,
                last_updated_at=datetime.now(timezone.utc).isoformat(),
            )

            msg_id = self._session_manager.add_message(session_id, "hermes", response_text, source, "success", latency)
            self._record_activity("command", response_text, "success")

            if speak and self._config.get("tts_enabled", True):
                self._tts.say(response_text)

            if self._window:
                self._safe_evaluate_js("window.dispatchEvent(new CustomEvent('hermes_new_message'))")

            return {
                "success": True,
                "response": response_text,
                "message_id": msg_id,
                "latencyMs": latency,
                "remoteSessionId": data.get("sessionId")
            }
        except Exception as e:
            print(f"[BRIDGE ERROR] Excepción al enviar mensaje: {e}")
            self._app_state.update(last_error=str(e))
            self._app_state.patch_runtime(connection_status="offline", listening_state="idle")
            self._app_state.patch_service(
                "hermes",
                state="error",
                detail=str(e),
                last_updated_at=datetime.now(timezone.utc).isoformat(),
            )
            msg_id = self._session_manager.add_message(session_id, "hermes", str(e), "manual", "error")
            self._record_activity("command", str(e), "error")
            if self._window:
                self._safe_evaluate_js("window.dispatchEvent(new CustomEvent('hermes_new_message'))")
            return {"success": False, "error": str(e), "message_id": msg_id}

    def set_runtime_listening_state(self, state: str, detail: str = "") -> None:
        normalized = (state or "idle").strip().lower()
        overlay_enabled = bool(self._config.get("overlay_enabled", True))
        overlay_visible = overlay_enabled and normalized not in {"idle", "hidden"}
        self._app_state.update(overlay_state=normalized)
        self._app_state.patch_runtime(
            listening_state=normalized,
            overlay_visible=overlay_visible,
            overlay_detail=str(detail or ""),
        )

    def set_runtime_overlay_text(self, request_text: str = "", response_text: str = "") -> None:
        request_preview = str(request_text or "")
        response_preview = str(response_text or "")
        self._app_state.update(
            last_transcript=request_preview,
            last_response_preview=response_preview,
        )
        self._app_state.patch_runtime(
            overlay_request=request_preview,
            overlay_response=response_preview,
            overlay_detail=response_preview or request_preview,
        )

    def set_runtime_overlay_mode(self, mode: str) -> None:
        normalized = (mode or "mini").strip().lower()
        self._app_state.patch_runtime(overlay_mode=normalized)

    def set_runtime_overlay_position(self, x: int | None, y: int | None) -> None:
        self._app_state.patch_runtime(overlay_x=x, overlay_y=y)

    def set_runtime_overlay_enabled(self, enabled: bool) -> None:
        runtime = self._app_state.state.runtime
        should_be_visible = bool(enabled) and runtime.listening_state not in {"idle", "hidden"}
        self._app_state.patch_runtime(
            overlay_enabled=bool(enabled),
            overlay_visible=should_be_visible,
        )

    def set_runtime_overlay_visibility(self, visible: bool) -> None:
        self._app_state.patch_runtime(overlay_visible=bool(visible))

    def set_runtime_paused(self, paused: bool) -> None:
        self._app_state.patch_service(
            "bridge",
            state="paused" if paused else "running",
            detail="paused" if paused else "active",
            last_updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _sync_runtime_from_config(self) -> None:
        hotkey = str(self._config.get("hotkey", "") or "")
        self._app_state.patch_runtime(
            hotkey=hotkey,
            mic_device=self._config.get("mic_device", None),
            mic_device_name=str(self._config.get("mic_device_name", "") or ""),
            mic_device_hostapi=self._config.get("mic_device_hostapi", None),
            overlay_enabled=bool(self._config.get("overlay_enabled", True)),
            overlay_mode=str(self._config.get("overlay_mode", "mini") or "mini").lower(),
            overlay_x=self._config.get("overlay_x", None),
            overlay_y=self._config.get("overlay_y", None),
        )
        self._app_state.patch_shortcut(accelerator=hotkey)

    def _sync_tray_state(self) -> None:
        if not self._tray:
            return

        try:
            self._tray.set_shortcut_display(str(self._config.get("hotkey", "") or ""))
        except Exception:
            pass

        try:
            self._tray.update_quick_commands(self.get_quick_commands())
        except Exception:
            pass

        try:
            activity_labels = [entry.get("text", "") for entry in self._recent_activity if entry.get("text")]
            self._tray.set_recent_activity(activity_labels[:5])
        except Exception:
            pass

        self._sync_tray_microphone_state()

    def speak_text(self, text: str) -> bool:
        if self._tts:
            self._tts.say(text)
            return True
        return False

    # --- Shortcuts ---
    def capture_hotkey(self, timeout: float = 5.0) -> str:
        if self._shortcut_manager:
            result = self._shortcut_manager.capture_next_hotkey(timeout)
            return result or ""
        return ""

    def check_hotkey_conflict(self, hotkey: str) -> bool:
        if self._shortcut_manager:
            return self._shortcut_manager.check_conflict(hotkey)
        return False

    def get_quick_commands(self) -> list[dict[str, Any]]:
        cmds = self._custom_commands.get_all()
        return [{"id": c["id"], "label": c.get("name", c["id"])} for c in cmds]

    def run_quick_command(self, command_id: str) -> bool:
        return self._custom_commands.execute(command_id)

    def notify_tray(self, title: str, message: str) -> bool:
        if self._tray:
            self._tray.notify(title, message)
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
            self._safe_evaluate_js("window.dispatchEvent(new CustomEvent('hermes_new_message'))")
        return True

    def _safe_evaluate_js(self, script: str) -> None:
        """Evaluate JS in the webview only if it matches an allow-listed pattern.

        Blocks common injection vectors (eval, Function constructors, script tags,
        unescaped backticks/quotes) as a defense-in-depth measure.
        """
        if not self._window:
            return

        dangerous = ("eval(", "Function(", "<script", "javascript:", "\\x", "\\u")
        if any(token in script.lower() for token in dangerous):
            print(f"[BRIDGE SECURITY] Blocked dangerous JS: {script[:80]}")
            return

        # Only allow calls that look like window.dispatchEvent(new CustomEvent(...))
        allowed_prefixes = ("window.dispatchEvent(new CustomEvent(",)
        if not any(script.strip().startswith(p) for p in allowed_prefixes):
            print(f"[BRIDGE SECURITY] Blocked unallowed JS: {script[:80]}")
            return

        self._window.evaluate_js(script)

    def _record_activity(self, activity_type: str, text: str, status: str) -> None:
        if not text:
            return

        self._recent_activity.appendleft({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": activity_type,
            "text": text,
            "status": status,
        })
        if self._tray:
            try:
                self._tray.set_recent_activity([entry["text"] for entry in self._recent_activity if entry.get("text")][:5])
            except Exception:
                pass

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
