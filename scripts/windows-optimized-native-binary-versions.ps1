# Read-only, create-only Windows file-version evidence for optimized frozen binaries.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$report = Join-Path $root 'build\release-audit\optimized-candidate-sbom-review\native-binary-fileversion-evidence.json'
$bundle = Join-Path $root 'build\gc-agent-exclusion-candidate\dist\GitHubCommunityAgent'
$manifest = Join-Path $root 'build\release-audit\optimized-candidate-sbom-review\actual-frozen-files.json'
if (Test-Path -LiteralPath $report) { throw "Preserve existing audit evidence: $report" }
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) { throw 'Run frozen SBOM review first' }
$data = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
$items = @($data.files | Where-Object { $_.kind -eq 'binary' })
if ($items.Count -ne 26) { throw "Unexpected compiled binary count $($items.Count). Review instead of trusting mapping." }
$output = @()
foreach ($item in $items) {
    $relative = $item.path
    if (-not $relative -or $relative -match '(?i)\.\.|^[\\/]') { throw 'Unsafe binary relative path' }
    $full = Join-Path $bundle ($relative -replace '/', '\')
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "Frozen binary missing: $relative" }
    $hash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash
    if ($hash -ne $item.sha256) { throw "Frozen manifest hash mismatch: $relative" }
    $version = (Get-Item -LiteralPath $full).VersionInfo
    $output += [pscustomobject]@{
        path = $relative
        sha256 = $hash
        file_version_string = $version.FileVersion
        product_version_string = $version.ProductVersion
        company_name_unverified = $version.CompanyName
        product_name_unverified = $version.ProductName
        file_description_unverified = $version.FileDescription
        file_version_metadata_is_provenance = $false
        license_text_verified = $false
    }
}
$result = [ordered]@{
    scope = 'Windows VERSIONINFO on actual 26 hashed frozen binaries; names self-declared and NOT third-party license or origin proof'
    generated_utc = [DateTime]::UtcNow.ToString('o')
    binaries = $output
    actual_binary_count = $output.Count
    third_party_licenses_verified = $false
    release_approved = $false
}
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $report -Encoding UTF8
Write-Host 'Frozen binary Windows VERSIONINFO report:' $report
Write-Host 'Hashes matched prior actual bundle manifest:' $output.Count
Write-Host 'VERSIONINFO names are self-reported; legal origins and licenses still need verification.'
