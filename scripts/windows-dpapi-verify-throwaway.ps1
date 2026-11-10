# Cross-account DPAPI verifier for the THROWAWAY blob created by
# scripts/windows_dpapi_two_account_throwaway.py. Built-in Windows PowerShell
# 5.1 only (no Python, no repository access), so a second Windows account that
# cannot read the first account's profile can still run it.
#
# Equivalence: GC Agent calls CryptUnprotectData with no entropy, no prompt
# (CRYPTPROTECT_UI_FORBIDDEN) and current-user scope; .NET
# ProtectedData.Unprotect(blob, $null, CurrentUser) makes the same call.
# Account A must first get "decrypted" with THIS script for the same blob,
# otherwise a "denied" from account B proves nothing.
#
#   -Mode Verify -File <...\gc-agent-dpapi-throwaway.bin> -Expect allowed|denied
#   -Mode SelfCheck   (protect+unprotect random bytes in memory: proves DPAPI
#                      works for THIS account; writes nothing)
# Never prints plaintext. Never reads GC Agent settings. Writes no files.
[CmdletBinding()]
param(
    [ValidateSet('Verify', 'SelfCheck')][string]$Mode = 'Verify',
    [string]$File = '',
    [ValidateSet('allowed', 'denied')][string]$Expect = 'denied',
    # SHA256 recorded by account A; proves B tested the identical blob.
    [string]$ExpectSha256 = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.Security
$scope = [System.Security.Cryptography.DataProtectionScope]::CurrentUser
$me = [System.Security.Principal.WindowsIdentity]::GetCurrent()
Write-Host "Windows account: $($me.Name)"
Write-Host "Account SID:     $($me.User.Value)"

if ($Mode -eq 'SelfCheck') {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $blob = [System.Security.Cryptography.ProtectedData]::Protect($bytes, $null, $scope)
    $back = [System.Security.Cryptography.ProtectedData]::Unprotect($blob, $null, $scope)
    if ([Convert]::ToBase64String($back) -eq [Convert]::ToBase64String($bytes)) {
        Write-Host 'DPAPI SELF-CHECK PASS: DPAPI works for this account (in memory only).'
        exit 0
    }
    Write-Host 'DPAPI SELF-CHECK FAIL'
    exit 1
}

if ([System.IO.Path]::GetFileName($File) -ne 'gc-agent-dpapi-throwaway.bin') {
    Write-Host 'INCOMPLETE: only gc-agent-dpapi-throwaway.bin is permitted.'
    exit 2
}
try {
    $item = Get-Item -LiteralPath $File -Force
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Write-Host 'INCOMPLETE: linked path refused.'
        exit 2
    }
    $blob = [System.IO.File]::ReadAllBytes($item.FullName)
} catch {
    # A file-access denial is NOT a DPAPI result.
    Write-Host "INCOMPLETE: this account cannot read the blob file ($($_.Exception.GetType().Name))."
    exit 2
}
if ($blob.Length -lt 20 -or $blob.Length -gt 10000) {
    Write-Host 'INCOMPLETE: unexpected blob size.'
    exit 2
}
$sha = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash
Write-Host "Blob read OK:    $($blob.Length) bytes, SHA256 $sha"
if ($ExpectSha256 -and $sha -ne $ExpectSha256.Trim().ToUpperInvariant()) {
    Write-Host 'INCOMPLETE: blob hash differs from the one account A recorded.'
    exit 2
}
try {
    $plain = [System.Security.Cryptography.ProtectedData]::Unprotect($blob, $null, $scope)
    $outcome = if ($plain.Length -eq 32) { 'decrypted' } else { 'denied' }
} catch [System.Security.Cryptography.CryptographicException] {
    $outcome = 'denied'
    Write-Host "DPAPI error:     $($_.Exception.Message.Trim())"
}
Write-Host "DPAPI outcome:   $outcome"
Write-Host "Expected:        $Expect"
$ok = ($Expect -eq 'allowed' -and $outcome -eq 'decrypted') -or ($Expect -eq 'denied' -and $outcome -eq 'denied')
Write-Host $(if ($ok) { 'PASS' } else { 'FAIL' })
Write-Host 'Only disposable random bytes were used; real GC settings not accessed.'
if ($ok) { exit 0 } else { exit 1 }
