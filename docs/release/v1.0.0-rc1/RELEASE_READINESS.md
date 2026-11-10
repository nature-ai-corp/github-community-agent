# GitHub Community Agent 1.0.0-rc1 — Windows release readiness (GO / NO-GO)

Assessed 2026-11-10 on `feature/unified-task-home` at `d423f49` (PR #11,
Draft). Nothing was merged, tagged, signed or published, and nothing here is
legal approval.

## Verdict

| Area | Verdict |
|---|---|
| Technical (build, tests, installer, upgrade, security, CI) | **GO** |
| Release text inside the installer | **NO-GO** until updated: `NOTICE` says "not yet released … awaits human legal review"; the terms page says "DRAFT FOR LEGAL REVIEW" |
| Legal approvals | **NO-GO** until decided by counsel or the owner (below) |
| Real-install / SmartScreen validation | **Pending** (owner, on a clean Windows 11 PC/VM) |
| Owner authorization (merge, tag, publish) | **Not given** |
| **Overall** | **NO-GO for public publication today.** Technically ready; blocked only by the human decisions below |

## Owner decisions in effect

- **Windows-only V1:** no Linux work.
- **Name and features:** keep the name "GitHub Community Agent", the five Work
  Types and Apache-2.0. No new features.
- **Signing:** optional for the first pre-release.
- **Disclaimer:** keep the independence disclaimer.
- **Visual Studio license:** none is assumed merely because CPython includes
  Microsoft runtime components.

## 1. Completed technical checks (this assessment, HEAD `d423f49`)

| Check | Result | Evidence |
|---|---|---|
| Functionality frozen | Working tree clean; no app change since the RC verification | `git status` |
| Installer rebuilt from HEAD | **Byte-identical** to the verified RC1 installer: SHA256 `F4262E53…22E09EA`, ProductVersion `1.0.0-rc1`, NotSigned | `build/release-staging-rc1/` |
| Clean install, byte-verify, uninstall (isolated AppId and folder) | PASS, 979 files (958 bundle + 16 third-party + LICENSE, NOTICE, END_USER_TERMS) | `license-payload-verification/run-20261110T183400Z` |
| Terms page acceptance and rejection (isolated wizard; Next never pressed) | First page = terms; default "I do not accept" with **Next disabled**; "I accept" enables Next; declining disables it again; page text shows the DRAFT marker and the Microsoft section; nothing installed | `license-page-probe/probe-final-*.json` |
| Upgrade from the previous build (OLD `a2bc626`, CPython 3.13.14 / OpenSSL 3.0.21 → RC1) | PASS: settings identical; DPAPI key decryptable; `settings.dpapi` bytes unchanged; Tasks identical; schema migrated; data kept through uninstall; reinstall read 3 Tasks; trial registry entry removed | `upgrade-continuity/run-20261110T183426Z` |
| Unrelated and real user data | The real installation, `work.sqlite3` and `settings.dpapi` are unchanged after every run; isolated builds cannot target real folders (compile error, plus a `PrepareToInstall` guard) | each summary; `tests/test_isolated_installer_builds.py` |
| Frozen-EXE security | 13/13 PASS (Host, Origin and nonce 403; size 413; stall; health) | `security-probe-rc1/final-20261110T183552Z` |
| TLS / HTTPS (OpenSSL 3.5.9 + certifi) | OK | `security-probe-rc1/tls-20261110T183559Z` |
| Microsoft Defender (this exact installer, app EXE, bundle) | No threats (intelligence 1.463.226.0) | gate doc |
| DPAPI cross-account | PASS (owner-run) | gate doc, Gate 3 |
| Automated tests | 337 passed, 1 skipped (CPython 3.13.17); 335 passed, 3 skipped (3.13.14) | local |
| CI, PR #11 head | 7/7 PASS (run 42868272713) | GitHub Actions |
| CI, PR #6–#9 heads | Previously blocked by billing (0 steps). Re-run today: **PASS** (3/3 each: that era's workflow had Ubuntu 3.11–3.13 only) | runs 42432608449, 42435394681, 42435919929, 42437278170 (attempt 2) |
| Version, SBOM, notices | `1.0.0rc1` everywhere; package check PASS; `legal_review_approved: false` (unchanged, correct) | gate doc |

## 2. Release-license documentation review

| Item | Technical state | Open human decision |
|---|---|---|
| Apache-2.0 application license | `LICENSE` and `NOTICE` installed and byte-verified | `NOTICE` last paragraph ("not yet released … awaits human legal review") must be updated at release |
| Third-party notices and SBOM | All 958 bundle files classified; 16 license files installed and byte-verified | Approve the package for the exact MANIFEST hash set (DECISION 1); pin governance (DECISION 5) |
| certifi (MPL-2.0) source | Exact sdist shipped and checked against the frozen files | Confirm that this meets MPL §3.2 (DECISION 2) |
| CPython redistribution conditions (Microsoft Distributable Code) | No VS license assumed. Conditions (a) and (c) are met. (e) is addressed by the DRAFT terms page reproducing CPython's text verbatim | Counsel to approve or replace the DRAFT terms; owner attestation for (d), "not malicious, deceptive or unlawful"; (b) is decided together with the name |
| GitHub independence disclaimer | Shipped in `NOTICE`, the notices, README, the EXE description and the terms page | Owner kept the name (business decision). Trademark acceptability is not approved; that is counsel's call |
| Public-domain notices (SQLite, liblzma) | Project-written statements | Approve the wording (DECISION 4) |

