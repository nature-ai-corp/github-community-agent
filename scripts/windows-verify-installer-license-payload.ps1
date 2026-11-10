# Prove that a BUILT GC Agent Windows installer actually installs the
# third-party LICENSE/NOTICE/SBOM package, not merely that the files exist in
# the repository.
#
# Compiles packaging/windows/gc-agent.iss (the same [Files] recipe as the
# internal installer) with a fresh, distinct AppId and no shortcuts, installs
# it silently into a new folder under build/license-payload-verification/,
# compares every installed byte with the bundle and the committed package,
# then silently uninstalls it. It never launches the app, never targets the
# real GC Agent AppId or install folder, and checks that the real installation
# and user data (work.sqlite3, settings.dpapi) are byte-identical afterwards.
# No signing, publication or network access.
[CmdletBinding()]
param(
    [string]$BundleDir = '',
    [string]$BuildPython = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $BuildPython) { $BuildPython = Join-Path $root 'build\release-bundle\venv\Scripts\python.exe' }
$python = (Resolve-Path -LiteralPath $BuildPython).Path
$tool = Join-Path $root 'scripts\third_party_notices.py'
$iss = Join-Path $root 'packaging\windows\gc-agent.iss'
$package = Join-Path $root 'packaging\third-party-licenses'
if (-not $BundleDir) {
    $BundleDir = Join-Path $root 'build\release-bundle\dist\GitHubCommunityAgent'
}
$BundleDir = (Resolve-Path -LiteralPath $BundleDir).Path
$compiler = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compiler) { throw 'Inno Setup 6 ISCC.exe not found.' }

# 1. The committed package must describe this exact bundle.
& $python $tool check --bundle $BundleDir
if ($LASTEXITCODE -ne 0) { throw 'Package/bundle mismatch; payload verification not attempted.' }

# 2. Fresh evidence folder; never reuse or overwrite earlier runs.
$runRoot = Join-Path $root 'build\license-payload-verification'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$run = Join-Path $runRoot "run-$stamp"
if (Test-Path -LiteralPath $run) { throw "Run folder exists; refusing to overwrite: $run" }
New-Item -ItemType Directory -Path $run | Out-Null
$installDir = Join-Path $run 'install'
$guid = [guid]::NewGuid().ToString().ToUpper()
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{$guid}_is1"

# 3. Fingerprint the REAL installation and user data before anything runs.
$realExe = Join-Path $env:LOCALAPPDATA 'Programs\GitHub Community Agent\GitHubCommunityAgent.exe'
$dataDir = Join-Path $env:LOCALAPPDATA 'GitHubCommunityAgent'
$guarded = @($realExe, (Join-Path $dataDir 'work.sqlite3'), (Join-Path $dataDir 'settings.dpapi'))
function Get-Fingerprints {
    $guarded | ForEach-Object {
        if (Test-Path -LiteralPath $_) { "$_=" + (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash }
        else { "$_=absent" }
    }
}
$before = @(Get-Fingerprints)

# 4. Compile the real installer recipe with an isolated identity.
$log = Join-Path $run 'iscc.log'
$ErrorActionPreference = 'Continue'   # ISCC may write progress to stderr
& $compiler "/DPayloadVerificationAppId={{$guid}" "/DBundleDir=$BundleDir" `
    '/DOutputName=GitHubCommunityAgent-LicensePayloadVerification' "/O$run" $iss 2>&1 |
    ForEach-Object { "$_" } | Set-Content -LiteralPath $log -Encoding UTF8
$isccExit = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($isccExit -ne 0) { throw "Inno Setup compilation failed; see $log" }
$setup = Join-Path $run 'GitHubCommunityAgent-LicensePayloadVerification.exe'
if (-not (Test-Path -LiteralPath $setup)) { throw 'Compiled installer not found.' }
$setupHash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash

# 5. The compiler's own record must list every package file it compressed.
$compiled = Get-Content -LiteralPath $log -Raw
$packageRoot = (Resolve-Path -LiteralPath $package).Path
$missingFromLog = @(Get-ChildItem -LiteralPath $package -Recurse -File | Where-Object {
    # ISCC logs un-normalised source paths (...\windows\..\third-party-licenses\...).
    $relative = $_.FullName.Substring($packageRoot.Length).TrimStart('\')
    -not $compiled.Contains("third-party-licenses\$relative")
})
if ($missingFromLog.Count -ne 0) {
    $missingFromLog | ForEach-Object { Write-Host 'Not compressed into installer:' $_.FullName }
    throw 'Installer compile log does not include every third-party license file.'
}

# 6. Silent per-user install into the isolated run folder.
$p = Start-Process -FilePath $setup -Wait -PassThru -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER',
    "/DIR=`"$installDir`"", "/LOG=`"$(Join-Path $run 'install.log')`"")
if ($p.ExitCode -ne 0) { throw "Isolated install failed with exit code $($p.ExitCode)" }

# 7. Byte-level verification of the INSTALLED payload.
$report = Join-Path $run 'installed-payload-report.json'
& $python $tool verify-installed --app-dir $installDir --bundle $BundleDir --package $package --report $report
$payloadOk = ($LASTEXITCODE -eq 0)

# 8. Silent uninstall; it must remove the files and its registry entry.
$uninstaller = Join-Path $installDir 'unins000.exe'
if (Test-Path -LiteralPath $uninstaller) {
    Start-Process -FilePath $uninstaller -Wait -ArgumentList @(
        '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
        "/LOG=`"$(Join-Path $run 'uninstall.log')`"")
}
$deadline = (Get-Date).AddSeconds(60)
while (((Test-Path -LiteralPath (Join-Path $installDir 'GitHubCommunityAgent.exe')) -or
        (Test-Path -LiteralPath $uninstallKey)) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
}
$uninstalled = -not (Test-Path -LiteralPath (Join-Path $installDir 'GitHubCommunityAgent.exe')) -and
               -not (Test-Path -LiteralPath $uninstallKey)

# 9. Real installation and user data must be untouched.
$after = @(Get-Fingerprints)
$untouched = ($before -join "`n") -eq ($after -join "`n")

$summary = [ordered]@{
    bundle = $BundleDir
    installer_sha256 = $setupHash
    payload_verification_app_id = "{$guid}"
    compile_log_lists_all_license_files = $true
    installed_payload_pass = $payloadOk
    uninstalled_cleanly = $uninstalled
    real_installation_and_user_data_unchanged = $untouched
    legal_review_approved = $false
    signed = $false
}
$summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'summary.json') -Encoding UTF8
Write-Host "Evidence folder: $run"
Write-Host "Installer SHA256: $setupHash"
if ($payloadOk -and $uninstalled -and $untouched) {
    Write-Host 'INSTALLER LICENSE PAYLOAD VERIFICATION PASS (unsigned; legal review still required).'
    exit 0
}
Write-Host "INSTALLER LICENSE PAYLOAD VERIFICATION FAILED: payload=$payloadOk uninstall=$uninstalled userdata=$untouched"
exit 1
