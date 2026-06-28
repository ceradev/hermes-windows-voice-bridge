# Snapshot Classification

Generated during Phase 1.1b of the Hermes Voice Bridge stabilization plan.

Inputs inspected:

- `docs/SNAPSHOT_INVENTORY.md`
- `git status --short`
- `git diff --stat`
- `git diff --cached --stat`
- targeted `git diff` output for backend/runtime, overlay/tray, frontend routing/pages/contexts/CSS, package files, scripts, `.gitignore`, and deleted test content
- untracked documentation, scripts, React page/component files, local agent tooling, lock file, and build output

`git diff --cached --stat` is empty, so all current changes are unstaged.

## Classification table

| file | area | action | rationale | proposed commit group |
|---|---|---:|---|---|
| `.gitignore` | repo-ignore | investigate | Diff narrows several bytecode ignores but also adds broad `test_*.py` and `*.mp3` ignores while still not covering `.agents/`, `skills-lock.json`, or `src/ui/app/build-output.txt`; broad test ignore could hide future tests. | repo-ignore-cleanup |
| `src/api/webview_bridge.py` | backend/voice | commit | Adds runtime state plumbing, overlay/tray synchronization, microphone config application, shortcut restart, remote session ID persistence through `SessionManager`, health state updates, activity-to-tray updates, and runtime state API used by React; duplicate `deque` import should be cleaned before final commit. | backend-runtime-state |
| `src/core/config/config_service.py` | backend/voice | commit | Adds persisted microphone metadata, overlay config, notifications flag, and a lock around config reads/writes so tray/voice/UI updates do not race config persistence; duplicate `json` import should be cleaned before final commit. | backend-runtime-state |
| `src/core/session/session_manager.py` | backend/voice | commit | Adds session lookup, remote session ID setter, normalized/manual/system title sources, first-message auto-title generation in English/Spanish, and runtime preview updates for user/Hermes messages. | backend-session-titles |
| `src/core/state/__init__.py` | backend/voice | commit | Exports the new `RuntimeStatus` dataclass required by runtime snapshots. | backend-runtime-state |
| `src/core/state/app_state.py` | backend/voice | commit | Introduces `RuntimeStatus` fields for connection, hotkey, microphone, overlay, visibility, and listening state; adds `patch_runtime()` and makes service patching notify listeners from a locked snapshot. | backend-runtime-state |
| `src/platform/tray/tray_manager.py` | backend/overlay-tray | commit | Replaces custom tkinter popup with pystray-native menu, status tooltip, microphone submenu, quick command submenu, recent activity submenu, pause/settings/restart/quit actions, and refreshed icon/menu state. | backend-overlay-tray |
| `src/platform/windows/desktop_app.py` | backend/overlay-tray | commit | Wires one shared `AppStateStore` through session manager/bridge, configures overlay callbacks for persisted position/visibility/dashboard/mic actions, registers voice loop with bridge, and adds tray microphone-change handling; duplicate `logging` import should be cleaned before final commit. | backend-overlay-tray |
| `src/platform/windows/overlay_service.py` | backend/overlay-tray | investigate | Major overlay rewrite adds always-visible pill, drag persistence, dashboard/mic/close affordances, visibility callbacks, and state animations, but `set_mode()` is a no-op while config/UI expose mini/full modes. | backend-overlay-tray |
| `src/platform/windows/voice_loop.py` | backend/voice | commit | Adds voice loop registration with bridge, microphone stream restart, same-hotkey cancel support, overlay detail/result states, runtime listening-state updates, and lower default silence RMS; duplicate `threading` import should be cleaned before final commit. | backend-runtime-state |
| `src/services/audio/audio_service.py` | backend/voice | commit | Extends `record_command()` with `cancel_check` so the voice loop can abort recording on repeated trigger hotkey without waiting for silence timeout. | backend-runtime-state |
| `src/storage/database.py` | backend/voice | commit | Adds migration 3 for `sessions.title_source` and initializes generic session names as system-owned so auto-titling can safely rename only default sessions. | backend-session-titles |
| `src/ui/app/package-lock.json` | frontend/contexts-css | commit | Lockfile reflects added `@fontsource/geist-sans` and `@fontsource/geist-mono` dependencies used by `main.tsx` and the redesigned typography. | frontend-design-system |
| `src/ui/app/package.json` | frontend/contexts-css | commit | Adds Geist font packages required by the new UI font imports. | frontend-design-system |
| `src/ui/app/src/App.tsx` | frontend/routing-pages | commit | Removes mini-mode inline dashboard, routes old pages out, and routes `/chat` and `/configure` to replacement pages; commit is safe only after replacement pages compile. | frontend-route-consolidation |
| `src/ui/app/src/components/Audio/AudioVisualizer.tsx` | frontend/routing-pages | commit | Deletion appears intentional: `Home.tsx` no longer imports it and the old mini-mode/audio-level visualizer was replaced by runtime/status cards. | frontend-route-consolidation |
| `src/ui/app/src/components/HotkeyRecorder.tsx` | frontend/components | commit | Internationalizes recorder labels/ARIA text and switches styling to shared CSS variables for the consolidated Configure page. | frontend-route-consolidation |
| `src/ui/app/src/components/Layout/Header.tsx` | frontend/components | investigate | Header styling was rewritten, but its title/eyebrow switch still includes old removed routes (`/sessions`, `/history`, `/voice`, `/shortcuts`, `/hermes`, `/tts`) that are no longer registered in `App.tsx`. | frontend-route-consolidation |
| `src/ui/app/src/components/Layout/PageHeader.tsx` | frontend/components | commit | Converts section header to the new display/eyebrow visual rhythm used by Settings, Configure, and Commands. | frontend-design-system |
| `src/ui/app/src/components/Layout/Sidebar.tsx` | frontend/routing-pages | commit | Replaces old many-page nav with the consolidated workspace nav (`/`, `/chat`, `/configure`, `/commands`) and adds health/pause/unread notification affordances. | frontend-route-consolidation |
| `src/ui/app/src/components/Layout/Titlebar.tsx` | frontend/components | commit | Replaces last-message titlebar with runtime-aware brand/status/window controls using `HermesContext.runtime`. | frontend-route-consolidation |
| `src/ui/app/src/contexts/HermesContext.tsx` | frontend/contexts-css | commit | Adds typed runtime snapshot, config/runtime polling, `hermes_config_updated` refresh handling, overlay config updates, healthChecked flag, and runtime-derived convenience fields used by settings/sidebar/titlebar/home. | frontend-runtime-contexts |
| `src/ui/app/src/contexts/LanguageContext.tsx` | frontend/contexts-css | commit | Adds translation keys for consolidated sessions/history/notifications/overlay/settings/voice/Hermes/shortcuts/TTS/system alerts and tightens language lookup types. | frontend-runtime-contexts |
| `src/ui/app/src/contexts/ThemeContext.tsx` | frontend/contexts-css | commit | Adds `data-theme="light"` for the new CSS variable theme while preserving `dark` class behavior. | frontend-design-system |
| `src/ui/app/src/contexts/ToastContext.tsx` | frontend/contexts-css | commit | Replaces transient-only toasts with persisted notification/toast items, unread count, warning type, read/delete/clear APIs, and a bell/dropdown-oriented data model. | frontend-runtime-contexts |
| `src/ui/app/src/index.css` | frontend/contexts-css | commit | Replaces the visual system with shared surfaces, typography, tokens, scrollbars, nav items, fields, buttons, and animation classes used across the redesigned UI. | frontend-design-system |
| `src/ui/app/src/main.tsx` | frontend/contexts-css | commit | Imports Geist Sans/Mono font packages required by the new CSS/font stack. | frontend-design-system |
| `src/ui/app/src/pages/Commands.tsx` | frontend/routing-pages | commit | Reworks command library/editor to the new `SectionHeader`, surface, field, and button components without changing the core custom-command CRUD/test flow. | frontend-route-consolidation |
| `src/ui/app/src/pages/History.tsx` | frontend/routing-pages | commit | Deletion appears intentional: old history view is replaced by `Chat.tsx` activity mode and App no longer routes `/history`. | frontend-route-consolidation |
| `src/ui/app/src/pages/Home.tsx` | frontend/routing-pages | commit | Replaces old mini/chat/audio-visualizer dashboard with a runtime-driven overview, status cards, recent interactions, and quick access panels. | frontend-route-consolidation |
| `src/ui/app/src/pages/Notifications.tsx` | frontend/routing-pages | commit | Deletion appears intentional: notification concepts moved into `ToastContext`/sidebar bell and overlay controls moved into Settings; App no longer routes `/notifications` as a main page. | frontend-route-consolidation |
| `src/ui/app/src/pages/Sessions.tsx` | frontend/routing-pages | commit | Deletion appears intentional: sessions and messages are consolidated into `Chat.tsx`; App no longer routes `/sessions`. | frontend-route-consolidation |
| `src/ui/app/src/pages/Settings.tsx` | frontend/routing-pages | commit | Rebuilds settings around backend connection, overlay toggles/mode, and app behavior using Hermes runtime overlay APIs. | frontend-route-consolidation |
| `src/ui/app/src/pages/Shortcuts.tsx` | frontend/routing-pages | commit | Deletion appears intentional: shortcut configuration moves to `Configure.tsx` with `HotkeyRecorder`; App no longer routes `/shortcuts`. | frontend-route-consolidation |
| `src/ui/app/src/pages/Voice.tsx` | frontend/routing-pages | commit | Deletion appears intentional: voice input, wake phrases, Hermes connection, and TTS settings are split between `Configure.tsx` and `Settings.tsx`; App no longer imports `Voice`/`Hermes`. | frontend-route-consolidation |
| `src/ui/app/src/services/api.ts` | frontend/contexts-css | commit | Adds runtime-state typing/API, rename/delete-session wrappers, and safer delete return behavior required by Chat/HermesContext. | frontend-runtime-contexts |
| `src/ui/app/tailwind.config.cjs` | frontend/contexts-css | commit | Extends Tailwind theme to match the new UI token/animation surface used by the redesign. | frontend-design-system |
| `src/ui/desktop/theme.py` | backend/overlay-tray | commit | Updates legacy desktop tkinter palette to the new dark/neutral/accent token set so fallback/native UI surfaces match the redesign. | backend-overlay-tray |
| `src/ui/overlays/status_overlay.py` | backend/overlay-tray | commit | Updates the older status overlay colors and adds state-colored indicator/border handling so it visually matches the new overlay direction. | backend-overlay-tray |
| `tests/test_windows_voice_desktop_support.py` | tests | investigate | Deleted test asserted old `hermes_voice_bridge.ui.desktop` palette/API client and release scripts; likely obsolete, but deleting it removes packaging/script regression coverage without replacement. | test-strategy |
| `.agents/skills/brandkit/SKILL.md` | local-tooling | discard | Project snapshot should not commit local agent skill content; it is unrelated to Hermes runtime and should be excluded or ignored. | local-tooling-discard |
| `.agents/skills/design-taste-frontend/SKILL.md` | local-tooling | discard | Local design skill material, not product source or documentation for Hermes. | local-tooling-discard |
| `.agents/skills/design-taste-frontend-v1/SKILL.md` | local-tooling | discard | Local design skill material, not product source or documentation for Hermes. | local-tooling-discard |
| `.agents/skills/full-output-enforcement/SKILL.md` | local-tooling | discard | Local agent behavior file; should not be part of application commits. | local-tooling-discard |
| `.agents/skills/gpt-taste/SKILL.md` | local-tooling | discard | Local UI-generation skill; unrelated to runtime/product source. | local-tooling-discard |
| `.agents/skills/high-end-visual-design/SKILL.md` | local-tooling | discard | Local design skill material; discard or ignore. | local-tooling-discard |
| `.agents/skills/image-to-code/SKILL.md` | local-tooling | discard | Local generation workflow file; not application code. | local-tooling-discard |
| `.agents/skills/imagegen-frontend-mobile/SKILL.md` | local-tooling | discard | Local generation workflow file; not application code. | local-tooling-discard |
| `.agents/skills/imagegen-frontend-web/SKILL.md` | local-tooling | discard | Local generation workflow file; not application code. | local-tooling-discard |
| `.agents/skills/industrial-brutalist-ui/SKILL.md` | local-tooling | discard | Local design skill material; discard or ignore. | local-tooling-discard |
| `.agents/skills/minimalist-ui/SKILL.md` | local-tooling | discard | Local design skill material; discard or ignore. | local-tooling-discard |
| `.agents/skills/redesign-existing-projects/SKILL.md` | local-tooling | discard | Local design skill material; discard or ignore. | local-tooling-discard |
| `.agents/skills/stitch-design-taste/DESIGN.md` | local-tooling | discard | Local design-system prompt artifact; not Hermes product documentation. | local-tooling-discard |
| `.agents/skills/stitch-design-taste/SKILL.md` | local-tooling | discard | Local design skill material; discard or ignore. | local-tooling-discard |
| `docs/PROJECT_STATUS.md` | docs | commit | Commit-worthy audit/status document describing current architecture, known risks, and next steps for stabilization. | docs-snapshot-audit |
| `docs/SNAPSHOT_INVENTORY.md` | docs | commit | Commit-worthy Phase 1.1a inventory that this classification depends on. | docs-snapshot-audit |
| `docs/SNAPSHOT_CLASSIFICATION.md` | docs | commit | Commit-worthy Phase 1.1b classification generated from the inspected snapshot. | docs-snapshot-audit |
| `scripts/HermesVoiceBridge.iss` | docs/scripts/packaging | investigate | Installer script is useful packaging work, but it references `{#MyAppName}` without defining `MyAppName`, points to `run_voice_desktop.ps1`, and adds an icon for missing `run_voice_tray.ps1`. | scripts-packaging |
| `scripts/run_voice.ps1` | docs/scripts/packaging | investigate | Launcher still runs `src\windows_hermes_voice.py`, while current status docs identify `src/platform/windows/desktop_app.py` as the modern desktop entrypoint. | scripts-packaging |
| `scripts/run_voice_desktop.ps1` | docs/scripts/packaging | investigate | Desktop launcher runs `src\windows_hermes_voice_desktop.py`, which may be historical rather than the current `src/platform/windows/desktop_app.py` entrypoint. | scripts-packaging |
| `scripts/run_voice_panel_web.ps1` | docs/scripts/packaging | investigate | Deprecation shim still opens `src\windows_hermes_voice_desktop.py`; confirm or update to the official desktop entrypoint before committing. | scripts-packaging |
| `scripts/run_voice_watchdog.ps1` | docs/scripts/packaging | investigate | Watchdog restarts `src\windows_hermes_voice.py`, not the current desktop app path, so it may supervise the wrong process. | scripts-packaging |
| `skills-lock.json` | local-tooling | discard | Local agent skill lock, apparently malformed from the inspected file start and unrelated to product source; discard or ignore with `.agents/`. | local-tooling-discard |
| `src/ui/app/build-output.txt` | build | discard | Captured Vite build log with ANSI output; should be deleted and/or ignored, not committed. | build-artifact-discard |
| `src/ui/app/src/components/Layout/SystemAlerts.tsx` | frontend/components | investigate | Potentially useful offline/recovery banner/toasts, but untracked file is not imported anywhere and inspected content uses hooks/`React.FC` without visible imports. | frontend-runtime-contexts |
| `src/ui/app/src/pages/Chat.tsx` | frontend/routing-pages | investigate | Replacement for sessions/history is functionally commit-worthy, but inspected file starts without visible `useState`/`useEffect` imports and uses `toast('...', 'success')` against the new `ToastContext` signature where the second argument is message unless a third type is passed. | frontend-route-consolidation |
| `src/ui/app/src/pages/Configure.tsx` | frontend/routing-pages | investigate | Replacement for voice/shortcuts/TTS is functionally commit-worthy, but inspected file starts without visible `useState`/`useEffect`/`useMemo` imports. | frontend-route-consolidation |

