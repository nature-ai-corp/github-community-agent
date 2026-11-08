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

## Windows user-executed builder result — 2026-11-08

Observed evidence from Windows PowerShell on `feature/unified-task-home` at
`7cab155`, native Python 3.13.14 and PyInstaller 6.22.3:

- `python -m pip install -e ".[dev,build]"` completed successfully.
- `scripts/windows-test-regression.ps1` reported **211 passed in 2.31s**,
  **0 failures**, `GC Agent Windows regression PASS`.
- `scripts/windows-build-exe.ps1` successfully built a Windows onedir
  `dist\\GitHubCommunityAgent\\GitHubCommunityAgent.exe`.
- Frozen executable self-check reported **PASS** and unsigned onedir
  build reported **PASS**.
- This evidence confirms initial build and embedded-resource smoke, **not**
  real browser UI launch, network request, DPAPI load, user data retention,
  installer compilation, installation, upgrade, uninstallation, signing or
  official release. These remain pending.

Next safe test: start the frozen EXE (without passing --self-check), verify the
correct Work Center opens on localhost, inspect existing My Work and Archived
Work without changing content, and close the console app. Only after this
should Inno Setup compilation and per-user installer tests proceed.

## Frozen Work Center opens but shows no Work records (investigation)

The user showed that frozen `GitHubCommunityAgent.exe` launched localhost UI
successfully but the **My Work and Recent Work lists were empty**; the prior
Python Work Center had Task #1 through #10. This is **not** successful Work
data continuity acceptance and **installer compilation/installation must be
held** pending diagnosis.

Native and frozen `work_center.data_directory()` are intended to use the
same `%LOCALAPPDATA%\\GitHubCommunityAgent` directory, regardless of
executable path, but the runtime environment/path and any Settings failure
have not been confirmed.

New frozen launcher option `--diagnostics` is read-only. It prints the
effective user name, LOCALAPPDATA path, Work database existence, encrypted
settings existence and stored Task row count. It never prints secrets,
accesses GitHub, creates a new SQLite file or alters the journal.

