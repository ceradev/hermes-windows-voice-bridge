$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host 'Hermes Voice Panel (Web) is deprecated. Opening the native desktop app instead.'
python -B .\src\windows_hermes_voice_desktop.py
