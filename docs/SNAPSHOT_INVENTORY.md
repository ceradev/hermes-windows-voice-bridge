# Snapshot Inventory

> Generated during Phase 1.1a of the stabilization plan.
> Command: `git status --short`

## Summary

- **Modified tracked files**: 40
- **Deleted tracked files**: 6
- **Untracked files**: 14
- **Net diff**: ~+3,065 / ~-2,646 lines across tracked files

This snapshot represents a large, mixed set of changes spanning backend, UI, build/packaging and documentation.

---

## Modified tracked files

| File | Area | Lines | Notes |
|------|------|-------|-------|
| `.gitignore` | repo | 51 | Likely ignoring new build artifacts or untracked paths |
| `src/api/webview_bridge.py` | backend | +335 | Large refactor (WebviewBridge god-object changes) |
| `src/core/config/config_service.py` | backend | +41 | Config changes (version? paths?) |
| `src/core/session/session_manager.py` | backend | +184 | Session management changes |
| `src/core/state/__init__.py` | backend | +3 | State exports |
| `src/core/state/app_state.py` | backend | +43 | Runtime state changes |
| `src/platform/tray/tray_manager.py` | backend | +496/-496 | Major rewrite |
| `src/platform/windows/desktop_app.py` | backend | +70 | App lifecycle/integration changes |
| `src/platform/windows/overlay_service.py` | backend | +525/-525 | Major rewrite of overlay |
| `src/platform/windows/voice_loop.py` | backend | +136 | Voice pipeline changes |
| `src/services/audio/audio_service.py` | backend | +5 | Minor audio change |
| `src/storage/database.py` | backend | +24 | DB changes |
| `src/ui/app/package-lock.json` | frontend deps | +20 | Dependency update |
| `src/ui/app/package.json` | frontend deps | +2 | New dependency? |
| `src/ui/app/src/App.tsx` | frontend | +78 | Routing changes |
| `src/ui/app/src/components/HotkeyRecorder.tsx` | frontend | +38 | Hotkey recording changes |
| `src/ui/app/src/components/Layout/Header.tsx` | frontend | +112/-112 | Header rewrite |
| `src/ui/app/src/components/Layout/PageHeader.tsx` | frontend | +23 | Page header changes |
| `src/ui/app/src/components/Layout/Sidebar.tsx` | frontend | +204 | Sidebar rewrite |
| `src/ui/app/src/components/Layout/Titlebar.tsx` | frontend | +89 | Titlebar changes |
| `src/ui/app/src/contexts/HermesContext.tsx` | frontend | +278 | Hermes context rewrite |
| `src/ui/app/src/contexts/LanguageContext.tsx` | frontend | +435 | Translation updates |
| `src/ui/app/src/contexts/ThemeContext.tsx` | frontend | +2 | Minor theme change |
| `src/ui/app/src/contexts/ToastContext.tsx` | frontend | +210 | Toast system rewrite |
| `src/ui/app/src/index.css` | frontend | +257/-257 | CSS redesign |
| `src/ui/app/src/main.tsx` | frontend | +2 | Entry point changes |
| `src/ui/app/src/pages/Commands.tsx` | frontend | +144 | Commands page rewrite |
| `src/ui/app/src/pages/Home.tsx` | frontend | +430/-430 | Home page rewrite |
| `src/ui/app/src/pages/Settings.tsx` | frontend | +225 | Settings rewrite |
| `src/ui/app/src/services/api.ts` | frontend | +45 | API client changes |
| `src/ui/app/tailwind.config.cjs` | frontend config | +65 | Tailwind theme extensions |
| `src/ui/desktop/theme.py` | backend UI | +28 | Desktop theme changes |
| `src/ui/overlays/status_overlay.py` | backend UI | +36 | Status overlay changes |

## Deleted tracked files

| File | Area | Reason (to verify) |
|------|------|--------------------|
| `src/ui/app/src/components/Audio/AudioVisualizer.tsx` | frontend | Unused or replaced? |
| `src/ui/app/src/pages/History.tsx` | frontend | Consolidated? Removed? |
| `src/ui/app/src/pages/Notifications.tsx` | frontend | Removed? |
| `src/ui/app/src/pages/Sessions.tsx` | frontend | Removed? |
| `src/ui/app/src/pages/Shortcuts.tsx` | frontend | Removed? |
| `src/ui/app/src/pages/Voice.tsx` | frontend | Removed? |
| `tests/test_windows_voice_desktop_support.py` | tests | Removed? |

## Untracked files

| File | Area | Notes |
|------|------|-------|
| `.agents/` | tooling | Agent-related files, probably local config |
| `docs/` | documentation | New docs (audit, plan, etc.) |
| `scripts/HermesVoiceBridge.iss` | packaging | Inno Setup script |
| `scripts/run_voice.ps1` | tooling | PowerShell launcher |
| `scripts/run_voice_desktop.ps1` | tooling | PowerShell launcher |
| `scripts/run_voice_panel_web.ps1` | tooling | PowerShell launcher |
| `scripts/run_voice_watchdog.ps1` | tooling | PowerShell launcher |
| `skills-lock.json` | tooling | Skill lock file |
| `src/ui/app/build-output.txt` | build | Build log output (should probably be ignored/removed) |
| `src/ui/app/src/components/Layout/SystemAlerts.tsx` | frontend | New component |
| `src/ui/app/src/pages/Chat.tsx` | frontend | New page |
| `src/ui/app/src/pages/Configure.tsx` | frontend | New page |
