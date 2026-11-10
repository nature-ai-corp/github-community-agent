# GitHub Community Agent 1.0.0-rc1 — Windows release readiness (GO / NO-GO)

Assessed 2026-11-10 on `feature/unified-task-home` at `d423f49` (PR #11,
Draft). Nothing was merged, tagged, signed or published, and nothing here is
legal approval.

## Verdict (updated 2026-11-10 for the simplified release procedure)

The procedure is now the Worker-style checklist in
[`FINAL_APPROVAL_CHECKLIST.md`](FINAL_APPROVAL_CHECKLIST.md):
- no signed attestation and no internal legal-approval record;
- the Software Release Attestation dated November 10, 2026 has been
  **withdrawn** and is not release evidence;
- counsel review is an **optional** owner choice.

### Final release packaging (2026-11-10)

**Final installer:** `GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe`
(`build/release-staging-rc1-final/`):
- **SHA256:** `018EB04617D3A60314A79D08E0C22CB2CF4D61EE2916383D03CF6708E93DB825`;
- **Size:** 13,081,789 bytes;
- **ProductVersion:** `1.0.0-rc1`;
- **Signature:** NotSigned (an unsigned pre-release is allowed).

It was built from the unchanged verified app build: EXE `0A4B022F…`, CPython
3.13.17 / OpenSSL 3.5.9.

**Final wording:**
- the "DRAFT FOR LEGAL REVIEW" line was removed from `END_USER_TERMS.txt`;
- `NOTICE` now says releases are published on GitHub Releases with SHA256
  checksums, and that pre-releases may be unsigned;
- the internal `legal_review_approved` / `legal_review_note` fields were removed
  from `MANIFEST.json`. A neutral `evidence_note` replaces them, and the
  validator now rejects the obsolete fields;
- all license texts, notices, the SBOM and the Microsoft conditions are
  unchanged and byte-verified.

| Verification on the final installer | Result |
|---|---|
| Automated tests | 344 passed, 1 skipped (CPython 3.13.17); 342 passed, 3 skipped (3.13.14) |
| License package check (`third_party_notices.py check`) | PASS; only `MANIFEST.json` changed |
| Fresh isolated install, byte-verify of every packaged file, uninstall | PASS, 979 files (`license-payload-verification/run-20261110T203344Z`) |
| Upgrade from the previous build, task database and DPAPI preservation | PASS: settings identical, key decryptable, `settings.dpapi` bytes unchanged, Tasks identical, schema migrated, data kept through uninstall/reinstall (`upgrade-continuity/run-20261110T203410Z`) |
| Frozen-EXE security | 13/13 PASS (`security-probe-rc1/final-20261110T203525Z`) |
| TLS / HTTPS | OK (`security-probe-rc1/tls-20261110T203532Z`) |
| Microsoft Defender | No threats; platform 4.18.26100.4, engine 1.1.26100.4, intelligence 1.463.226.0 |
| Real installation and user data | Unchanged in every run |
| Manual license page tests on the final wording | **Prepared, not yet operated**: isolated Decline and Accept builds compiled (`build/manual-license-test/run-20261110T203328Z-decline`, `run-20261110T203342Z-accept`). The earlier person-operated PASS results (below) cover the previous wording |
| CI | Run after push (see the commit record) |

| Area | Verdict |
|---|---|
| Technical (build, tests, installer, upgrade, security) | **GO** |
| Release text inside the installer | **GO**: final wording, no draft or unreleased statements |
| Genuine legal obligations in the shipped build | **Met** |
| Manual license page tests on the **final** binary | **Pending**: run the kit (Decline, then Accept) |
| Owner risk decisions (name kept; terms sufficiency) | Owner (no document required) |
| Clean Windows 11 / SmartScreen check | Recommended, not legally required |
| Owner authorization (merge, tag, publish) | **Not given** |
| **Overall** | **Ready for the owner's final checks and authorization.** Not published, and not authorized to publish |

### Earlier status (superseded)

### Manual license page tests (operated by a person, 2026-11-10)

Kit: `scripts/windows-manual-license-page-test.ps1`. Each run used an isolated
AppId and folder; real installation and data were unchanged in every run.

