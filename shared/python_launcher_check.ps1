$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\_python.ps1"
$repo = Split-Path $PSScriptRoot -Parent
$expected = Join-Path $repo '.venv\Scripts\python.exe'
$got = Resolve-PythonLauncher
if ($got.Command -ne $expected) { throw "Default launcher ignored the repository .venv: $($got.Command)" }
if (Test-PythonLauncher -Command $expected -RequiredModules @('halo_package_that_does_not_exist')) {
    throw 'A missing required dependency was accepted'
}
$failed = $false
try { Resolve-PythonLauncher -PythonCommand (Join-Path $repo 'absent interpreter.exe') | Out-Null }
catch { $failed = $_.Exception.Message -match 'supplied|override' }
if (-not $failed) { throw 'Invalid explicit override silently fell back' }
$explicit = Resolve-PythonLauncher -PythonCommand $expected -PythonArguments @('-I')
if ($explicit.Command -ne $expected -or $explicit.Arguments[0] -ne '-I') { throw 'Explicit launcher arguments were lost' }
Write-Host '[python_launcher_check] local .venv, dependency rejection, explicit override, spaced path: OK'
