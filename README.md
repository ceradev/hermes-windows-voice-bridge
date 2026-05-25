# Hermes voice bridge on Windows

This folder contains a first-pass Windows client for your VPS-hosted Hermes.

## What it does

- Listens for a wake phrase like `hermes`, `oye hermes`, or `hey hermes`
- Or listens for a hotkey like `Ctrl+Shift+H`
- Records the next command
- Transcribes it locally
- Sends the text to the Hermes webhook on your VPS
- Hermes answers in Telegram
- If `HERMES_WEBHOOK_SYNC=1`, the Windows bridge also reads the final Hermes reply aloud locally

## Important

This is an MVP wake-word bridge, not a trained commercial wake-word engine.
It works by using local speech-to-text on short audio windows to detect the wake phrase.
Good enough to start. We can upgrade it later to Porcupine/OpenWakeWord if you want stricter always-on detection.

## VPS side already done

- Webhook enabled
- Route `voice` created
- Gateway running
- Test POST accepted

## Windows setup

1. Install Python 3.11+ on Windows.
2. Open PowerShell in this folder.
3. Install deps:

```powershell
pip install -r requirements.txt
```

4. Set env vars:

```powershell
$env:HERMES_WEBHOOK_URL='http://YOUR_VPS_IP:8644/webhooks/voice'
$env:HERMES_WEBHOOK_SECRET='PASTE_THE_SECRET_FROM_VPS'
$env:HERMES_STT_MODEL='base'
$env:HERMES_STT_LANGUAGE='es'
$env:HERMES_HOTKEY='ctrl+shift+h'
$env:HERMES_FEEDBACK_MODE='both'   # off | beep | voice | both
$env:HERMES_FEEDBACK_VOICE=''      # optional: hint for SAPI voice name
$env:HERMES_WEBHOOK_SYNC='1'       # wait for Hermes final response and read it aloud
$env:HERMES_WEBHOOK_TIMEOUT='120'  # seconds; bump if replies are slow
$env:HERMES_AUTH_REFRESH_URL=''    # optional: backend endpoint that exchanges refresh_token for fresh session tokens
$env:HERMES_AUTH_TIMEOUT='10'      # seconds for auth refresh callouts
```

If you use `scripts/install_autostart.ps1`, it will also save the current
`HERMES_*` values into `state/voice.env` so the tray can start with the same
settings after login.

5. Run:

```powershell
python .\src\windows_hermes_voice.py
```

Or just double-click / run:

```powershell
.\scripts\run_voice.ps1
```

If you want auto-restart on crash, use the watchdog instead:

```powershell
.\scripts\run_voice_watchdog.ps1
```

If you want the native-ish tray mode with Pause / Resume / Restart / Exit:

- Exit also removes the tray/startup shortcuts and the scheduled task.

```powershell
.\scripts\run_voice_tray.ps1
```

If you want the desktop app:

- native window: `src/windows_hermes_voice_desktop.py`
- local control API: `src/windows_hermes_voice_panel_api.py`
- live status + live logs in a normal Windows app
- microphone selection, wake phrases, hotkey, feedback, timing config
- visual shortcut editor, persistent-session toggle, and compact runtime overlays
- desktop launcher: `scripts/run_voice_desktop.ps1` or `python -B .\\src\\windows_hermes_voice_desktop.py`

```powershell
python -B .\\src\\windows_hermes_voice_desktop.py
```

The browser panel path is now legacy. Use the desktop app instead.
The desktop app now includes session storage controls plus shortcut/overlay polish; `panel-web/` should no longer be treated as the primary UX surface.

## Uninstall / clean remove

If you want it gone for real, run:

```powershell
.\scripts\uninstall_voice_bridge.ps1
```

That removes:
- scheduled task
- Startup shortcut
- Start Menu shortcut
- `voice.env`
- `runtime_state.json`
- session persistence files (`session.json`, `session.secrets`)
- bridge logs
- running bridge/tray processes

Then delete the folder if you want.

- If audio is too sensitive, raise `HERMES_WAKE_ENERGY` a bit.
- If it stops too early, raise `HERMES_SILENCE_RMS` or `SILENCE_TIMEOUT_SECONDS` in the script.
- For a more polished feel, set `HERMES_FEEDBACK_MODE=both` to get a short beep + spoken confirmation on wake / send.
- If your mic is not the default device, run:

```powershell
python .\src\windows_hermes_voice.py --list-devices
```

Then set `HERMES_MIC_DEVICE` to the device index.

## Next step: auto-start

To make it start with Windows, run:

```powershell
.\scripts\install_autostart.ps1
```

That creates a logon Scheduled Task plus a Startup shortcut so the tray launches hidden even if one startup path is flaky.

To build a shareable Windows bundle from the repo contents, run:

```powershell
.\scripts\package_voice_bridge.ps1
```

That writes `dist/HermesVoiceBridge-windows.zip` with the native app files and excludes the deprecated web panel surface.

To build a Windows installer with Inno Setup, run:

```powershell
.\scripts\build_installer.ps1
```

That expects `ISCC.exe` in PATH and produces `dist/HermesVoiceBridge-setup.exe`.

If you want the desktop app, use the Start Menu shortcut or the tray menu to open it on demand.

If the tray icon disappears after reboot, check `state/voice.env` first.
Missing `HERMES_WEBHOOK_URL` or `HERMES_WEBHOOK_SECRET` will make the
bridge exit before the tray stays visible.

## Next upgrade

If you want, next step is:
- replace this approximate wake phrase detector with a proper wake-word engine
- tune the spoken response voice for a more native English / Spanish split