## Recommended commit sequence

Do not commit the snapshot in one piece. Resolve all `investigate` items first, then commit in this order:

1. **docs-snapshot-audit**
   - Files: `docs/PROJECT_STATUS.md`, `docs/SNAPSHOT_INVENTORY.md`, `docs/SNAPSHOT_CLASSIFICATION.md`
   - Suggested message: `docs: add stabilization snapshot audit`
   - Reason: documents the current snapshot before code changes are split.

2. **backend-session-titles**
   - Files: `src/core/session/session_manager.py`, `src/storage/database.py`
   - Suggested message: `feat: add session title sources`
   - Reason: database migration and session manager behavior are tightly coupled.

3. **backend-runtime-state**
   - Files: `src/core/config/config_service.py`, `src/core/state/__init__.py`, `src/core/state/app_state.py`, `src/api/webview_bridge.py`, `src/platform/windows/voice_loop.py`, `src/services/audio/audio_service.py`
   - Suggested message: `feat: sync runtime voice state`
   - Preconditions: remove duplicate imports and verify bridge/voice loop still import cleanly.

4. **backend-overlay-tray**
   - Files: `src/platform/tray/tray_manager.py`, `src/platform/windows/desktop_app.py`, `src/platform/windows/overlay_service.py`, `src/ui/desktop/theme.py`, `src/ui/overlays/status_overlay.py`
   - Suggested message: `feat: wire tray and overlay runtime`
   - Preconditions: decide whether to implement `OverlayService.set_mode()` or remove mini/full mode from UI/config before commit.

