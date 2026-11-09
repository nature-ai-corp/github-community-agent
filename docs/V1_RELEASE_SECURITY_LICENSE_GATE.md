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

## Actual PyInstaller onedir manifest and embedded modules — source prepared, Windows run pending

The environment dependency metadata check is complete (**220 passed**
native Windows regression on the prior head; 21 unique environment packages,
0 missing license metadata). This does **not** establish which files or
embedded modules actually shipped.

New two-part, offline, read-only audit:
- `scripts/frozen_bundle_inventory.py`: hashes every real file under the
  existing `dist\\GitHubCommunityAgent` onedir folder and reports actual
  relative path, SHA256, byte size and a coarse file kind. Rejects customer
  DBs/DPAPI/secret-like files, symbolic links and Windows junctions.
  The file manifest is actual payload evidence, **not** a legal SBOM.
- `scripts/windows-frozen-payload-audit.ps1`: runs the Python inventory,
  then PyInstaller's `pyi-archive_viewer --brief --recursive` against the
  existing frozen EXE, recording internal archive-module names without
  extraction or executing GC Agent. These are documented PyInstaller 6
  inspection options.

The audit preserves previous files and refuses to overwrite its own output.
Expected results under `build\\release-audit`:

- `frozen-bundle-files.json`
- `frozen-embedded-archive.txt`

Run from an existing Windows build (the installed executable and customer
data are unchanged):

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-frozen-payload-audit.ps1
```

**Acceptance requires reviewing the output, not just a successful audit
command.** In particular, inspect all DLL/PYD runtime binaries, embedded
third-party Python modules, original license texts, PyInstaller bootloader
exception, bundled Python runtime and third-party redistribution notices.
Do not infer actual license identifiers from file extensions. This inventory
also does not assess the Inno Setup compressed installer EXE itself; its
installed LICENSE/NOTICE were reviewed separately. Windows signatures,
malware/security scans and multi-account isolation are still open.

No public release, merge, tag or code signing is authorized.

## Frozen manifest failure: bundled PEM classification (2026-11-08)

The user executed the Windows frozen-payload audit after **227 pytest
tests passed (0 failures)**. The file inventory blocked at
`ValueError: Forbidden user-data or secret-like file in frozen bundle`.
The original script treated **every .pem** as a customer secret, but
PyInstaller can bundle `certifi/cacert.pem`, which is a *public CA
certificate trust bundle* rather than a private key.

The error did **not report which file** caused this particular failure;
the certifi PEM explanation is a plausible root cause, not confirmed
from the original log. A narrow correction has been prepared:
- Only `_internal/certifi/cacert.pem` can be treated as a public
  certificate bundle, and only if the file is small and all PEM BEGIN/END
  sections are `CERTIFICATE`. All other PEM files and secret-like files
  remain blocked.
- A blocked file now reports its **relative path only** without printing
  its contents or exposing Windows user paths.
- Added tests for the CA trust bundle, private-key rejection even at the
  permitted filename, and arbitrary PEM rejection.

Windows must rerun the tests and inventory; do not treat the prior blocked
audit as PASS and do not modify the frozen bundle by hand. If a different
path is flagged, inspect the path and adjust rules only with evidence.
The audit remains incomplete until the file manifest and PyInstaller
recursive archive listing both succeed and are reviewed.

## Actual frozen payload inventory — Windows PASS (2026-11-08)

The user ran native Windows test and frozen-payload audit on source branch
`feature/unified-task-home` at `22fd448`, and provided the full output:

- `windows-test-regression.ps1`: **230 passed in 1.95s**, 0 failures.
- `windows-frozen-payload-audit.ps1`: manifest created successfully:
  **958 files**, **31,332,500 bytes**.
- Categories: **1 archive**, **26 binaries**, **1 license/notice candidate**,
  **926 other files**, **1 public CA certificate bundle**, **3 UI assets**.
- PyInstaller embedded recursive archive listing successfully generated:
  **717 lines**.
- Manifest: `build/release-audit/frozen-bundle-files.json`.
- Embedded archive: `build/release-audit/frozen-embedded-archive.txt`.
- No user files, installed applications, credentials, Windows Defender
  settings or GitHub data were modified by the audit.

The earlier broad `.pem` block had been narrowed to allow only the known
public certifi CA bundle with certificate-only content. This time the
inventory **completed**, so that classification issue is operationally
resolved for this build.

**Accepted:** reproducible read-only *file-and-archive inventory generation*.
**Not accepted:** complete SBOM, dependency origin attribution, per-binary
redistribution licensing, notices completeness, malware scan, code signing
or public release.

### Next local inventory extract — no rebuild, no credential disclosure

Run in the Windows project directory against the already-generated manifest:

```powershell
$report = Get-Content ".\build\release-audit\frozen-bundle-files.json" -Raw | ConvertFrom-Json
$report.files | Where-Object { $_.kind -in @("binary","archive","license_or_notice_candidate","public_ca_certificates") } |
    Select-Object path, kind, size_bytes | Format-Table -AutoSize
