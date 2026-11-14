# 2.0.0-b1 — production-AppId upgrade acceptance in a clean Windows VM (runbook)

**Status: NOT YET PERFORMED.** The development machine (Windows 11 Home) has no Hyper-V
manager, no Windows Sandbox and no VirtualBox/VMware, and its installed GC Agent is a
`0.0.1-devtrial` build that must not be touched. This test therefore needs a separate, clean
Windows 10/11 x64 VM (or a dedicated physical test machine) operated by the owner.

The isolated random-AppId trial (V1.0.0-rc1 tag source → 2.0.0-b1, 42/42 PASS, see
`RELEASE_READINESS.md`) does **not** substitute for this test: it never used the product AppId
`{B728F255-29F8-438B-B2F7-E495DF0120E1}`, the default per-user install folder or the published
V1 installer binary.

## Inputs (copy into the VM; verify hashes first)

| File | SHA256 |
|---|---|
| `GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe` (published V1 asset) | `018eb04617d3a60314a79d08e0c22cb2cf4d61ee2916383d03cf6708e93db825` |
| `GitHubCommunityAgent-2.0.0-b1-Setup-x64-unsigned.exe` (candidate, from `SHA256SUMS.txt`) | see `SHA256SUMS.txt` |
| this repository at the candidate commit (for `scripts\windows-upgrade-uninstall-verify.ps1` and `scripts\windows-manual-license-page-test.ps1`) | — |

```powershell
Get-FileHash .\GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe -Algorithm SHA256
Get-FileHash .\GitHubCommunityAgent-2.0.0-b1-Setup-x64-unsigned.exe -Algorithm SHA256
```

Use throwaway data only: a disposable AI API key or a fake one, no real GitHub token, no
Bluesky or DEV credentials. Nothing in this runbook publishes anything.

## Steps and expected results

1. **Clean VM snapshot.** No GC Agent installed; `%LOCALAPPDATA%\GitHubCommunityAgent` absent.
2. **Install V1.0.0-rc1** (published installer, normal wizard). On the license page first test
   **Decline**: keep "I do not accept" → Next stays disabled → Cancel → Exit Setup → Yes.
   Expected: nothing installed. Then run it again and **Accept** → Install → Finish.
3. **Create V1 data.** In V1: Settings (provider, model, the throwaway key, a public repository);
   create **10** Tasks (any V1 Work Types; failed runs count); archive one Task.
4. **Baseline (hash-only):** close the app, then
   `powershell -ExecutionPolicy Bypass -File scripts\windows-upgrade-uninstall-verify.ps1 -Phase Baseline`
   Expected: "BASELINE created" (it refuses unless exactly 10 Task records exist).
5. **Upgrade:** run the 2.0.0-b1 installer over V1 (same product AppId). Repeat the license-page
   **Decline** test first (expected: V1 stays installed and unchanged), then **Accept**.
6. **Verify after upgrade (do not start V2 yet):** `... -Phase AfterUpgrade`. Expected: data
   byte-identical to the baseline, EXE self-check and read-only diagnostics pass, 10 Tasks.
   Apps & features shows **GitHub Community Agent 2.0.0-b1** (one entry, not two).
7. **Uninstall** (Apps & features), then `... -Phase AfterUninstall`. Expected: program folder and
   registry entry removed; `%LOCALAPPDATA%\GitHubCommunityAgent` kept and byte-identical.
8. **Reinstall 2.0.0-b1**, then `... -Phase AfterReinstall`. Expected: data byte-identical, 10 Tasks.
   (The hash-based phases must all run before V2's first start: the first start migrates the
   database by adding the Promotion tables, after which the V1 baseline no longer matches.)
9. **First start of V2.** Expected: settings shown with "key stored"; all 10 Tasks with their
   Activity History; the archived Task under Archived Work; New Task → Promotion offers exactly
   GitHub Discussions, Repository Optimization, Bluesky and DEV Community; Settings → Promotion
   offers GitHub, Bluesky and DEV Community; a Promotion draft cannot be approved before
   "Mark technical review complete". Close the app; `work.sqlite3` now contains the
   `promotion_*` tables; `settings.dpapi` is unchanged.
10. **Uninstall once more** and confirm `%LOCALAPPDATA%\GitHubCommunityAgent` (migrated data) is
    kept. Record results (license-page screenshots, script outputs, Apps & features) in
    `RELEASE_READINESS.md` §C and revert the VM snapshot.

## Pass criteria

All steps behave as expected; any deviation is a release blocker. Do not continue after a
script reports "STOP"; do not restore or delete data to make a check pass.
