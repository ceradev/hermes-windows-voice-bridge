from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(slots=True)
class OverlaySignal:
    kind: str
    title: str
    detail: str = ""
    duration_ms: int = 1600


def _get_mode(status: Dict[str, Any]) -> str:
    return str((status.get("summary") or {}).get("mode") or "unknown").lower()


def _get_last_event(status: Dict[str, Any]) -> str:
    return str((status.get("summary") or {}).get("last_event") or "")


def _get_last_good(status: Dict[str, Any]) -> str:
    return str((status.get("log_state") or {}).get("last_good") or "")


def _get_runtime_signal(status: Dict[str, Any]) -> Dict[str, Any]:
    signal = status.get("runtime_signal") or {}
    if isinstance(signal, dict) and signal:
        return signal
    summary_signal = (status.get("summary") or {}).get("runtime_signal") or {}
    return summary_signal if isinstance(summary_signal, dict) else {}


def derive_overlay_signal(previous: Dict[str, Any] | None, current: Dict[str, Any]) -> OverlaySignal | None:
    previous = previous or {}
    prev_mode = _get_mode(previous)
    mode = _get_mode(current)
    last_event = _get_last_event(current)
    prev_last_event = _get_last_event(previous)
    last_good = _get_last_good(current)
    prev_last_good = _get_last_good(previous)
    runtime_signal = _get_runtime_signal(current)
    previous_signal = _get_runtime_signal(previous)

    if mode == "paused":
        return None

    sequence = int(runtime_signal.get("sequence", 0) or 0)
    previous_sequence = int(previous_signal.get("sequence", 0) or 0)
    if sequence and sequence != previous_sequence:
        kind = str(runtime_signal.get("kind") or "").lower()
        title = str(runtime_signal.get("title") or "").strip()
        detail = str(runtime_signal.get("detail") or "").strip()
        if kind in {"listening", "transcribing", "responding", "speaking", "transcribed"}:
            return OverlaySignal(kind=kind, title=title or kind.title(), detail=detail, duration_ms=1700)
        if kind in {"idle", "error"}:
            return None

    if mode == "listening" and prev_mode != "listening":
        return OverlaySignal(kind="listening", title="● Listening…", detail="Hermes is waiting for your command.", duration_ms=1400)

    lowered_event = last_event.lower()
    if last_event and last_event != prev_last_event:
        if "post event=voice route=voice" in lowered_event:
            return OverlaySignal(kind="transcribing", title="Transcribing…", detail="Turning your voice into text.", duration_ms=1500)
        if "inbound message: platform=webhook user=voice" in lowered_event:
            return OverlaySignal(kind="responding", title="Hermes responding…", detail="Waiting for the VPS answer.", duration_ms=1600)

    if last_good and last_good != prev_last_good:
        return OverlaySignal(kind="speaking", title="Speaking…", detail="Hermes response ready.", duration_ms=1800)

    return None
