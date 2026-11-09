# GC Agent Windows installed-app acceptance, READ-ONLY.
# Only reports whether previously migrated data, archived record counts, and
# installed EXE resources are accessible. Does not read/print API keys.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$installed = Join-Path $env:LOCALAPPDATA 'Programs\GitHub Community Agent\GitHubCommunityAgent.exe'
$portable = Join-Path $root 'dist\GitHubCommunityAgent\GitHubCommunityAgent.exe'
$data = Join-Path $env:LOCALAPPDATA 'GitHubCommunityAgent'
$db = Join-Path $data 'work.sqlite3'
$keyFile = Join-Path $data 'settings.dpapi'
$backup = Join-Path $HOME 'Documents\GC-Agent-PreInstall-Backup'
$oldDb = Join-Path $backup 'work.sqlite3'
$oldKeyFile = Join-Path $backup 'settings.dpapi'

Write-Host "Checking installed GC Agent under current Windows user ($env:USERNAME)."
if (-not (Test-Path -LiteralPath $installed -PathType Leaf)) {
    throw "GC Agent installed executable not found: $installed"
}
if (-not (Test-Path -LiteralPath $db -PathType Leaf)) {
    throw "Existing GC Agent history database missing: $db"
}
if (-not (Test-Path -LiteralPath $keyFile -PathType Leaf)) {
    throw "Existing DPAPI settings file missing: $keyFile"
}

& $installed --self-check
if ($LASTEXITCODE -ne 0) { throw "Installed GC Agent executable self-check failed." }

Write-Host "Installed executable SHA256:" (Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash
if (Test-Path -LiteralPath $portable -PathType Leaf) {
    $left = (Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash
    $right = (Get-FileHash -LiteralPath $portable -Algorithm SHA256).Hash
    if ($left -ne $right) {
        throw "Installed EXE differs from the source bundle (unexpected)."
    }
    Write-Host "Installed EXE matches previously built onedir EXE: YES"
} else {
    Write-Host "Onedir EXE not present; byte comparison skipped."
}

& $installed --diagnostics
if ($LASTEXITCODE -ne 0) { throw "Installed GC Agent read-only diagnostics failed." }

# A running Work Center can keep SQLite open under Windows. Read-only
# diagnostics above are the live-data check. A raw file hash is only valid
# once all application processes have closed; do not force-close them and do
# not mistake an inaccessible hash for a corrupt database.
# Hash comparison also does not prove DPAPI key decryption.
$hashIncomplete = $false
foreach ($pair in @(@($db, $oldDb, "Work database"), @($keyFile, $oldKeyFile, "DPAPI settings"))) {
    $current = [string]$pair[0]
    $prior = [string]$pair[1]
    $label = [string]$pair[2]
    if (-not (Test-Path -LiteralPath $prior -PathType Leaf)) {
        Write-Host "$label backup missing; comparison SKIPPED."
        $hashIncomplete = $true
        continue
    }
    try {
        $h1 = (Get-FileHash -LiteralPath $current -Algorithm SHA256 -ErrorAction Stop).Hash
        $h2 = (Get-FileHash -LiteralPath $prior -Algorithm SHA256 -ErrorAction Stop).Hash
    } catch [System.Exception] {
        if ($label -eq "Work database") {
            Write-Warning "Work database SHA256 INCOMPLETE: file could be in use by running GC Agent. Stop the app and rerun this script for byte comparison."
            $hashIncomplete = $true
            continue
        }
        throw
    }
    if ($h1 -ne $h2) {
        Write-Warning "$label differs from pre-install backup. Changes may be legitimate; investigate before upgrade/uninstall."
        $hashIncomplete = $true
    } else {
        Write-Host "$label matches pre-install backup: YES"
    }
}

$signature = Get-AuthenticodeSignature -LiteralPath $installed
Write-Host "Installed EXE Authenticode status:" $signature.Status
Write-Host "Manual Archived Work and encrypted Test Connection checks are still REQUIRED."
Write-Host "No files were modified. No install, upgrade, or uninstall occurred."
if ($hashIncomplete) {
    Write-Warning "Installed-app data-file comparison INCOMPLETE. The EXE, settings presence, and Task count passed; repeat with all GC Agent processes stopped."
    exit 2
}
Write-Host "Installed-app read-only file comparison PASS (functional UI and DPAPI connection still require manual checks)."
