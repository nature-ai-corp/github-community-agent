# Compile a per-user, unsigned internal GC Agent installer from an existing
# validated onedir bundle. No network download, signing, release or installation.
# -UpgradeTrial creates a distinct installer for installer-mechanics testing only.
[CmdletBinding()]
param(
    [switch]$UpgradeTrial,
    # Onedir to package. Default: the clean release bundle produced by
    # scripts/windows-build-release-bundle.ps1. The committed third-party
    # license package must match it exactly.
    [string]$BundleDir = '',
    # Interpreter of the venv that built BundleDir (needed for provenance checks).
    [string]$BuildPython = '',
    # Output folder (default dist\installer); existing installers are never overwritten.
    [string]$OutputDir = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $BundleDir) { $BundleDir = Join-Path $root 'build\release-bundle\dist\GitHubCommunityAgent' }
if (-not $OutputDir) { $OutputDir = Join-Path $root 'dist\installer' }
if (-not $BuildPython) { $BuildPython = Join-Path $root 'build\release-bundle\venv\Scripts\python.exe' }
$BundleDir = (Resolve-Path -LiteralPath $BundleDir).Path
$exe = Join-Path $BundleDir 'GitHubCommunityAgent.exe'
if (-not (Test-Path -LiteralPath $exe)) {
    throw "No GC Agent ONEDIR EXE found. First run scripts/windows-build-release-bundle.ps1."
}
& $exe --self-check
if ($LASTEXITCODE -ne 0) { throw 'Frozen application self-check failed; installer not built.' }
# Fail closed: third-party LICENSE/NOTICE/SBOM must describe THIS exact bundle,
# and the EXE version metadata must equal the package version.
$python = (Resolve-Path -LiteralPath $BuildPython).Path
& $python (Join-Path $root 'scripts\third_party_notices.py') check --bundle $BundleDir
if ($LASTEXITCODE -ne 0) {
    throw 'Third-party license package does not match this bundle; installer not built.'
}
& $python (Join-Path $root 'scripts\windows_version_info.py') check --exe $exe
if ($LASTEXITCODE -ne 0) { throw 'EXE version metadata does not match the package version.' }
$appVersion = (& $python (Join-Path $root 'scripts\windows_version_info.py') inno | Select-Object -Last 1).Trim()
$potential = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
)
if (${env:ProgramFiles(x86)}) {
    $potential += (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe')
}
$compiler = $potential | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compiler) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $compiler = $cmd.Source }
}
if (-not $compiler) {
    throw 'Inno Setup 6 ISCC.exe not found. Install Inno Setup from its official source, then retry.'
}
if ($UpgradeTrial) {
    $out = Join-Path $OutputDir 'GitHubCommunityAgent-UpgradeTrial-Unsigned.exe'
    $iss = Join-Path $root 'packaging\windows\gc-agent-upgrade-trial.iss'
    Write-Host 'INTERNAL UPGRADE TRIAL: same bundled application, different installer version 0.0.1-devtrial.'
    Write-Host 'This validates installation mechanics ONLY, not an application feature/code upgrade.'
} else {
    $out = Join-Path $OutputDir 'GitHubCommunityAgent-InternalTest-Unsigned.exe'
    $iss = Join-Path $root 'packaging\windows\gc-agent.iss'
}
if (Test-Path -LiteralPath $out) {
    throw "Existing test installer must not be overwritten: $out. Move or rename it first."
}
if ($UpgradeTrial) {
    & $compiler "/DBundleDir=$BundleDir" "/O$OutputDir" $iss
} else {
    & $compiler "/DBundleDir=$BundleDir" "/DAppVersion=$appVersion" "/O$OutputDir" $iss
}
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed: $LASTEXITCODE" }
if (-not (Test-Path -LiteralPath $out)) {
    throw "Inno Setup reported success but output not found: $out"
}
$hash = (Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash
Write-Host "GC Agent unsigned internal Windows installer build PASS."
Write-Host "File: $out"
Write-Host "SHA256: $hash"
Write-Host 'No installer execution, signing, or publication performed.'