5. **frontend-design-system**
   - Files: `src/ui/app/package.json`, `src/ui/app/package-lock.json`, `src/ui/app/src/main.tsx`, `src/ui/app/src/index.css`, `src/ui/app/tailwind.config.cjs`, `src/ui/app/src/contexts/ThemeContext.tsx`, `src/ui/app/src/components/Layout/PageHeader.tsx`
   - Suggested message: `feat: add Hermes UI design system`
   - Reason: dependencies, font imports, Tailwind config, theme attribute, CSS tokens, and shared page header are one visual foundation.

6. **frontend-runtime-contexts**
   - Files: `src/ui/app/src/services/api.ts`, `src/ui/app/src/contexts/HermesContext.tsx`, `src/ui/app/src/contexts/ToastContext.tsx`, `src/ui/app/src/contexts/LanguageContext.tsx`, `src/ui/app/src/components/Layout/SystemAlerts.tsx` if retained/imported/fixed
   - Suggested message: `feat: expose runtime state in UI`
   - Preconditions: decide whether `SystemAlerts.tsx` is included in the app shell and fix any missing imports/signature mismatches.

7. **frontend-route-consolidation**
   - Files: `src/ui/app/src/App.tsx`, `src/ui/app/src/components/HotkeyRecorder.tsx`, `src/ui/app/src/components/Layout/Header.tsx`, `src/ui/app/src/components/Layout/Sidebar.tsx`, `src/ui/app/src/components/Layout/Titlebar.tsx`, `src/ui/app/src/pages/Home.tsx`, `src/ui/app/src/pages/Commands.tsx`, `src/ui/app/src/pages/Settings.tsx`, `src/ui/app/src/pages/Chat.tsx`, `src/ui/app/src/pages/Configure.tsx`, deleted `src/ui/app/src/components/Audio/AudioVisualizer.tsx`, deleted `History.tsx`, `Notifications.tsx`, `Sessions.tsx`, `Shortcuts.tsx`, `Voice.tsx`
   - Suggested message: `feat: consolidate dashboard routes`
   - Preconditions: fix/import `Chat.tsx` and `Configure.tsx`, remove stale old-route cases from Header or keep deliberate redirects, and verify frontend build.

