$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'python not found in PATH'
}

$logDir = Join-Path $root 'state\logs\HermesVoiceBridge'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir 'watchdog.log'

function Write-Log([string]$message) {
  $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  Add-Content -Path $logFile -Value "[$ts] $message"
}

Write-Log 'watchdog started'

$restartDelaySeconds = 5
$backoffSeconds = 5
$maxBackoffSeconds = 60

while ($true) {
  Write-Log 'starting windows_hermes_voice.py'
  try {
    & python -B .\src\windows_hermes_voice.py
    $exitCode = $LASTEXITCODE
    Write-Log "process exited with code $exitCode"
  } catch {
    Write-Log ("process crashed: " + $_.Exception.Message)
  }

  Start-Sleep -Seconds $backoffSeconds
  if ($backoffSeconds -lt $maxBackoffSeconds) {
    $backoffSeconds = [Math]::Min($backoffSeconds * 2, $maxBackoffSeconds)
  }
}
