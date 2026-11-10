# MANUAL installer license-page test, operated by a person. The script itself
# never clicks, types or sends window messages to the wizard.
#
# It compiles packaging/windows/gc-agent.iss as an ISOLATED build:
#   * a unique temporary AppId (never the real GitHub Community Agent AppId);
#   * a unique temporary install folder under build/manual-license-test/;
#   * the built-in PrepareToInstall guard that refuses the real program
#     folder and the real data folder, even if /DIR is overridden.
# It fingerprints the real installation and user data before and after,
# launches the wizard with an Inno log, waits for the person to finish, and
# then checks the result against the chosen scenario:
#   -Scenario Decline : keep "I do not accept"; Next must stay disabled;
#                       press Cancel -> "Exit Setup" -> Yes.
#                       Expected: Setup exit code 2 (cancelled before
#                       installation), no install folder, no registry entry.
#   -Scenario Accept  : select "I accept the agreement", Next, Install, Finish
#                       (leave "Launch" unticked if offered).
#                       Expected: exit code 0, installed payload byte-verified
#                       (incl. END_USER_TERMS.txt), then removed by this script
#                       with the isolated uninstaller.
# -PrepareOnly compiles and prints the plan without launching anything.
# No signing, network, real AppId, real install folder or user-data access.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet('Decline', 'Accept')][string]$Scenario,
    [string]$BundleDir = '',
    [string]$BuildPython = '',
    [int]$TimeoutMinutes = 30,
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $BundleDir) { $BundleDir = Join-Path $root 'build\release-bundle\dist\GitHubCommunityAgent' }
if (-not $BuildPython) { $BuildPython = Join-Path $root 'build\release-bundle\venv\Scripts\python.exe' }
$BundleDir = (Resolve-Path -LiteralPath $BundleDir).Path
$python = (Resolve-Path -LiteralPath $BuildPython).Path
$iss = Join-Path $root 'packaging\windows\gc-agent.iss'
$compiler = @((Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
              (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compiler) { throw 'Inno Setup 6 ISCC.exe not found.' }

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$run = Join-Path $root "build\manual-license-test\run-$stamp-$($Scenario.ToLower())"
if (Test-Path -LiteralPath $run) { throw "Run folder exists: $run" }
New-Item -ItemType Directory -Path $run | Out-Null
$installDir = Join-Path $run 'isolated-install'
$guid = [guid]::NewGuid().ToString().ToUpper()
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{$guid}_is1"
$realAppKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{B728F255-29F8-438B-B2F7-E495DF0120E1}_is1'

$realExe = Join-Path $env:LOCALAPPDATA 'Programs\GitHub Community Agent\GitHubCommunityAgent.exe'
$dataDir = Join-Path $env:LOCALAPPDATA 'GitHubCommunityAgent'
$guarded = @($realExe, (Join-Path $dataDir 'work.sqlite3'), (Join-Path $dataDir 'settings.dpapi'))
function Get-Fingerprints {
    $f = @($guarded | ForEach-Object {
        if (Test-Path -LiteralPath $_) { "$_=" + (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash } else { "$_=absent" } })
    if (Test-Path -LiteralPath $realAppKey) {
        $p = Get-ItemProperty -LiteralPath $realAppKey
        $f += "realAppKey=$($p.DisplayVersion)|$($p.InstallLocation)"
    } else { $f += 'realAppKey=absent' }
    return $f
}
$before = @(Get-Fingerprints)

$log = Join-Path $run 'iscc.log'
& $compiler /Q "/DPayloadVerificationAppId={{$guid}" '/DIsolatedAppName=GC Agent Manual License Test' `
    "/DIsolatedInstallDir=$installDir" "/DBundleDir=$BundleDir" '/DOutputName=ManualLicenseTest' "/O$run" $iss *> $log
if ($LASTEXITCODE -ne 0) { throw "Isolated installer compile failed; see $log" }
$setup = Join-Path $run 'ManualLicenseTest.exe'
$setupLog = Join-Path $run 'setup.log'

Write-Host ''
Write-Host "Isolated test installer : $setup"
Write-Host "Temporary AppId         : {$guid}"
Write-Host "Isolated install folder : $installDir"
Write-Host "Scenario                : $Scenario"
if ($Scenario -eq 'Decline') {
    Write-Host 'OPERATOR STEPS: on the License Agreement page keep "I do not accept the agreement".'
    Write-Host '  Check that Next is greyed out (disabled). Do NOT select "I accept".'
    Write-Host '  Click Cancel, then Yes in "Exit Setup".'
} else {
    Write-Host 'OPERATOR STEPS: read the terms; first confirm Next is greyed out while "I do not accept" is selected.'
    Write-Host '  Select "I accept the agreement" (Next becomes active), click Next, Install, then Finish.'
}
Write-Host 'While the wizard is open, do not type into other windows: the wizard has keyboard focus.'
if ($PrepareOnly) { Write-Host "PREPARE ONLY: nothing launched. Evidence folder: $run"; exit 0 }

$p = Start-Process -FilePath $setup -PassThru -ArgumentList "/LOG=`"$setupLog`""
if (-not $p.WaitForExit($TimeoutMinutes * 60 * 1000)) {
    Get-Process | Where-Object { $_.ProcessName -like 'ManualLicenseTest*' } | Stop-Process -Force
    throw "Timed out after $TimeoutMinutes minutes; wizard stopped."
}
$exit = $p.ExitCode
$installed = Test-Path -LiteralPath (Join-Path $installDir 'GitHubCommunityAgent.exe')
$registered = Test-Path -LiteralPath $uninstallKey
$payloadOk = $null; $uninstalled = $null
if ($installed) {
    $report = Join-Path $run 'installed-payload-report.json'
    & $python (Join-Path $root 'scripts\third_party_notices.py') verify-installed --app-dir $installDir --bundle $BundleDir --report $report
    $payloadOk = ($LASTEXITCODE -eq 0)
    $u = Join-Path $installDir 'unins000.exe'
    if (Test-Path -LiteralPath $u) { Start-Process -FilePath $u -Wait -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' }
    $deadline = (Get-Date).AddSeconds(60)
    while (((Test-Path -LiteralPath (Join-Path $installDir 'GitHubCommunityAgent.exe')) -or (Test-Path -LiteralPath $uninstallKey)) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 500 }
    $uninstalled = -not (Test-Path -LiteralPath (Join-Path $installDir 'GitHubCommunityAgent.exe')) -and -not (Test-Path -LiteralPath $uninstallKey)
}
$after = @(Get-Fingerprints)
$untouched = ($before -join "`n") -eq ($after -join "`n")

if ($Scenario -eq 'Decline') {
    $pass = ($exit -eq 2) -and -not $installed -and -not $registered -and $untouched
} else {
    $pass = ($exit -eq 0) -and $installed -and $payloadOk -and $uninstalled -and $untouched
}
$summary = [ordered]@{
    scenario = $Scenario; temporary_app_id = "{$guid}"; isolated_install_dir = $installDir
    setup_exit_code = $exit; installed = $installed; registered_before_cleanup = $registered
    installed_payload_byte_verified = $payloadOk; isolated_uninstall_clean = $uninstalled
    real_installation_and_user_data_unchanged = $untouched; automated_ui_input_used = $false; pass = $pass
}
$summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'summary.json') -Encoding UTF8
$summary.GetEnumerator() | ForEach-Object { Write-Host ("  {0,-42} {1}" -f $_.Key, $_.Value) }
Write-Host "Evidence folder: $run"
if ($pass) { Write-Host "MANUAL LICENSE PAGE TEST ($Scenario) PASS"; exit 0 }
Write-Host "MANUAL LICENSE PAGE TEST ($Scenario) FAILED"; exit 1