8. **scripts-packaging**
   - Files: `scripts/HermesVoiceBridge.iss`, `scripts/run_voice.ps1`, `scripts/run_voice_desktop.ps1`, `scripts/run_voice_panel_web.ps1`, `scripts/run_voice_watchdog.ps1`
   - Suggested message: `chore: add Windows launcher scripts`
   - Preconditions: align all launchers/installer entries to the official desktop entrypoint, define `MyAppName`, and remove references to missing scripts.

9. **test-strategy**
   - Files: `tests/test_windows_voice_desktop_support.py` deletion, or a replacement test file if the old assertions are obsolete
   - Suggested message: `test: update desktop support coverage`
   - Preconditions: replace legacy package/script assertions with tests for the current desktop entrypoint/installer, or explicitly document why coverage is obsolete.

10. **repo-ignore-cleanup**
    - Files: `.gitignore`
    - Suggested message: `chore: clean local artifact ignores`
    - Preconditions: remove overbroad `test_*.py` ignore unless intentional; add ignores for `.agents/`, `skills-lock.json`, and `src/ui/app/build-output.txt` only if the project agrees these are local artifacts.

Discard outside the commit sequence:

- `.agents/**`
- `skills-lock.json`
- `src/ui/app/build-output.txt`

## Investigate items and exact questions