| Run | Scenario | Setup exit | Installed | Payload verified | Isolated uninstall | Result |
|---|---|---|---|---|---|---|
| `run-20261110T200950Z-decline` | Decline | 0 | yes | yes | clean | **FAIL**: the license was accepted during a Decline run (operator path), so this is not a rejection result |
| `run-20261110T201155Z-decline` | Decline | **2** | **no** | — | — | **PASS** |
| `run-20261110T201301Z-accept` | Accept | 0 | yes | **yes** | **clean** | **PASS** |

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
| Installer rebuilt from HEAD | **Byte-identical** to the verified RC1 installer: SHA256 `F4262E53…22E09EA`, ProductVersion `1.0.0-rc1`, NotSigned. **Superseded** by the text-correction build below | `build/release-staging-rc1/` |
| Text-correction build (NOTICE Worker attribution; terms §1 Apache rights incl. modification; terms §3 VCRUNTIME wording; DRAFT and "not yet released" kept) | First build `CAFEAF6C…8A8E16` (verified, then **superseded**). The line endings of the three installer-embedded texts (`LICENSE`, `NOTICE`, `END_USER_TERMS.txt`) are now pinned to CRLF in `.gitattributes`, so a fresh checkout reproduces the same installer bytes. **Current installer SHA256 `84454641961AF0C9C03435FF1DDC9B2D9956A2996C1265CEED8A8A973D079430`**, NotSigned. Install, byte-verify and uninstall PASS (979 files, `run-20261110T192651Z`); upgrade trial PASS (`run-20261110T192717Z`); Defender: no threats. `SHA256SUMS.txt` and `RELEASE_NOTES.md` updated | `build/release-staging-rc1-v3/` |
| **Interactive wizard probe: unreliable, withdrawn** | On this build, the license page again showed **Next disabled** until "I accept" and disabled again on "I do not accept", with the corrected text and the DRAFT marker. **But** about 13 s after the probe stopped acting (decline selected, then a window-close request), the wizard proceeded to install into the probe's **isolated scratch folder** (931 files, until force-stopped). **Cause since determined** ([`MANUAL_LICENSE_PAGE_TEST.md`](MANUAL_LICENSE_PAGE_TEST.md)): live keyboard/mouse input on this PC, recorded by `GetLastInputInfo` with no harness input, reached the foreground wizard. It was not an installer setting, not a license bypass, and not the harness's own messages. The test-harness design (an interactive wizard on a desktop in use) was the defect. The isolation held: no registry entry; real installation and data unchanged; scratch install removed. The automated probe is no longer used. Acceptance and rejection must be confirmed **manually** in the owner's clean-VM test (§4) | `license-page-probe/probe-v2-*.json` |
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
| CPython redistribution conditions (Microsoft Distributable Code) | No VS license assumed. Conditions (a) and (c) are met. (e) is addressed by the DRAFT terms page reproducing CPython's text verbatim | (Updated) Terms sufficiency: owner risk decision, with legal advice optional. (d) is met by the product; no attestation required. (b) is decided together with the name |
| GitHub independence disclaimer | Shipped in `NOTICE`, the notices, README, the EXE description and the terms page | Owner kept the name (business decision). Trademark acceptability is not approved; that is counsel's call |
| Public-domain notices (SQLite, liblzma) | Project-written statements | Approve the wording (DECISION 4) |

No requirement was removed, and nothing was marked approved. These are the
human items still open, and they block public distribution. The consolidated
decision table is in [`LEGAL_DECISION_REPORT.md`](LEGAL_DECISION_REPORT.md).
It adds one owner item: the Nature AI Worker attribution line required in
`NOTICE` by Apache §4(d).

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

**Reproducibility (verified 2026-11-10).**
- A fresh checkout of the branch builds an installer with **identical
  content**: all 19 installer text inputs are byte-equal, and the package check
  passes.
- The setup EXE's SHA256 also depends on the source **file timestamps**, which
  Inno Setup stores. With the original timestamps applied, a fresh checkout
  reproduced `84454641…079430` exactly.
- **Therefore:** publish the exact verified file
  (`build/release-staging-rc1-v3/GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe`)
  with `SHA256SUMS.txt`. Do not rebuild it from the tag for upload.

**Alternative:** merge only #11 into `main` (it contains all), then close
#6–#9 as included. This is faster, but the review history is less clear.

## 4. Outstanding real-install and SmartScreen validation (owner)

1. **Clean Windows 11 x64 VM** (no developer tools, Defender and SmartScreen at
   their defaults, a standard user):
   - download the asset in Edge over HTTPS (so it gets Mark-of-the-Web);
   - verify the SHA256;
   - record the SmartScreen prompt (expected for an unsigned file: "Unknown
     publisher", then More info → Run anyway);
   - read the terms. **First select "I do not accept" and confirm that Next
     stays disabled and Cancel exits without installing**; then rerun, accept
     and continue. This manual check replaces the withdrawn automated probe;
   - start the app, save a dummy or real key, run Review Issues on a public repo;
   - uninstall and confirm `%LOCALAPPDATA%\GitHubCommunityAgent` remains.
2. **Optional:** upgrade your real installed internal build (real AppId) and
   confirm your Tasks and settings remain.
3. **Defender:** repeat on the final asset if the release-text commit changes
   the installer, which it will.

## 5. Owner decisions and authorization (simplified; superseded the earlier list)

No signed attestation, no internal legal-approval record, and no mandatory
counsel step. What remains:
1. **Risk decisions:**
   - the product name is kept, as decided;
   - publish the terms page as is, minus DRAFT, or get optional legal advice
     first.
2. **Release text:** approve the wording that replaces the `NOTICE` "not yet
   released … awaits human legal review" paragraph, the removal of the DRAFT
   line, and `RELEASE_NOTES.md`.
3. **Authorization:** merges (§3), the immutable tag `v1.0.0-rc1` on `main`, and
   a **GitHub pre-release** with the verified asset and `SHA256SUMS.txt`.

Signing is optional (the unsigned pre-release is allowed and disclosed). An
Inno Setup commercial license is optional (see the checklist, section D).

## Shortest path to the first public Windows pre-release

1. **Owner:** decisions 1–2 above.
2. **Agent, on authorization:** one release-text commit, touching no
   application code:
   - the `NOTICE` paragraph;
   - remove the DRAFT line;
   - drop the internal `legal_review_approved` flag from the generator,
     `MANIFEST.json` and tests;
   - optionally, README "Development status".

   Then rebuild the installer from the verified bundle; re-run the package,
   payload and upgrade checks, the Defender scan and the manual license page
   Decline/Accept tests; regenerate `SHA256SUMS.txt`; update `RELEASE_NOTES.md`;
   CI 7/7.
3. **Owner, recommended:** clean Windows 11 download, SmartScreen check and
   install with the final asset (§4.1).
4. **Owner:** merge #6→#7→#8→#9→#11 with merge commits; verify tree equality;
   tag `v1.0.0-rc1`; publish the GitHub pre-release with **only** the
   allowlisted assets (installer, `SHA256SUMS.txt`, notes); confirm the
   published checksum.
