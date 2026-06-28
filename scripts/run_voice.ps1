$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'python not found in PATH'
}

python -B .\src\windows_hermes_voice.py
