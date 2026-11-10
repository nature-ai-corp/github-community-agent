# Azure Artifact Signing for GC Agent's OWN executables (prepared, owner-run).
#
# DEFAULT = PLAN MODE: validates prerequisites and prints the exact SignTool
# command. Nothing is signed, no network call is made, no file is modified.
# -Execute performs real signing and must only be used by the owner after
# signing has been authorized (see docs/WINDOWS_CODE_SIGNING_READINESS.md).
#
# Signs ONLY:  <bundle>\GitHubCommunityAgent.exe  (step 1, before packaging)
# The setup EXE and its uninstaller are signed by Inno Setup during
# compilation (scripts/windows-build-installer.ps1 -SignMetadata ...).
# Third-party binaries (PSF/Microsoft-signed) are NEVER re-signed; the script
# refuses any target that already carries a signature.
#
# SHA-256 file digest, RFC 3161 SHA-256 timestamp from Microsoft's Artifact
# Signing TSA (Artifact Signing certificates are valid for only 3 days, so
# the timestamp is mandatory). Authentication: DefaultAzureCredential via the
# dlib (locally: `az login` as an identity holding "Artifact Signing
# Certificate Profile Signer" on the certificate profile). No secret is read,
# stored or printed by this script.
[CmdletBinding()]
param(
    [string]$BundleDir = '',
    # metadata.json: Endpoint, CodeSigningAccountName, CertificateProfileName
    # (+ optional CorrelationId, ExcludeCredentials). Must contain no secrets.
    [Parameter(Mandatory = $true)][string]$Metadata,
    # x64 Azure.CodeSigning.Dlib.dll from Artifact Signing Client Tools.
    [Parameter(Mandatory = $true)][string]$Dlib,
    [string]$SignTool = '',
    [string]$TimestampUrl = 'http://timestamp.acs.microsoft.com',
    [string]$ExpectedSigner = 'CN=NATURE AI CORP',
    [switch]$Execute
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $BundleDir) { $BundleDir = Join-Path $root 'build\release-bundle\dist\GitHubCommunityAgent' }
$bundle = (Resolve-Path -LiteralPath $BundleDir).Path
$target = Join-Path $bundle 'GitHubCommunityAgent.exe'

# --- prerequisites (read-only) ---
if (-not $SignTool) {
    $kits = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
    $SignTool = Get-ChildItem -LiteralPath $kits -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.Directory.Name -eq 'x64' } | Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $SignTool -or -not (Test-Path -LiteralPath $SignTool)) { throw 'x64 signtool.exe not found; pass -SignTool.' }
if ($SignTool -match '\\10\.0\.20348\.') { throw 'Windows SDK 20348 SignTool is not supported by the Artifact Signing dlib.' }
if ($SignTool -notmatch '\\x64\\') { throw 'Use the x64 signtool.exe with the x64 dlib (architectures must match).' }
$Dlib = (Resolve-Path -LiteralPath $Dlib).Path
if ((Split-Path $Dlib -Leaf) -ne 'Azure.CodeSigning.Dlib.dll') { throw "Unexpected dlib file name: $Dlib" }
if ($Dlib -notmatch '\\x64\\') { throw 'Use the x64 Azure.CodeSigning.Dlib.dll (must match x64 signtool).' }
$Metadata = (Resolve-Path -LiteralPath $Metadata).Path
$meta = Get-Content -LiteralPath $Metadata -Raw | ConvertFrom-Json
foreach ($k in 'Endpoint', 'CodeSigningAccountName', 'CertificateProfileName') {
    if (-not ($meta.PSObject.Properties.Name -contains $k) -or -not $meta.$k) { throw "metadata.json missing $k" }
}
if ($meta.Endpoint -notmatch '^https://[a-z0-9]+\.codesigning\.azure\.net/?$') {
    throw "metadata.json Endpoint is not an Artifact Signing regional endpoint: $($meta.Endpoint)"
}
$secretLike = @($meta.PSObject.Properties.Name | Where-Object { $_ -match '(?i)secret|password|key|token' })
if ($secretLike.Count) { throw "metadata.json must not contain credentials: $($secretLike -join ', ')" }

# Fail closed on target state: exists, is the GC Agent build, UNSIGNED.
if (-not (Test-Path -LiteralPath $target)) { throw "Target not found: $target" }
$pre = Get-AuthenticodeSignature -LiteralPath $target
if ($pre.Status -ne 'NotSigned') { throw "Refusing: target already has a signature ($($pre.Status)). Never re-sign." }
& $target --self-check
if ($LASTEXITCODE -ne 0) { throw 'Unsigned EXE self-check failed; not signing.' }

$signArgs = @('sign', '/v', '/fd', 'SHA256', '/tr', $TimestampUrl, '/td', 'SHA256',
    '/dlib', $Dlib, '/dmdf', $Metadata, $target)
Write-Host 'Artifact Signing plan:'
Write-Host "  account  : $($meta.CodeSigningAccountName)  profile: $($meta.CertificateProfileName)  endpoint: $($meta.Endpoint)"
Write-Host "  target   : $target  (SHA256 before: $((Get-FileHash -LiteralPath $target).Hash))"
Write-Host "  command  : `"$SignTool`" $($signArgs -join ' ')"
if (-not $Execute) {
    Write-Host 'PLAN ONLY: nothing was signed. Re-run with -Execute only after owner authorization.'
    exit 0
}

# --- owner-authorized execution ---
& $SignTool @signArgs
if ($LASTEXITCODE -ne 0) { throw "signtool sign failed: $LASTEXITCODE" }
& $target --self-check
if ($LASTEXITCODE -ne 0) { throw 'SIGNED EXE self-check FAILED: do not package or distribute it.' }
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'windows-verify-signatures.ps1') `
    -BundleDir $bundle -ExpectedSigner $ExpectedSigner -SignTool $SignTool
if ($LASTEXITCODE -ne 0) { throw 'Post-signing verification failed.' }
Write-Host "Signed: $target  (SHA256 after: $((Get-FileHash -LiteralPath $target).Hash))"
Write-Host 'NEXT (required): the EXE hash changed. Regenerate the third-party package against this bundle'
Write-Host '  (scripts/third_party_notices.py generate/check), then build the installer with -SignMetadata.'
