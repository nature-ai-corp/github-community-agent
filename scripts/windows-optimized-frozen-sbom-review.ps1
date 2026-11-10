# Read only on EXISTING optimized frozen onedir. Creates NEW audit evidence only.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$py = Join-Path $root '.venv\Scripts\python.exe'
$viewer = Join-Path $root '.venv\Scripts\pyi-archive_viewer.exe'
$bundle = Join-Path $root 'build\gc-agent-exclusion-candidate\dist\GitHubCommunityAgent'
$exe = Join-Path $bundle 'GitHubCommunityAgent.exe'
$parent = Join-Path $root 'build\release-audit\optimized-candidate-sbom-review'
if (-not (Test-Path -LiteralPath $py -PathType Leaf) -or
    -not (Test-Path -LiteralPath $viewer -PathType Leaf) -or
    -not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw 'Missing existing optimized candidate or Python archive tools; do not rebuild or install.'
}
if (Test-Path -LiteralPath $parent) {
    throw "Audit output already exists; preserve old evidence: $parent"
}
$manifest = Join-Path $parent 'actual-frozen-files.json'
$listing = Join-Path $parent 'pyinstaller-embedded-archive.txt'
$triage = Join-Path $parent 'embedded-module-candidates.json'
$report = Join-Path $parent 'component-provenance-review.json'
New-Item -ItemType Directory -Path $parent | Out-Null
& $py (Join-Path $root 'scripts\frozen_bundle_inventory.py') --bundle $bundle --output $manifest
if ($LASTEXITCODE -ne 0) { throw 'Actual optimized file audit failed' }
$lines = @(& $viewer --brief --recursive $exe 2>&1)
if ($LASTEXITCODE -ne 0 -or $lines.Count -eq 0) { throw 'Embedded module listing failed' }
$lines | Set-Content -LiteralPath $listing -Encoding UTF8
& $py (Join-Path $root 'scripts\frozen_archive_module_triage.py') --archive-list $listing --output $triage
if ($LASTEXITCODE -ne 0) { throw 'Optimized archive triage failed' }
& $py (Join-Path $root 'scripts\frozen_candidate_provenance_review.py') --manifest $manifest --triage $triage --output $report
if ($LASTEXITCODE -ne 0) { throw 'Frozen provenance candidate review failed' }
Write-Host 'Candidate EXE SHA256:' (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
Write-Host 'Optimized audit artifacts preserved at:' $parent
Write-Host 'This is not an approved SBOM or license/NOTICE compliance finding.'
