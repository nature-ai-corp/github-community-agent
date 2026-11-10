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
DefaultDirName={localappdata}\Programs\GitHub Community Agent
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
UsePreviousAppDir=yes
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

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\NOTICE"; DestDir: "{app}"; Flags: ignoreversion
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
