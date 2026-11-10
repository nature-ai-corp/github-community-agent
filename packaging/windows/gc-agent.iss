; GitHub Community Agent - internal unsigned test installer
; This is a separate per-user installation. Never remove user work records or
; encrypted settings in %LOCALAPPDATA%\GitHubCommunityAgent on uninstall.
#ifdef PayloadVerificationAppId
  ; Isolated verification/trial build ONLY (distinct AppId and name, no
  ; shortcuts), so it can never upgrade or replace a real installation.
  #ifndef IsolatedAppName
    #define IsolatedAppName "GitHub Community Agent License Payload Verification"
  #endif
  #define AppName IsolatedAppName
  ; An isolated build must also have its OWN unique temporary install folder;
  ; it never defaults to the real installation folder.
  #ifndef IsolatedInstallDir
    #error Isolated builds require /DIsolatedInstallDir=<unique temporary folder>; refusing to default to the real installation folder.
  #endif
#else
  #define AppName "GitHub Community Agent"
#endif
#ifndef AppVersion
  #define AppVersion "1.0.0-rc1"
#endif
#ifndef OutputName
  #define OutputName "GitHubCommunityAgent-InternalTest-Unsigned"
#endif
#ifndef BundleDir
  ; Clean release bundle from scripts/windows-build-release-bundle.ps1
  ; (CPython 3.13.17 / OpenSSL 3.5, hash-locked venv without test tools).
  #define BundleDir "..\..\build\release-bundle\dist\GitHubCommunityAgent"
#endif
; Third-party LICENSE/NOTICE/SBOM package generated from the frozen bundle by
; scripts/third_party_notices.py. scripts/windows-build-installer.ps1 refuses
; to compile unless that package matches BundleDir exactly.
#define ThirdPartyDir AddBackslash(SourcePath) + "..\third-party-licenses"
#if !FileExists(ThirdPartyDir + "\THIRD_PARTY_NOTICES.txt")
  #error Missing third-party-licenses\THIRD_PARTY_NOTICES.txt; installer blocked.
#endif
#if !FileExists(ThirdPartyDir + "\MANIFEST.json")
  #error Missing third-party-licenses\MANIFEST.json; installer blocked.
#endif

[Setup]
#ifdef PayloadVerificationAppId
AppId={#PayloadVerificationAppId}
#else
AppId={{B728F255-29F8-438B-B2F7-E495DF0120E1}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=NATURE AI CORP
#ifdef PayloadVerificationAppId
DefaultDirName={#IsolatedInstallDir}
UsePreviousAppDir=no
DisableDirPage=yes
#else
DefaultDirName={localappdata}\Programs\GitHub Community Agent
UsePreviousAppDir=yes
#endif
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\GitHubCommunityAgent.exe
DisableProgramGroupPage=yes
OutputDir=..\..\dist\installer
OutputBaseFilename={#OutputName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
ChangesEnvironment=no
; End-user terms and third-party notice: shown before installation; the
; wizard's Next button stays disabled until "I accept the agreement" is chosen.
LicenseFile=END_USER_TERMS.txt
#ifdef SignToolName
; Owner-authorized signed build only (scripts/windows-build-installer.ps1
; -SignMetadata). The command itself is passed with ISCC /S, never stored here.
; Signs the setup EXE AND the uninstaller; default builds stay unsigned.
SignTool={#SignToolName}
SignedUninstaller=yes
#endif

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\NOTICE"; DestDir: "{app}"; Flags: ignoreversion
Source: "END_USER_TERMS.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ThirdPartyDir}\*"; DestDir: "{app}\third-party-licenses"; Flags: recursesubdirs createallsubdirs ignoreversion

#ifndef PayloadVerificationAppId
[Icons]
Name: "{group}\GitHub Community Agent"; Filename: "{app}\GitHubCommunityAgent.exe"
Name: "{userdesktop}\GitHub Community Agent"; Filename: "{app}\GitHubCommunityAgent.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
#endif

; No [UninstallDelete] and no cleanup scripts: user work.sqlite3,
; settings.dpapi and activity logs are independent of installation files.
; No automatic startup or GitHub write actions.

#ifdef PayloadVerificationAppId
[Code]
{ Isolated builds: refuse, before any file is copied, to install into the real
  GitHub Community Agent installation folder or the real user-data folder,
  even if /DIR= overrides the isolated default (silent or interactive). }
function GcIsUnder(const Path, Root: String): Boolean;
begin
  Result := Pos(Lowercase(AddBackslash(Root)), Lowercase(AddBackslash(Path))) = 1;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  App: String;
begin
  Result := '';
  App := ExpandConstant('{app}');
  if GcIsUnder(App, ExpandConstant('{localappdata}\Programs\GitHub Community Agent')) or
     GcIsUnder(App, ExpandConstant('{localappdata}\GitHubCommunityAgent'))
  #ifdef GuardTestRoot
     or GcIsUnder(App, '{#GuardTestRoot}')
  #endif
  then
    Result := 'Isolated trial build refuses to install into a protected GitHub Community Agent folder: ' + App;
end;
#endif
