import threading
import time
import numpy as np

class VoiceLoop:
    def __init__(self, config, audio, wakeword, bridge, shortcut_manager, tts, overlay):
        self.config = config
        self.audio = audio
        self.wakeword = wakeword
        self.bridge = bridge
        self.shortcut_manager = shortcut_manager
        self.tts = tts
        self.overlay = overlay
        self.tray = None
        self._running = False
        self.is_paused = False
        self._thread = None

    def set_tray(self, tray):
        self.tray = tray
        
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            
    def _loop(self):
        sample_rate = 16000
        block_sec = self.config.get("block_seconds", 0.25)
        blocksize = max(1, int(sample_rate * block_sec))
        
        wake_rms = self.config.get("wake_energy", 0.008)
        silence_rms = self.config.get("silence_rms", 0.008)
        wake_window_sec = self.config.get("wake_window_seconds", 2.0)
        wake_frames_max = max(1, int(wake_window_sec / block_sec))
        
        wake_buffer = []
        last_device_signature = None
        
        # Start shortcut listener if configured
        hotkey = self.config.get("hotkey", "ctrl+shift+space")
        visual_hotkey = self.config.get("visual_hotkey", "ctrl+shift+v")
        if hotkey or visual_hotkey:
            self.shortcut_manager.start(hotkey, visual_hotkey)
            
        auto_listen = False
            
        while self._running:
            try:
                preferred_index = self.config.get("mic_device", None)
                preferred_name = self.config.get("mic_device_name", None)
                preferred_hostapi = self.config.get("mic_device_hostapi", None)
                with self.audio.create_stream(
                    preferred_index,
                    block_sec,
                    preferred_name=preferred_name,
                    preferred_hostapi=preferred_hostapi,
                ) as stream:
                    selected_device = getattr(self.audio, "last_selected_device", None)
                    selection_reason = getattr(self.audio, "last_selection_reason", "")
                    device_signature = (
                        selected_device.get("index") if selected_device else None,
                        selection_reason,
                    )
                    if device_signature != last_device_signature:
                        last_device_signature = device_signature
                        print(
                            f"[MIC] Using {self.audio.describe_device(selected_device)}"
                            + (f" via {selection_reason}" if selection_reason else "")
                        )
                    while self._running:
                        # Pause condition
                        if self.is_paused:
                            time.sleep(0.5)
                            wake_buffer.clear()
                            continue

                        # Wait if TTS is currently speaking
                        if self.tts.is_speaking:
                            time.sleep(0.1)
                            wake_buffer.clear()
                            continue
                        
                        # Auto-listen continuation
                        if auto_listen:
                            time.sleep(0.3) # Give user a tiny breath window after TTS stops
                            auto_listen = self._handle_command(stream, blocksize, silence_rms, source="auto")
                            wake_buffer.clear()
                            continue

                        # 1. Check hotkey first
                        if self.shortcut_manager.is_triggered():
                            self.shortcut_manager.clear_trigger()
                            auto_listen = self._handle_command(stream, blocksize, silence_rms, source="hotkey")
                            wake_buffer.clear()
                            continue
                        
                        # 1.b Check visual hotkey
                        if getattr(self.shortcut_manager, 'is_visual_triggered', lambda: False)():
                            self.shortcut_manager.clear_visual_trigger()
                            auto_listen = self._handle_command(stream, blocksize, silence_rms, source="vision")
                            wake_buffer.clear()
                            continue
                        
                        # 2. Process audio for wake word
                        try:
                            block, _ = stream.read(blocksize)
                            audio_data = block[:, 0].astype(np.float32).copy()
                            level = self.audio.get_rms(audio_data)
                        
                            if getattr(self.bridge, 'window', None):
                                try:
                                    self.bridge.window.evaluate_js(f"window.dispatchEvent(new CustomEvent('hermes_audio_level', {{detail: {level}}}))")
                                except Exception: pass
                        
                            if level > wake_rms:
                                wake_buffer.append(audio_data)
                                if len(wake_buffer) > wake_frames_max:
                                    wake_buffer.pop(0)
                                
                                combined = np.concatenate(wake_buffer)
                                text = self.wakeword.transcribe(combined, language=self.config.get("stt_language", "es"), vad_filter=False)
                            
                                phrases = self.config.get("wake_phrases", [])
                                if text and self.wakeword.contains_wake_phrase(text, phrases):
                                    print(f"Wake phrase detected! Transcription: {text}")
                                    auto_listen = self._handle_command(stream, blocksize, silence_rms, source="voice")
                                    wake_buffer.clear()
                            else:
                                wake_buffer.clear()
                        except Exception as e:
                            print(f"Audio read error: {e}")
                            break
                        
            except Exception as e:
                print(f"Voice loop fatal error: {e}")
                time.sleep(1.0)
            
    def _handle_command(self, stream, blocksize, silence_rms, source="voice"):
        image_base64 = None
        if source == "vision":
            print("[VISION] 📸 Tomando captura de pantalla...")
            try:
                from src.platform.windows.desktop_vision import capture_screen_base64
                image_base64 = capture_screen_base64()
                if getattr(self.bridge, 'window', None):
                    self.bridge.window.evaluate_js("document.body.style.transition = 'none'; document.body.style.backgroundColor = 'white'; setTimeout(() => { document.body.style.transition = 'background-color 0.5s ease'; document.body.style.backgroundColor = ''; }, 50);")
            except Exception as e:
                print(f"[VISION] Error: {e}")
                
        print(f"\n[MIC] 🟢 Empezando a escuchar (Origen: {source})...")
        self.overlay.show("listening")
        if self.tray:
            self.tray.set_mic_active(True)
        
        # Play elegant earcon instead of harsh TTS beep
        self.audio.play_earcon("wake")
        
        def emit_level(level):
            if getattr(self.bridge, 'window', None):
                try:
                    self.bridge.window.evaluate_js(f"window.dispatchEvent(new CustomEvent('hermes_audio_level', {{detail: {level}}}))")
                except Exception: pass

        command_audio = self.audio.record_command(
            stream, 
            blocksize, 
            silence_rms, 
            self.config.get("silence_timeout_seconds", 3.0), 
            self.config.get("max_command_seconds", 15.0),
            self.config.get("initial_timeout_seconds", 3.5),
            level_callback=emit_level
        )
        
        print(f"[MIC] 🔴 Fin de la escucha (Grabados {len(command_audio)} frames).")
        
        if command_audio.size > 0:
            print("[STT] ⏳ Transcribiendo audio con Inteligencia Artificial...")
            self.overlay.show("processing")
            # Apagamos el filtro VAD porque a veces recorta las voces bajas
            text = self.wakeword.transcribe(command_audio, language=self.config.get("stt_language", "es"), vad_filter=False)
            
            if text:
                print(f"[STT] ✅ Texto reconocido: '{text}'")
                self.overlay.hide()
                if self.tray:
                    self.tray.set_mic_active(False)
                
                # Check for local commands first
                from src.platform.windows.local_commands import process_local_command
                if process_local_command(text):
                    print(f"[LOCAL] 🖥️ Comando local ejecutado.")
                    self.audio.play_earcon("done")
                    self.bridge.log_local_action(text, "Acción de sistema ejecutada localmente.")
                    if self.tray:
                        self.tray.set_mic_active(False)
                    return True
                
                # Send message via bridge to ensure UI reacts and DB updates
                res = self.bridge.send_message(text, image_base64=image_base64)

                if res.get("success", False):
                    self.audio.play_earcon("done")
                else:
                    self.audio.play_earcon("error")

                print(f"[API] 📡 Respuesta de Hermes: {res.get('success', False)}")
                if self.tray:
                    self.tray.set_mic_active(False)
                return res.get("success", False)
            else:
                print("[STT] ❌ El audio contenía ruido pero no se reconoció ningún texto claro.")
                self.overlay.hide()
                if self.tray:
                    self.tray.set_mic_active(False)
                return False
        else:
            print("[MIC] 💤 Silencio detectado. Cancelando escucha y volviendo a dormir.")
            self.overlay.hide()
            if self.tray:
                self.tray.set_mic_active(False)
            return False
