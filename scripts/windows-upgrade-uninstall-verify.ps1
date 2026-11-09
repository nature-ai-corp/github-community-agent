# Read-only checks for GC Agent upgrade, uninstall and reinstall continuity.
# -Phase Baseline writes ONLY a verification manifest; it never backs up,
# erases, runs, upgrades or uninstalls the application.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Baseline','AfterUpgrade','AfterUninstall','AfterReinstall')]
    [string]$Phase
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$data = Join-Path $env:LOCALAPPDATA 'GitHubCommunityAgent'
$db = Join-Path $data 'work.sqlite3'
$settings = Join-Path $data 'settings.dpapi'
$installed = Join-Path $env:LOCALAPPDATA 'Programs\GitHub Community Agent\GitHubCommunityAgent.exe'
$manifest = Join-Path $HOME 'Documents\GC-Agent-Upgrade-Uninstall-Baseline.json'
$processes = @(Get-Process -Name 'GitHubCommunityAgent' -ErrorAction SilentlyContinue)
if ($processes.Count -gt 0) {
    throw "Close ALL GitHubCommunityAgent.exe processes before hash/upgrade/uninstall verification. No process was stopped."
}
foreach ($file in @($db,$settings)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Required original user data is missing; HALT: $file"
    }
}
try {
    $dbHash = (Get-FileHash -LiteralPath $db -Algorithm SHA256 -ErrorAction Stop).Hash
    $settingsHash = (Get-FileHash -LiteralPath $settings -Algorithm SHA256 -ErrorAction Stop).Hash
} catch {
    throw "User data files cannot be hashed. Close application processes; do not continue upgrade/uninstall."
}
$present = Test-Path -LiteralPath $installed -PathType Leaf
if ($Phase -eq 'AfterUninstall') {
    if ($present) { throw 'Installed EXE still exists; uninstall has not completed.' }
} else {
    if (-not $present) { throw "Installed GC Agent EXE missing for $Phase." }
}
if ($Phase -eq 'Baseline') {
    # Use the frozen runtime (not the Microsoft Store Python venv) to verify
    # the baseline Task count before freezing hashes.
    $diagnosticLines = @(& $installed --diagnostics)
    if ($LASTEXITCODE -ne 0) { throw 'Installed EXE diagnostic failed; cannot capture baseline.' }
    $taskLine = @($diagnosticLines | Where-Object { $_ -match '^Stored Task count \(including archived\): (\d+)
        throw "Baseline already exists; refusing to overwrite: $manifest"
    }
    $record = [ordered]@{
        product = 'GitHub Community Agent'
        windowsUser = [Environment]::UserName
        dataDirectory = $data
        workDatabaseSHA256 = $dbHash
        settingsSHA256 = $settingsHash
        originalTaskCount = $n
        createdUtc = [DateTime]::UtcNow.ToString('o')
    }
    $record | ConvertTo-Json | Set-Content -LiteralPath $manifest -Encoding UTF8 -NoNewline
    Write-Host "GC Agent upgrade/uninstall BASELINE created: $manifest"
    Write-Host "This is only a hash manifest, not a database backup."
    Write-Host "Keep the existing GC-Agent-PreInstall-Backup folder secure and unchanged."
    exit 0
}
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
    throw "Baseline manifest missing. Run -Phase Baseline BEFORE upgrading."
}
$prior = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
if ($prior.product -ne 'GitHub Community Agent' -or
    $prior.windowsUser -ne [Environment]::UserName -or
    $prior.dataDirectory -ne $data) {
    throw 'Baseline identity/path mismatch. No assumptions about data continuity are allowed.'
}
if ($prior.workDatabaseSHA256 -ne $dbHash -or $prior.settingsSHA256 -ne $settingsHash) {
    throw "GC Agent user data differs from baseline after $Phase; STOP. Investigate; do not restore, delete, upgrade, or uninstall further."
}
Write-Host "$Phase GC Agent user-data byte continuity PASS."
Write-Host "work.sqlite3 and settings.dpapi are SHA256-identical to the baseline."
if ($present) {
    & $installed --self-check
    if ($LASTEXITCODE -ne 0) { throw 'Installed EXE resource self-check failed.' }
    & $installed --diagnostics
    if ($LASTEXITCODE -ne 0) { throw 'Installed EXE data diagnostics failed.' }
}
Write-Host 'READ-ONLY VERIFICATION COMPLETE. No user data or installed files were changed.'
 })
    if ($taskLine.Count -ne 1) { throw 'Cannot reliably determine current Task count; refusing baseline.' }
    $n = [int](([string]$taskLine[0]).Split(':')[-1].Trim())
    if ($n -ne 10) { throw "Expected 10 retained Task records before testing; found $n. Refusing baseline." }
    if (Test-Path -LiteralPath $manifest) {
        throw "Baseline already exists; refusing to overwrite: $manifest"
    }
    $record = [ordered]@{
        product = 'GitHub Community Agent'
        windowsUser = [Environment]::UserName
        dataDirectory = $data
        workDatabaseSHA256 = $dbHash
        settingsSHA256 = $settingsHash
        createdUtc = [DateTime]::UtcNow.ToString('o')
    }
    $record | ConvertTo-Json | Set-Content -LiteralPath $manifest -Encoding UTF8 -NoNewline
    Write-Host "GC Agent upgrade/uninstall BASELINE created: $manifest"
    Write-Host "This is only a hash manifest, not a database backup."
    Write-Host "Keep the existing GC-Agent-PreInstall-Backup folder secure and unchanged."
    exit 0
}
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
    throw "Baseline manifest missing. Run -Phase Baseline BEFORE upgrading."
}
$prior = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
if ($prior.product -ne 'GitHub Community Agent' -or
    $prior.windowsUser -ne [Environment]::UserName -or
    $prior.dataDirectory -ne $data) {
    throw 'Baseline identity/path mismatch. No assumptions about data continuity are allowed.'
}
if ($prior.workDatabaseSHA256 -ne $dbHash -or $prior.settingsSHA256 -ne $settingsHash) {
    throw "GC Agent user data differs from baseline after $Phase; STOP. Investigate; do not restore, delete, upgrade, or uninstall further."
}
Write-Host "$Phase GC Agent user-data byte continuity PASS."
Write-Host "work.sqlite3 and settings.dpapi are SHA256-identical to the baseline."
if ($present) {
    & $installed --self-check
    if ($LASTEXITCODE -ne 0) { throw 'Installed EXE resource self-check failed.' }
    & $installed --diagnostics
    if ($LASTEXITCODE -ne 0) { throw 'Installed EXE data diagnostics failed.' }
}
Write-Host 'READ-ONLY VERIFICATION COMPLETE. No user data or installed files were changed.'
