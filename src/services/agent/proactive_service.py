import time
import threading
import logging
from typing import Callable, List, Dict, Any

logger = logging.getLogger(__name__)

class ProactiveService:
    def __init__(self, bridge):
        self.bridge = bridge
        self.running = False
        self.thread = None
        self.timers = []
        self._lock = threading.Lock()

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="ProactiveLoop")
        self.thread.start()
        logger.info("ProactiveService started.")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info("ProactiveService stopped.")

    def add_timer(self, duration_seconds: int, prompt: str):
        """Añade un temporizador. Cuando expire, se enviará el prompt al VPS."""
        with self._lock:
            self.timers.append({
                "trigger_at": time.time() + duration_seconds,
                "prompt": prompt
            })
        logger.info(f"Timer added for {duration_seconds}s: {prompt}")

    def _loop(self):
        while self.running:
            now = time.time()
            triggered = []
            
            with self._lock:
                # Find expired timers
                for t in self.timers:
                    if now >= t["trigger_at"]:
                        triggered.append(t)
                
                # Remove expired timers
                self.timers = [t for t in self.timers if now < t["trigger_at"]]

            for t in triggered:
                self._fire_event(t["prompt"])

            time.sleep(1.0) # Check every second

    def _fire_event(self, prompt: str):
        logger.info(f"Proactive event fired: {prompt}")
        event_message = f"[SYSTEM: El temporizador para '{prompt}' ha finalizado. Responde a esto AHORA MISMO en este chat de forma natural, sin usar Telegram ni notificaciones externas.]"
        
        try:
            # Enviar mensaje como 'manual' para evitar que el VPS lo desvíe a Telegram
            self.bridge.send_message(event_message, source="manual")
        except Exception as e:
            logger.error(f"Error firing proactive event: {e}")