```

Provide the resulting list, or summarize it. Do not upload a full
local environment dump or secret-bearing files. Review the archive
listing too, but do not assume the number of listing lines equals the
number of independent third-party packages. Need to map each included
component to an origin/version/license before distribution.

## Binary/file-origin review from user-provided manifest extract (2026-11-08)

The user supplied the path/kind/size inventory filtered to 26 binaries,
one archive, one license/notice candidate and one public CA certificate:
29 records. Observed notable components (not yet full verified SBOM):

| Origin candidate | Observed files | License-review scope |
| --- | --- | --- |
| CPython Windows 3.13 | `python313.dll`, `base_library.zip`, `_asyncio.pyd`, `_ssl.pyd`, `_hashlib.pyd`, `_sqlite3.pyd` etc. | CPython license, Python's bundled extension/linkage notices |
| OpenSSL 3 runtime | `libcrypto-3.dll`, `libssl-3.dll` | OpenSSL 3 Apache-2.0 license; confirm exact binary origin and version |
| SQLite engine | `sqlite3.dll`, `_sqlite3.pyd` | Core SQLite declared public domain; confirm precise build origin |
| Tcl/Tk 8.6 | `tcl86t.dll`, `tk86t.dll`, `_tkinter.pyd`, `_tk_data/license.terms` | Retain licensing text; review Tcl/Tk and bundled script resources |
| C runtime / other native libs | `VCRUNTIME140.dll`, `libffi-8.dll`, `zlib1.dll`, `pyexpat.pyd` | Need origin-specific version, attribution and redistribution checks |
| TLS CA bundle | `_internal/certifi/cacert.pem` | Public trust store; provenance and certifi license still require checking |
| PyInstaller bootloader | `GitHubCommunityAgent.exe` | PyInstaller bootloader licensing/exception and binary signing remain open |

**Important correction:** Tkinter/Tcl/Tk cannot be marked unused or
removed solely because the installed Work Center uses a web page.
`src/github_community_agent/desktop.py` imports Tkinter at module load
and defines a legacy `CommunityDesktop` UI; `work_center.py` imports
`execute_workflow` from `desktop.py`, so ordinary Work Center execution
has a code-level dependency on that module. Removing Tk/Tkinter without
refactoring would risk a runtime regression. No changes to the working
frozen package are authorized. A future simplification should separate
workflow logic from Tk GUI in its own PR, then rebuild and rerun real
Windows acceptance before considering an exclusion.

The observed sole license/notice candidate `_internal/_tk_data/license.terms`
is **not evidence that this bundle contains all necessary third-party license
texts**. The 926 files classified as 'other' have not been analyzed.
The PyInstaller recursive archive output has 717 lines, but package
identity/version/license coverage is not derived from line count.

Official background sources for *general upstream licensing* (not exact
binary verification):
- OpenSSL 3: https://openssl-library.org/source/license/index.html
- Tcl/Tk: https://www.tcl-lang.com/software/tcltk/license.html
- SQLite: https://www.sqlite.org/copyright.html
- CPython on Windows: https://docs.python.org/3.13/using/windows.html

### Local, existing-manifest follow-up — inspect remaining 926 files

```powershell
$report = Get-Content ".\build\release-audit\frozen-bundle-files.json" -Raw | ConvertFrom-Json
$report.files | Where-Object kind -eq "other" |
    Group-Object { ($_.path -split "/")[1] } |
    Sort-Object Count -Descending |
    Select-Object -First 15 Count, Name
