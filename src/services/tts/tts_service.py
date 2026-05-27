import queue
import threading
import time
import re
from typing import List, Optional

import os
import tempfile
import asyncio

try:
    import winsound
except ImportError:
    winsound = None

try:
    import edge_tts
    import pygame
except ImportError:
    edge_tts = None
    pygame = None

# Hide pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

class TTSService:
    def __init__(self, mode: str = "both", voice_name: str = "", rate: int = 215):
        self.mode = mode if mode in {"off", "beep", "voice", "both"} else "both"
        # Default to a great neural voice
        self.voice_name = voice_name or "es-ES-AlvaroNeural"
        self.rate = rate
        self.queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self.voice_failed = False
        self.is_speaking = False
        
        if pygame is not None:
            pygame.mixer.init()
        
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def update_settings(self, mode: str, voice_name: str):
        self.mode = mode
        self.voice_name = voice_name

    def beep(self) -> None:
        if self.mode not in {"beep", "both"}:
            return
        try:
            if winsound is not None:
                winsound.Beep(880, 85)
            else:
                print("\a", end="", flush=True)
        except Exception:
            pass

    def say(self, text: str) -> None:
        if self.mode not in {"voice", "both"} or not text:
            return
        for chunk in self._chunk_tts_text(text):
            self.queue.put(chunk)

    def pulse(self, text: str) -> None:
        self.beep()
        self.say(text)

    def _prepare_tts_text(self, text: str, max_chars: int = 500) -> str:
        text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("```", " ").replace("`", " ")
        text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
        text = re.sub(r"(?m)^\s*#{1,6}\s+", "", text)
        text = re.sub(r"(?m)^\s*[-*•]\s+", "", text)
        text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
        text = re.sub(r"\n+", ". ", text)
        for token in ["**", "__", "~~", "||"]:
            text = text.replace(token, "")
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]

    def _chunk_tts_text(self, text: str, max_chars: int = 180) -> List[str]:
        prepared = self._prepare_tts_text(text, max_chars=500)
        if not prepared:
            return []

        def split_long_segment(segment: str) -> List[str]:
            segment = segment.strip()
            if len(segment) <= max_chars:
                return [segment] if segment else []
            parts = re.split(r"(?<=[,;:!?])\s+", segment)
            out: List[str] = []
            buf = ""
            for part in parts:
                if not part: continue
                if len(part) > max_chars:
                    start = 0
                    while start < len(part):
                        out.append(part[start:start+max_chars].strip())
                        start += max_chars
                    continue
                if buf and len(buf) + 1 + len(part) <= max_chars:
                    buf = f"{buf} {part}"
                else:
                    if buf: out.append(buf)
                    buf = part
            if buf: out.append(buf)
            return out

        sentences = re.split(r"(?<=[.!?;:])\s+", prepared)
        chunks: List[str] = []
        buf = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence: continue
            for piece in split_long_segment(sentence):
                if buf and len(buf) + 1 + len(piece) <= max_chars:
                    buf = f"{buf} {piece}"
                else:
                    if buf: chunks.append(buf)
                    buf = piece
        if buf: chunks.append(buf)
        return chunks

    def _speak_once(self, text: str) -> None:
        if edge_tts is None or pygame is None:
            raise RuntimeError("edge_tts or pygame is not installed")
            
        temp_file = tempfile.mktemp(suffix=".mp3")
        try:
            # Adjust rate if needed (e.g., "+10%")
            rate_str = "+0%"
            if self.rate > 200:
                perc = min(100, int((self.rate - 200) / 2))
                rate_str = f"+{perc}%"
                
            communicate = edge_tts.Communicate(text, self.voice_name, rate=rate_str)
            asyncio.run(communicate.save(temp_file))
            
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
        finally:
            pygame.mixer.music.unload()
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

    def _run(self) -> None:
        if edge_tts is None or pygame is None:
            self.voice_failed = True
            return

        while True:
            text = self.queue.get()
            if text is None:
                self.is_speaking = False
                return
            try:
                self.is_speaking = True
                self._speak_once(text)
                if not self.queue.empty():
                    time.sleep(0.12)
                else:
                    self.is_speaking = False
            except Exception as e:
                print(f"[TTS] Error procesando audio: {e}")
                self.is_speaking = False
                # Do not return! Let the thread stay alive for the next message.
                time.sleep(1)
