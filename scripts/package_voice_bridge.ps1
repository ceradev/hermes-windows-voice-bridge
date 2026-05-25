$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$distDir = Join-Path $root 'dist'
$stageDir = Join-Path $distDir 'HermesVoiceBridge'
$zipPath = Join-Path $distDir 'HermesVoiceBridge-windows.zip'

if (Test-Path $stageDir) { Remove-Item -Recurse -Force $stageDir }
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
New-Item -ItemType Directory -Force -Path $stageDir | Out-Null

$include = @(
  'src',
  'scripts',
  'requirements.txt',
  'README.md'
)

foreach ($entry in $include) {
  $source = Join-Path $root $entry
  if (Test-Path $source) {
    Copy-Item -Recurse -Force $source $stageDir
  }
}

$stateDir = Join-Path $stageDir 'state'
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stateDir 'logs\HermesVoiceBridge') | Out-Null

$legacyPanel = Join-Path $stageDir 'panel-web'
if (Test-Path $legacyPanel) {
  Remove-Item -Recurse -Force $legacyPanel
}

Compress-Archive -Path (Join-Path $stageDir '*') -DestinationPath $zipPath -Force
Write-Host "Created package: $zipPath"
