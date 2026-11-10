; GC Agent V1 isolated RELEASE-CANDIDATE packaging contract (NOT approved).
; Unlike gc-agent.iss, this specification cannot compile without explicit
; externally reviewed third-party legal material. Do not sign/publish.
; It never writes into installed user Task/DPAPI data. The optimized frozen
; candidate is an existing separate onedir, not dist/GitHubCommunityAgent.
#define AppName "GitHub Community Agent"
#ifndef AppVersion
  #error AppVersion must be an explicitly approved non-dev release candidate version.
#endif
#if AppVersion == "0.0.0-dev0"
  #error Refusing development version in release-candidate spec.
#endif
#ifndef ReviewedLegalDir
  #error ReviewedLegalDir must point to an independently reviewed, complete third-party license/NOTICE distribution tree.
#endif
#ifndef LegalReviewEvidence
  #error LegalReviewEvidence must be an approved review record identifying the exact frozen candidate and legal text hash set.
#endif
#ifndef OutputName
  #define OutputName "GitHubCommunityAgent-RELEASE-CANDIDATE-UNSIGNED"
#endif

; Compile-time existence checks supplement (never replace) human review.
#if !FileExists(AddBackslash(ReviewedLegalDir) + "THIRD_PARTY_NOTICES.txt")
  #error Missing reviewed THIRD_PARTY_NOTICES.txt; release candidate blocked.
#endif
#if !FileExists(AddBackslash(ReviewedLegalDir) + "REVIEW_APPROVAL.json")
  #error Missing approved license review record; release candidate blocked.
#endif
#if !FileExists(LegalReviewEvidence)
  #error Missing independent legal review evidence.
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
OutputDir=..\..\build\gc-agent-release-candidate-installer
OutputBaseFilename={#OutputName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
ChangesEnvironment=no

[Files]
Source: "..\..\build\gc-agent-exclusion-candidate\dist\GitHubCommunityAgent\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\NOTICE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReviewedLegalDir}\*"; DestDir: "{app}\third-party-licenses"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\GitHub Community Agent"; Filename: "{app}\GitHubCommunityAgent.exe"
Name: "{userdesktop}\GitHub Community Agent"; Filename: "{app}\GitHubCommunityAgent.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

; No [UninstallDelete]. This script does not access or remove work.sqlite3,
; settings.dpapi, application activity records or Nature AI Worker.
; IMPORTANT: Do not compile by inventing an approval JSON or copying the
; unreviewed build-venv license candidates into ReviewedLegalDir.
; Separate independent validation is required for installer payload contents,
; changed-code upgrade behavior, code signing and authorized publication.
