# Build locally; this neither signs nor publishes anything.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    if ($PSVersionTable.PSEdition -eq "Core" -and -not $IsWindows) {
        throw "The current desktop artifact is Windows x64 only."
    }
    & uv sync --locked --extra full --group build --python 3.12
    if ($LASTEXITCODE -ne 0) { throw "Locked full/build environment could not be installed" }
    & "$repo/.venv/Scripts/python.exe" -m PyInstaller --noconfirm --clean "$PSScriptRoot/halo-backend.spec"
    if ($LASTEXITCODE -ne 0) { throw "Backend freeze failed" }
    $triple = (& rustc --print host-tuple).Trim()
    if ($LASTEXITCODE -ne 0 -or $triple -ne "x86_64-pc-windows-msvc") {
        throw "Expected x86_64-pc-windows-msvc host; cross-freezing is unsupported"
    }
    $destination = Join-Path $repo "ui/src-tauri/binaries"
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -LiteralPath "$repo/dist/halo-backend.exe" -Destination "$destination/halo-backend-$triple.exe"
    Write-Host "Built full-profile backend: binaries/halo-backend-$triple.exe"
} finally {
    Pop-Location
}
