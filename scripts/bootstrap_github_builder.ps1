# Bootstrap standalone GitHub Builder repository from GC V1.
# Usage (Windows PowerShell):
#   .\scripts\bootstrap_github_builder.ps1
#   .\scripts\bootstrap_github_builder.ps1 -Execute
# Default is a preview: no local or GitHub writes occur.
[CmdletBinding()]
param(
    [switch]$Execute,
    [string]$Destination = (Join-Path $HOME "projects\github-builder"),
    [string]$TargetRepo = "nature-ai-corp/github-builder"
)
$ErrorActionPreference = "Stop"
$source = "https://github.com/nature-ai-corp/github-community-agent.git"
$v1Sha = "e0dc19db3874e56e29070b1ed03b313739151e3d"
Write-Host "Source: $source @ $v1Sha (V1 main baseline)"
Write-Host "Target: $TargetRepo (PRIVATE)"
Write-Host "Local:  $Destination"
Write-Host "Action: clone V1 tracked files, start independent git history, push private bootstrap"
Write-Warning "This creates a technical clone: its Community product naming and workflows remain until a separate GB refactor."
if (-not $Execute) {
    Write-Host "DRY RUN ONLY. Run again with -Execute after reviewing the plan."
    return
}
foreach ($bin in @("git", "gh")) {
    if (-not (Get-Command $bin -ErrorAction SilentlyContinue)) {
        throw "$bin is required and was not found on PATH."
    }
}
gh auth status | Out-Host
if ($LASTEXITCODE -ne 0) { throw "GitHub CLI authentication is required." }
if (Test-Path -LiteralPath $Destination) { throw "Destination already exists. Refusing to overwrite: $Destination" }
gh repo view $TargetRepo --json nameWithOwner *> $null
if ($LASTEXITCODE -eq 0) { throw "Target GitHub repository already exists: $TargetRepo" }
$parent = Split-Path -Parent $Destination
if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
$createdLocal = $false
try {
    git clone --no-checkout $source $Destination
    if ($LASTEXITCODE -ne 0) { throw "Clone failed." }
    $createdLocal = $true
    Push-Location $Destination
    try {
        git checkout --detach $v1Sha
        if ($LASTEXITCODE -ne 0) { throw "V1 source commit unavailable." }
        $actual = (git rev-parse HEAD).Trim()
        if ($actual -ne $v1Sha) { throw "V1 source SHA mismatch." }
        $v2Paths = @(git ls-files | Where-Object { $_ -match "(?i)(^|/)(promotion|promoter)(/|\.|$)" })
        if ($v2Paths.Count -gt 0) {
            Write-Warning "V1 baseline contains files with Promotion-like names; inspect before using: $($v2Paths -join ', ')"
        }
        # Only tracked files from the committed V1 baseline are in the working tree.
        Remove-Item -Recurse -Force ".git"
        git init -b main
        if ($LASTEXITCODE -ne 0) { throw "Git init failed." }
        @"
# GitHub Builder — Bootstrap Foundation

This repository was cloned from the committed **GitHub Community Agent V1** source
(`$v1Sha`) as the technical starting point for **GitHub Builder**.

**Not a ready-to-run GitHub Builder product.** Community-specific code, UI labels,
package names, installers, secrets configuration and workflows require refactoring
before any GB release. V2 Promotion was deliberately not copied.

See the original LICENSE and NOTICE for attribution and licensing.
"@ | Set-Content -Encoding utf8 -Path "GB_BOOTSTRAP.md"
        git add -A
        git commit -m "chore: bootstrap GitHub Builder from GC Agent V1 baseline"
        if ($LASTEXITCODE -ne 0) { throw "Commit failed. Configure git user.name and user.email." }
        gh repo create $TargetRepo --private --source . --remote origin --push
        if ($LASTEXITCODE -ne 0) { throw "GitHub repository creation or push failed. Inspect local directory; do not blindly retry." }
        gh repo view $TargetRepo --json nameWithOwner,visibility,url | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Failed to verify newly created repository." }
        Write-Host "BOOTSTRAP COMPLETE; do not release before GB refactor and Windows acceptance tests."
    } finally { Pop-Location }
} catch {
    Write-Warning "Stopped safely: $($_.Exception.Message)"
    if ($createdLocal) { Write-Warning "Local clone retained for inspection at $Destination" }
    throw
}
