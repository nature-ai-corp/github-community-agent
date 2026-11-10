# Build the CLEAN GC Agent Windows onedir bundle that installers package.
#
# * Runtime: an official, PSF-signed CPython 3.13.17 x64 (OpenSSL 3.5 LTS),
#   extracted from python.org MSIs by an administrative extract (msiexec /a);
#   nothing is installed or registered system-wide.
# * Build venv: created fresh from that runtime, with ONLY the hash-locked
#   packaging/windows/build-requirements.txt (no pytest/Pygments/dev tools).
# * EXE gets Windows version metadata from github_community_agent.__version__.
# No signing, installer, release, network upload, or user-data access.
[CmdletBinding()]
param(
    [string]$Runtime = '',
    [string]$OutRoot = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Runtime) { $Runtime = Join-Path $root 'build\runtime-3.13.17\python' }
if (-not $OutRoot) { $OutRoot = Join-Path $root 'build\release-bundle' }
$Runtime = (Resolve-Path -LiteralPath $Runtime).Path
$expectedPython = '3.13.17'
$expectedOpenSsl = '^OpenSSL 3\.5\.\d+ '

# 1. Runtime provenance: official PSF signature on interpreter and OpenSSL.
foreach ($rel in 'python.exe', 'python313.dll', 'DLLs\libssl-3.dll', 'DLLs\libcrypto-3.dll', 'DLLs\_ssl.pyd') {
    $sig = Get-AuthenticodeSignature -LiteralPath (Join-Path $Runtime $rel)
    if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch '^CN=Python Software Foundation,') {
        throw "Runtime file is not validly signed by the Python Software Foundation: $rel"
    }
}
$basePy = Join-Path $Runtime 'python.exe'
$facts = & $basePy -I -c "import sys,ssl,tkinter;print(sys.version.split()[0]);print(ssl.OPENSSL_VERSION)"
if ($LASTEXITCODE -ne 0 -or $facts[0] -ne $expectedPython -or $facts[1] -notmatch $expectedOpenSsl) {
    throw "Runtime must be CPython $expectedPython with OpenSSL 3.5 LTS and tkinter; got: $facts"
}
Write-Host "Runtime: CPython $($facts[0]); $($facts[1]) (PSF-signed)"

if (Test-Path -LiteralPath $OutRoot) {
    throw "Output exists: $OutRoot. Move or rename it; nothing is overwritten."
}
New-Item -ItemType Directory -Path $OutRoot | Out-Null
$venv = Join-Path $OutRoot 'venv'
$py = Join-Path $venv 'Scripts\python.exe'
$dist = Join-Path $OutRoot 'dist'
$bundle = Join-Path $dist 'GitHubCommunityAgent'
$exe = Join-Path $bundle 'GitHubCommunityAgent.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
Push-Location $root
try {
    # 2. Fresh, hash-locked build venv.
    & $basePy -I -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
    & $py -m pip install --no-input --require-hashes --no-deps --only-binary ':all:' `
        -r (Join-Path $root 'packaging\windows\build-requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Hash-locked build dependency install failed' }
    & $py -m pip install --no-input --no-deps --no-build-isolation --editable $root
    if ($LASTEXITCODE -ne 0) { throw 'First-party package install failed' }
    $forbidden = & $py -c "import importlib.metadata as m;print(' '.join(sorted(d.metadata['Name'] for d in m.distributions() if d.metadata['Name'].lower() in {'pytest','pygments','colorama','iniconfig','pluggy'})))"
    if ($forbidden) { throw "Test-only distributions present in release venv: $forbidden" }

    # 3. EXE version metadata from the single version source.
    $versionFile = Join-Path $OutRoot 'version_info.txt'
    & $py (Join-Path $root 'scripts\windows_version_info.py') write --output $versionFile
    if ($LASTEXITCODE -ne 0) { throw 'Version file generation failed' }

    # 4. Freeze.
    $pyiArgs = @(
        '-m', 'PyInstaller',
        '--noconfirm', '--clean', '--onedir', '--console',
        '--name', 'GitHubCommunityAgent',
        '--paths', (Join-Path $root 'src'),
        '--collect-data', 'github_community_agent',
        '--exclude-module', 'pytest', '--exclude-module', '_pytest', '--exclude-module', 'pygments',
        '--version-file', $versionFile,
        '--distpath', $dist,
        '--workpath', (Join-Path $OutRoot 'work'),
        '--specpath', (Join-Path $OutRoot 'spec'),
        (Join-Path $root 'scripts\gc_agent_launcher.py')
    )
    & $py @pyiArgs
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed: $LASTEXITCODE" }
    & $exe --self-check
    if ($LASTEXITCODE -ne 0) { throw 'Frozen self-check failed' }

    # 5. Fail-closed verification of what was actually frozen.
    & $py (Join-Path $root 'scripts\windows_version_info.py') check --exe $exe
    if ($LASTEXITCODE -ne 0) { throw 'EXE version metadata check failed' }
    $listing = @(& (Join-Path $venv 'Scripts\pyi-archive_viewer.exe') --brief --recursive $exe 2>&1)
    if ($LASTEXITCODE -ne 0 -or $listing.Count -eq 0) { throw 'Archive inspection failed' }
    $listing | Set-Content -LiteralPath (Join-Path $OutRoot 'embedded-archive.txt') -Encoding UTF8
    $dev = @($listing | Where-Object { "$_" -match '(^|[\s/''"])(pytest|_pytest|pygments)(\.|[\s''",]|$)' })
    if ($dev.Count -ne 0) { throw "Test-only modules frozen into bundle: $($dev | Select-Object -First 5)" }
    Write-Host "GC Agent RELEASE bundle build PASS (unsigned): $exe"
    Write-Host "Build venv for notices/installer checks: $py"
} finally {
    Pop-Location
}
