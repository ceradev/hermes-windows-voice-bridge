$ErrorActionPreference = 'Stop'
$scriptDir = $PSScriptRoot
$root = Split-Path -Parent $scriptDir
Set-Location $root

$startup = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$taskName = 'Hermes Voice Bridge'
$stateDir = Join-Path $root 'state'
$envFile = Join-Path $stateDir 'voice.env'
$runtimeState = Join-Path $stateDir 'runtime_state.json'
$sessionState = Join-Path $stateDir 'session.json'
$sessionSecrets = Join-Path $stateDir 'session.secrets'
$logDir = Join-Path $stateDir 'logs\HermesVoiceBridge'

$paths = @(
  (Join-Path $startup 'Hermes Voice Bridge.lnk'),
  (Join-Path (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs') 'Hermes Voice Bridge (Desktop).lnk'),
  (Join-Path (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs') 'Hermes Voice Panel (Web).lnk')
)

try {
  Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Out-Null
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task: $taskName"
} catch {
  Write-Host "Scheduled task not removed or not found: $($_.Exception.Message)"
}

foreach ($path in $paths) {
  if (Test-Path $path) {
    Remove-Item -Force $path
    Write-Host "Removed shortcut: $path"
  }
}

try {
  Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match 'windows_hermes_voice(_tray|_desktop|_panel_api)?\.py' } |
    ForEach-Object {
      if ($_.ProcessId) {
        taskkill /PID $_.ProcessId /T /F | Out-Null
        Write-Host "Killed PID $($_.ProcessId)"
      }
    }
} catch {
  Write-Host "Could not kill running bridge processes: $($_.Exception.Message)"
}

if (Test-Path $envFile) {
  Remove-Item -Force $envFile
  Write-Host "Removed env file: $envFile"
}

foreach ($statePath in @($runtimeState, $sessionState, $sessionSecrets)) {
  if (Test-Path $statePath) {
    Remove-Item -Force $statePath
    Write-Host "Removed state file: $statePath"
  }
}

if (Test-Path $logDir) {
  Remove-Item -Recurse -Force $logDir
  Write-Host "Removed logs: $logDir"
}

Write-Host 'Hermes Voice Bridge autostart cleaned.'
