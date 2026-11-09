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

# Hash comparison does not reveal user data, but also doesn't prove a key
# can be decrypted. Backups were taken immediately before installation.
foreach ($pair in @(@($db, $oldDb, "Work database"), @($keyFile, $oldKeyFile, "DPAPI settings"))) {
    $current = [string]$pair[0]
    $prior = [string]$pair[1]
    $label = [string]$pair[2]
    if (-not (Test-Path -LiteralPath $prior -PathType Leaf)) {
        Write-Host "$label backup missing; comparison SKIPPED."
        continue
    }
    $h1 = (Get-FileHash -LiteralPath $current -Algorithm SHA256).Hash
    $h2 = (Get-FileHash -LiteralPath $prior -Algorithm SHA256).Hash
    if ($h1 -ne $h2) {
        Write-Host "$label changed since pre-install backup; investigate before upgrade/uninstall."
    } else {
        Write-Host "$label matches pre-install backup: YES"
    }
}

$signature = Get-AuthenticodeSignature -LiteralPath $installed
Write-Host "Installed EXE Authenticode status:" $signature.Status
Write-Host "Installed-binary and data-file checks completed. Manual Archived Work and encrypted Test Connection checks are still REQUIRED."
Write-Host "No files were modified. No install, upgrade, or uninstall occurred."
