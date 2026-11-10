# READ-ONLY Authenticode verification for GC Agent Windows artifacts.
#
# Checks each target with BOTH Get-AuthenticodeSignature and
# `signtool verify /pa /all /v`:
#   * signature Valid under the default Authenticode (/pa) policy
#   * signer certificate subject contains -ExpectedSigner (CN=...)
#   * file digest is SHA-256 (no SHA-1 primary signature)
#   * the signature carries a trusted RFC 3161 timestamp (required because
#     Artifact Signing certificates are valid for only three days)
# For a release bundle folder (-BundleDir) it also checks that every
# third-party PE file still carries its ORIGINAL publisher signature
# (Python Software Foundation / Microsoft) and was NOT re-signed.
#
# Never signs, modifies, uploads or executes the files it checks.
# Exit code 0 = all checks PASS, 1 = at least one FAIL.
[CmdletBinding()]
param(
    # Files to check for OUR signature (e.g. the app EXE, setup EXE, unins000.exe).
    [string[]]$File = @(),
    # Onedir bundle: GitHubCommunityAgent.exe must carry OUR signature, all
    # other PE files their original third-party signature.
    [string]$BundleDir = '',
    # Substring required in the signer certificate subject.
    [string]$ExpectedSigner = 'CN=NATURE AI CORP',
    [string]$SignTool = '',
    [string]$Report = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $SignTool) {
    $kits = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
    $SignTool = Get-ChildItem -LiteralPath $kits -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.Directory.Name -eq 'x64' } | Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $SignTool -or -not (Test-Path -LiteralPath $SignTool)) {
    throw 'signtool.exe (Windows SDK, x64) not found; pass -SignTool.'
}
# Third-party publishers whose original signatures must remain untouched.
$thirdPartySigners = @('CN=Python Software Foundation', 'CN=Microsoft Windows Software Compatibility Publisher')

function Test-One([string]$Path, [string[]]$AllowedSigners) {
    $r = [ordered]@{ file = $Path; status = ''; signer = ''; sha256_digest = $false; timestamped = $false; signtool_verify = $false; pass = $false; problems = @() }
    $sig = Get-AuthenticodeSignature -LiteralPath $Path
    $r.status = "$($sig.Status)"
    if ($sig.SignerCertificate) { $r.signer = $sig.SignerCertificate.Subject }
    if ($sig.Status -ne 'Valid') { $r.problems += "Authenticode status $($sig.Status)" }
    if (-not ($AllowedSigners | Where-Object { $r.signer -like "*$_*" })) {
        $r.problems += "Signer '$($r.signer)' is not one of: $($AllowedSigners -join '; ')"
    }
    if ($sig.TimeStamperCertificate) { $r.timestamped = $true }
    # signtool reports an unsigned file on stderr; under Windows PowerShell 5.1
    # that must be captured as output, not raised as a terminating error.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = @(& $SignTool verify /pa /all /v $Path 2>&1 | ForEach-Object { "$_" })
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    $r.signtool_verify = ($code -eq 0)
    if (-not $r.signtool_verify) { $r.problems += 'signtool verify /pa /all failed' }
    $hashLines = @($out | Where-Object { $_ -match '^Hash of file \((\w+)\)' })
    $r.sha256_digest = ($hashLines.Count -gt 0) -and -not ($hashLines | Where-Object { $_ -notmatch '\(sha256\)' })
    if (-not $r.sha256_digest) { $r.problems += "File digest not exclusively SHA-256: $($hashLines -join ' | ')" }
    if (-not ($out | Where-Object { $_ -match '^The signature is timestamped' })) { $r.timestamped = $false }
    if (-not $r.timestamped) { $r.problems += 'No trusted timestamp' }
    $r.pass = ($r.problems.Count -eq 0)
    return [pscustomobject]$r
}

$results = @()
foreach ($f in $File) {
    $results += Test-One (Resolve-Path -LiteralPath $f).Path @($ExpectedSigner)
}
if ($BundleDir) {
    $bundle = (Resolve-Path -LiteralPath $BundleDir).Path
    $pe = Get-ChildItem -LiteralPath $bundle -Recurse -File | Where-Object { $_.Extension -in '.exe', '.dll', '.pyd', '.sys', '.ocx' }
    foreach ($p in $pe) {
        if ($p.Name -eq 'GitHubCommunityAgent.exe' -and $p.DirectoryName -eq $bundle) {
            $results += Test-One $p.FullName @($ExpectedSigner)
        } else {
            $results += Test-One $p.FullName $thirdPartySigners
        }
    }
}
if ($results.Count -eq 0) { throw 'Nothing to verify: pass -File and/or -BundleDir.' }

foreach ($r in $results) {
    $tag = if ($r.pass) { 'PASS' } else { 'FAIL' }
    Write-Host ("{0}  {1}  [{2}]" -f $tag, $r.file, ($r.signer -split ',')[0])
    foreach ($p in $r.problems) { Write-Host "        - $p" }
}
if ($Report) {
    $results | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Report -Encoding UTF8
}
$failed = @($results | Where-Object { -not $_.pass }).Count
Write-Host ("{0}/{1} files PASS; signtool: {2}" -f ($results.Count - $failed), $results.Count, $SignTool)
if ($failed) {
    Write-Host 'SIGNATURE VERIFICATION FAILED'
    exit 1
}
Write-Host 'SIGNATURE VERIFICATION PASS (read-only)'
exit 0
