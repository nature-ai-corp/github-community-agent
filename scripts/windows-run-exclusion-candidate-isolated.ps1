# Launch the already-built UNSIGNED exclusion candidate with a NEW isolated GC data root.
# This is a live, user-operated UI acceptance trial, not an automated E2E PASS.
# Never install, copy DPAPI settings, or touch the real user's GC Agent AppData.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$candidate = Join-Path $root 'build\gc-agent-exclusion-candidate\dist\GitHubCommunityAgent\GitHubCommunityAgent.exe'
$trialParent = Join-Path $root 'build\gc-agent-e2e-trials'
$originalLocalAppData = $env:LOCALAPPDATA
if (-not $originalLocalAppData) { throw 'LOCALAPPDATA is not set; refusing live trial.' }
if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
    throw 'Isolated candidate EXE does not exist; run the candidate build first.'
}
# Do not read, copy, modify or re-encrypt the existing user's settings/DB.
$realData = Join-Path $originalLocalAppData 'GitHubCommunityAgent'
$trial = Join-Path $trialParent ('trial-' + [guid]::NewGuid().ToString('N'))
$trialData = Join-Path $trial 'GitHubCommunityAgent'
if ([string]::Equals($realData, $trialData, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unsafe user data root collision.'
}
New-Item -ItemType Directory -Path $trial -Force | Out-Null
if (-not (Test-Path -LiteralPath $trial -PathType Container)) {
    throw 'Failed to create independent trial root.'
}
Write-Host 'GC Agent ISOLATED candidate UI trial. No release or installer.'
Write-Host 'Existing user data root (WILL NOT BE USED):' $realData
Write-Host 'NEW empty trial data root:' $trialData
Write-Host 'Provide ONLY test-authorized model/GitHub read credentials inside trial Settings UI.'
Write-Host 'Candidate Work Center will open in your browser. Complete the five real V1 tasks manually.'
Write-Host 'Check local draft review: Mark reviewed must NOT post anything to GitHub.'
Write-Host 'Close the trial application using Ctrl+C when finished.'
Write-Host 'Trial evidence/data is retained for inspection. Do not paste secrets into logs.'
$env:LOCALAPPDATA = $trial
try {
    & $candidate --self-check
    if ($LASTEXITCODE -ne 0) { throw 'Candidate self-check failed; no UI trial started.' }
    & $candidate
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { throw "Candidate UI exited with code $exitCode" }
} finally {
    $env:LOCALAPPDATA = $originalLocalAppData
    Write-Host 'LOCALAPPDATA restored for this PowerShell session.'
    Write-Host 'Trial data retained at:' $trialData
    Write-Host 'Original installed application and user records were not targeted.'
}
