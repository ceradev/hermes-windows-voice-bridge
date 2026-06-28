# Phase 1.16 Smoke Test Report

Date: 2026-06-28

## Setup

- Project: `C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge`
- Python: `python -m pytest` under Windows / Python 3.13.1
- Reviewed pipeline files:
  - `src/platform/windows/voice_loop.py`
  - `src/services/audio/audio_service.py`
  - `src/platform/windows/overlay_service.py`
  - `src/api/webview_bridge.py`
  - `src/services/tts/tts_service.py`
  - `src/services/hermes/hermes_client.py`
- Added automated mocked smoke coverage in `tests/test_phase1_smoke_pipeline.py`.
- Live audio probe found input devices (`input_devices=28`), but no physical spoken command was supplied during this automated/headless run.
- Hermes API health check against the configured/default endpoint returned `False`; no live Hermes server was reachable from this environment.

## Test Cases

| ID | Stage | Method | Status | Evidence |
| --- | --- | --- | --- | --- |
| TC-01 | Existing test suite | `python -m pytest tests/` | FAIL | Collection stopped with 6 import errors before executing tests. See blockers. |
| TC-02 | Wake detection rejects silence/noise | Mocked `VoiceLoop._loop` with fake stream blocks | PASS | `test_wake_detection_does_not_trigger_on_silence_or_non_wake_noise` passed. Silence never transcribed; non-wake noise used VAD transcription and did not call command handler. |
| TC-03 | Wake phrase dispatch | Mocked `VoiceLoop._loop` with wake transcript `oye hermes` | PASS | `test_wake_phrase_detection_dispatches_voice_command_once` passed; dispatched one `source="voice"` command after VAD wake transcription. |
| TC-04 | STT → Hermes request → overlay state path | Mocked command recording, STT transcript, bridge response, overlay | PASS | `test_headless_voice_command_flow_exercises_stt_hermes_tts_and_overlay_states` passed. Runtime states observed: `idle → listening → thinking → thinking → speaking → idle`. |
| TC-05 | TTS queue/stop | Mocked `edge_tts`/`pygame` worker | PASS | `test_tts_can_queue_speech_and_stop_playback_on_shutdown` passed; speech queued, `is_speaking` became true, shutdown stopped playback and joined the worker. |
| TC-06 | Live microphone wake/STT | Physical mic/spoken wake phrase | BLOCKED | Microphones are visible, but the automated environment cannot provide/verify real spoken audio. Mock coverage exercised the code path instead. |
| TC-07 | Live Hermes client request | `HermesClient.health()` | BLOCKED | Health returned `False`; no live Hermes API endpoint was reachable. Mock bridge request path passed. |
| TC-08 | Live TTS playback | Audible speaker verification | BLOCKED | Playback semantics were verified with mocked `pygame`; audible output was not confirmed in this environment. |

## Observed Behavior

- Wake detection in `src/platform/windows/voice_loop.py:217` runs wake-window STT with `vad_filter=True`. Mocked silence kept the wake buffer empty and never transcribed. Mocked above-threshold non-wake noise transcribed but did not enter `_handle_command` because `contains_wake_phrase` returned false.
- Positive wake phrase detection dispatched a single voice activation from `_loop`, matching the expected wake-detection gate before command handling.
- Command handling moved through overlay/runtime states at `src/platform/windows/voice_loop.py:280`, `src/platform/windows/voice_loop.py:321`, `src/platform/windows/voice_loop.py:351`, `src/platform/windows/voice_loop.py:360`, and back to idle at `src/platform/windows/voice_loop.py:365`.
- Hermes submission is invoked through `self.bridge.send_message(...)` at `src/platform/windows/voice_loop.py:352`; `WebviewBridge.send_message` is implemented at `src/api/webview_bridge.py:364` and queues TTS when the server returns `speak=true` at `src/api/webview_bridge.py:420`.
- TTS queueing is implemented in `src/services/tts/tts_service.py:64`; stop/shutdown behavior is implemented at `src/services/tts/tts_service.py:167` and calls `pygame.mixer.music.stop()` at `src/services/tts/tts_service.py:184`.
- Hermes live health uses `src/services/hermes/hermes_client.py:86`; it returned `False` in this environment.

Automated smoke command result:

```text
python -m pytest tests/test_phase1_smoke_pipeline.py -q
....                                                                     [100%]
4 passed in 0.83s
```

Existing suite result:

```text
python -m pytest tests/
collected 43 items / 6 errors
ERROR tests/test_refactor_foundations.py
ERROR tests/test_windows_voice.py
ERROR tests/test_windows_voice_control.py
ERROR tests/test_windows_voice_desktop_models.py
ERROR tests/test_windows_voice_overlay.py
ERROR tests/test_windows_voice_panel_api.py
```

## Verdict

Phase 1.16 smoke verification is **PARTIAL PASS / BLOCKED FOR LIVE E2E**.

- The voice pipeline logic can be exercised headlessly with mocks through wake detection, STT transcript handling, Hermes bridge request, TTS queue/stop, and overlay state transitions.
- A true live end-to-end spoken test is blocked by missing interactive audio input and an unreachable Hermes API server.
- The existing full pytest suite currently fails during collection due unresolved legacy import paths, so it is not a clean Phase 2 gate yet.

## Blockers

1. **Existing tests fail collection due missing import targets.**
   - `tests/test_refactor_foundations.py:8` imports `hermes_voice_bridge.core.config`, but no `hermes_voice_bridge` package exists in `src/`.
   - `tests/test_windows_voice.py:11` imports `windows_hermes_voice`, but no `windows_hermes_voice.py` exists in the project.
   - `tests/test_windows_voice_control.py:9` imports `windows_hermes_voice_control`, but no `windows_hermes_voice_control.py` exists in the project.
   - `tests/test_windows_voice_desktop_models.py:7`, `tests/test_windows_voice_overlay.py:7`, and `tests/test_windows_voice_panel_api.py:8` also import the absent `hermes_voice_bridge` namespace.
   - Diagnosis: test suite still references a legacy package/module layout after the current source tree moved to top-level `src.core`, `src.ui`, `src.platform`, etc.
2. **Live Hermes server unavailable.**
   - `HermesClient.health()` returned `False`; live request/response cannot be proven until `api_base_url` points at a reachable Hermes service.
3. **Live spoken wake/STT unavailable in this run.**
   - Input devices are present, but this non-interactive smoke run cannot produce a physical wake phrase/command or verify real speaker output.
