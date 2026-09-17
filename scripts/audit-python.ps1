[CmdletBinding()]
param(
    [int]$Attempts = 3,
    [string]$PythonCommand = "python"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$requirements = Join-Path ([IO.Path]::GetTempPath()) "halo-audit-$PID.txt"
try {
    & uv export --locked --extra full --no-emit-project --output-file $requirements --quiet
    if ($LASTEXITCODE -ne 0) { throw "could not export the locked Python graph" }
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        $errorFile = "$requirements.err"
        $lines = & $PythonCommand -m pip_audit --vulnerability-service osv -r $requirements --disable-pip --no-deps --format json 2>$errorFile
        $code = $LASTEXITCODE
        $raw = $lines -join "`n"
        $report = $null
        try { $report = $raw | ConvertFrom-Json -ErrorAction Stop } catch {}
        if ($report) {
            if ($code -eq 0) { Write-Host "[pip-audit] no vulnerability reported"; return }
            Write-Output $raw
            throw "pip-audit found vulnerabilities"
        }
        if ($attempt -lt $Attempts) { Start-Sleep -Seconds $attempt }
    }
    throw "pip-audit unavailable after $Attempts attempts (OSV/infrastructure failure)"
} finally {
    Remove-Item -LiteralPath $requirements, "$requirements.err" -Force -ErrorAction SilentlyContinue
}
