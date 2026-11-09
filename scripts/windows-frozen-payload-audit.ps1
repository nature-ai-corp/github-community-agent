# Read-only frozen PyInstaller payload audit. Does not build, install, sign,
# run the Work Center, access customer files or read API credentials.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$py = Join-Path $root '.venv\Scripts\python.exe'
$viewer = Join-Path $root '.venv\Scripts\pyi-archive_viewer.exe'
$bundle = Join-Path $root 'dist\GitHubCommunityAgent'
$exe = Join-Path $bundle 'GitHubCommunityAgent.exe'
$base = Join-Path $root 'build\release-audit'
$manifest = Join-Path $base 'frozen-bundle-files.json'
$archiveList = Join-Path $base 'frozen-embedded-archive.txt'
foreach ($f in @($py, $viewer, $exe)) {
    if (-not (Test-Path -LiteralPath $f -PathType Leaf)) {
        throw "Required audit input missing: $f"
    }
}
foreach ($f in @($manifest, $archiveList)) {
    if (Test-Path -LiteralPath $f) {
        throw "Existing audit output must be preserved; rename/move before rerun: $f"
    }
}
New-Item -ItemType Directory -Path $base -Force | Out-Null
& $py (Join-Path $root 'scripts\frozen_bundle_inventory.py') --bundle $bundle --output $manifest
if ($LASTEXITCODE -ne 0) { throw 'Frozen actual-file inventory failed.' }

# PyInstaller itself provides archive introspection. Inspect embedded PYZ
# module names recursively; do not extract anything or execute the app.
$archiveText = @(& $viewer --brief --recursive $exe 2>&1)
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller archive viewer failed; manifest remains for review.' }
if ($archiveText.Count -eq 0) { throw 'Archive viewer produced no contents.' }
$archiveText | Set-Content -LiteralPath $archiveList -Encoding UTF8
Write-Host "Embedded archive listing created: $archiveList"
Write-Host "Embedded archive output lines:" $archiveText.Count
Write-Host 'AUDIT STILL OPEN: archive member names do not identify every license or original package version.'
Write-Host 'No user files, installed software, credentials, Defender settings, or GitHub data were modified.'
