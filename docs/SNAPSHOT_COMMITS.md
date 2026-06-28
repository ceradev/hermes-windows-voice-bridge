# Snapshot Commit Summary

Generated during Phase 1.1c of the Hermes Voice Bridge stabilization plan.

All commits follow the classification in `docs/SNAPSHOT_CLASSIFICATION.md`. Working tree is clean except for two pre-existing untracked test files (`tests/test_session_naming.py`, `tests/test_webview_bridge_config_sync.py`) that are not part of this snapshot.

## Commits (newest first)

| Hash | Message | Files |
|---|---|---|
| `1a17ae2` | `chore: clean local artifact ignores` | `.gitignore` |
| `748589e` | `test: remove obsolete desktop support tests` | `tests/test_windows_voice_desktop_support.py` (deleted) |
| `9882389` | `chore: add Windows launcher scripts` | `scripts/HermesVoiceBridge.iss`, `scripts/run_voice.ps1`, `scripts/run_voice_desktop.ps1`, `scripts/run_voice_panel_web.ps1`, `scripts/run_voice_watchdog.ps1` |
| `018ff56` | `feat: consolidate dashboard routes` | `src/ui/app/src/App.tsx`, `HotkeyRecorder.tsx`, `Header.tsx`, `Sidebar.tsx`, `Titlebar.tsx`, `Home.tsx`, `Commands.tsx`, `Settings.tsx`, `Chat.tsx` (new), `Configure.tsx` (new), `AudioVisualizer.tsx` (deleted), `History.tsx` (deleted), `Notifications.tsx` (deleted), `Sessions.tsx` (deleted), `Shortcuts.tsx` (deleted), `Voice.tsx` (deleted) |
| `d9d7b29` | `feat: expose runtime state in UI` | `src/ui/app/src/services/api.ts`, `HermesContext.tsx`, `ToastContext.tsx`, `LanguageContext.tsx`, `SystemAlerts.tsx` (new) |
| `f35bc9d` | `feat: add Hermes UI design system` | `src/ui/app/package.json`, `package-lock.json`, `main.tsx`, `index.css`, `tailwind.config.cjs`, `ThemeContext.tsx`, `PageHeader.tsx` |
| `9b4c037` | `feat: wire tray and overlay runtime` | `src/platform/tray/tray_manager.py`, `src/platform/windows/desktop_app.py`, `src/platform/windows/overlay_service.py`, `src/ui/desktop/theme.py`, `src/ui/overlays/status_overlay.py` |
| `8f13f80` | `feat: sync runtime voice state` | `src/core/config/config_service.py`, `src/core/state/__init__.py`, `src/core/state/app_state.py`, `src/api/webview_bridge.py`, `src/platform/windows/voice_loop.py`, `src/services/audio/audio_service.py` |
| `37483f3` | `feat: add session title sources` | `src/core/session/session_manager.py`, `src/storage/database.py` |
| `24662d2` | `docs: add stabilization snapshot audit` | `docs/PROJECT_STATUS.md`, `docs/SNAPSHOT_INVENTORY.md`, `docs/SNAPSHOT_CLASSIFICATION.md` |

## Cleanup applied before committing

- **Duplicate imports removed**: `webview_bridge.py` (deque), `config_service.py` (json), `desktop_app.py` (logging), `voice_loop.py` (threading)
- **Header.tsx**: stale route labels for `/sessions`, `/history`, `/notifications`, `/voice`, `/shortcuts`, `/hermes`, `/tts` removed; only routes registered in `App.tsx` remain
- **Configure.tsx**: added explicit type annotation for `.map((s: string) => ...)` to satisfy `tsc --noEmit`
- **`.gitignore`**: removed broad `test_*.py` ignore; added `.agents/`, `skills-lock.json`, `src/ui/app/build-output.txt`

## Intentionally discarded (not committed)

- `.agents/` — local agent skill content, not project source
- `skills-lock.json` — local agent lock file
- `src/ui/app/build-output.txt` — Vite build log artifact

## Known issues documented (not blocking this commit)

- `overlay_service.py`: `set_mode()` is a no-op; mini/full mode exposed in UI/config but not implemented (Phase 1.3)
- `SystemAlerts.tsx`: offline/recovery banner exists but is not wired into the app layout (future UX task)
- Scripts reference legacy entrypoints (`src\windows_hermes_voice.py`, `src\windows_hermes_voice_desktop.py`); alignment to `src/platform/windows/desktop_app.py` deferred to Phase 1.2
- `HermesVoiceBridge.iss`: `{#MyAppName}` not defined; references missing `run_voice_tray.ps1`

## Verification

- `python -m py_compile` passes on all 13 changed `.py` files
- `npx tsc --noEmit` passes on the frontend