$report.files | Where-Object { $_.kind -eq "license_or_notice_candidate" } |
    Select-Object path, size_bytes
```

The first grouping is only a descriptive folder summary. To avoid
incorrect package attribution (e.g. `_internal/_tk_data`, `_internal/tcl`
and `_internal/tk` paths), inspect actual relative paths before assigning
software components or licensing obligations.

**Status:** file list reviewed in part, release still BLOCKED on complete
provenance, licenses, signing, frozen security/AV assessment and additional
Windows acceptance.

## Remaining 926 onedir 'other' resources — Windows user evidence (Nov 8, 2026)

A read-only PowerShell grouping of the existing frozen-bundle manifest
shows **all 926** items categorized `other` are in just four directories:

| Directory | Other files |
| --- | ---: |
| `_tcl_data` | 832 |
| `_tk_data` | 88 |
| `tcl8` | 5 |
| `certifi` | 1 |
| **Total** | **926** |

Therefore **925/926** of the `other` entries (99.9%) are concentrated
under Tcl/Tk-related directory names. Folder names are *origin clues*,
not a formal mapping of all files to a verified upstream distribution,
version, notice or license. The remaining one item is in `certifi`;
the already classified public `cacert.pem` is counted **separately**
from these 926 `other` files.

This supports preserving current Tkinter/Tcl/Tk dependencies while the
application still imports `execute_workflow` from `desktop.py` and that
module imports Tkinter. A smaller, Web-only distribution may be possible
**only after** separating the workflow logic from Tkinter UI in a separate
reviewed change and performing full frozen Windows reacceptance. No
current installer cleanup, rebuild or code exclusion is authorized.

Remaining work on **actual frozen binary SBOM** includes mapping each
embedded archive Python module to a package/version, inspecting the full
licenses and required notices for Tcl/Tk, CPython, OpenSSL, libffi, zlib,
Microsoft runtime, certifi, PyInstaller and any other real bundled
dependency, and verifying the installer's own included documentation.
The archive listing alone is not a signed or complete SBOM.

## PyInstaller embedded-module triage tool (Nov 8, 2026) — Windows execution pending

The prior Windows run created a **717-line** embedded-archive listing.
The new offline `scripts/frozen_archive_module_triage.py` reads that
existing text file and makes *candidate classifications* for quoted
PyInstaller module names:

- `first_party`: `github_community_agent.*`
- `stdlib_candidate`: modules whose top-level name is in the current
  Python interpreter's `sys.stdlib_module_names`
- `environment_distribution_candidate`: names mapping through
  `importlib.metadata.packages_distributions()` to installed Python
  distribution names, not necessarily frozen versions
- `unresolved`: no such mapping; manual review required

Only the *first quoted item per line* is interpreted, so labels such as
`PYMODULE` are not double-counted. The original line count, parse
occurrences, unique candidate names and unmatched lines are all reported,
and uncertainty is preserved. The parser is intentionally conservative
and may miss or misclassify some PyInstaller listings. No external API,
client credentials, AppData, installed files, binary execution or
network access are used.

### User Windows step

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
.\.venv\Scripts\python.exe .\scripts\frozen_archive_module_triage.py --archive-list ".\build\release-audit\frozen-embedded-archive.txt" --output ".\build\release-audit\frozen-module-triage.json"
```

