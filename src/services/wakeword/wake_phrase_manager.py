import re
import unicodedata
from typing import Iterable, Optional, Tuple

import numpy as np
from faster_whisper import WhisperModel

# Close STT mis-hearings of "Hermes" — keep the list tight to avoid false wakes.
_HERMES_WAKE_ALIASES = frozenset(
    {
        "hermes",
        "ermes",
        "jermes",
        "ermis",
        "helmes",
        "hermez",
    }
)

_HEY_PREFIXES = frozenset({"hey", "oye", "ey", "ei", "hi"})


class WakePhraseManager:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def normalize_text(self, text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.lower()
        text = re.sub(r"[^a-z0-9áéíóúüñ\s]", " ", text)
        return " ".join(text.split())

    def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
        *,
        vad_filter: bool = True,
        beam_size: int = 1,
        initial_prompt: Optional[str] = None,
    ) -> str:
        kwargs: dict = {
            "language": language,
            "beam_size": max(1, int(beam_size or 1)),
            "vad_filter": vad_filter,
            "condition_on_previous_text": False,
            "temperature": 0.0,
        }
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt

        segments, _info = self.model.transcribe(audio, **kwargs)
        parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        return self.normalize_text(" ".join(parts))

    def build_stt_prompt(self, wake_phrases: Iterable[str]) -> str:
        phrases = [self.normalize_text(p) for p in wake_phrases if str(p).strip()]
        if not phrases:
            return "hermes, hey hermes, oye hermes"
        return ", ".join(phrases)

    def _token_is_hermes(self, token: str) -> bool:
        if not token:
            return False
        return token in _HERMES_WAKE_ALIASES

    def _tokens_equal_phrase(self, window: list[str], phrase_tokens: list[str]) -> bool:
        if not phrase_tokens or len(window) != len(phrase_tokens):
            return False
        if window == phrase_tokens:
            return True
        if (
            len(phrase_tokens) == 2
            and phrase_tokens[0] in _HEY_PREFIXES
            and self._token_is_hermes(phrase_tokens[1])
            and window[0] in _HEY_PREFIXES
            and self._token_is_hermes(window[1])
        ):
            return True
        if len(phrase_tokens) == 1 and self._token_is_hermes(phrase_tokens[0]):
            return self._token_is_hermes(window[0])
        return False

    def _phrase_tokens_match(self, text_tokens: list[str], phrase_tokens: list[str]) -> bool:
        if not phrase_tokens:
            return False

        if len(phrase_tokens) == 1 and self._token_is_hermes(phrase_tokens[0]):
            return any(self._token_is_hermes(tok) for tok in text_tokens)

        window_size = len(phrase_tokens)
        for i in range(len(text_tokens) - window_size + 1):
            window = text_tokens[i : i + window_size]
            if self._tokens_equal_phrase(window, phrase_tokens):
                return True
        return False

    def _phrase_at_start(self, text_tokens: list[str], phrase_tokens: list[str]) -> bool:
        if not phrase_tokens or len(text_tokens) < len(phrase_tokens):
            return False
        return self._tokens_equal_phrase(text_tokens[: len(phrase_tokens)], phrase_tokens)

    def contains_wake_phrase(self, text: str, wake_phrases: Iterable[str]) -> bool:
        text = self.normalize_text(text)
        if not text:
            return False

        text_tokens = text.split()
        for phrase in wake_phrases:
            phrase_tokens = self.normalize_text(phrase).split()
            if self._phrase_tokens_match(text_tokens, phrase_tokens):
                return True
        return False

    def split_wake_and_command(
        self,
        text: str,
        wake_phrases: Iterable[str],
        *,
        at_start: bool = True,
    ) -> Tuple[bool, str]:
        """Return (wake_detected, command_text_after_wake).

        For wake-word detection, ``at_start=True`` requires the phrase at the
        beginning of the utterance so mid-sentence STT hallucinations are ignored.
        """
        normalized = self.normalize_text(text)
        if not normalized:
            return False, ""

        text_tokens = normalized.split()
        best_end = -1

        ordered_phrases = sorted(
            (self.normalize_text(p) for p in wake_phrases if str(p).strip()),
            key=lambda p: len(p.split()),
            reverse=True,
        )

        for phrase in ordered_phrases:
            phrase_tokens = phrase.split()
            if not phrase_tokens:
                continue

            if at_start:
                if self._phrase_at_start(text_tokens, phrase_tokens):
                    best_end = len(phrase_tokens)
                    break
                continue

            window_size = len(phrase_tokens)
            for i in range(len(text_tokens) - window_size + 1):
                if self._phrase_tokens_match(text_tokens[i : i + window_size], phrase_tokens):
                    end = i + window_size
                    if end > best_end:
                        best_end = end

        if best_end < 0:
            return False, ""

        remainder = " ".join(text_tokens[best_end:]).strip()
        return True, remainder
