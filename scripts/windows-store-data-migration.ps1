# Opt-in migration from Windows Store (MSIX) Python virtual AppData to the
# normal GC Agent user-local directory used by an independent Windows EXE.
# Dry-run is the default. -Apply is required to modify the destination.
# The original Store Python files are never modified or deleted.
[CmdletBinding()]
param([switch]$Apply)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$exe = Join-Path $root 'dist\GitHubCommunityAgent\GitHubCommunityAgent.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Repository Python venv not found."
}
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Independent EXE not found; build it before migration."
}
if (-not $env:LOCALAPPDATA) {
    throw "LOCALAPPDATA is not defined."
}

# Python is run from the existing venv backed by the Store Python runtime.
# Resolve the *physical* path while still in its MSIX virtualized context.
$probe = @'
import json, os, sqlite3
from github_community_agent.work_center import data_directory
root = data_directory()
db = root / "work.sqlite3"
if not db.is_file():
    raise RuntimeError("Source Store Python work.sqlite3 not found")
with sqlite3.connect(db.as_uri()+"?mode=ro", uri=True) as con:
    count = con.execute("SELECT COUNT(*) FROM work").fetchone()[0]
print(json.dumps({
    "source": os.path.realpath(root),
    "count": count,
    "settings": (root / "settings.dpapi").is_file()
}))
'@
$raw = ($probe | & $python -)
if ($LASTEXITCODE -ne 0) { throw 'Source store Python database probe failed.' }
$info = $raw | ConvertFrom-Json
$source = [System.IO.Path]::GetFullPath([string]$info.source)
$target = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'GitHubCommunityAgent'))
if ([string]::Equals($source, $target, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Source and destination resolve to the same physical directory. No migration should run."
}
$localRoot = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd('\')
$expected = $localRoot + '\Packages\'
if (-not $source.StartsWith($expected, [StringComparison]::OrdinalIgnoreCase) -or
    -not $source.Contains('\LocalCache\Local\') -or
    -not $source.EndsWith('\GitHubCommunityAgent', [StringComparison]::OrdinalIgnoreCase)) {
    throw "Source was not proved to be the Windows Store MSIX redirected GC Agent directory: $source"
}
$sourceDb = Join-Path $source 'work.sqlite3'
$sourceSettings = Join-Path $source 'settings.dpapi'
$targetDb = Join-Path $target 'work.sqlite3'
$targetSettings = Join-Path $target 'settings.dpapi'
if (-not (Test-Path -LiteralPath $sourceDb -PathType Leaf)) {
    throw 'Physical source work.sqlite3 is not visible to PowerShell.'
}
if (-not (Test-Path -LiteralPath $sourceSettings -PathType Leaf)) {
    throw 'Physical Store Python settings.dpapi is absent.'
}
if ([int]$info.count -lt 1) { throw 'Source has no Tasks; refusing migration.' }
if (-not [bool]$info.settings) { throw 'Store Python did not find encrypted settings.' }
if (Test-Path -LiteralPath $targetSettings) {
    throw 'Target already has encrypted settings; refusing to overwrite or merge.'
}
if ((Test-Path -LiteralPath ($sourceDb + '-wal')) -or
    (Test-Path -LiteralPath ($sourceDb + '-shm'))) {
    throw 'Source SQLite WAL/SHM exists. Close both apps; do not raw-copy a live database.'
}
if ((Test-Path -LiteralPath ($targetDb + '-wal')) -or
    (Test-Path -LiteralPath ($targetDb + '-shm'))) {
    throw 'Target SQLite WAL/SHM exists. Close the independent EXE before migrating.'
}

# Only an already-empty independent database can be replaced.
if (Test-Path -LiteralPath $targetDb) {
    & $exe --diagnostics | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Frozen EXE diagnostics failed.' }
    # The independent EXE must inspect the target, not the Store Python view.
    $counts = @(& $exe --diagnostics)
    $countLine = $counts | Where-Object { $_ -match '^Stored Task count \(including archived\): (\d+)$' }
    if (@($countLine).Count -ne 1) { throw 'Cannot prove target database is empty.' }
    $count = [int](([string]$countLine).Split(':')[-1].Trim())
    if ($count -ne 0) { throw "Target database already contains $count Tasks; refusing overwrite." }
}

Write-Host "Source physical directory: $source"
Write-Host "Source Tasks: $($info.count)"
Write-Host "Source encrypted settings present: True"
Write-Host "Destination directory: $target"
Write-Host "Destination: absent or an independently verified empty database with no settings"
if (-not $Apply) {
    Write-Host 'DRY RUN PASS. No files changed.'
    Write-Host 'For explicit migration, close both GC Agent processes and run again with -Apply.'
    exit 0
}

# Explicit and guarded one-time migration. Preserve original Store data.
# Stage copies, verify content hashes, then rename only the known empty target.
$backupDir = Join-Path $target ('migration-backup-' + [guid]::NewGuid().ToString('N'))
$stagingDir = Join-Path $target ('migration-stage-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $target | Out-Null
New-Item -ItemType Directory -Path $backupDir | Out-Null
New-Item -ItemType Directory -Path $stagingDir | Out-Null
$stageDb = Join-Path $stagingDir 'work.sqlite3'
$stageSettings = Join-Path $stagingDir 'settings.dpapi'
Copy-Item -LiteralPath $sourceDb -Destination $stageDb -ErrorAction Stop
Copy-Item -LiteralPath $sourceSettings -Destination $stageSettings -ErrorAction Stop
foreach ($pair in @(@($sourceDb, $stageDb), @($sourceSettings, $stageSettings))) {
    $left = (Get-FileHash -LiteralPath $pair[0] -Algorithm SHA256).Hash
    $right = (Get-FileHash -LiteralPath $pair[1] -Algorithm SHA256).Hash
    if ($left -ne $right) { throw "Staging copy hash mismatch. No target migration performed." }
}
# Backup the independent EXE's empty DB (if one was created during testing).
if (Test-Path -LiteralPath $targetDb) {
    Move-Item -LiteralPath $targetDb -Destination (Join-Path $backupDir 'work.sqlite3') -ErrorAction Stop
}
Move-Item -LiteralPath $stageDb -Destination $targetDb -ErrorAction Stop
Move-Item -LiteralPath $stageSettings -Destination $targetSettings -ErrorAction Stop

Write-Host 'MIGRATION FILE COPY COMPLETE. Original Store data was preserved.'
Write-Host "Empty independent database backup folder: $backupDir"
& $exe --diagnostics
if ($LASTEXITCODE -ne 0) { throw 'Post-migration frozen diagnostic failed.' }
Write-Host 'Verify the stored Task count above equals the original source count.'
Write-Host 'Only then start the independent Work Center EXE and confirm My Work and Archived Work.'
