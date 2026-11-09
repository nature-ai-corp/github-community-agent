# READ ONLY: identify actually-running GC Agent executable(s) and trial Task metadata.
# No token/DPAPI reads, no task result text, no database changes, no network.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$candidate = Join-Path $root 'build\gc-agent-exclusion-candidate\dist\GitHubCommunityAgent\GitHubCommunityAgent.exe'
$baseline = Join-Path $root 'dist\GitHubCommunityAgent\GitHubCommunityAgent.exe'
$trials = Join-Path $root 'build\gc-agent-e2e-trials'
$python = Join-Path $root '.venv\Scripts\python.exe'
Write-Host 'READ-ONLY GC Agent executable and trial-provenance inspection.'
Write-Host 'No settings, API keys, task content or existing user AppData will be read.'
foreach ($item in @(@('ACCEPTED_BASELINE', $baseline), @('EXCLUSION_CANDIDATE', $candidate))) {
    $name, $path = $item
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $resolved = (Resolve-Path -LiteralPath $path).Path
        $hash = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash
        Write-Host "$name : $resolved"
        Write-Host "$name SHA256 : $hash"
    } else {
        Write-Host "$name : not found"
    }
}
# Query running process executable paths from OS; no injection or termination.
try {
    $running = @(Get-CimInstance -ClassName Win32_Process -Filter "Name='GitHubCommunityAgent.exe'")
    if ($running.Count -eq 0) {
        Write-Host 'No running GitHubCommunityAgent.exe process found.'
    }
    foreach ($proc in $running) {
        $path = $proc.ExecutablePath
        if (-not $path) {
            Write-Host "PID $($proc.ProcessId) : executable path unavailable; cannot attribute."
            continue
        }
        $kind = 'OTHER_OR_INSTALLED'
        if ([string]::Equals($path, $candidate, [StringComparison]::OrdinalIgnoreCase)) {
            $kind = 'EXCLUSION_CANDIDATE'
        } elseif ([string]::Equals($path, $baseline, [StringComparison]::OrdinalIgnoreCase)) {
            $kind = 'ACCEPTED_BASELINE'
        }
        Write-Host "PID $($proc.ProcessId) : $kind : $path"
    }
} catch {
    Write-Host 'Windows process path inspection unavailable. Cannot attribute running EXE.'
}
# Only inspect the new test directory, not the existing real user's AppData.
if (-not (Test-Path -LiteralPath $trials -PathType Container)) {
    Write-Host 'No dedicated isolated-trial root found.'
    Write-Host 'Historical five Task exports cannot be attributed to the optimized candidate.'
    exit 0
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    Write-Host 'Python missing; cannot inspect trial Task event metadata.'
    exit 0
}
# No shell interpolation of repo text into Python code; fixed embedded snippet.
$code = @'
import os
from pathlib import Path
import sqlite3
import sys

base = Path(sys.argv[1]).resolve()
if base.is_symlink():
    raise SystemExit("Refusing linked trial-root inspection")
for trial in sorted(base.glob("trial-*")):
    if not trial.is_dir() or trial.is_symlink():
        continue
    db = trial / "GitHubCommunityAgent" / "work.sqlite3"
    if not db.is_file() or db.is_symlink():
        print("Trial:", trial.name, "- no regular task database")
        continue
    print("Trial:", trial.name, "database present")
    try:
        uri = db.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            total = conn.execute("SELECT count(*) FROM work").fetchone()[0]
            rows = conn.execute(
                "SELECT definition_id, status, count(*) FROM work "
                "GROUP BY definition_id, status ORDER BY definition_id, status"
            ).fetchall()
            events = conn.execute(
                "SELECT event, count(*) FROM work_events "
                "GROUP BY event ORDER BY event"
            ).fetchall()
        print("  Task total:", total)
        for definition, status, count in rows:
            print("  Type/status/count:", definition, status, count)
        for event, count in events:
            print("  Activity event/count:", event, count)
    except (sqlite3.Error, OSError) as exc:
        print("  Read-only metadata inspection unavailable:", type(exc).__name__)
'@
$code | & $python - $trials
if ($LASTEXITCODE -ne 0) { throw 'Read-only isolated-trial metadata inspection failed.' }
Write-Host 'WARNING: process path + trial metadata alone cannot prove historical Task-to-process linkage.'
Write-Host 'Do not claim optimized-candidate E2E until an attested trial launch is linked to execution.'
