# Build an unsigned, internal-test-only Windows onedir app bundle.
# No release/tag/upload/signing; no existing user's AppData is touched.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing Windows repo venv: $python. Run python -m venv .venv first."
}
$dist = Join-Path $root 'dist\GitHubCommunityAgent'
$entry = Join-Path $root 'scripts\gc_agent_launcher.py'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $root
try {
    & $python -c "import PyInstaller; print('PyInstaller', PyInstaller.__version__)"
    if ($LASTEXITCODE -ne 0) {
        throw 'PyInstaller not installed. Run: .\.venv\Scripts\python.exe -m pip install -e ".[build]"'
    }
    # Remove ONLY this product's previous build output; never touch Work DB,
    # the original Worker, or unrelated projects/artifacts.
    if (Test-Path -LiteralPath $dist) {
        throw "Existing product build found: $dist. Move or rename it before building; no overwrite."
    }
    $args = @(
        '-m', 'PyInstaller',
        '--noconfirm', '--clean', '--onedir', '--console',
        '--name', 'GitHubCommunityAgent',
        '--paths', (Join-Path $root 'src'),
        '--collect-data', 'github_community_agent',
        '--distpath', (Join-Path $root 'dist'),
        '--workpath', (Join-Path $root 'build\gc-agent-pyi'),
        '--specpath', (Join-Path $root 'build\gc-agent-pyi-spec'),
        $entry
    )
    & $python @args
    if ($LASTEXITCODE -ne 0) { throw "GC Agent PyInstaller build failed: $LASTEXITCODE" }
    $exe = Join-Path $dist 'GitHubCommunityAgent.exe'
    if (-not (Test-Path -LiteralPath $exe)) { throw "Missing frozen executable: $exe" }
    & $exe --self-check
    if ($LASTEXITCODE -ne 0) { throw "Frozen executable self-check failed: $LASTEXITCODE" }
    Write-Host "GC Agent unsigned Windows ONEDIR build PASS: $exe"
    Write-Host "INTERNAL TEST ONLY. No signing, installer, or release was performed."
} finally {
    Pop-Location
}
