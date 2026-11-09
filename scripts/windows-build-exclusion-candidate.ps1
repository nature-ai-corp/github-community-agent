# Internal-only, isolated Windows PyInstaller exclusion experiment.
# Never touches the accepted dist/GitHubCommunityAgent or installed Work data.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$py = Join-Path $root '.venv\Scripts\python.exe'
$launcher = Join-Path $root 'scripts\gc_agent_launcher.py'
$baselineExe = Join-Path $root 'dist\GitHubCommunityAgent\GitHubCommunityAgent.exe'
$candidateRoot = Join-Path $root 'build\gc-agent-exclusion-candidate'
$candidateDist = Join-Path $candidateRoot 'dist'
$candidateWork = Join-Path $candidateRoot 'work'
$candidateSpec = Join-Path $candidateRoot 'spec'
$candidateExe = Join-Path $candidateDist 'GitHubCommunityAgent\GitHubCommunityAgent.exe'
if (-not (Test-Path -LiteralPath $py -PathType Leaf)) { throw "Missing project virtualenv Python" }
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw "Missing GC Agent launcher" }
if (-not (Test-Path -LiteralPath $baselineExe -PathType Leaf)) {
    throw "Accepted baseline executable missing. Refuse candidate comparison."
}
# Never overwrite or clean earlier experiment evidence. Existing accepted
# bundle lives outside this path, and is never passed as PyInstaller output.
if (Test-Path -LiteralPath $candidateRoot) {
    throw "Candidate directory exists: $candidateRoot. Preserve it; do not overwrite."
}
$baselineBefore = (Get-FileHash -LiteralPath $baselineExe -Algorithm SHA256).Hash
Push-Location $root
try {
    $args = @(
        '-m', 'PyInstaller',
        '--noconfirm', '--clean', '--onedir', '--console',
        '--name', 'GitHubCommunityAgent',
        '--paths', (Join-Path $root 'src'),
        '--collect-data', 'github_community_agent',
        '--exclude-module', 'pytest',
        '--exclude-module', '_pytest',
        '--exclude-module', 'pygments',
        '--distpath', $candidateDist,
        '--workpath', $candidateWork,
        '--specpath', $candidateSpec,
        $launcher
    )
    Write-Host 'Building UNSIGNED ISOLATED GC Agent candidate. No installer.'
    & $py @args
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller candidate build failed: $LASTEXITCODE" }
    if (-not (Test-Path -LiteralPath $candidateExe -PathType Leaf)) {
        throw "Candidate executable missing"
    }
    & $candidateExe --self-check
    if ($LASTEXITCODE -ne 0) { throw "Candidate self-check FAILED; reject candidate." }
    $baselineAfter = (Get-FileHash -LiteralPath $baselineExe -Algorithm SHA256).Hash
    if ($baselineBefore -ne $baselineAfter) {
        throw 'Accepted baseline executable hash CHANGED. Stop and investigate.'
    }
    $baselineFiles = @(Get-ChildItem -LiteralPath (Split-Path $baselineExe) -File -Recurse)
    $candidateFiles = @(Get-ChildItem -LiteralPath (Split-Path $candidateExe) -File -Recurse)
    $baselineBytes = ($baselineFiles | Measure-Object -Property Length -Sum).Sum
    $candidateBytes = ($candidateFiles | Measure-Object -Property Length -Sum).Sum
    Write-Host 'Baseline SHA256 unchanged:' $baselineAfter
    Write-Host 'Baseline files:' $baselineFiles.Count 'bytes:' $baselineBytes
    Write-Host 'Candidate files:' $candidateFiles.Count 'bytes:' $candidateBytes
    Write-Host 'Candidate path:' $candidateExe
    Write-Host 'ISOLATED CANDIDATE SELF-CHECK PASS. Not accepted as official release.'
    Write-Host 'Must verify embedded modules, negative security, five real V1 Work Types and separate install/data continuity before promotion.'
} finally {
    Pop-Location
}
