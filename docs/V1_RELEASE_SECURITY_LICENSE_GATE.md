# GC Agent V1 — Windows release security and license gate

**Status: public release BLOCKED.** This checklist is not a certification, signed package, malware scan, or complete software bill of materials (SBOM).

## Evidence already confirmed on Windows

- All five V1 read-only Community Management Work Types have real application-run evidence.
- Native Windows regression: 214 passed on the earlier head; rerun on latest audit changes.
- PyInstaller onedir, per-user Inno Setup installation, upgrade trial, uninstall and reinstall preserved ten Task records and saved Windows DPAPI credentials.
- Live OpenAI model connection succeeded with the stored encrypted API key.
- Installer is unsigned; app version remains 0.0.0.dev0. The upgrade trial reuses identical application code and does not prove a real code/schema upgrade.

## Security gates

- Verify GitHub is read-only in the installed executable. Fixed GraphQL queries may use HTTP POST but are not GitHub mutations; observe zero actual GitHub write operations.
- Validate user GitHub Discussions token least privilege and no credential leakage into Task reports, SQLite, UI GET responses, browser storage or logs.
- Validate the local HTTP server binds only to 127.0.0.1 and enforces Host, Origin and session nonce on state-changing requests; repeat negative tests on the frozen installed build.
- DPAPI is scoped to the Windows user; it does not defend against malicious software running under the SAME Windows user.
- Check separate Windows test account with no migrated data; ensure no Task history or credential cross-user visibility. Do NOT copy a real settings.dpapi into a second account.
- Preserve app identity separate from Nature AI Worker and enforce user-data retention on upgrade, uninstall and reinstall.
- Independently validate Windows Defender/security findings. Read-only security status is NOT a malware scan.

## License and software inventory gates

- Repository LICENSE is Apache-2.0 and NOTICE names the Nature AI Worker origins; installed package includes both LICENSE and NOTICE.
- These documents do NOT yet prove that PyInstaller, bundled Python interpreter, compiled binaries, httpx dependencies, bootloader and other frozen components have the complete license attribution required for redistribution.
- The offline Python-environment inventory is a CANDIDATE LIST ONLY. It includes build/test dependencies and cannot establish the exact PyInstaller bundle contents or constitute a complete SBOM.
- Review all actual bundled third-party notices, licenses, compiled files, dependency versions and packaging obligations before signing or distribution.
- Establish approved stable product version, exact source commit, hashes and signature verification. No signing certificate is available in this repo.

## Safe Windows audit commands

From the project root:

    git pull --ff-only
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-release-security-preflight.ps1

The release preflight checks the installed vs built executable SHA256, reads Authenticode and optional Defender status, and writes a local build/release-audit/python-environment-dependencies.json candidate inventory. It does not run a scan, sign binaries, disable protections, modify Work data, or publish.

## Still blocked

Latest exact-head regression, separate-account isolation, negative frozen HTTP/token tests, true app-code/schema upgrade, frozen dependency license/SBOM, Windows security review, publisher signing, stable version and PR dependency review. All PRs remain Draft, no merge/tag/release.

## User-run latest Windows release preflight — 2026-11-08

On branch `feature/unified-task-home` at `422dc91` the user executed:

- `windows-upgrade-uninstall-verify.ps1 -Phase AfterReinstall`: **PASS**;
  original work.sqlite3 and settings.dpapi SHA256 equal baseline, 10 Task rows
  including archived, frozen executable self-check passed.
- `windows-test-regression.ps1`: **218 passed in 3.99s**, zero failed,
  `GC Agent Windows regression PASS`.
- `windows-release-security-preflight.ps1`: both frozen bundle and installed
  app self-check passed; installed EXE matched built EXE SHA256.
  Authenticode **NotSigned** (public release BLOCKER).
- Defender status: `AntivirusEnabled=True` and
  `RealTimeProtectionEnabled=True`. No malware scan was run or claimed.
- Candidate Python environment license inventory produced at
  `build/release-audit/python-environment-dependencies.json`:
  **22 distributions, 2 with missing license metadata**.
  Names of the two were NOT present in the user-submitted terminal output.
- Preflight concluded `RELEASE PREFLIGHT INCOMPLETE`: signing, third-party
  notices, Windows security and actual frozen payload review still open.

### Next evidence

From the existing local inventory (do not modify data or run a new audit):

```powershell
$inventory = Get-Content ".\build\release-audit\python-environment-dependencies.json" -Raw | ConvertFrom-Json
$inventory.dependencies | Where-Object license_metadata_missing |
    Select-Object name, version
```

Missing metadata is **not proof of an unlicensed or prohibited component**.
Review actual distribution LICENSE files and exact frozen bundle before
classifying redistribution risk. Do not resolve by inventing license
identifiers or treating the build environment list as a final SBOM.

## License metadata clarification from Windows evidence (Nov 8, 2026)

The user inspected the candidate environment inventory: both entries flagged
`license_metadata_missing` were **github-community-agent 0.0.0.dev0**.
Thus these are *two metadata instances for the project's own first-party
package*, not two identified unlicensed third-party dependencies.

Actions:
- `pyproject.toml` now declares the first-party project's
  `license = "Apache-2.0"` and `license-files = ["LICENSE", "NOTICE"]`.
  Build backend minimum is setuptools 77 so PEP 639 SPDX metadata is
  supported. No public version change.
- The candidate inventory de-duplicates canonical package name + version,
  preserves the number of duplicate metadata instances, and reports
  first-party and THIRD-PARTY missing license metadata independently.
- It does not erase, rewrite or silently invent historical installed
  package license data. A new editable installation/build is required
  before the new project license metadata appears in the environment.

### Native Windows recheck (not yet executed)

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -e ".[dev,build]"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
Rename-Item -LiteralPath .\build\release-audit\python-environment-dependencies.json -NewName python-environment-dependencies-before-license-fix.json
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-release-security-preflight.ps1
```

The previous inventory is preserved under a distinct name. The new audit
should identify zero missing third-party license metadata **if no other
packages changed**; the actual Windows output controls acceptance. Even
zero metadata gaps is not proof of complete redistribution notices, a
bundled-binary SBOM, malware scan, code signing or release approval.

## Native Windows license metadata remediation verified — 2026-11-08

User ran `pip install -e ".[dev,build]"` on branch
`feature/unified-task-home` at `e9eb271`, followed by
`windows-test-regression.ps1` and the read-only
`windows-release-security-preflight.ps1`.

Exact reported results:
- **220 passed in 1.80s**, 0 failed — `GC Agent Windows regression PASS`.
- Frozen onedir and installed EXE self-check PASS; installed EXE equals built
  EXE SHA256.
- Environment inventory: **21 unique distributions**, **22 metadata
  instances**, **one duplicated name/version metadata**.
- **Missing license metadata: 0**.
- **Missing third-party license metadata: 0**.
- Windows Defender AntivirusEnabled=True, RealTimeProtectionEnabled=True,
  but no malware scan was executed.
- Authenticode `NotSigned` — public release BLOCKER.
- The local preflight still correctly reports
  `RELEASE PREFLIGHT INCOMPLETE` because exact frozen payload, required
  third-party redistribution notices, signing and broader security assessment
  remain open.

The previously missing two entries were duplicate first-party
`github-community-agent 0.0.0.dev0` metadata. The SPDX metadata addition
and unique-distribution accounting are therefore **verified as successful
for the build environment**. This result must **not** be extrapolated into
a completed frozen-binary SBOM, malware/security clearance or public-release
approval. The application currently installed for user testing remains the
existing unsigned build; updating editable packaging metadata does not
magically rebuild/sign that installed EXE.
