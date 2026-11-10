# Installer license page — wizard auto-advance investigation and manual test

Prepared 2026-11-10 at `68a9f56`. Isolated tests only. No signing, merge or
release, and nothing marked approved.

## 1. Investigation: why the wizard "advanced on its own"

**Configuration reviewed** (`packaging/windows/gc-agent.iss`):
- `LicenseFile=END_USER_TERMS.txt`, with Inno's standard accept and decline
  radio buttons;
- isolated builds: `DisableDirPage=yes`, `UsePreviousAppDir=no`,
  `DefaultDirName={#IsolatedInstallDir}`, plus the `PrepareToInstall` guard.

There is no auto-advance, timer, or `ShouldSkipPage`/`NextButtonClick` code.
Inno Setup 6.7.4 has no feature that accepts the license by itself.

**Controlled experiment** (isolated AppId and folder, Inno `/LOG`, read-only
observer, harness input = **none**):

| Time | Observed (wizard always the foreground window) |
|---|---|
| 3.2 s | License page; "I do not accept" selected; **Next disabled** |
| 7.2 – 10.1 s | `GetLastInputInfo`: **system keyboard/mouse input events** (the harness sent nothing) |
| 11.2 s | "I accept" selected; Next enabled |
| 12.9 s | Input event |
| 15.8 s | "Ready to Install" |
| 16.3 s | Input event |
| 17.4 s | "Installing", into the **isolated** folder only |
| 23.2 s | "Completing"; then an input event, and the wizard closed |

An earlier run with the same setup (no harness input) also reached "Ready to
Install" about 30 s after launch.

**Classification:**
- **Installer configuration:** **No.** The wizard sat on the license page
  with Next disabled until input events arrived, and each state change followed
  a recorded input event.
- **License-acceptance bypass:** **No.** "I accept" was selected *before* Next
  became enabled, and Next was then activated. The gate behaved exactly as
  designed; the license was accepted by input.
- **Residual automation input from the harness:** **No.** In the decisive run
  the harness sent nothing, and `GetLastInputInfo` only moves on keyboard or
  mouse input (physical, or injected with `SendInput`), never on the window
  messages the old probe used.
- **Test harness defect:** **Yes, the root cause.** The automated probes
  launched an **interactive** wizard on a desktop that was in use. Setup takes
  the foreground and keyboard focus, so live keyboard/mouse input on this PC
  (for example, typing that was meant for another window: `A` selects
  "I **a**ccept", `Enter` presses the default Next/Install/Finish button) drove
  the wizard.
- **Source of the input:** the data shows real input events but cannot say
  whether they came from the person at this PC or from another input-automation
  tool. It was not this harness.
- **Earlier incidents:** the same mechanism is consistent with both, but they
  had no input logging and cannot be proven retroactively.

**Consequences:**
- The isolation fix (unique AppId, unique folder, `PrepareToInstall` guard)
  contained every incident. Real installation and data hashes were unchanged
  each time, and every isolated install was removed.
- Automated interactive wizard probes are **withdrawn**. The license page is
  verified by a person, using the kit below.

## 2. Manual test kit (`scripts/windows-manual-license-page-test.ps1`)

**Isolation:**
- each run compiles `gc-agent.iss` with a **unique temporary AppId** and a
  **unique temporary install folder** under
  `build\manual-license-test\run-<UTC>-<scenario>\`;
- the guard refuses the real program folder and
  `%LOCALAPPDATA%\GitHubCommunityAgent`;
- the script fingerprints the real EXE, `work.sqlite3`, `settings.dpapi` and
  the real AppId's uninstall entry before and after.

**What it does:**
- it **sends no clicks, keys or window messages**; the person operates the
  wizard;
- it reads Setup's exit code, the isolated folder and the registry, and
  byte-verifies the installed payload in the accept scenario;
- it removes the isolated install with its own uninstaller, and writes
  `summary.json`.

Use a quiet desktop: close other apps or don't type elsewhere while the wizard
is open, because the wizard has keyboard focus.

### Test A: rejection (run first)

```powershell
cd C:\Users\aiuser\projects\github-community-agent
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-manual-license-page-test.ps1 -Scenario Decline
```
1. The wizard opens on **License Agreement**, with **"I do not accept the
   agreement"** selected.
2. Confirm that **Next is greyed out**. Read the page:
   - title "GitHub Community Agent - End-User Terms and Third-Party Notice";
   - "DRAFT FOR LEGAL REVIEW";
   - §1 lists "prepare derivative works of (modify)";
   - §3 states that VCRUNTIME140.dll is Microsoft Distributable Code.
3. Do **not** select "I accept". Click **Cancel**, then **Yes** in "Exit
   Setup".
4. **Expected:** `MANUAL LICENSE PAGE TEST (Decline) PASS`, with Setup exit
   code **2** (cancelled before installation), `installed = False`, no
   registry entry, and real data unchanged.

### Test B: acceptance

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-manual-license-page-test.ps1 -Scenario Accept
```
1. Confirm again that Next is greyed out while "I do not accept" is selected.
2. Select **"I accept the agreement"**. Next becomes active.
3. Click **Next**, then **Install**, then **Finish**.
4. **Expected:** `MANUAL LICENSE PAGE TEST (Accept) PASS`, with exit code 0,
   the installed payload byte-verified (979 files, including
   `END_USER_TERMS.txt`), a clean isolated uninstall, and real data unchanged.

`-PrepareOnly` compiles and prints the plan without launching anything.

**Results, operated by a person (2026-11-10).** Every run used an isolated
AppId and folder; real installation and data were unchanged in every run.

| Run | Scenario | Setup exit | Outcome |
|---|---|---|---|
| `run-20261110T200950Z-decline` | Decline | 0 | **FAIL**: the license was accepted and installed during a Decline run, so it is not valid rejection evidence. The isolated install was removed cleanly |
| `run-20261110T201155Z-decline` | Decline | **2** | **PASS**: cancelled before installation, nothing installed, no registry entry |
| `run-20261110T201301Z-accept` | Accept | 0 | **PASS**: installed, payload byte-verified (including `END_USER_TERMS.txt`), clean isolated uninstall |

The rejection and acceptance behavior of the license page is verified for
installer `84454641…079430`. Repeat both scenarios on the final binary after
the release-text commit.

The same two checks are also part of the owner's clean Windows 11 VM test,
with the real release asset (`RELEASE_READINESS.md` §4).
