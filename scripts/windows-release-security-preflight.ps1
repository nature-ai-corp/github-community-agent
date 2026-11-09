# Offline, read-only security preflight for the existing GC Agent V1 bundle.
# No API keys read, no application requests, no Windows Defender exclusions,
# and no signing/publishing. The verification output remains local.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$exe = Join-Path $root 'dist\GitHubCommunityAgent\GitHubCommunityAgent.exe'
$install = Join-Path $env:LOCALAPPDATA 'Programs\GitHub Community Agent\GitHubCommunityAgent.exe'
$license = Join-Path $root 'LICENSE'
$notice = Join-Path $root 'NOTICE'
$iss = Join-Path $root 'packaging\windows\gc-agent.iss'
$reportDir = Join-Path $root 'build\release-audit'

foreach ($file in @($python, $exe, $install, $license, $notice, $iss)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Release preflight input missing: $file"
    }
}
$issText = Get-Content -LiteralPath $iss -Raw
if ($issText -notmatch 'PrivilegesRequired=lowest' -or
    $issText -notmatch 'AppId=\{\{B728F255-29F8-438B-B2F7-E495DF0120E1\}' -or
    $issText -match '(?m)^\s*\[UninstallDelete\]\s*$') {
    throw 'Inno Setup identity/least-privilege/data-retention contract failed.'
}

& $exe --self-check
if ($LASTEXITCODE -ne 0) { throw 'Bundled EXE self-check failed.' }
& $install --self-check
if ($LASTEXITCODE -ne 0) { throw 'Installed EXE self-check failed.' }

$sourceHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
$installedHash = (Get-FileHash -LiteralPath $install -Algorithm SHA256).Hash
if ($sourceHash -ne $installedHash) {
    throw 'Installed program differs from the frozen EXE. Investigate before release.'
}
Write-Host 'Installed EXE equals built EXE SHA256: YES.'
$signature = Get-AuthenticodeSignature -LiteralPath $install
Write-Host "Installed Authenticode status:" $signature.Status
if ($signature.Status -ne 'Valid') {
    Write-Warning 'Unsigned or invalid Authenticode signature: RELEASE BLOCKER; no public distribution.'
}

# Windows security status is informative only. Never suppress/bypass AV.
$defender = Get-Command Get-MpComputerStatus -ErrorAction SilentlyContinue
if ($defender) {
    try {
        $status = Get-MpComputerStatus
        Write-Host "Defender AntivirusEnabled:" $status.AntivirusEnabled
        Write-Host "Defender RealTimeProtectionEnabled:" $status.RealTimeProtectionEnabled
    } catch {
        Write-Warning 'Defender status unavailable; record as incomplete, not PASS.'
    }
} else {
    Write-Host 'Get-MpComputerStatus unavailable; AV verification requires independent Windows security review.'
}
Write-Host 'No scan results claimed; this script does not disable, exclude or bypass security protection.'

New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
$inventory = Join-Path $reportDir 'python-environment-dependencies.json'
if (Test-Path -LiteralPath $inventory) {
    throw "Audit inventory already exists; move or rename it before rerun: $inventory"
}
& $python (Join-Path $root 'scripts\release_dependency_inventory.py') --output $inventory
if ($LASTEXITCODE -ne 0) { throw 'Dependency license metadata inventory failed.' }
Write-Host 'This candidate Python-environment inventory is not an SBOM for the frozen bundle.'
Write-Host 'RELEASE PREFLIGHT INCOMPLETE: signing, third-party notices, Windows security and exact frozen payload review still required.'
