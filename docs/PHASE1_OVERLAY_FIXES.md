# Phase 1 Overlay Fixes

Updated: 2026-06-28

## Fixed

- Implemented `OverlayService.set_mode()` for `mini` and `full` modes and persisted mode changes through `ConfigService` via the desktop runtime callback.
- Changed `OverlayService.hide()` so it fully withdraws the Tkinter overlay instead of leaving a shrunken pill visible.
- Implemented `OverlayService.show_result(request_text, response_text)` so the overlay stores and displays the latest request/response text.
- Added expanded overlay behavior through hover in `full` mode or click/pin from the pill, showing state, latest request, and latest response without opening the dashboard.
- Wired voice-loop `listening`, `thinking`, and `speaking` states into overlay display and runtime state snapshots.
- Added runtime request/response fields so overlay text state stays consistent with `AppStateStore`.
- Removed the dead `src/platform/windows/overlay_app.py` module.