The script refuses to overwrite an existing triage file. Keep the older
manifests unchanged. Provide the console summary and (optionally) only the
unresolved *module names*, not the entire report or any secrets.
This source audit **does not close SBOM, version/provenance, licenses, third-party
NOTICE, code signing or public release gates**.

## Windows archive-triage result — parser failed to cover actual file (2026-11-08)

The user ran the newly added `frozen_archive_module_triage.py` against
the prior actual 717-line PyInstaller listing. The source regression suite
reported **234 passed in 2.02s, zero failed**. However, the parser produced:

- Original listing: **717 lines**
- Matched module occurrences: **3**
- Unique parsed names: **2**
- Unmatched listing lines: **714**
- Classified `unresolved`: **2**

**Status: TRIAGE FAILED COVERAGE / INVALID SBOM EVIDENCE.** The current
parser assumes PyInstaller archive member names appear in quotes. The
actual archive-list format is not yet available in the review context,
so we cannot conclude which output convention it uses or fix it by guessing.
Do **not** interpret the 714 unmatched lines as 714 dependencies or
third-party licensing failures. The underlying frozen file inventory
(958 files) and the real 234-test native Windows regression remain valid.

Before changing the parser, capture a *small, sanitizable sample* of the
existing local file, without reading secrets or publishing the entire report:

```powershell
Get-Content ".\build\release-audit\frozen-embedded-archive.txt" -TotalCount 30
```

Review the output for user-specific paths before sharing. Next update must
include fixtures that reflect the **observed** PyInstaller output and fail
when source coverage is inadequate; never declare SBOM complete based solely
on a parsing success. Preserve the prior generated report and raw listing.

## Embedded archive parser corrected from ACTUAL Windows format (2026-11-08)

The user supplied the first 30 lines of `frozen-embedded-archive.txt`.
Unlike the synthetic original fixtures, `pyi-archive_viewer --brief
--recursive` shows indented bare names beneath `Contents of ...`
headers. For example:

```text
Contents of 'PYZ.pyz' (PYZ):
 __future__
 _aix_support
 _colorize
 _pytest
 _pytest._version
 _pytest.outcomes
```

The initial 3/717 parse was therefore invalid. The parser now accepts
unquoted indented identifiers, does not treat `PYZ.pyz` as a module,
continues accepting legacy quoted-list fixture lines, preserves unmatched
line counts, and flags common development module candidates.

**New release-risk finding (requires diagnosis):** The ACTUAL frozen
EXE archive listing includes at least `_pytest`, `_pytest._version`,
`_pytest.outcomes`. These appear to be pytest test framework modules,
not a normally necessary production dependency. Their presence is
observed, but **cause, impact and full extent are not yet proven**.
Do not delete bundled files manually or assume that pytest was shipped
unavoidably. Diagnose whether `PyInstaller` collected this through
`desktop.py`, `work_center.py`, the launcher, analysis hooks or an
unexpected import, and if optimization is justified do it in a separate
reviewed code/build change with full real Windows reinstall acceptance.

### Windows re-validation without rebuilding or overwriting audit evidence

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
Rename-Item -LiteralPath .\build\release-audit\frozen-module-triage.json -NewName frozen-module-triage-before-format-fix.json
.\.venv\Scripts\python.exe .\scripts\frozen_archive_module_triage.py --archive-list ".\build\release-audit\frozen-embedded-archive.txt" --output ".\build\release-audit\frozen-module-triage.json"
```

Preserve the old invalid report for audit traceability. The printed
`Development module candidates`, `Unmatched listing lines`,
`unique names` and `unresolved` counts determine next review.
High unmatched count or unexpected classified names mean the report is
still incomplete. This only reads the already generated archive listing,
not customer data, and makes no installed-product changes.