**Existing already-built EXE does not have this new option.** Rebuild safely
by renaming the old program output folder (not the user's AppData):

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
.\.venv\Scripts\python.exe -m pytest -q --basetemp "$env:LOCALAPPDATA\\GitHubCommunityAgent\\test-runs\\manual-diagnostic"
Rename-Item -LiteralPath .\dist\GitHubCommunityAgent -NewName GitHubCommunityAgent-before-diagnostics
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-build-exe.ps1
.\dist\GitHubCommunityAgent\GitHubCommunityAgent.exe --diagnostics
```

Compare with native Python in the same Windows session:

```powershell
@'
from github_community_agent.work_center import data_directory
from pathlib import Path
import sqlite3
p = data_directory()
db = p / "work.sqlite3"
print("Native data directory:", p)
print("Native database exists:", db.is_file())
if db.is_file():
    with sqlite3.connect(db.as_uri()+"?mode=ro", uri=True) as con:
        print("Native Task count:", con.execute("SELECT COUNT(*) FROM work").fetchone()[0])
print("Native protected settings exists:", (p / "settings.dpapi").is_file())
'@ | .\.venv\Scripts\python.exe -
```

If both report 10 Tasks, investigate frontend API/initialization errors
rather than moving or deleting user data. If the effective path or count
differs, **do not copy DPAPI credential material**; identify why the
environment differs before changing any application data. If the old frozen
EXE is running, stop it before renaming the bundle.

## Confirmed root cause — Microsoft Store Python MSIX file virtualization (Nov 8)

User's two read-only diagnostics reported the **same logical** directory
`C:\\Users\\aiuser\\AppData\\Local\\GitHubCommunityAgent`, but:
- Frozen independent EXE: existing `work.sqlite3` with **0 Tasks**, and
  `settings.dpapi` **not found**.
- Python venv backed by `WindowsApps\\PythonSoftwareFoundation.Python.3.13`:
  existing `work.sqlite3` with **10 Tasks** and
  `settings.dpapi` **found**.

This strongly matches Windows Store Python's documented MSIX AppData
redirection. The venv interpreter can see a per-package private physical
folder while the independent EXE sees unvirtualized AppData. See Microsoft
MSIX documentation and Python's Windows Store guidance. To verify, use
`os.path.realpath(data_directory())` **inside the Store Python process**.

The GC Agent app's ordinary user-data target remains
`%LOCALAPPDATA%\\GitHubCommunityAgent`; it should **not** depend on or
hard-code the Windows Store Python package identity in normal runtime.

### Controlled one-time migration (only this user / test system)

1. Stop *both* Python-run and frozen GC Agent applications. Do not install the
   Inno Setup EXE yet. Do not manually rename, erase or move the old files.
2. Pull the branch (new script has no dependency on rebuilding EXE beyond the
   existing `--diagnostics` frozen binary):
   ```powershell
   git pull --ff-only
   powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\windows-store-data-migration.ps1
   ```
3. **Dry run is default**: it verifies the Store Python physical source has
   Tasks and encrypted settings, source is in an MSIX package's LocalCache,
   no WAL/SHM journal exists, target has no encrypted settings and its
   database is absent or exactly **zero Tasks**, and refuses junctions.
4. After reviewing the paths and preserving original files, explicitly
   approve migration using:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\windows-store-data-migration.ps1 -Apply
   ```
5. The script stages copies, checks SHA256 equality, backs up the old empty
   independent database, copies the 10-Task database and encrypted settings
   to the regular Windows user data folder, and runs frozen EXE diagnostics.
   Original Store Python data is **not modified or deleted**. Existing nonempty
   independent data or credentials are **never overwritten**.
6. Then run `dist\\GitHubCommunityAgent\\GitHubCommunityAgent.exe`, inspect
   all 10 original Task IDs including Archived Work, Activity History, and
   saved settings. Confirm that the same Windows identity can decrypt
   `settings.dpapi`. Do not display credential values.
7. Only after this acceptance should work resume on Inno Setup build and
   installation/upgrade/uninstall tests.

The script is opt-in, not a silently performed installer migration. If it
reports a source path different from the expected MSIX package or refuses
for any reason, investigate and do **not** bypass guards or delete files.

## Dry-run detector correction — November 8, 2026

The user attempted the first migration dry-run, which **safely stopped**
with `Source and destination resolve to the same physical directory`.
This revealed a false assumption in our detection: `os.path.realpath`
returns the visible logical AppData string and **does not resolve MSIX
file-virtualization redirection**. No files were changed, and no migration
was run.

Revised dry-run detection:
- Reads the original Task count and SHA256 fingerprints of the original
  database and DPAPI settings **from the existing Store-Python-backed venv**.
- Enumerates only `%LOCALAPPDATA%\\Packages\\PythonSoftwareFoundation.Python.3.13_*\\LocalCache\\Local\\GitHubCommunityAgent`
  candidate backing directories, accessed from ordinary PowerShell.
- Requires **exactly one** physical candidate with both matching file
  fingerprints, then applies the previous directory/empty-destination,
  symlink/junction and SQLite-journal guards.
- The default mode **remains non-mutating**; `-Apply` is neither implied
  nor recommended until the revised Dry Run output is reviewed.

Next Windows step:

```powershell
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\windows-store-data-migration.ps1
```

**Do not execute -Apply, install, or uninstall yet.** If the matching
physical source cannot be uniquely found, the script refuses migration
rather than guessing paths.

## User-confirmed Windows migration Dry Run PASS — 2026-11-08

Native Windows PowerShell results on branch `feature/unified-task-home`:
- `windows-test-regression.ps1`: **213 passed in 1.54s**, zero failures.
- Store-Python-backed original source was uniquely fingerprint-matched to
  `%LOCALAPPDATA%\\Packages\\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\\LocalCache\\Local\\GitHubCommunityAgent`.
- Original source database: **10 Task records** (including archived).
- Original source encrypted `settings.dpapi`: present.
- Nonvirtualized target directory: `%LOCALAPPDATA%\\GitHubCommunityAgent`.
- Independent frozen EXE confirmed target database exists but contains
  **0 Task records**, and there is **no target protected settings file**.
- Script printed **`DRY RUN PASS. No files changed.`**
- As of this evidence, **-Apply has NOT been executed**, so original/exe data
  continuity remains pending.

Next authorized-by-user-operated step is to stop all GC Agent processes,
explicitly execute the opt-in `-Apply` migration and verify the frozen EXE
shows 10 Tasks plus saved model Settings, then review original Task IDs and
archived reports. Original Store Python files must stay intact. The target's
previous empty database is backed up. Keep Inno Setup blocked until that
verification succeeds.
