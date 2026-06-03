$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$uiDir = Join-Path $root 'src\ui\app'
$desktopApp = Join-Path $root 'src\platform\windows\desktop_app.py'

if (-not (Test-Path $desktopApp)) {
  throw "Missing desktop launcher: $desktopApp (use branch origin/development)"
}

Write-Host "== Hermes desktop React =="
Write-Host "Repo: $root"
Write-Host ""

Write-Host "1/2 Building src\ui\app ..."
Set-Location $uiDir
if (-not (Test-Path 'node_modules')) {
  npm install
}
npm run build
if ($LASTEXITCODE -ne 0) { throw "UI build failed" }

Write-Host ""
Write-Host "2/2 Starting pywebview desktop ..."
Set-Location $root
python -B $desktopApp
