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

## Frozen EXE user-data continuity — latest user UI evidence

On Nov 8, 2026, following an approved controlled migration from the
Microsoft Store Python AppData virtual store to the ordinary GC Agent
user-local directory, the user supplied an actual **frozen EXE Work Center**
screenshot showing original active Tasks **#10, #8, #6, #2, #1** in My Work
and Recent Work with their original IDs and finished states. The left sidebar
also displayed `openai · gpt-4.1-mini` from the previously saved settings.
This closes the prior *empty My Work* symptom at the visible UI level.

**Acceptance scope remains limited:** the screenshot does not independently
prove Archive records #3/#4/#5/#7/#9 are displayed, the DPAPI key can be
decrypted and used, or that the later Inno Setup installed binary retains
data. Inspect Archived Work and Settings in the frozen EXE before accepting
the entire runtime continuity gate. Do not treat user-visible model name as
proof of a valid API key or a successful live connection.

### Next non-installing step

With the existing onedir bundle already passing `--self-check`, first
compile the **internal unsigned installer only**:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-build-installer.ps1
```

An installed Inno Setup 6 compiler is required. This build does not run the
installer and should produce an EXE in `dist\installer` and print SHA256.
If it fails, capture the full compiler error. **Do not install yet** until
the output is inspected and a backup/verification plan for Task history and
settings is completed.

## Inno Setup internal unsigned installer compilation — user-confirmed PASS

On November 8, 2026, the user executed
`scripts/windows-build-installer.ps1` after preserving a pre-existing
same-named installer. The native Windows output explicitly reported:

- `Successful compile (12.016 sec)`
- `GC Agent unsigned internal Windows installer build PASS.`
- Result: `dist\\installer\\GitHubCommunityAgent-InternalTest-Unsigned.exe`
- A SHA256 hash was printed by the build process.
- `No installer execution, signing, or publication performed.`

**Accepted scope: Inno Setup compilation only.** The artifact has not yet
been installed or exercised under the program installation path. A
screenshot does not establish installed EXE startup, fresh install,
upgrades, uninstall retention, Windows Defender status, independent
integrity verification, or DPAPI decryption.

Before the manual installer acceptance, stop all GC Agent processes.
Preserve an offline backup of the nonvirtualized
`%LOCALAPPDATA%\\GitHubCommunityAgent\\work.sqlite3` and
`settings.dpapi` under the same Windows identity, and record the
original 10 Task IDs/archived counts. Do not upload credentials or
backups. Confirm the installer SHA256 again before execution. On a
permitted Windows testing machine, run the unsigned installer only with
appropriate local security policy, and record warning/blocker outcomes
rather than bypassing protection. Verify Start menu launch and Task
continuity, then design an independent clean-account acceptance.
No destructive uninstall/upgrade before continuity has passed.

## Installed app first-run user evidence and non-destructive verification

The user installed the unsigned Inno Setup developer package on Windows and
provided a screenshot of the installed Work Center at localhost. The screenshot
shows the original **five active Task IDs #10, #8, #6, #2, #1**, all Finished,
with Recent Work and the saved model label. This supports a successful initial
per-user installed-app UI launch and *active* task continuity. It does NOT
yet confirm the five archived records, a live DPAPI-decrypted model
connection, upgrade or uninstall behavior.

Use the added **read-only** local verification script. It never installs,
moves or deletes files:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-installed-acceptance.ps1
```

The installed-acceptance script:
- Runs `--self-check` on the actual per-user installed EXE.
- Compares installed EXE SHA256 to the original onedir EXE, if available.
- Runs `--diagnostics` for user data and existing Task count without reading
  or printing secrets.
- Checks presence of work.sqlite3 and settings.dpapi, and compares their
  hashes with the pre-install backups (when present). Work file hashes may
  differ after legitimate changes; investigate differences instead of
  automatically reverting anything.
- Prints the Authenticode signature status; `NotSigned` is expected for this
  internal build and **not** an official release approval.
- Never performs uninstall, upgrade, copy, GitHub posting or model requests.

**Manual checks are still required**: in Archived Work verify Task
#3/#4/#5/#7/#9 and Activity History; in Settings verify credentials are
reported as saved and use Test Connection for a live model request without
revealing the API key. Do not confuse saved model label with credential
decryption proof.

Only after these checks pass should an independent, separately staged
upgrade and uninstall validation be planned. Never remove existing data
without a specific explicit user decision. Keep PR Draft and version dev0.

