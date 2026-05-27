import numpy as np
import unicodedata
import re
from typing import Optional, Iterable, List
from faster_whisper import WhisperModel

class WakePhraseManager:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def normalize_text(self, text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.lower()
        text = re.sub(r"[^a-z0-9áéíóúüñ\s]", " ", text)
        return " ".join(text.split())

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None, vad_filter: bool = True) -> str:
        segments, _info = self.model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=vad_filter,
            condition_on_previous_text=False,
            temperature=0.0,
        )
        parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        return self.normalize_text(" ".join(parts))

    def contains_wake_phrase(self, text: str, wake_phrases: Iterable[str]) -> bool:
        text = self.normalize_text(text)
        if not text:
            return False

        # Strictly check if any configured phrase is a substring of the spoken text
        return any(self.normalize_text(phrase) in text for phrase in wake_phrases)
