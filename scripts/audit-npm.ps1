[CmdletBinding()]
param([int]$Attempts = 3)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $root "ui")
try {
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        $errorFile = Join-Path ([IO.Path]::GetTempPath()) "halo-npm-audit-$PID-$attempt.txt"
        $lines = & npm audit --audit-level=high --json 2>$errorFile
        $code = $LASTEXITCODE
        $raw = $lines -join "`n"
        $report = $null
        try { $report = $raw | ConvertFrom-Json -ErrorAction Stop } catch {}
        if ($report -and $report.metadata -and $report.metadata.vulnerabilities) {
            if ($code -eq 0) { Write-Host "[npm-audit] no high-severity vulnerability"; return }
            Write-Output $raw
            throw "npm audit found vulnerabilities"
        }
        if ($attempt -lt $Attempts) { Start-Sleep -Seconds $attempt }
    }
    throw "npm audit unavailable after $Attempts attempts (registry/infrastructure failure)"
} finally {
    Pop-Location
    Get-ChildItem ([IO.Path]::GetTempPath()) -Filter "halo-npm-audit-$PID-*.txt" -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}
