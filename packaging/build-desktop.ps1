# Official unsigned Windows artifact route. No installation or publication.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
& "$PSScriptRoot/build-backend.ps1"
Push-Location (Join-Path (Split-Path -Parent $PSScriptRoot) "ui")
try {
    & npm run tauri -- build --config src-tauri/tauri.release.conf.json
    if ($LASTEXITCODE -ne 0) { throw "Desktop build failed" }
} finally {
    Pop-Location
}
