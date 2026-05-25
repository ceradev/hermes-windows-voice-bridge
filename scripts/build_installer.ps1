$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $compiler) {
  throw 'ISCC.exe not found. Install Inno Setup first: https://jrsoftware.org/isinfo.php'
}

& $compiler.Source "$root\scripts\HermesVoiceBridge.iss"
if ($LASTEXITCODE -ne 0) {
  throw "ISCC failed with exit code $LASTEXITCODE"
}

Write-Host 'Installer built under dist/ as HermesVoiceBridge-setup.exe'
