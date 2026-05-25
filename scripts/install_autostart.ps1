$ErrorActionPreference = 'Stop'
$scriptDir = $PSScriptRoot
$root = Split-Path -Parent $scriptDir
Set-Location $root

$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$shortcutPath = Join-Path $startup 'Hermes Voice Bridge.lnk'
$taskName = 'Hermes Voice Bridge'

$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
  throw 'pythonw.exe not found in PATH. Install Python with the Windows launcher or add pythonw.exe to PATH.'
}

$stateDir = Join-Path $root 'state'
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$trayScript = Join-Path $root 'src\windows_hermes_voice_tray.py'
$desktopLauncher = Join-Path $scriptDir 'run_voice_desktop.ps1'
$envFile = Join-Path $stateDir 'voice.env'

$persistKeys = @(
  'HERMES_WEBHOOK_URL',
  'HERMES_WEBHOOK_SECRET',
  'HERMES_STT_MODEL',
  'HERMES_STT_LANGUAGE',
  'HERMES_WAKE_PHRASES',
  'HERMES_WAKE_ENERGY',
  'HERMES_SILENCE_RMS',
  'HERMES_MIC_DEVICE',
  'HERMES_HOTKEY',
  'HERMES_FEEDBACK_MODE',
  'HERMES_FEEDBACK_VOICE',
  'HERMES_WEBHOOK_SYNC',
  'HERMES_WEBHOOK_TIMEOUT',
  'HERMES_PERSIST_SESSION',
  'HERMES_OVERLAY_ENABLED',
  'HERMES_NOTIFICATIONS_ENABLED',
  'HERMES_TTS_ENABLED',
  'HERMES_AUTH_REFRESH_URL',
  'HERMES_AUTH_TIMEOUT',
  'HERMES_AUTH_HEADER',
  'HERMES_AUTH_SECRET',
  'HERMES_AUTH_SECRET_HEADER'
)

$lines = @()
foreach ($key in $persistKeys) {
  $value = [Environment]::GetEnvironmentVariable($key, 'User')
  if ([string]::IsNullOrWhiteSpace($value)) {
    $value = [Environment]::GetEnvironmentVariable($key, 'Process')
  }
  if (-not [string]::IsNullOrWhiteSpace($value)) {
    $lines += "$key=$value"
  }
}

if ($lines.Count -gt 0) {
  Set-Content -Path $envFile -Value $lines -Encoding UTF8
  Write-Host "Wrote env file: $envFile"
} else {
  Write-Host "No HERMES_* values found in User/Process env; leaving $envFile unchanged"
}

$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
  try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
    Write-Host "Removed existing scheduled task: $taskName"
  } catch {
    Write-Host "Could not remove existing scheduled task cleanly: $($_.Exception.Message)"
  }
}

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "-B `"$trayScript`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = 'PT30S'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Launch Hermes Voice Bridge tray at logon.' -Force | Out-Null
Write-Host "Created scheduled task: $taskName"

$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($shortcutPath)
$sc.TargetPath = $pythonw
$sc.Arguments = "-B `"$trayScript`""
$sc.WorkingDirectory = $root
$sc.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,137"
$sc.Save()

$programs = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$legacyWebShortcut = Join-Path $programs 'Hermes Voice Panel (Web).lnk'
if (Test-Path $legacyWebShortcut) {
  Remove-Item -Force $legacyWebShortcut
  Write-Host "Removed legacy shortcut: $legacyWebShortcut"
}
$desktopShortcutPath = Join-Path $programs 'Hermes Voice Bridge (Desktop).lnk'
$sc2 = $wsh.CreateShortcut($desktopShortcutPath)
$sc2.TargetPath = $pythonw
$sc2.Arguments = "`"$desktopLauncher`""
$sc2.WorkingDirectory = $root
$sc2.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,167"
$sc2.Save()

Write-Host "Created startup shortcut: $shortcutPath"
Write-Host "Created desktop shortcut: $desktopShortcutPath"
