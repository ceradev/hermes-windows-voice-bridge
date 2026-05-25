# Hermes Voice Bridge Native Refactor Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Convert Hermes Voice Bridge from a script-first hybrid panel into a Windows-native background utility with persistent session, central state, robust lifecycle, and a premium desktop UX.

**Architecture:** Move to a layered app package with `core/`, `services/`, `platform/`, `ui/`, `storage/`, and `api/`. The tray becomes the lifecycle owner, the settings window becomes a thin client over shared state, and session/config/logging stop being scattered across scripts.

**Tech Stack:** Python 3.11+, Tkinter short-term, native Windows mutex/process APIs, JSON/env storage now, DPAPI-ready secure store abstraction, pystray, sounddevice, faster-whisper.

---

## Current diagnosis

1. `src/windows_hermes_voice.py` is still a monolith that mixes config parsing, audio loop, hotkey registration, webhook transport, TTS cleanup, runtime logging, and lifecycle control.
2. `src/windows_hermes_voice_tray.py`, `src/windows_hermes_voice_desktop.py`, and `src/windows_hermes_voice_panel_api.py` duplicate state interpretation and process control.
3. Session persistence for authenticated Hermes desktop flows does not exist as a first-class concept.
4. The current desktop app is technically native but architecturally still a control panel over an API, not a cohesive app model.
5. Shortcut UX is only a string value (`ctrl+shift+h`) with no editor model, no conflict engine, and no interaction design.
6. Logs exist, but they are not formally split into user/debug/crash channels.

## Target package layout

```text
src/
  hermes_voice_bridge/
    core/
      lifecycle/
      state/
      events/
      logging/
      config/
      session/
    services/
      audio/
      wakeword/
      transcription/
      hermes/
      tts/
      autostart/
    platform/
      tray/
      windows/
      notifications/
      shortcuts/
    ui/
      desktop/
      overlays/
      settings/
      components/
    api/
      local_api/
    storage/
      cache/
      repositories/
```

## UX target

### Tray
- Title: `Hermes Voice Bridge`
- Dynamic line: `● Ready`, `● Listening`, `● Transcribing`, `● Responding`, `● Paused`, `● Error`
- Actions:
  - Start Listening
  - Stop Listening
  - Open Hermes
  - View Logs
  - Settings
  - Restart Services
  - Quit

### Overlay
- Small pill overlay centered low on screen.
- States:
  - `● Listening…`
  - `Transcribing…`
  - `Hermes responding…`
  - `Speaking…`
- Animations: 120–180 ms opacity/scale transition.

### Settings IA
- General
- Audio
- Shortcuts
- Hermes
- TTS
- Logs
- Advanced

### Shortcut editor
- Dedicated capture component.
- Visual key pills: `[ CTRL ] + [ SHIFT ] + [ SPACE ]`
- Live pressed-state animation.
- Conflict banner when reserved or already mapped.
- Clear/reset affordance.

## Foundation already added in this refactor pass

- `core/events/EventBus`
- `core/state/AppStateStore`
- `core/session/SessionManager`
- `core/config/ConfigService`
- `core/logging/BridgeLogger`
- `core/lifecycle/AppLifecycle`
- `storage/repositories/JsonSessionRepository`
- `platform/windows/SecureValueStore`
- `ui/settings/ShortcutEditorState`

These pieces are the new backbone and should be consumed by tray/desktop/API instead of growing more globals.

## Phase 1 — Core extraction

### Task 1: Introduce the package backbone
**Files:**
- Create: `src/hermes_voice_bridge/**`
- Verify: imports from scripts

**Steps:**
1. Keep legacy entry scripts as launchers only.
2. Move shared config/session/logging/state concerns into the new package.
3. Ensure new modules are dependency-light and testable on Linux CI.

### Task 2: Make tray the lifecycle owner
**Files:**
- Modify: `src/windows_hermes_voice_tray.py`
- Create: `src/hermes_voice_bridge/platform/tray/*.py`

