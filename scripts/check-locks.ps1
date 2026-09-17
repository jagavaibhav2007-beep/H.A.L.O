[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

& uv lock --check --directory $root
if ($LASTEXITCODE -ne 0) { throw "uv.lock is stale" }

$npmLock = Join-Path $root "ui/package-lock.json"
$before = (Get-FileHash -LiteralPath $npmLock -Algorithm SHA256).Hash
Push-Location (Join-Path $root "ui")
try { & npm install --package-lock-only --ignore-scripts --no-audit }
finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "npm lock validation failed" }
$after = (Get-FileHash -LiteralPath $npmLock -Algorithm SHA256).Hash
if ($before -ne $after) { throw "ui/package-lock.json was stale and has been rewritten" }

Push-Location (Join-Path $root "ui/src-tauri")
try { & cargo metadata --locked --offline --format-version 1 | Out-Null }
finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw "Cargo.lock is stale or unavailable offline" }
Write-Host "[locks] Python, npm, and Cargo locks are synchronized"
