# Gate 3 — Cross-account DPAPI test: owner instructions (NOT YET RUN)

**Status: PENDING.** No result exists until the steps below are run by a
person with two real Windows accounts. Do not record PASS from same-account runs.

Goal: show that a credential protected by GC Agent for Windows account A
cannot be decrypted by a different Windows account B on the same PC. Only
32 **random throwaway bytes** are used; real GC Agent settings are never read.

## Why the steps look like this (checked on this PC, 2026-11-10)

- Account B cannot read `C:\Users\aiuser` (owner, Administrators and SYSTEM
  only), so B cannot run the repo's Python script or `.venv`. B therefore
  uses `scripts\windows-dpapi-verify-throwaway.ps1`, which needs only
  built-in Windows PowerShell 5.1.
- That verifier makes the same Windows call as GC Agent: `CryptUnprotectData`,
  no entropy, current-user scope. Step A5 proves this on A's own blob. On
  this PC, the app module and the verifier both decrypted the same
  same-account blob, so the method is equivalent.
- `C:\Users\Public\Documents` grants Modify to `INTERACTIVE` users, so a
  file A creates there is readable by B when B is signed in.
- If B cannot read the file, the verifier prints **INCOMPLETE (exit 2)**. A
  file-access failure is never counted as a DPAPI denial.

## Prerequisites

1. **A second real Windows account (B) that you control, with its password.**
   Local accounts on this PC: `aiuser` (A), `AI User`, `AT Tester`, and
   `CodexSandbox*`. Use `AT Tester` only if it is yours to use. **Do not use
   the `CodexSandbox*` accounts**; they belong to other tooling. To create a
   temporary account instead, in an **Administrator** PowerShell:
   ```powershell
   New-LocalUser -Name 'GCDPAPITest' -Password (Read-Host -AsSecureString 'Password') -Description 'Temporary GC Agent DPAPI test'
   Add-LocalGroupMember -Group 'Users' -Member 'GCDPAPITest'
   ```
2. Do **not** run any step as Administrator, and do not copy `settings.dpapi`
   or anything from `%LOCALAPPDATA%\GitHubCommunityAgent`.

## Account A (aiuser), normal PowerShell

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
$T = 'C:\Users\Public\Documents\GC-Agent-DPAPI-Test'
New-Item -ItemType Directory -Path $T            # must not already exist
$B = Join-Path $T 'gc-agent-dpapi-throwaway.bin'

# A2: create the throwaway blob with GC Agent's own DPAPI module
.\.venv\Scripts\python.exe .\scripts\windows_dpapi_two_account_throwaway.py create --file $B
# A3: same account decrypts it (expected: PASS)
.\.venv\Scripts\python.exe .\scripts\windows_dpapi_two_account_throwaway.py verify --file $B --expect allowed
# A4: record the blob hash; WRITE IT DOWN
(Get-FileHash -LiteralPath $B -Algorithm SHA256).Hash
# A5: method control. The PowerShell verifier must ALSO decrypt A's blob (expected: PASS)
$H = (Get-FileHash -LiteralPath $B -Algorithm SHA256).Hash
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-dpapi-verify-throwaway.ps1 -File $B -Expect allowed -ExpectSha256 $H
# A6: give B the verifier and record its hash; WRITE IT DOWN
Copy-Item .\scripts\windows-dpapi-verify-throwaway.ps1 $T
(Get-FileHash -LiteralPath (Join-Path $T 'windows-dpapi-verify-throwaway.ps1') -Algorithm SHA256).Hash
```

If A3 or A5 does not print `PASS`, stop: the test cannot be valid.

## Account B, signed in as B

Use **Switch user** (Win+L, then pick B). Alternatively, from A's desktop run
`runas /user:"AT Tester" "powershell -NoProfile -NoExit"` and enter B's
password. Then, in B's PowerShell:

```powershell
$T = 'C:\Users\Public\Documents\GC-Agent-DPAPI-Test'
whoami /user                                          # B1: SID must differ from A's
(Get-FileHash (Join-Path $T 'windows-dpapi-verify-throwaway.ps1') -Algorithm SHA256).Hash   # B2: must equal A6
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $T 'windows-dpapi-verify-throwaway.ps1') -Mode SelfCheck
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $T 'windows-dpapi-verify-throwaway.ps1') -File (Join-Path $T 'gc-agent-dpapi-throwaway.bin') -Expect denied -ExpectSha256 '<hash from A4>'
```

### Expected results for B

| Step | Expected output | Meaning |
|---|---|---|
| B1 | A SID different from A's `S-1-5-21-…-1006` | Really a different identity |
| B2 | Same hash as A6 | Verifier not altered |
| SelfCheck | `DPAPI SELF-CHECK PASS` | DPAPI works for B, so a denial is not a broken profile |
| Verify | `Blob read OK`, `DPAPI error: Key not valid for use in specified state.`, `DPAPI outcome: denied`, `PASS`, exit 0 | **Gate 3 evidence** |

How to read other results:
- `INCOMPLETE …` (exit 2): not evidence. B could not read the file, or the
  hash differs. Fix access and repeat.
- `DPAPI error: The data is invalid.`: the blob is damaged, not denied.
  Repeat from A2 with a new folder.
- `DPAPI outcome: decrypted` / `FAIL`: **serious**. Stop, keep all output and
  report it; cross-account isolation did not hold.

## Back as account A: confirm and clean up

```powershell
$T = 'C:\Users\Public\Documents\GC-Agent-DPAPI-Test'
# A7: A can still decrypt the unchanged blob (expected: PASS)
.\.venv\Scripts\python.exe .\scripts\windows_dpapi_two_account_throwaway.py verify --file (Join-Path $T 'gc-agent-dpapi-throwaway.bin') --expect allowed
# Cleanup: remove ONLY the test folder (random bytes + verifier copy)
Remove-Item -LiteralPath $T -Recurse
Test-Path $T                                          # expected: False
```
Sign B out. If you created `GCDPAPITest` only for this test, remove it in an
Administrator PowerShell:
```powershell
Remove-LocalUser -Name 'GCDPAPITest'
Get-CimInstance Win32_UserProfile | Where-Object LocalPath -like '*\GCDPAPITest' | Remove-CimInstance
```
Do not delete `AT Tester` or any account that existed before.

## What to send back for the record

The console output of A3, A5, B1, B2, SelfCheck, the B verify step and A7.
It contains no secrets: only account names, SIDs, hashes and outcomes.
Gate 3 is marked PASS only from that output.
