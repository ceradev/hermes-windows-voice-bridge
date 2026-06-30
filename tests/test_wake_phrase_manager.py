from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.wakeword.wake_phrase_manager import WakePhraseManager


def build_manager() -> WakePhraseManager:
    # Model is not loaded/used in these unit tests
    return WakePhraseManager.__new__(WakePhraseManager)


def test_normalize_text_strips_accents_and_punctuation() -> None:
    manager = build_manager()
    assert manager.normalize_text("¡Hey, Hermes!") == "hey hermes"
    assert manager.normalize_text("  OYE   HERMES  ") == "oye hermes"


def test_contains_wake_phrase_matches_exact_word() -> None:
    manager = build_manager()
    phrases = ["hermes"]
    assert manager.contains_wake_phrase("hermes", phrases) is True
    assert manager.contains_wake_phrase("oye hermes", phrases) is True
    assert manager.contains_wake_phrase("hermes escucha", phrases) is True


def test_contains_wake_phrase_rejects_substring_match() -> None:
    manager = build_manager()
    phrases = ["hermes"]
    assert manager.contains_wake_phrase("hermetic", phrases) is False
    assert manager.contains_wake_phrase("un hermetico dijo hermes", phrases) is True


def test_contains_wake_phrase_matches_multi_word_phrase() -> None:
    manager = build_manager()
    phrases = ["oye hermes"]
    assert manager.contains_wake_phrase("oye hermes", phrases) is True
    assert manager.contains_wake_phrase("oye hermes escucha", phrases) is True


def test_contains_wake_phrase_rejects_partial_multi_word_phrase() -> None:
    manager = build_manager()
    phrases = ["oye hermes"]
    assert manager.contains_wake_phrase("oye", phrases) is False
    assert manager.contains_wake_phrase("hermes", phrases) is False
    assert manager.contains_wake_phrase("oye tu hermes", phrases) is False


def test_contains_wake_phrase_handles_case_and_punctuation() -> None:
    manager = build_manager()
    phrases = ["Hey Hermes"]
    assert manager.contains_wake_phrase("¡Hey, Hermes!", phrases) is True
    assert manager.contains_wake_phrase("dije hey hermes", phrases) is True


def test_contains_wake_phrase_returns_false_for_empty_text() -> None:
    manager = build_manager()
    phrases = ["hermes"]
    assert manager.contains_wake_phrase("", phrases) is False
    assert manager.contains_wake_phrase("   ", phrases) is False


def test_contains_wake_phrase_matches_fuzzy_stt_variants() -> None:
    manager = build_manager()
    phrases = ["hermes", "hey hermes"]
    assert manager.contains_wake_phrase("ermes", phrases) is True
    assert manager.contains_wake_phrase("hey ermes", phrases) is True
    assert manager.contains_wake_phrase("jermes que hora es", phrases) is True
    assert manager.contains_wake_phrase("helmes", phrases) is True


def test_split_wake_and_command_rejects_mid_sentence_hallucination() -> None:
    manager = build_manager()
    phrases = ["hermes", "hey hermes", "oye hermes"]
    detected, cmd = manager.split_wake_and_command("dije hey ermes al final", phrases)
    assert detected is False
    assert cmd == ""

    detected, cmd = manager.split_wake_and_command("armes hola", phrases)
    assert detected is False
    assert cmd == ""


def test_split_wake_and_command_extracts_tail() -> None:
    manager = build_manager()
    phrases = ["hermes", "hey hermes", "oye hermes"]
    detected, cmd = manager.split_wake_and_command("hey ermes que hora es", phrases)
    assert detected is True
    assert cmd == "que hora es"

    detected, cmd = manager.split_wake_and_command("hermes", phrases)
    assert detected is True
    assert cmd == ""

    detected, cmd = manager.split_wake_and_command("hola mundo", phrases)
    assert detected is False
    assert cmd == ""


def test_build_stt_prompt_includes_wake_phrases() -> None:
    manager = build_manager()
    assert "hermes" in manager.build_stt_prompt(["Hey Hermes", "oye hermes"])


def test_contains_wake_phrase_ignores_empty_phrases() -> None:
    manager = build_manager()
    phrases = ["", "hermes"]
    assert manager.contains_wake_phrase("hermes", phrases) is True