No requirement was removed, and nothing was marked approved. These are the
human items still open, and they block public distribution.

## 3. PR dependency audit (#6 → #7 → #8 → #9 → #11)

**Stack:** `main (dde0d25)` ← #6 `1c6a27f` ← #7 `73643db` ← #8 `bb2bd1b` ← #9 `a33de01` ← #11 `d423f49`.
- Each PR's base is the previous PR's branch, and each base is an ancestor of
  the next head.
- `d423f49` contains every earlier PR.
- All five are Draft, `MERGEABLE`, and now `CLEAN`.
- **Conflicts:** none, because the history is linear.

**Required checks:** no branch protection (private repo, Free plan), so nothing
is enforced. Policy: CI green on each PR head before it is merged. Current
state: #6–#9 green (3-job legacy workflow), #11 green (7 jobs).

**Safe merge order (owner action; not performed):**
1. Mark #6 ready, then merge into `main` with **"Create a merge commit"**.
   - Do **not** squash or rebase: that rewrites the commits that #7–#11 also
     contain and would create conflicts or duplicates further down the stack.
   - Do **not** delete the head branch until the next PR has been retargeted.
2. Retarget #7 to `main` (Edit → base). Let CI run, then merge with a merge
   commit.
3. Repeat for #8 and #9.
4. Repeat for #11 last.
5. **Verify:** `git rev-parse origin/main^{tree}` must equal
   `git rev-parse d423f49^{tree}` (or the tree of the final release-text
   commit). If they match, no rebuild is needed: the verified installer
   corresponds exactly to `main`.

**Alternative:** merge only #11 into `main` (it contains all), then close
#6–#9 as included. This is faster, but the review history is less clear.

## 4. Outstanding real-install and SmartScreen validation (owner)

1. **Clean Windows 11 x64 VM** (no developer tools, Defender and SmartScreen at
   their defaults, a standard user):
   - download the asset in Edge over HTTPS (so it gets Mark-of-the-Web);
   - verify the SHA256;
   - record the SmartScreen prompt (expected for an unsigned file: "Unknown
     publisher", then More info → Run anyway);
   - read and accept the terms; confirm that declining blocks the install;
   - start the app, save a dummy or real key, run Review Issues on a public repo;
   - uninstall and confirm `%LOCALAPPDATA%\GitHubCommunityAgent` remains.
2. **Optional:** upgrade your real installed internal build (real AppId) and
   confirm your Tasks and settings remain.
3. **Defender:** repeat on the final asset if the release-text commit changes
   the installer, which it will.

## 5. Owner approvals required

1. **Legal path for the pre-release.** Either counsel approves (or replaces) the
   DRAFT terms and the license items in §2, **or** the owner explicitly and in
   writing accepts publishing the pre-release before that review. That second
   option is an owner risk decision; the agent will not make it.
2. **Owner attestation for condition (d).**
3. **Release text.** Approve the final wording of the `NOTICE` last paragraph
   and the terms header (remove "DRAFT"/"not yet released" only once item 1 is
   decided), and the release notes (`RELEASE_NOTES.md`).
4. **Merges.** Authorize the merges (§3), the tag `v1.0.0-rc1` on `main`, and
   publication as a **GitHub pre-release** with the asset and `SHA256SUMS.txt`.
5. **Signing.** Optional, per the owner decision. If skipped, the release notes
   disclose it (done).

## Shortest safe path to the first public Windows pre-release

1. **Owner/counsel:** decide item 1 and attest (d) — the only true blockers.
2. **Agent (on authorization):** one release-text commit. It updates the
   `NOTICE` last paragraph and the terms header, and README "Development status"
   if wanted, and touches no application code. Then rebuild the installer from
   the verified bundle, re-run the package check, payload, terms-page and
   upgrade checks and the Defender scan, regenerate `SHA256SUMS.txt`, update
   `RELEASE_NOTES.md` with the new hash, and confirm 7/7 CI. About 30–45 minutes.
3. **Owner:** clean Windows 11 VM install and SmartScreen check with the final
   asset (§4.1). About 30 minutes.
4. **Owner:** merge #6→#7→#8→#9→#11 as in §3; verify the tree equality.
5. **Owner:** tag `v1.0.0-rc1` on `main`; create a GitHub Release marked
   **pre-release**, with the asset and `SHA256SUMS.txt`, using
   `RELEASE_NOTES.md` as the description.

Signing, the Azure setup and the real-AppId upgrade are not on this path.
Signing is optional, and the upgrade is recommended but not required.
