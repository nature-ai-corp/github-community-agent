# Runs the current Windows GC Agent pytest suite without reusing the user's
# existing pytest-of-* temp directory. Does not modify user Work records.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing local .venv Python. Install the project development dependencies first."
}
$runRoot = Join-Path $env:LOCALAPPDATA 'GitHubCommunityAgent\test-runs'
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
$run = Join-Path $runRoot ("pytest-" + [guid]::NewGuid().ToString('N'))
# pytest creates the basetemp directory itself and owns only this unique run.
Write-Host "Isolated pytest temp: $run"
Write-Host "Running all tests; a failure summary must not be hidden by stale pytest-current permissions."
Push-Location $root
try {
    & $python -m pytest -q -ra --tb=short --basetemp $run
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
if ($exitCode -ne 0) {
    Write-Host "GC Agent tests FAILED (exit $exitCode). Preserve this output to locate the real test failure."
    Write-Host "Diagnostic temporary files remain under: $run"
    exit $exitCode
}
Write-Host "GC Agent Windows regression PASS."
# Avoid forcibly deleting test-generated files while Windows may still hold
# handles to them. These are isolated under the GC Agent user's own test-runs.
exit 0