| item | question to resolve before committing |
|---|---|
| `.gitignore` | Should `test_*.py` really be ignored globally, or should only generated test/cache artifacts be ignored? Should `.agents/`, `skills-lock.json`, and `src/ui/app/build-output.txt` be added to ignores? |
| `src/platform/windows/overlay_service.py` | Is mini/full overlay mode a real feature for this snapshot? If yes, what should `set_mode()` do; if no, should UI/config stop exposing mode? |
| `src/ui/app/src/components/Layout/Header.tsx` | Should old route labels for `/sessions`, `/history`, `/voice`, `/shortcuts`, `/hermes`, and `/tts` be removed, redirected, or kept for backwards-compatible deep links? |
| `tests/test_windows_voice_desktop_support.py` | Was the deleted test obsolete because it targeted legacy `hermes_voice_bridge.ui.desktop`, or should equivalent coverage be rewritten for `src/platform/windows/desktop_app.py` and the new installer scripts? |
| `scripts/HermesVoiceBridge.iss` | What is the official installed app name and launcher? Define `MyAppName`, remove missing `run_voice_tray.ps1`, and confirm whether the installer should launch PowerShell scripts or a packaged executable. |
| `scripts/run_voice*.ps1` | Are `src\windows_hermes_voice.py` and `src\windows_hermes_voice_desktop.py` still valid entrypoints, or should every script use `src/platform/windows/desktop_app.py`? |
| `scripts/run_voice_watchdog.ps1` | Should watchdog supervise the console voice process, the desktop app, or be removed from the installer path? |
| `src/ui/app/src/components/Layout/SystemAlerts.tsx` | Should this component be mounted in `App.tsx`/layout? If retained, add required React hook/type imports and verify the offline banner condition is correct. |
| `src/ui/app/src/pages/Chat.tsx` | Add/verify React hook imports and fix toast calls to match the new `toast(title, message?, type?)` signature; confirm it fully replaces Sessions and History pages. |
| `src/ui/app/src/pages/Configure.tsx` | Add/verify React hook imports and confirm the saved shortcut/config API payloads match backend expectations. |
| `skills-lock.json` | Is this a required project lockfile or a local agent-tool lock? Inspected content appears local and not product-owned. |
| `.agents/**` | Are project-specific agent skills intentionally part of the repository? Current requirement says treat them as local tooling and discard/ignore. |
| `src/ui/app/build-output.txt` | Delete and/or ignore this generated build log; do not commit. |
