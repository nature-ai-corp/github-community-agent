; GitHub Community Agent - internal unsigned test installer
; This is a separate per-user installation. Never remove user work records or
; encrypted settings in %LOCALAPPDATA%\GitHubCommunityAgent on uninstall.
#define AppName "GitHub Community Agent"
#ifndef AppVersion
  #define AppVersion "0.0.0-dev0"
#endif

[Setup]
AppId={{B728F255-29F8-438B-B2F7-E495DF0120E1}
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
OutputBaseFilename=GitHubCommunityAgent-InternalTest-Unsigned
Compression=lzma
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
ChangesEnvironment=no

[Files]
Source: "..\..\dist\GitHubCommunityAgent\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\NOTICE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\GitHub Community Agent"; Filename: "{app}\GitHubCommunityAgent.exe"
Name: "{userdesktop}\GitHub Community Agent"; Filename: "{app}\GitHubCommunityAgent.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

; No [UninstallDelete] and no cleanup scripts: user work.sqlite3,
; settings.dpapi and activity logs are independent of installation files.
; No automatic startup or GitHub write actions.