**Steps:**
1. Instantiate `EventBus`, `AppStateStore`, `BridgeLogger`, `AppLifecycle` at tray startup.
2. Make the tray publish events instead of only writing log strings.
3. Register shutdown callbacks for bridge process, API process, and temp handles.

### Task 3: Centralize config access
**Files:**
- Modify: `src/windows_hermes_voice.py`
- Modify: `src/windows_hermes_voice_panel_api.py`
- Modify: `src/windows_hermes_voice_tray.py`

**Steps:**
1. Replace local env parsing with `ConfigService` calls.
2. Keep `voice.env` as source of truth for persisted settings.
3. Stop duplicating `load_env_file` wrappers in multiple scripts.

### Task 4: Introduce session persistence
**Files:**
- Create: `state/session.json` via repository
- Create: `state/session.secrets`
- Modify: desktop login flow once auth UI exists

**Steps:**
1. Use `SessionManager` for save/restore/logout.
2. Add `remember me` semantics.
3. Publish `session.restored`, `session.expired`, `session.logged_out` events.

## Phase 2 — Native runtime shell

### Task 5: Rebuild tray menu
**Files:**
- Modify: `src/windows_hermes_voice_tray.py`
- Create: `src/hermes_voice_bridge/platform/tray/menu_model.py`

**Steps:**
1. Compute menu from central app state.
2. Show dynamic status and safe action enable/disable logic.
3. Expose logs/settings/open folder without mixing menu logic and subprocess logic.

### Task 6: Add overlay state machine
**Files:**
- Create: `src/hermes_voice_bridge/ui/overlays/*.py`
- Modify: bridge event emission points

**Steps:**
1. Emit `audio.started`, `transcription.completed`, `hermes.response`, `tts.started`.
2. Render a small always-on-top overlay driven by state.
3. Auto-hide after response completion.

## Phase 3 — Settings redesign

### Task 7: Replace the current wide control panel with a utility-style settings app
**Files:**
- Modify: `src/windows_hermes_voice_desktop.py`
- Create: `src/hermes_voice_bridge/ui/desktop/*`

**Steps:**
1. Change from dashboard cards to settings navigation.
2. Keep summary surface compact and secondary.
3. Promote configuration tasks to first-class pages.

### Task 8: Build modern shortcut editor
**Files:**
- Create: `src/hermes_voice_bridge/platform/shortcuts/*`
- Create: `src/hermes_voice_bridge/ui/components/shortcut_editor.py`

**Steps:**
1. Capture low-level key presses.
2. Render visual pills and live transitions.
3. Validate reserved combos and duplicates.
4. Persist normalized accelerator strings through `ConfigService`.

## Phase 4 — Legacy removal

### Task 9: Kill web-panel leftovers
**Files:**
- Remove later: `panel-web/`
- Modify: `src/windows_hermes_voice_panel_api.py`

**Steps:**
1. Stop serving `panel-web/dist`.
2. Keep the local API only for desktop/tray IPC or replace it with in-proc message passing.
3. Remove `run_voice_panel_web.ps1` from the happy path.

### Task 10: Uninstall and cleanup hardening
**Files:**
- Modify: `scripts/uninstall_voice_bridge.ps1`
- Modify: tray exit path

**Steps:**
1. Stop processes cleanly.
2. Remove autostart artifacts created by the app.
3. Preserve or purge persisted session based on uninstall mode.

## Validation checklist

- [ ] Session survives window close and tray minimization.
- [ ] Session restores after app restart.
- [ ] Session dies only on logout, token expiry, or reboot if tokens are non-persistent.
- [ ] Tray is single-instance and remains authoritative.
- [ ] Overlay reflects real runtime events.
- [ ] Shortcut editor detects conflicts before save.
- [ ] Logs are split into user/debug/crash files.
- [ ] Shutdown closes bridge, API, and listeners without orphan processes.

## Visual direction summary

- Fluent-inspired dark UI
- Subtle glass surfaces
- Large radius cards only where necessary
- Minimal chrome
- Clear typography hierarchy
- Utility-first settings, not admin-dashboard layout
- Strong status semantics with tiny footprint