## Installed-app diagnostics: live SQLite hash locked (2026-11-08)

User ran the installed acceptance script and reported:
- Windows regression **214 passed in 2.51s** (0 failed).
- Installed EXE frozen self-check PASS.
- Installed EXE SHA256 matched the original frozen onedir EXE.
- Installed EXE diagnostics: work.sqlite3 exists, settings.dpapi exists,
  **10 Task records** including Archived Work.
- Pre-install backups were present: `work.sqlite3` 53248 bytes and
  `settings.dpapi` 614 bytes.
- Raw `Get-FileHash` of `work.sqlite3` failed with a Windows sharing
  violation because a GC Agent process held the database open. This does
  **not** establish corruption, loss or a functional regression.
- The previous script terminated before completing backup hash comparisons.

The revised read-only script now records SQLite SHA256 as **INCOMPLETE**
if the file is locked, proceeds to independent checks, and returns exit code
2 rather than asserting false PASS. It never closes processes or modifies
SQLite. **Stop all GC Agent running applications (including portable EXEs
and browser-spawned local servers) before rerunning**:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-installed-acceptance.ps1
```

If all file checks pass and there are no legitimate post-backup changes,
the script will indicate a read-only file-comparison PASS. If the Work DB
or settings legitimately changed, a difference is reported for human
review rather than automatically restored or deleted. Confirm the five
archived Task IDs and live model Test Connection through the installed
UI separately while the application is running, then close it for
the file comparison. Upgrade and uninstall are still pending.

## Installed program and user data file continuity — Windows PASS

The user reran `scripts/windows-installed-acceptance.ps1` after closing
running GC Agent processes. The script reported:

- `GC Agent frozen executable self-check PASS`
- Installed EXE SHA256 matched the previously built onedir EXE
- Installed program was running under Windows user `aiuser` and using
  `%LOCALAPPDATA%\\GitHubCommunityAgent`
- Original `work.sqlite3` exists with **10 Task rows** (including archived)
- `settings.dpapi` exists
- `Work database matches pre-install backup: YES`
- `DPAPI settings matches pre-install backup: YES`
- `Installed EXE Authenticode status: NotSigned` (expected internal build)
- `Installed-app read-only file comparison PASS`
- The verification changed no files

**Accepted:** per-user installed executable integrity relative to the built
bundle, all 10 stored Task records' database byte continuity, and DPAPI
settings file byte continuity after installation. The previously observed
Windows file-sharing error no longer affects acceptance.

**Not yet accepted:** manual Archived Work UI showing #3/#4/#5/#7/#9 and
Activity History; a live Settings Test Connection using the stored provider
key (without re-entering it); actual clean-install on a separate test account,
upgrade, uninstall retention, code signing or formal release.

## Installed Archived Work UI — user-confirmed PASS

The user supplied an actual installed Windows GC Agent screenshot of
**Archived Work** on November 8, 2026. All five archived Task IDs are
visible with their original status and Work Type:

- #9 Community Report — Finished
- #7 Draft Discussion Reply — Failed
- #5 Draft Discussion Reply — Failed
- #4 Draft Issue Reply — Finished
- #3 Draft Issue Reply — Failed

The report detail for Task #9 is open and still shows the original
GitHub source link. The sidebar's Recent Work lists only the five
non-archived items (#10/#8/#6/#2/#1). Combined with the prior
SHA256-verification, **all ten original Task records are retained after
installation**. This screenshot does not specifically show expanded
Activity History, so individual recorded event rows remain a separate
UI detail to inspect if full activity visibility is required.

**Outstanding:** live provider Test Connection using the encrypted,
previously saved API Key, without entering it again; independent
upgrade and uninstall retention tests. No formal release or signing.

## Installed-app encrypted credential and live provider check — PASS

On November 8, 2026, the user showed the **installed** GC Agent Settings UI:
- Provider `OpenAI`, model `gpt-4.1-mini`.
- API key input was blank by design, with the UI message
  `A key is stored encrypted. Leave empty to keep it.`
- They clicked **Test connection** without entering or replacing the saved
  API key. The UI displayed
  **`Connection succeeded (live provider check).`**

This confirms actual installed-runtime access to the previously stored
encrypted credential and a successful live model connection (not merely
presence of the DPAPI file or displayed model name).

Combined with the already established Windows 214-passed regression,
installed frozen EXE integrity, full My Work/Archived Work Task-ID
continuity and unchanged database/settings hashes, **initial Windows
per-user installation and data continuity acceptance is PASS**.

Remaining separate gates: installed Activity History event-row detail
inspection; controlled real upgrade to a distinct, approved test version;
uninstall retaining user data; reinstall; clean separate-user acceptance;
negative security tests, dependency and NOTICE review, signed final
installer and release approval. Do not merge, sign, tag or release yet.

## Controlled upgrade / uninstall / reinstall trial — staged, not executed

After initial GC Agent Windows installation and DPAPI live connection passed,
the next validation uses a **distinct Inno Setup installer display version**
\`0.0.1-devtrial\` and output file
\`dist\installer\GitHubCommunityAgent-UpgradeTrial-Unsigned.exe\`. This
trial deliberately bundles the *same existing onedir application binary*;
it tests Inno Setup's upgrade/registration and data retention, **NOT**
functional code upgrades or application schema migrations. The product
Python metadata still says \`0.0.0.dev0\`; it is NOT a production release.

### Phase A — create baseline and compile second test installer

1. Close all GitHubCommunityAgent.exe processes (including portable EXE).
   Confirm the previous *real* \`Documents\GC-Agent-PreInstall-Backup\`
   copies of \`work.sqlite3\` and \`settings.dpapi\` remain secure.
2. In PowerShell (no installation, no overwrite):

\`\`\`powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-upgrade-uninstall-verify.ps1 -Phase Baseline
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-build-installer.ps1 -UpgradeTrial
\`\`\`

The baseline script **refuses** to run while GC Agent EXEs are running, or
if it cannot find the installed program, the protected settings file,
the database, or all **10 original Task records**. It stores a
hash-only JSON manifest in the current user's Documents, never copies
secrets. It refuses to overwrite any previous baseline.

The upgrade-trial builder verifies the existing frozen EXE, compiles a
second installer with the SAME GC AppId and a DISTINCT display version
and file name, and prints SHA256. It does not execute the installer.
If a trial installer of that name already exists, it refuses to overwrite.
Keep both installers and both data backups intact.

**Stop here and review the exact output and SHA256 before executing the
upgrade installer.**

### Phase B — real upgrade, if the Phase A result is accepted

In a test Windows environment, run the new unsigned trial installer
interactively after checking system security warnings. Do not bypass policy
restrictions. Install into the same per-user GC Agent path (default).
After setup completes, inspect the installed app: My Work #1/#2/#6/#8/#10,
Archived Work #3/#4/#5/#7/#9, Task reports, Activity History, Settings and
Test Connection. Close the app fully; compare files:

\`\`\`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-upgrade-uninstall-verify.ps1 -Phase AfterUpgrade
\`\`\`

The script requires the original SHA256 for work.sqlite3 and settings.dpapi
to be unchanged, and the installed binary to self-check and read 10 Tasks.
Do not perform further steps if any comparison fails. Keep the versioned
trial installer for potential authorized reinstall.

### Phase C — uninstall, then reinstall (separate approval after Phase B)

Do **not** uninstall without verifying the current backup and Phase B PASS.
Use Windows Installed Apps for GitHub Community Agent, **not**
Nature AI Worker. The installer does not include \`[UninstallDelete]\` and
must retain user \`%LOCALAPPDATA%\GitHubCommunityAgent\`. Close the app,
then run:

\`\`\`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-upgrade-uninstall-verify.ps1 -Phase AfterUninstall
\`\`\`

The verifier requires that the GC Agent installed EXE has been removed,
while both personal data files remain SHA256-identical to baseline. It
does not start any process for an uninstalled application.

Reinstall the *same* upgrade-trial installer only after this passes.
Confirm My Work, Archived Work, Settings and live Test Connection again.
Close the app, then:

\`\`\`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-upgrade-uninstall-verify.ps1 -Phase AfterReinstall
\`\`\`

These checks do **not** themselves perform upgrade/uninstall/reinstall and
never erase database or DPAPI files. Full application-code upgrade across
different application binaries and actual database-schema upgrades are
separate future tests. No merge, tag, signing or release until the
broader release gates are explicitly approved.

## Upgrade Trial Windows acceptance PASS — 2026-11-08

The user executed the unsigned `0.0.1-devtrial` Inno Setup upgrade over the
previous per-user developer installation and supplied three independent
screenshots from the Windows test machine:

1. **Installed Settings UI** still shows OpenAI/`gpt-4.1-mini`, a previously
   encrypted/saved API key, and `Connection succeeded (live provider check).`
2. **Archived Work UI** still shows all original five archived Task IDs
   #9/#7/#5/#4/#3 with the same report/work types and terminal statuses.
3. The read-only `windows-upgrade-uninstall-verify.ps1 -Phase AfterUpgrade`
   emitted:
   - `AfterUpgrade GC Agent user-data byte continuity PASS.`
   - `work.sqlite3 and settings.dpapi are SHA256-identical to the baseline.`
   - `GC Agent frozen executable self-check PASS`
   - `Stored Task count (including archived): 10`
   - `READ-ONLY VERIFICATION COMPLETE. No user data or installed files were changed.`

**Accepted:** Inno Setup per-user installer replacement/upgrade behavior,
continued readability of archived history and encrypted provider setting,
and byte-identical Work/DPAPI data files.

**Scope qualification:** this trial changed only Inno Setup version and
installer identity metadata, while bundling the same GC Agent app code.
It is not evidence for real application-code or schema migration safety.

**Next controlled gate:** After confirming an independently stored backup,
close all GC Agent executable instances. Uninstall ONLY the independently
installed GitHub Community Agent (not Nature AI Worker) through Windows
Installed Apps. After uninstall, run
`windows-upgrade-uninstall-verify.ps1 -Phase AfterUninstall`, verifying
the installed EXE was removed and work.sqlite3/settings.dpapi are
still SHA256-identical to the baseline. Stop before reinstall if this
verification fails. No automated removal of user data is authorized.

## User-confirmed controlled uninstall / retained data PASS — November 8 2026

The user ran the installed `unins000.exe` (Inno Setup's registered
uninstaller). The UI explicitly reported: **GitHub Community Agent was
successfully removed from your computer**.

Afterward, the same Windows user ran
`scripts/windows-upgrade-uninstall-verify.ps1 -Phase AfterUninstall`,
which printed:
- `AfterUninstall GC Agent user-data byte continuity PASS.`
- `work.sqlite3 and settings.dpapi are SHA256-identical to the baseline.`
- `READ-ONLY VERIFICATION COMPLETE. No user data or installed files were changed.`

The verifier only accepts AfterUninstall if the GC Agent installed EXE is
absent, and both data files still exist with baseline-identical hashes.
Therefore normal Inno Setup uninstallation and data retention are
**accepted PASS**. These results do not yet demonstrate *reinstallation*
or another Windows user's clean installation.

**Next acceptance step:** Run the previously compiled and verified
`GitHubCommunityAgent-UpgradeTrial-Unsigned.exe` again under the same
Windows user, keeping the standard GC install directory. From the Start
Menu launch the reinstalled GC Agent and verify My Work, Archived Work and
Settings Test Connection, then close all GC Agent processes and run:
`windows-upgrade-uninstall-verify.ps1 -Phase AfterReinstall`.
Preserve existing baseline, source backups and original Store Python data.

## Reinstall after uninstall — user-confirmed Windows PASS

After the previously accepted successful uninstall and unchanged personal
data hashes, the user ran the same unsigned
`GitHubCommunityAgent-UpgradeTrial-Unsigned.exe` installer again under
the original Windows identity, and supplied two screenshots (Nov 8, 2026):

- The installed Settings screen shows OpenAI / `gpt-4.1-mini`, the saved
  encrypted API key, and **`Connection succeeded (live provider check).`**
- `scripts/windows-upgrade-uninstall-verify.ps1 -Phase AfterReinstall`
  reported **`AfterReinstall GC Agent user-data byte continuity PASS.`**
  Both work.sqlite3 and settings.dpapi remained SHA256-identical to the
  baseline; installed EXE self-check passed; read-only diagnostics found
  **10 Task rows including archived**, both files present, and verification
  completed with no changes.

**Accepted**: the full Windows per-user internal trial
initial install → installer-version upgrade → uninstall → reinstall workflow,
with original 10-Task database and encrypted provider connection retained
through all phases. The upgrade was an installer-metadata/version trial
bundling the same program binaries, **not** an application code/schema upgrade.

The reinstall screenshots do not separately show the Archived Work list
and its event-by-event Activity History; earlier pre-uninstall installed UI
did show all five archived Task IDs. Full release gates remain open:
real different-code/schema upgrade, clean second-account installation,
Windows platform security and signed publisher distribution, dependency
license/NOTICE inventory, hosted CI and Draft PR stack review. No merge,
signing, tagging or public release is authorized.
