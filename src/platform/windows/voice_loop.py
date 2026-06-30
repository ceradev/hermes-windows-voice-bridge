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
        self._cancel_flag = False
        self._restart_stream = False
        self._last_wake_attempt = 0.0
        self._activation_lock = threading.Lock()
        self._listening_active = False
        self._pending_listen_source: str | None = None

        if hasattr(self.bridge, "set_voice_loop"):
            self.bridge.set_voice_loop(self)

    def set_tray(self, tray):
        self.tray = tray

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0):
        self._running = False
        self._cancel_flag = True
        self._restart_stream = True
        if self._thread:
            self._thread.join(timeout=timeout)

    def request_stream_restart(self):
        self._restart_stream = True

    def request_listening(self, source: str = "manual", *, cancel_if_active: bool = True) -> str:
        """Queue or cancel a listening session from any UI thread.

        Returns ``"queued"`` when the voice loop accepted a new activation,
        ``"cancelled"`` when an active recording was asked to stop, and
        ``"ignored"`` when another activation is already pending.
        """
        normalized_source = str(source or "manual").strip().lower() or "manual"
        with self._activation_lock:
            if self._listening_active:
                if cancel_if_active:
                    self._cancel_flag = True
                    return "cancelled"
                return "ignored"
            if self._pending_listen_source is not None:
                return "ignored"
            self._pending_listen_source = normalized_source
            return "queued"

    def _consume_listen_request(self) -> str | None:
        with self._activation_lock:
            source = self._pending_listen_source
            self._pending_listen_source = None
            return source

    def _begin_listening(self, source: str) -> bool:
        with self._activation_lock:
            if self._listening_active:
                return False
            self._listening_active = True
            self._pending_listen_source = None
            self._cancel_flag = False
            return True

    def _finish_listening(self) -> None:
        self._clear_activation_triggers()
        with self._activation_lock:
            self._listening_active = False
            self._pending_listen_source = None
            self._cancel_flag = False

    def _clear_activation_triggers(self) -> None:
        try:
            self.shortcut_manager.clear_trigger()
        except Exception:
            pass
        try:
            self.shortcut_manager.clear_visual_trigger()
        except Exception:
            pass

    def _loop(self):
        sample_rate = 16000
        block_sec = self.config.get("block_seconds", 0.25)
        blocksize = max(1, int(sample_rate * block_sec))

        wake_rms = self.config.get("wake_energy", 0.007)
        silence_rms = self.config.get("silence_rms", 0.015)
        wake_window_sec = float(self.config.get("wake_window_seconds", 1.25))
        wake_hangover_sec = float(self.config.get("wake_hangover_seconds", 0.35))
        wake_min_speech_sec = float(self.config.get("wake_min_speech_seconds", 0.45))
        wake_speech_ratio_min = float(self.config.get("wake_speech_ratio_min", 0.55))
        wake_frames_max = max(1, int(wake_window_sec / block_sec))
        hangover_frames = max(1, int(wake_hangover_sec / block_sec))
        min_speech_frames = max(1, int(wake_min_speech_sec / block_sec))

        wake_buffer: list[np.ndarray] = []
        speech_frames = 0
        silence_after_speech = 0
        stt_beam_wake = 1
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
                        if self._restart_stream:
                            self._restart_stream = False
                            wake_buffer.clear()
                            speech_frames = 0
                            silence_after_speech = 0
                            break

                        # Pause condition
                        if self.is_paused:
                            time.sleep(0.5)
                            wake_buffer.clear()
                            speech_frames = 0
                            silence_after_speech = 0
                            continue

                        # Wait if TTS is currently speaking
                        if self.tts.is_speaking:
                            time.sleep(0.1)
                            wake_buffer.clear()
                            speech_frames = 0
                            silence_after_speech = 0
                            continue

                        # Auto-listen continuation
                        if auto_listen:
                            time.sleep(0.3) # Give user a tiny breath window after TTS stops
                            auto_listen = self._handle_command(stream, blocksize, silence_rms, source="auto")
                            wake_buffer.clear()
                            speech_frames = 0
                            silence_after_speech = 0
                            continue

                        requested_source = self._consume_listen_request()
                        if requested_source:
                            auto_listen = self._handle_command(stream, blocksize, silence_rms, source=requested_source)
                            wake_buffer.clear()
                            speech_frames = 0
                            silence_after_speech = 0
                            continue

                        # 1. Check hotkey first
                        if self.shortcut_manager.is_triggered():
                            self.shortcut_manager.clear_trigger()
                            auto_listen = self._handle_command(stream, blocksize, silence_rms, source="hotkey")
                            wake_buffer.clear()
                            speech_frames = 0
                            silence_after_speech = 0
                            continue

                        # 1.b Check visual hotkey
                        if getattr(self.shortcut_manager, 'is_visual_triggered', lambda: False)():
                            self.shortcut_manager.clear_visual_trigger()
                            auto_listen = self._handle_command(stream, blocksize, silence_rms, source="vision")
                            wake_buffer.clear()
                            speech_frames = 0
                            silence_after_speech = 0
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
                                speech_frames += 1
                                silence_after_speech = 0
                                if len(wake_buffer) > wake_frames_max:
                                    wake_buffer.pop(0)
                            elif wake_buffer:
                                wake_buffer.append(audio_data)
                                silence_after_speech += 1
                                if len(wake_buffer) > wake_frames_max:
                                    wake_buffer.pop(0)
                            else:
                                speech_frames = 0
                                silence_after_speech = 0

                            if wake_buffer and speech_frames >= min_speech_frames:
                                window_full = len(wake_buffer) >= wake_frames_max
                                utterance_done = silence_after_speech >= hangover_frames
                                speech_ratio = speech_frames / max(len(wake_buffer), 1)
                                if (window_full or utterance_done) and speech_ratio >= wake_speech_ratio_min:
                                    now = time.time()
                                    cooldown = float(self.config.get("wake_cooldown_seconds", 1.2))
                                    if now - self._last_wake_attempt >= cooldown:
                                        combined = np.concatenate(wake_buffer)
                                        avg_level = self.audio.get_rms(combined)
                                        if avg_level < wake_rms * 1.1:
                                            wake_buffer.clear()
                                            speech_frames = 0
                                            silence_after_speech = 0
                                            continue

                                        text = self.wakeword.transcribe(
                                            combined,
                                            language=self.config.get("stt_language", "es"),
                                            vad_filter=True,
                                            beam_size=stt_beam_wake,
                                        )
                                        self._last_wake_attempt = now
                                        wake_buffer.clear()
                                        speech_frames = 0
                                        silence_after_speech = 0

                                        if text:
                                            print(f"[WAKE] STT sample: '{text}'")
                                        phrases = self.config.get("wake_phrases", [])
                                        detected, command_tail = self.wakeword.split_wake_and_command(text, phrases)
                                        if detected:
                                            print(f"Wake phrase detected! Transcription: {text}")
                                            auto_listen = self._handle_command(
                                                stream,
                                                blocksize,
                                                silence_rms,
                                                source="voice",
                                                prefilled_text=command_tail or None,
                                            )
                            elif silence_after_speech > hangover_frames * 3:
                                wake_buffer.clear()
                                speech_frames = 0
                                silence_after_speech = 0
                        except Exception as e:
                            print(f"Audio read error: {e}")
                            break

            except Exception as e:
                print(f"Voice loop fatal error: {e}")
                time.sleep(1.0)

    def _check_cancel(self) -> bool:
        """Check whether the activation hotkey was pressed again (same-key cancel).

        Called from inside ``record_command``'s tight loop so it must be
        lightweight.  Returns ``True`` when a cancel is signalled.
        """
        if self.shortcut_manager.is_triggered():
            self.shortcut_manager.clear_trigger()
            with self._activation_lock:
                self._cancel_flag = True
            return True
        if self.shortcut_manager.is_visual_triggered():
            self.shortcut_manager.clear_visual_trigger()
            with self._activation_lock:
                self._cancel_flag = True
            return True
        with self._activation_lock:
            return self._cancel_flag

    def _handle_command(self, stream, blocksize, silence_rms, source="voice", prefilled_text: str | None = None):
        if not self._begin_listening(source):
            print(f"[MIC] Ignoring {source} activation because listening is already active.")
            return False
        try:
            return self._handle_command_unlocked(
                stream, blocksize, silence_rms, source=source, prefilled_text=prefilled_text
            )
        finally:
            self._finish_listening()

    def _handle_command_unlocked(self, stream, blocksize, silence_rms, source="voice", prefilled_text: str | None = None):
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
        self._cancel_flag = False
        self.overlay.show("listening", "Wake phrase or hotkey detected.")
        if hasattr(self.bridge, "set_runtime_listening_state"):
            self.bridge.set_runtime_listening_state("listening", "Wake phrase or hotkey detected.")
        if self.tray:
            self.tray.set_mic_active(True)

        stt_prompt = self.wakeword.build_stt_prompt(self.config.get("wake_phrases", []))
        stt_beam = max(1, int(self.config.get("stt_beam_size", 5)))

        prefilled = (prefilled_text or "").strip()
        if prefilled:
            print(f"[STT] ✅ Comando en la misma frase: '{prefilled}'")
            text = self.wakeword.normalize_text(prefilled)
            return self._process_transcribed_text(text, image_base64=image_base64, source=source)

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
            level_callback=emit_level,
            cancel_check=self._check_cancel,
        )

        # ── Same-hotkey cancel ───────────────────────────────────────────
        if self._cancel_flag:
            self._cancel_flag = False
            print("[MIC] ⛔ Escucha cancelada por el usuario (hotkey).")
            self.overlay.cancel_active()
            if hasattr(self.bridge, "set_runtime_listening_state"):
                self.bridge.set_runtime_listening_state("idle")
            if self.tray:
                self.tray.set_mic_active(False)
            return False

        print(f"[MIC] 🔴 Fin de la escucha (Grabados {len(command_audio)} frames).")

        if command_audio.size > 0:
            print("[STT] ⏳ Transcribiendo audio con Inteligencia Artificial...")
            self.overlay.show("processing", "Transcribing your command...")
            if hasattr(self.bridge, "set_runtime_listening_state"):
                self.bridge.set_runtime_listening_state("thinking", "Transcribing your command...")
            # Apagamos el filtro VAD porque a veces recorta las voces bajas
            text = self.wakeword.transcribe(
                command_audio,
                language=self.config.get("stt_language", "es"),
                vad_filter=False,
                beam_size=stt_beam,
                initial_prompt=stt_prompt,
            )

            if text:
                print(f"[STT] ✅ Texto reconocido: '{text}'")
                return self._process_transcribed_text(text, image_base64=image_base64, source=source)
            else:
                print("[STT] ❌ El audio contenía ruido pero no se reconoció ningún texto claro.")
                self.overlay.hide()
                if hasattr(self.bridge, "set_runtime_listening_state"):
                    self.bridge.set_runtime_listening_state("idle")
                if self.tray:
                    self.tray.set_mic_active(False)
                return False
        else:
            print("[MIC] 💤 Silencio detectado. Cancelando escucha y volviendo a dormir.")
            self.overlay.hide()
            if hasattr(self.bridge, "set_runtime_listening_state"):
                self.bridge.set_runtime_listening_state("idle")
            if self.tray:
                self.tray.set_mic_active(False)
            return False

    def _process_transcribed_text(self, text: str, *, image_base64, source: str) -> bool:
        if hasattr(self.bridge, "set_runtime_overlay_text"):
            self.bridge.set_runtime_overlay_text(text, "")
        if self.tray:
            self.tray.set_mic_active(False)

        from src.platform.windows.local_commands import process_local_command
        if process_local_command(text):
            print(f"[LOCAL] 🖥️ Comando local ejecutado.")
            self.audio.play_earcon("done")
            self.bridge.log_local_action(text, "Acción de sistema ejecutada localmente.")
            if hasattr(self.bridge, "set_runtime_overlay_text"):
                self.bridge.set_runtime_overlay_text(text, "Acción de sistema ejecutada localmente.")
            self.overlay.show_result(text, "Acción de sistema ejecutada localmente.")
            self.overlay.hide()
            if hasattr(self.bridge, "set_runtime_listening_state"):
                self.bridge.set_runtime_listening_state("idle")
            if self.tray:
                self.tray.set_mic_active(False)
            return True

        self.overlay.show("thinking", text)
        if hasattr(self.bridge, "set_runtime_listening_state"):
            self.bridge.set_runtime_listening_state("thinking", text)
        res = self.bridge.send_message(text, image_base64=image_base64)

        response_text = res.get("response", "")
        if response_text:
            if hasattr(self.bridge, "set_runtime_overlay_text"):
                self.bridge.set_runtime_overlay_text(text, response_text)
            self.overlay.show_result(text, response_text)
            if hasattr(self.bridge, "set_runtime_listening_state"):
                self.bridge.set_runtime_listening_state("speaking", response_text)
            while self._running and getattr(self.tts, "is_speaking", False):
                time.sleep(0.1)
            self.overlay.hide()
            if hasattr(self.bridge, "set_runtime_listening_state"):
                self.bridge.set_runtime_listening_state("idle")
        else:
            self.overlay.hide()
            if hasattr(self.bridge, "set_runtime_listening_state"):
                self.bridge.set_runtime_listening_state("idle")

        if res.get("success", False):
            self.audio.play_earcon("done")
        else:
            self.audio.play_earcon("error")

        print(f"[API] 📡 Respuesta de Hermes: {res.get('success', False)}")
        if self.tray:
            self.tray.set_mic_active(False)
        return res.get("success", False)
