[CmdletBinding()]
param(
    [string]$OutputDirectory = ".tmp/sbom",
    [string]$BackendPath
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$output = [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
$requirements = Join-Path $output "python-requirements.txt"
New-Item -ItemType Directory -Force -Path $output | Out-Null

& uv export --locked --extra full --no-emit-project --output-file $requirements --quiet
if ($LASTEXITCODE -ne 0) { throw "uv export failed" }
& uvx --from cyclonedx-bom==7.3.1 cyclonedx-py requirements $requirements `
    --pyproject "$root/pyproject.toml" --spec-version 1.6 --output-reproducible `
    --output-format JSON --output-file "$output/python.cdx.json"
if ($LASTEXITCODE -ne 0) { throw "Python SBOM generation failed" }

Push-Location "$root/ui"
try {
    $npmBom = & npm sbom --sbom-format cyclonedx --sbom-type application
    if ($LASTEXITCODE -ne 0) { throw "npm SBOM generation failed" }
    Set-Content -LiteralPath "$output/npm.cdx.json" -Value $npmBom -Encoding utf8
} finally { Pop-Location }

& "$root/.venv/Scripts/python.exe" "$PSScriptRoot/cargo_sbom.py" `
    --manifest "$root/ui/src-tauri/Cargo.toml" --output "$output/cargo.cdx.json"
if ($LASTEXITCODE -ne 0) { throw "Cargo SBOM generation failed" }

$assetArgs = @("$PSScriptRoot/asset_sbom.py", "--output", "$output/assets.cdx.json")
if ($BackendPath) { $assetArgs += @("--backend", $BackendPath) }
& "$root/.venv/Scripts/python.exe" @assetArgs
if ($LASTEXITCODE -ne 0) { throw "Asset SBOM generation failed" }
& "$root/.venv/Scripts/python.exe" "$PSScriptRoot/check_sbom_policy.py" $output
if ($LASTEXITCODE -ne 0) { throw "SBOM license policy failed" }
Remove-Item -LiteralPath $requirements -Force
Write-Host "CycloneDX inventories written to $output"
