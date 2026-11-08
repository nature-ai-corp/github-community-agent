# GitHub Community Agent — Internal Windows Installer Acceptance

**Scope:** independent GC Agent V1, not Nature AI Worker, not the NATURE AI
Platform. **Status: source/build configuration prepared; no installed or
signed Windows test artifact has been verified yet.** Private PRs remain Draft.

## Packaging design

- Python 3.11–3.13 on Windows, local repository virtual environment.
- PyInstaller onedir executable `dist/GitHubCommunityAgent/GitHubCommunityAgent.exe`.
  For initial internal troubleshooting it uses a console window; its live
  app UI is the existing Work Center opened in a local browser.
- It imports GC Agent's existing `work_center.main` rather than inventing
  a new UI or Task runtime. The launcher has `--self-check`, which checks
  frozen HTML/CSS and imports only. The self-check does **not** start the HTTP
  server, read stored keys or Work data, or call GitHub or an AI provider.
- Inno Setup 6 builds an unsigned, **per-user** Windows installer named
  `GitHubCommunityAgent-InternalTest-Unsigned.exe`. No administrator rights
  required. AppId fixed to GC Agent, distinct from Nature AI Worker.
- Default program installation:
  `%LOCALAPPDATA%\\Programs\\GitHub Community Agent`.
- Permanent Work and credentials:
  `%LOCALAPPDATA%\\GitHubCommunityAgent\\work.sqlite3` and
  `%LOCALAPPDATA%\\GitHubCommunityAgent\\settings.dpapi` (DPAPI).
- Program installation, upgrade and uninstall MUST NOT delete or change
  user Work files, archive history or encrypted settings. This is achieved
  by separating user data from program files and never providing
  `[UninstallDelete]` or cleanup commands. Manual data removal, if ever
  designed, needs a separate explicitly confirmed operation.
- No machine-wide files, drivers, firewall rules, service registrations,
  automatic GitHub posting, or silent auto-updaters.

## Internal Windows build commands

Use the repo currently on the Draft PR branch, preferably on a testing
computer with no conflicting GC Agent installer. **Stop all running
GitHubCommunityAgent.exe processes before installation, upgrades or uninstalls**
(do not stop unrelated Nature AI Worker processes).

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -e ".[dev,build]"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-build-exe.ps1
```

The EXE build will **refuse to overwrite** an existing
`dist\\GitHubCommunityAgent` directory; move or rename it deliberately
before rerunning. Do not delete the user Work directory.

Then install **Inno Setup 6** from its official site
https://jrsoftware.org/isinfo.php if not already present. Inno Setup is
external software; the build does not download or install it.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-build-installer.ps1
```

Expected output on successful execution includes an installer path and SHA256.
The installer step also refuses to overwrite an existing installer file.
Neither script signs or runs an installer.

## End-user acceptance procedure — manually on a test Windows account

1. Inspect the EXE bundle result and its `--self-check` success. Confirm
   the portable EXE opens the SAME functional Work Center UI on localhost,
   and exits cleanly. No separate Tkinter legacy desktop UI should appear.
2. Preserve a copy of the test user data before install: original Work IDs,
   Archived Work reports, `work.sqlite3`, `settings.dpapi`. Do not reveal
   API keys or upload the encrypted settings file publicly.
3. Execute the unsigned test installer locally with full awareness that
   Windows may show a SmartScreen or unverified-publisher warning. **Do not
   bypass organizational malware protections**; use an authorized test
   environment. If blocked, record as a failure and investigate.
4. Confirm installed application launches via Start Menu shortcut,
   displays My Work and Archived Work, preserves settings under the current
   user's Windows DPAPI identity, and shows the correct new tasks and history.
   Verify Issue/Discussion source URLs and reports are readable. Do not
   create/delete GitHub content.
5. **Upgrade test:** recompile a newer internal test build with identical
   AppId and higher approved version, run setup over the previous installed
   product, confirm UI remains functional, all Task IDs/report/Activity
   History remain, DPAPI settings still load, and no unrelated Worker files
   changed. This cannot be accepted until there are two distinct verified
   builds; do not pretend an upgrade test was run with identical binaries.
6. **Uninstall test:** close GC Agent, uninstall through Windows Installed
   Apps, verify the program and shortcuts were removed but
   `%LOCALAPPDATA%\\GitHubCommunityAgent` was retained, including journal
   and DPAPI settings. Do not manually delete this user data. Fresh
   installation under the SAME Windows identity must retain work history.
   Different user identities should not be presumed able to decrypt DPAPI.
7. Check Windows Defender and Windows security warnings, integrity of
   installed EXE and output SHA256, and that no app data, tokens, Work data
   or other products were packaged into the installer.
8. Test unusual cases: running application during upgrade, denied write to
   install directory, interrupted setup, uninstall failure, and a second
   Windows user. Record specific evidence and reversibility.

## Important open release gates

- Internal EXE and Inno Setup package must **first build successfully on
  Windows**; all current installer assets are source-only.
- `0.0.0.dev0` is development-only; choose a correct independent product
  version before any public release. Installer build defaults to
  `0.0.0-dev0` and is **not** a release artifact.
- The internal test installer is UNSIGNED. An official Windows release needs
  publisher code signing, signature verification, malware/security review,
  clean install/upgrade/uninstall test evidence and an independent release
  approval decision.
- Current console-style frozen build is for internal troubleshooting; before
  public distribution evaluate a windowless launcher and visible error
  reporting without exposing secrets.
- Dependency/license inventory (PyInstaller, bundled Python, httpx and
  transitive binaries), SBOM and NOTICE need final review.
- GitHub private Actions billing may prevent hosted tests; report actual
  results, not assumed passes.

**No merge, tag, release, or user-data mutation is authorized by this document.**
