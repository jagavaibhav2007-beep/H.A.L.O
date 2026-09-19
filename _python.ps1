# Shared Python 3.11+ launcher resolution, dot-sourced by dev.ps1 and verify.ps1.
# Keep free of script-specific state so both callers get identical behavior.
$script:HaloPythonRoot = $PSScriptRoot

function Test-PythonLauncher {
    param(
        [Parameter(Mandatory)]
        [string]$Command,

        [string[]]$PrefixArguments = @(),
        [string[]]$RequiredModules = @()
    )
    try {
        & $Command @PrefixArguments "$script:HaloPythonRoot\shared\python_probe.py" @RequiredModules 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Resolve-PythonLauncher {
    param(
        [string]$PythonCommand,
        [string[]]$PythonArguments = @()
    )

    if (-not $PythonCommand -and $env:HALO_PYTHON) {
        $PythonCommand = $env:HALO_PYTHON
        if ($env:HALO_PYTHON_ARGUMENTS) { $PythonArguments = @($env:HALO_PYTHON_ARGUMENTS | ConvertFrom-Json) }
    }
    if ($PythonCommand) {
        if (-not (Test-PythonLauncher -Command $PythonCommand -PrefixArguments $PythonArguments)) {
            throw "The supplied Python override cannot load Halo's required packages or Python 3.11+: $PythonCommand $($PythonArguments -join ' '). Install the locked dependencies (DEVELOPMENT.md); no fallback was attempted. Run shared/python_probe.py with this interpreter for package details."
        }
        return [pscustomobject]@{ Command = $PythonCommand; Arguments = @($PythonArguments) }
    }

    foreach ($local in @(".venv\Scripts\python.exe", '.venv/bin/python')) {
        $localPython = Join-Path $script:HaloPythonRoot $local
        if ((Test-Path -LiteralPath $localPython) -and (Test-PythonLauncher -Command $localPython)) {
            return [pscustomobject]@{ Command = $localPython; Arguments = @() }
        }
    }

    $pythonApplication = Get-Command python -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($pythonApplication -and (Test-PythonLauncher -Command $pythonApplication.Source)) {
        return [pscustomobject]@{ Command = $pythonApplication.Source; Arguments = @() }
    }

    $pyApplication = Get-Command py -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($pyApplication -and (Test-PythonLauncher -Command $pyApplication.Source -PrefixArguments @("-3"))) {
        return [pscustomobject]@{ Command = $pyApplication.Source; Arguments = @("-3") }
    }

    # ponytail: bundled-runtime scan covers agent/CI envs where python isn't on
    # PATH; local dev resolves at the python/py branches above.
    $runtimeRoots = @()
    if ($env:USERPROFILE) { $runtimeRoots += Join-Path $env:USERPROFILE ".cache\codex-runtimes" }
    if ($env:LOCALAPPDATA) { $runtimeRoots += Join-Path $env:LOCALAPPDATA "codex-runtimes" }
    foreach ($runtimeRoot in $runtimeRoots) {
        if (-not (Test-Path -LiteralPath $runtimeRoot -PathType Container)) { continue }
        $bundledPythons = Get-ChildItem -LiteralPath $runtimeRoot -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName "dependencies\python\python.exe" } |
            Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
        foreach ($bundledPython in $bundledPythons) {
            if (Test-PythonLauncher -Command $bundledPython) {
                return [pscustomobject]@{ Command = $bundledPython; Arguments = @() }
            }
        }
    }

    throw "No Python 3.11+ interpreter with Halo's required packages was found. Create .venv and install the locked dependencies in DEVELOPMENT.md, or set HALO_PYTHON to a prepared interpreter. Run shared/python_probe.py for package diagnostics."
}

function Invoke-Python {
    param(
        [Parameter(Mandatory)]
        [pscustomobject]$Launcher,

        [Parameter(Mandatory)]
        [string[]]$Arguments
    )
    & $Launcher.Command @($Launcher.Arguments) @Arguments
}
