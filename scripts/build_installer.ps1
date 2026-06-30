$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $compiler) {
  throw 'ISCC.exe not found. Install Inno Setup first: https://jrsoftware.org/isinfo.php'
}

$exePath = Join-Path $root 'dist\HermesVoiceBridge\HermesVoiceBridge.exe'
if (-not (Test-Path $exePath)) {
  Write-Host 'PyInstaller output not found. Running build.py first...'
  python build.py
  if ($LASTEXITCODE -ne 0) {
    throw "build.py failed with exit code $LASTEXITCODE"
  }
}

$issPath = Join-Path $root 'setup.iss'
if (-not (Test-Path $issPath)) {
  throw "Missing installer spec: $issPath"
}

& $compiler.Source $issPath
if ($LASTEXITCODE -ne 0) {
  throw "ISCC failed with exit code $LASTEXITCODE"
}

Write-Host 'Installer built. Check Output/ or dist/ for HermesVoiceBridge_Installer.exe'
