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

## Follow-up: archive triage regex escaping failure and precise fix

Native Windows test at `06967e1` reported **231 passed / 5 failed**
(total 236). All five failures were the new archive triage tests.
The same triage script matched **zero** of 717 lines; its report
therefore has no SBOM value and is retained as failed audit evidence.

Root cause confirmed in the source: raw regex literals accidentally
contained *double backslashes* (`\\\\s`, `\\\\d`, `\\\\.`),
so they matched literal escape characters rather than whitespace,
digits, or module-name periods. This affected both the bare-name
regex and the quoted-list prefix.

Commit `b59e366` replaces these with the intended single-backslash
raw regex sequences. Local isolated expression checks confirmed
matching sample bare names `_pytest.outcomes` and
`gc_agent_launcher`, quoted sample `0, 'httpx'`, while the archive
name `PYZ.pyz` remains excluded as a module by the existing filter.
These local checks are **not a replacement for the full native Windows
regression**, which must be rerun.

User Windows steps (preserving the previous unsuccessful triage JSON):

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
Rename-Item -LiteralPath .\build\release-audit\frozen-module-triage.json -NewName frozen-module-triage-before-regex-fix.json
.\.venv\Scripts\python.exe .\scripts\frozen_archive_module_triage.py --archive-list ".\build\release-audit\frozen-embedded-archive.txt" --output ".\build\release-audit\frozen-module-triage.json"
```

Do not remove the suspected `_pytest` modules or alter the installed
application before confirming the corrected inventory and its provenance.
All release gates remain open.

## Native Windows corrected embedded-module triage — verified (2026-11-09)

User pulled branch `feature/unified-task-home` through `924de96`,
ran `windows-test-regression.ps1` and reanalyzed the preserved actual
PyInstaller embedded archive. Results:

- **236 passed in 1.94s, 0 failed**.
- Archive listing **717 lines**, **711 matched module occurrences**,
  **711 unique parsed names**, **6 unmatched lines**.
- Classified candidates: **11 first_party**, **228 stdlib_candidate**,
  **462 environment_distribution_candidate**, **10 unresolved**.
- **343 development module candidates**; examples from actual audit include
  `_pytest`, `_pytest._version`, `_pytest.outcomes`, `pygments`,
  `pygments.console`, and many `pygments.*` submodules.
- `frozen-module-triage.json` created; previous failed audit outputs preserved.

**Accepted**: corrected module parsing substantially covers the actual
archive listing and its tests pass on native Windows. **NOT accepted**:
full SBOM or evidence that 343 distinct *packages* are included. These
are module names, not distributions. Candidate mappings originate from
the installed development environment, and may not identify the exact
provenance or versions of frozen modules.

### Immediate targeted review without rebuilding or modifying installed app

```powershell
$triage = Get-Content ".\build\release-audit\frozen-module-triage.json" -Raw | ConvertFrom-Json
$triage.members | Where-Object category -eq "unresolved" |
    Select-Object member, candidate_distributions
$triage.members | Where-Object category -eq "environment_distribution_candidate" |
    ForEach-Object { $_.candidate_distributions } |
    Sort-Object -Unique
$triage.development_module_candidates |
    ForEach-Object { ($_ -split '\\.')[0] } |
    Group-Object | Sort-Object Count -Descending |
    Select-Object Count, Name
```

Investigate the actual import graph and PyInstaller hook analysis before
excluding `pytest`, `pygments` or other packages. The observed `_pytest`
and `pygments` content is a build-hygiene concern, not proof of unsafe
functionality. **Do not delete files in the current proven executable**;
any future explicit exclusions require a separate build, real Windows
functional acceptance, installer continuity and security review.

Release remains blocked on full binary/component provenance, licenses
and notices, signed artifacts, security checks, independent user isolation,
real changed-code upgrade and approved version.

## Follow-up provenance from actual Windows triage JSON (2026-11-09)

User ran read-only queries against the corrected
`frozen-module-triage.json`. All **10** items classified
`unresolved` are identifiable as the first-party launcher or
PyInstaller runtime/bootstrap helpers:

`gc_agent_launcher`, `pyi_rth__tkinter`,
`pyi_rth_inspect`, `pyi_rth_multiprocessing`,
`pyi_rth_pkgutil`, `pyiboot01_bootstrap`,
`pyimod01_archive`, `pyimod02_importers`,
`pyimod03_ctypes`, `pyimod04_pywin32`.

They should not be reported as ten unknown unrelated third-party
distribution packages. The triage tool's generic category remains
literal; this human-origin attribution does not prove the exact bundled
PyInstaller build hash or its license obligations.

Installed-environment candidate distribution names extracted from the
archive module list: `anyio`, `certifi`, `h11`, `httpcore`,
`httpx`, `idna`, `packaging`, `Pygments`, `pytest`,
`typing_extensions`. This candidate list is **not** a validated set
of exact bundled versioned components.

Of **343** flagged dev module names, **340** have top-level
`pygments` and **3** have `_pytest`. 343 is the number of **module
names**, not the number of Python distributions. Read-only GitHub
source inspection of launcher, Work Center, desktop and core model/
analyst modules showed no direct `pytest` or `pygments` import in
those entry paths; this does **not** rule out indirect imports,
metadata hooks or PyInstaller auto-collection.

### Next diagnostic: inspect existing PyInstaller import-reference graph

Existing build work directory should contain a PyInstaller import graph
`xref-GitHubCommunityAgent.html`. Avoid editing or deleting it.
Check for the file first:

```powershell
Get-ChildItem ".\build\gc-agent-pyi" -Filter "xref-*.html" |
    Select-Object Name, Length, FullName
```

If present, inspect locally for the import chains into `pygments`
and `_pytest`. Do not infer a removable production dependency from
module name alone. If absent, the current real audit evidence is still
valid; do not rebuild existing accepted EXE just to create it.
Optimization should use a separate candidate build and require
repeat frozen functional/security/installer acceptance. No current
code exclusion or official release is authorized.

## Initial xref excerpt confirms pytest origin, not complete import chain (2026-11-09)

The user located the PyInstaller build-time module graph under
`build/gc-agent-pyi/GitHubCommunityAgent/xref-GitHubCommunityAgent.html`
and supplied the first 15 pattern matches from a `Select-String`
search for `_pytest|pygments`. The excerpt includes actual nodes
`_pytest`, `_pytest._version`, `_pytest.outcomes` and source
URLs under the Windows repository's
`.venv/Lib/site-packages/_pytest/` directory.

This establishes that those pytest modules are included from the
development Python environment; the excerpt does **not** reveal the
full directed path from `gc_agent_launcher` to the pytest/Pygments
root nodes. The `pygments.formatters.img` match in the early output
appears as an importer of a different missing module and does not
by itself show who imports Pygments. Avoid assigning responsibility
to httpx, hooks, or the application without directed evidence.

### Targeted importer extraction using the existing xref, no rebuild

```powershell
$xref = ".\build\gc-agent-pyi\GitHubCommunityAgent\xref-GitHubCommunityAgent.html"
$html = Get-Content -LiteralPath $xref -Raw
foreach ($module in @("pygments","pygments.lexers","_pytest","_pytest.outcomes")) {
    $marker = '<a name="' + $module + '"></a>'
    $start = $html.IndexOf($marker, [StringComparison]::Ordinal)
    if ($start -lt 0) { Write-Host "$module : node not found"; continue }
    $next = $html.IndexOf('<div class="node">', $start + $marker.Length, [StringComparison]::Ordinal)
    if ($next -lt 0) { $next = $html.Length }
    $node = $html.Substring($start, $next - $start)
    $match = [regex]::Match($node, '(?s)imported by:\s*(.*?)</div>')
    if (-not $match.Success) { Write-Host "$module : no imported-by section"; continue }
    $parents = [regex]::Matches($match.Groups[1].Value, '<a href="#([^"]+)">') |
        ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
    Write-Host "$module imported by: $($parents -join ', ')"
}
```

This displays *immediate importers*, not a full transitive entrypoint
trace. If it shows PyInstaller hooks or runtime helpers, follow them
only with evidence. Do not edit the installed EXE or delete existing
PyInstaller files; the full reviewed signed/licensed SBOM is still open.

## PyInstaller xref: importer evidence for Pygments and pytest (2026-11-09)

Actual Windows user-run `xref-GitHubCommunityAgent.html` importer
extraction (after 236 native tests PASS) identifies the following **direct
static import edges**:

- `httpx._main` → `pygments.lexers`.
  The large set of `pygments.lexers.*` submodules imports
  `pygments.lexers` and `pygments`, explaining the candidate
  340-module Pygments footprint. Static imports alone do not establish
  that all lexers are used at runtime.
- `anyio._backends._asyncio` → `_pytest.outcomes` →
  `_pytest`; also `_pytest.outcomes` → `_pytest` and
  `_pytest._version` → `_pytest`.
  This explains the three observed `_pytest` module candidates in
  the frozen archive.

These are **immediate importer relationships**, not proof that removing
dependencies would preserve every executed code path. In particular the
xref does not prove if `httpx._main` CLI highlighting is reached by
GC Agent or whether AnyIO's pytest reference is exercised. The original
source uses `httpx` as an HTTP client and does not directly import
Pygments or pytest in the reviewed entrypoints.

### Release engineering decision

**Do not remove files from the currently accepted frozen EXE, signed
installer or installed user files**. For an independently reviewable
future optimization, create a **separate isolated candidate** build in
a new directory (not the current `dist/GitHubCommunityAgent`) with
explicit PyInstaller excludes for `pytest`, `_pytest`, `pygments`,
then inspect its new archive. If it fails self-check or any actual
V1 workflow, reject that candidate. An accepted optimized build would
still require the full Windows installed-app functional/DPAPI/data-
retention, tests, negative-security and installer acceptance again
before it supersedes the prior candidate.

Before building, review whether the PyInstaller `--exclude-module`
flags have the intended behavior and whether `pygments` or
`_pytest` is needed in a selected optional code path. No exclusion
or rebuilding has been undertaken in this review.

**SBOM licensing, notices, publisher signing and independent Windows-user
security remain blocked.** This xref evidence is specifically a build
hygiene finding, not a security certification.

## Isolated unsigned exclusion experiment prepared — Windows run pending (2026-11-09)

The actual PyInstaller xref shows `httpx._main` importing
`pygments.lexers`, and `anyio._backends._asyncio` importing
`_pytest.outcomes`. The previously accepted EXE and installer remain
unchanged.

A separate test-only builder is available:
`scripts/windows-build-exclusion-candidate.ps1`.

- Precondition: existing accepted `dist/GitHubCommunityAgent` onedir
  bundle and original executable must exist.
- All NEW output is under
  `build/gc-agent-exclusion-candidate/` (distinct `dist`, `work`,
  `spec` folders). The script REFUSES to overwrite that directory.
- Uses the same source launcher and UI-data inclusion as the baseline,
  but excludes `pygments`, `pytest` and `_pytest` for an experiment.
- Candidate EXE must pass `--self-check`, and PyInstaller archive
  inspection MUST independently verify zero matching `pygments`,
  `pytest` and `_pytest` module names. Inspecting the archive is not
  equivalent to validating real V1 workflows.
- Prints baseline/candidate file counts and total file bytes, and
  verifies the original baseline EXE hash is unchanged. It does
  **not** run Inno Setup, install or uninstall, sign, publish, access
  AppData/DPAPI/work.sqlite3, or modify the original Nature AI Worker.
- Uses current development environment, so package upgrade drift and
  other changes could affect the outcome; reported size savings cannot
  automatically be attributed solely to exclude flags.
- Source guardrail tests have been added but **real native Windows
  execution is pending**.

### User-operated native Windows trial

First close any unnecessary GC Agent development windows, then use the
original project folder:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-build-exclusion-candidate.ps1
```

If an old `build/gc-agent-exclusion-candidate` folder is present,
the script fails safely. Do NOT erase prior evidence just to rerun.
Report the exact Windows test totals, candidate self-check, archive
exclusion check, candidate/baseline file counts and sizes.
A failed candidate is **not** a release candidate; keep existing
installed app and original accepted bundle as-is.

After a candidate succeeds, *before* any decision to replace the
previous build, confirm full V1 real GitHub read-only tasks, local
approvals, saved DPAPI key live model connection, nonwrite behavior,
Windows Host/Origin/nonce controls, upgrade/uninstall/reinstall
retention, included third-party LICENSE/NOTICE texts and code
signing prerequisites. No automatic deployment or promotion is
authorized. All PRs remain Draft, no merge/tag/sign/public release.

## Actual isolated unsigned exclusion candidate — Windows PASS for build/self-check (2026-11-09)

The user executed the independent `scripts/windows-build-exclusion-candidate.ps1`
on native Windows 11 (Python 3.13.14, PyInstaller 6.22.3, hooks 2026.9)
after pulling branch `feature/unified-task-home` through `6be9340`.
The exact log establishes:

- `windows-test-regression.ps1`: **238 passed in 3.57s**, 0 failures.
- PyInstaller separate candidate onedir build completed successfully at
  `build/gc-agent-exclusion-candidate/dist/GitHubCommunityAgent/`.
- Candidate `GitHubCommunityAgent.exe --self-check`: **PASS**.
- Candidate PyInstaller recursive archive listing: **372 lines**,
  **366 matched module occurrences**, **366 unique names**,
  **6 unmatched lines**. Candidate categories: **11 first_party**,
  **228 stdlib_candidate**, **117 environment_distribution_candidate**,
  **10 unresolved** (previously identified launcher/PyInstaller helpers).
- `Development module candidates: 0` and
  `Excluded module names in candidate archive: 0 verified` for
  `pytest`, `_pytest`, `pygments`.
- Previously accepted baseline EXE SHA256 unchanged:
  `B0BB3F5D954CC44F8B8BB968ADF36B0C98EDDB4D9D128750EBDE5CE094C4008A`.
- Baseline onedir: **958 files; 31,332,500 bytes**.
- Candidate onedir: **958 files; 29,507,071 bytes**.
- Difference: **1,825,429 bytes less (~5.83%)**,
  **345 fewer archived modules** (711 → 366).
- The candidate was **NOT installed, signed or promoted**. There was no
  installer run and no change to the existing user's Task/DPAPI data.

**Accepted only**: isolated, non-overwriting build; excluded-module
archive proof; frozen self-check; baseline EXE unchanged; file count and
size comparison. This does **not** establish that all five authentic V1
workflows, local review/approval behavior, saved-key DPAPI handling,
GitHub nonwrite protections, HTTP origin/nonce validation, or Windows
installation/data-upgrade continuity function in the candidate.

The unchanged 958 file count is consistent with removing Python modules
embedded in EXE/PYZ while preserving Tcl/Tk and other onedir resources,
but precise attribution of each saved byte requires controlled
reproducibility tests. The total size decrease must not be promoted as
a proven source-only dependency optimization if other build inputs drifted.

**Next gate:** run candidate-specific application-level tests in a
separate temporary user-data root or authorized independent Windows
test user, never against real personal Work records and saved API keys;
prove all five V1 read-only Work Types with actual GitHub/model evidence.
Any candidate considered for release would need full installer
upgrade/uninstall/reinstall, negative security, license/SBOM, anti-malware,
version/signing and PR stack acceptance again. Current public-release
blockers remain. Draft PRs must not be merged, signed, tagged or released.

## Native Windows isolated REAL frozen Work Center trial (prepared; NOT yet run)

The source at this point includes
`scripts/windows-run-exclusion-candidate-isolated.ps1`.
It launches the **already-built optimized candidate**, not an installer or
the previously accepted EXE. It first checks `--self-check`, then starts
the actual frozen Work Center, allowing browser-based human acceptance
against the *real application runtime*, not a mocked service.

For each run it creates a fresh, never-reused directory:
`build/gc-agent-e2e-trials/trial-<random-guid>/` and temporarily
overrides `LOCALAPPDATA` for the candidate process to that directory.
The candidate's actual data paths become:
`.../trial-<guid>/GitHubCommunityAgent/work.sqlite3` and
`.../trial-<guid>/GitHubCommunityAgent/settings.dpapi`.
It does **not** import/copy an existing DPAPI key or touch the original
`%LOCALAPPDATA%/GitHubCommunityAgent` contents. It restores
`LOCALAPPDATA` in the calling PowerShell session on exit; retained
trial files are intentional evidence. The spawned browser may inherit
the trial-local environment; browser profile behavior must be checked
rather than assumed.

### Native Windows acceptance command

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-run-exclusion-candidate-isolated.ps1
```

If GC Agent is already running in a regular installation, keep its
window/data separate; **do not enter the user's existing saved key**.
Within the new trial Work Center, explicitly enter independent,
test-authorized model credentials and, only when needed, a GitHub
Discussions **read-only** token. Private repositories may require
read credentials; use a clearly approved test repository. No
credentials should be pasted back into logs or chat. For real model
requests there may be API usage charges.

### Human acceptance checklist (record observed evidence, not assumptions)

1. On the new Work Center, open Settings, select model/provider and
   test repository and verify a real model connection. Verify the new
   Task list starts empty; old 10 Tasks do not appear.
2. Run **Review Issues** with real accessible GitHub Issues. Verify
   source URLs, meaningful evidence and coverage limitations.
3. Run **Review Discussions**, with an explicitly scoped read token
   where required. Verify source-backed results and limitations.
4. Run **Draft Issue Reply** for one actual Issue, confirm Task status
   **Needs My Attention**, visible draft and source link. Use **Mark
   reviewed**; status becomes finished **locally only**, and confirm
   no GitHub comment was actually posted.
5. Run **Draft Discussion Reply** for one actual Discussion. Repeat the
   local review/non-publication checks.
6. Run **Community Report** against actual accessible activity;
   verify issue/discussion coverage and explicit caveats.
7. Inspect Task history, readable report, technical JSON, and copy/
   export. Reopen with a new isolated trial root only for a genuinely
   fresh test; retained prior trial artifacts are not wiped.
8. Negative security checks: no Github write capability; no response
   to forged Host/Origin/nonce; DPAPI file should be unreadable under
   another independent Windows account (separate authorized setup).
   Existing unit security tests do **not** prove these live behaviors.

Record only Task IDs/statuses and non-sensitive evidence; redact repo
secrets if any. Test failures remain failures, do not mark completed
based on the build-only `--self-check`. A full second-Windows-user
isolation and installer-upgrade pass are **not performed** by this
script.

**Current status: trial script and guard tests committed, Windows
execution pending.** This is not authorization to replace or release
the accepted installed program. PR #11 stays Draft, no merge, tag,
signing or release. Original Nature AI Worker remains untouched.

## Five real V1 Task exports supplied by user (2026-11-09 UTC)

User provided five distinct JSON exports timestamped approximately
13:36–13:40 UTC for repository `nature-ai-corp/nature-ai-worker`:

| Task | Definition | Exported status | Evidence |
|---|---|---|---|
| #1 | `review_issues` | `finished` | 9 issue records fetched in one page, 5 analyzed, details read 5, source-linked assessment |
| #2 | `review_discussions` | `finished` | Discussion #32 fetched/analyzed, source-linked report |
| #3 | `draft_issue` | `finished` | unposted Issue #33 reply draft, `requires_human_review=true`, `posted=false` |
| #4 | `draft_discussion` | `finished` | unposted Discussion #32 reply draft, `requires_human_review=true`, `posted=false` |
| #5 | `community_report` | `finished` | 9 Issues fetched, 5 analyzed; 1 Discussion included; bounded/incomplete caveats |

All five have `error=null`, `read_only=true` and source
URLs. The Discussions read operation returned real #32 content,
indicating that configured read access was operational for this run,
not merely that a token was encrypted on disk.

**What the exports prove:** actual output artifacts of all five V1
workflows on the specified GitHub repo; coherent workflow type,
number and source references; draft generation without a claimed post.

**What they do NOT prove by themselves:**
- The screenshots previously showed a failed `git pull` for the
  newly introduced isolation runner, and the exports do not contain a
  build EXE SHA256, trial data-root path, or process command line.
  Therefore they cannot authenticate that the five tasks were run
  specifically with the **optimized isolated frozen candidate**, rather
  than the existing installed GC Agent.
- Both draft exports have `status=finished` while
  `requires_human_review=true`. The Work Center's intended state
  is `needs_attention` immediately after drafting and
  `finished` after a user explicitly marks the draft reviewed.
  Since exports do not include `work_events`, these documents do
  not establish whether the review transition occurred or whether it
  was bypassed. Check the source-app My Work activity before claiming
  approval-flow acceptance.
- `posted=false` is app-reported; source/side-effect verification
  or a guarded GitHub audit check is needed before treating no-write
  as independently witnessed.
- `sample_limited=true` in Tasks #1 and #5 is correctly flagged.
  For Task #2 `sample_limited=false` refers to the one fetched
  discussion, while `total_pages_known=false`; it must not be
  interpreted as an independently verified complete repository survey.
- The generated drafts and summaries require factual/editing review
  before actual human use. For example, the Discussion reply assumes
  release/documentation links, which should be verified against real
  release status. No live post is authorized.

**Disposition:** five actual V1 Work Type output artifacts witnessed
from user-exported application JSON. **Candidate-specific E2E,
review-state transition, cross-user DPAPI isolation, live host/
origin/nonce security, and proof of no GitHub write remain pending**.
Do not convert this output review into full release approval.

## User confirmation of human review transition (2026-11-09)

Following the five actual application JSON Task exports, the user
explicitly confirmed: **"i did review for Needs My Attention"**.

For both generated draft reply Tasks (#3 Issue #33 and #4
Discussion #32), the final exported `finished` status is therefore
consistent with the user having reviewed those drafts through
**Needs My Attention** rather than an unexplained automatic completion.
This resolves the earlier ambiguity about why the exports showed
`finished` together with `requires_human_review=true` and
`posted=false`.

**Accepted with user-attested operation**: two draft outputs
were human-reviewed and their final states are consistent with
the intended local `needs_attention` → `finished` transition.
The exports do not include individual `work_events`, so event-level
forensic proof of every transition is not independently captured.
Neither the final statuses nor `posted=false` alone independently
prove GitHub side-effect absence; these remain separate security
assertions. Candidate executable provenance is still unverified
because prior failed `git pull` and the JSON exports omit executable
path/hash and isolated LOCALAPPDATA root.

No release authorization is implied. PR #11 remains Draft with no
merge, signature, tag or release.

## EXE/process and isolated data provenance check (prepared, Windows run pending)

The five real V1 Task exports and user-verified Needs My Attention
transition remain accepted as **application-level evidence**. Their
source EXE path was not embedded, and a previous attempt to pull
the new isolated launcher failed with DNS resolution errors. It would
be incorrect to retroactively claim those exports were generated
by the optimized isolated build.

A new **read-only** diagnostic is available:
`scripts/windows-check-exclusion-candidate-provenance.ps1`.
It prints SHA256 and paths of the original build and independently
optimized candidate, attempts to identify running
`GitHubCommunityAgent.exe` process executable paths through Windows
CIM, and inspects ONLY
`build/gc-agent-e2e-trials/trial-*/GitHubCommunityAgent/work.sqlite3`
using SQLite `mode=ro`. It outputs aggregate Task definition/status
counts and `work_events` event-name/count totals, NOT Task content,
DB mutations, protected settings, credentials or tokens.

Run after the updated branch is available:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-check-exclusion-candidate-provenance.ps1
```

If `git pull` fails again, do not assume local new scripts exist;
fix/check DNS and only run scripts verified to be present.
No process may be running when inspected, in which case record that
provenance remains unresolved.

For **future newly launched isolated trials**, the updated
`windows-run-exclusion-candidate-isolated.ps1` writes a
non-secret `candidate-launch-attestation.json` within the unique
trial directory before EXE launch, containing actual candidate EXE
path/hash, UTC launch intent, and isolated data-root path. This file
is **not** retrospective evidence for older Tasks; by itself it also
does not prove that each Task used that process or that no GitHub post
occurred. Correlate the attestation with new Task events and
running-process path; security/side-effect acceptance stays separate.

**No existing executable, installer, database, protected settings or
Nature AI Worker repo was modified.** Diagnostic and attestation scripts
have static guard tests but native Windows verification is pending.
All PRs remain Draft. No signing, merge, tagging or release.

## Actual read-only Windows provenance-inspection results (2026-11-09)

The user pulled branch `feature/unified-task-home` through
`939a99e` and ran the newly added read-only script, with this
observed native Windows output:

- `windows-test-regression.ps1`: **242 passed in 1.82s**,
  zero failures.
- Baseline EXE path:
  `dist/GitHubCommunityAgent/GitHubCommunityAgent.exe`;
  SHA256:
  `B0BB3F5D954CC44F8B8BB968ADF36B0C98EDDB4D9D128750EBDE5CE094C4008A`.
- Optimized candidate EXE path:
  `build/gc-agent-exclusion-candidate/dist/GitHubCommunityAgent/GitHubCommunityAgent.exe`;
  SHA256:
  `620268DE3186CA97F7809001FA5EAFF4CF2D38EDDAD0632AA8E4664D59D3DA4E`.
- No `GitHubCommunityAgent.exe` process was running at inspection.
- Unique retained trial folder:
  `build/gc-agent-e2e-trials/trial-5b5fbee064604fe2acf85ff4deea42c8`.
  Its `GitHubCommunityAgent/work.sqlite3` was inspected read-only,
  without any protected settings or Task body access.
- **Five total Task records**, one each for
  `review_issues`, `review_discussions`, `draft_issue`,
  `draft_discussion`, and `community_report`, all currently
  `finished`.
- Verified event-name counts from the real isolated trial SQLite
  database: `created=5`, `completed=3`,
  `needs_attention=2`, `marked_reviewed_locally=2`.
- The two local review events are consistent with the user's
  explicit confirmation of reviewing both drafts through
  **Needs My Attention**, resolving the earlier review-state
  question at the stored-event level, not just status/export level.

**Disposition:** accept **isolated trial dataset** and persisted
local approval event evidence plus source regression **242 PASS**.
The trial database is demonstrably distinct from the ordinary
`%LOCALAPPDATA%/GitHubCommunityAgent` storage location.

**Remaining precise limitation:** because this trial predates the
new `candidate-launch-attestation.json` addition and no process was
running at inspection, the database and frozen-candidate hashes
cannot *cryptographically link* the historical Task executions to
the optimized candidate EXE. Historical candidate identity remains
strongly consistent with user workflow but formally unproven.
Independent GitHub no-write verification, signed installer, second
Windows-account DPAPI protection and full versioned installer
upgrade/NOTICE/SBOM reviews also remain open.

Do not require all five real workflows to be rerun merely to repeat
already validated business behavior. A newly instrumented, minimal
isolated trial with an EXE hash attestation may address formal
candidate-source provenance separately.

No software installation/release or existing user's saved data changed.
PR #11 stays Draft; no merge, tag, signing or publication.

## Native Windows provenance diagnostics — 242 tests PASS, isolated Task-event evidence (2026-11-09)

The user successfully pulled through `939a99e`, ran all native
Windows tests and the read-only provenance script. The exact observed
output is as follows:

- **242 tests passed in 1.82 seconds; 0 failures.**
- Accepted baseline EXE:
  `dist/GitHubCommunityAgent/GitHubCommunityAgent.exe`;
  SHA256 `B0BB3F5D954CC44F8B8BB968ADF36B0C98EDDB4D9D128750EBDE5CE094C4008A`.
  This is unchanged from the previous accepted baseline.
- Optimized EXE:
  `build/gc-agent-exclusion-candidate/dist/GitHubCommunityAgent/GitHubCommunityAgent.exe`;
  SHA256 `620268DE3186CA97F7809001FA5EAFF4CF2D38EDDAD0632AA8E4664D59D3DA4E`.
  These hashes distinguish baseline and optimized binaries.
- **No running GitHubCommunityAgent.exe process found** at inspection,
  so no runtime process path/PID was available for direct attribution.
- Exactly one inspected isolated trial directory:
  `build/gc-agent-e2e-trials/trial-5b5fbee064604fe2acf85ff4deea42c8/`
  containing a Task database with exactly **5** Task records.
- Grouped states: `community_report finished=1`,
  `draft_discussion finished=1`, `draft_issue finished=1`,
  `review_discussions finished=1`, `review_issues finished=1`.
- Actual local Task event counts: `created=5`,
  `completed=3`, `needs_attention=2`,
  `marked_reviewed_locally=2`.

These event counts **corroborate** the five previously supplied real
Task exports, and the user's explicit statement that both draft Tasks
were reviewed via **Needs My Attention**. This substantially strengthens
the evidence for the local review-state transitions compared with
final-status JSON exports alone. An isolated trial data root did hold
the matching five Task definitions. The user has not supplied the
historical trial process command line or matching EXE launch hash
attestation: those five Task records cannot be assigned with
cryptographic certainty to the optimized EXE merely because the
database sits under the isolated-trial path.

**Accepted**: 242 regression tests; baseline/candidate EXE hashes and
unchanged baseline; actual isolated Task states and event counts;
user-attested local review transition. **Still pending**:
authenticated historic trial EXE execution provenance, independent
GitHub no-write side-effect verification, cross-account DPAPI access
denial, native live Host/Origin/nonce negative security, full candidate
installer/upgrade acceptance, validated component SBOM/licenses and
signing.

For a new trial, a launch attestation is now available through
`windows-run-exclusion-candidate-isolated.ps1`, but repeating all
five model/GitHub workflow calls is unnecessary just to confirm process
identity: a minimal separately attested candidate launch plus
read-only inspection is preferable, clearly labeled as **new**
evidence, not retrospective proof.

## Live running optimized EXE process identity and fresh trial data isolation PASS (2026-11-09)

User supplied a Windows screenshot of
`scripts/windows-check-exclusion-candidate-provenance.ps1` while the
optimized GC Agent was actively running. The read-only OS/CIM query
actually returned:

- `PID 23796 : EXCLUSION_CANDIDATE`, whose executable path was
  `C:\Users\aiuser\projects\github-community-agent\build\gc-agent-exclusion-candidate\dist\GitHubCommunityAgent\GitHubCommunityAgent.exe`.
- Optimized candidate SHA256
  `620268DE3186CA97F7809001FA5EAFF4CF2D38EDDAD0632AA8E4664D59D3DA4E`.
- Original baseline EXE SHA256 remained
  `B0BB3F5D954CC44F8B8BB968ADF36B0C98EDDB4D9D128750EBDE5CE094C4008A`.
- Fresh trial directory
  `trial-0c7e076a671c47aba78cbdd9071ef237` contained a database
  with **Task total: 0**.
- Previous separate trial
  `trial-5b5fbee064604fe2acf85ff4deea42c8` still contained the
  five finished V1 Task definitions and events:
  `created=5`, `completed=3`,
  `needs_attention=2`, `marked_reviewed_locally=2`.

**Accepted at live-evidence level**: operating-system observation of a
real running optimized candidate EXE process; separate newly initialized
trial data with zero tasks; preserved earlier five-task test data;
unchanged baseline EXE hash. No launch provenance from historical
Task timestamps to the old process was independently established, so
DO NOT label the earlier five Task results as cryptographically
authenticated executions of the candidate. The new zero-task trial
is not an additional five-workflow E2E pass.

Remaining independent security and release gates: GitHub no-write
side-effect verification, separate-Windows-user DPAPI denial, live
Host/Origin/nonce attack-path checks, genuine changed-code installer
upgrade, binary/component SBOM/license NOTICE, signed public version.
No installed files or original Nature AI Worker files touched.

## Read-only live Windows loopback HTTP negative checks prepared (not yet executed)

The GC Agent Work Center uses a random per-launch HTTP port on
`127.0.0.1`, and the current verified optimized EXE is not replaced.
New script `scripts/windows_candidate_http_negative_probe.py` uses
only standard-library loopback HTTP. The operator supplies the
**current** Work Center URL from the already-running isolated
optimized candidate, with no port guessing or service discovery.

The test checks:

1. GC Agent Work Center identity via public `GET /api/definitions`
   (must contain five V1 definitions).
2. Invalid `Host` on GET must be HTTP 403.
3. `GET /api/tasks` and `GET /api/settings` without the session
   nonce must be HTTP 403.
4. `POST /api/tasks`, `POST /api/test-connection` with an
   intentionally WRONG nonce must be HTTP 403.
5. A POST with BOTH foreign `Origin` and wrong nonce must be HTTP
   403. This combined test **does not separately isolate the Origin
   control**; a later independent Origin test using a valid test
   nonce could be needed.
6. Forged `Host` with invalid nonce on POST must be HTTP 403.

The script deliberately NEVER obtains a valid nonce, reads
`settings.dpapi`, opens the user DB, passes credentials or triggers
authorized HTTP write operations. It disables proxy usage for the
loopback probe and validates the URL format/host/port. Test payloads
are the empty JSON object `{}`; no model/GitHub operations are
authorized. The script is a **security-negative smoke check**,
not proof that GitHub has no write capability nor complete CSRF
security. Source tests enforce loopback-only and no-secret
constraints, but native Windows test execution is PENDING.

### Live native Windows steps

In PowerShell window 1, in the GC Agent repository, run the already
prepared isolated optimized candidate launcher, and keep the window
running:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-run-exclusion-candidate-isolated.ps1
```

Note the current `GitHub Community Agent Work Center:
http://127.0.0.1:<port>/` line from Window 1. The port is randomized
and should **not** be assumed from earlier sessions.

In PowerShell window 2, run with exactly the current printed local
URL (replace `<port>` with the actual numeric port, without angle
brackets):

```powershell
cd C:\Users\aiuser\projects\github-community-agent
.\.venv\Scripts\python.exe .\scripts\windows_candidate_http_negative_probe.py --url "http://127.0.0.1:<port>/"
```

Expected: all eight checks PASS including identity; if anything fails,
preserve output and investigate before continuing. **Do not** paste
API keys or GitHub tokens. No new five-task/model execution is needed.
After tests stop the isolated candidate with Ctrl+C. The user-data
root for all newly created trials remains preserved, not deleted.

A complete Windows security gate still needs separately isolated
valid-nonce/foreign-origin checks, second-Windows-user DPAPI
negative test, actual no-GitHub-write evidence, changed-version
installer acceptance, third-party SBOM/NOTICE and signing.
Do not merge, tag, sign or release.

## Real Windows optimized candidate negative loopback HTTP probe — 8/8 PASS (2026-11-09)

User-provided actual PowerShell screenshot documents the optimized
isolated Work Center running at `http://127.0.0.1:64887/`. They ran
`scripts/windows_candidate_http_negative_probe.py` against that exact
current port; **8 / 8 tests passed**, specifically:

| Check | Expected/observed |
|---|---|
| GC Agent definitions discovery | 200 / 200 |
| Forged Host GET refused | 403 / 403 |
| Tasks GET without nonce refused | 403 / 403 |
| Settings GET without nonce refused | 403 / 403 |
| Tasks POST invalid nonce refused | 403 / 403 |
| Test connection POST invalid nonce refused | 403 / 403 |
| Settings POST foreign Origin **plus invalid nonce** refused | 403 / 403 |
| Tasks POST forged Host refused | 403 / 403 |

The running optimized candidate EXE had been independently identified
earlier as SHA256
`620268DE3186CA97F7809001FA5EAFF4CF2D38EDDAD0632AA8E4664D59D3DA4E`.
The screenshot of this specific test confirms live loopback behavior.
No valid nonce, authorized POST, model key or GitHub token was used.

**Accepted:** real Windows negative HTTP smoke test **8/8 PASS** for
malformed/unauthorized requests. **Not established:** foreign Origin
rejection *independent of invalid nonce*, authenticated workflow
authorization, independent proof of no GitHub-side write actions,
cross-Windows-user DPAPI, true changed-code installer upgrade,
complete actual-frozen SBOM/NOTICE, signing/release. These remain
independent release gates. No app installation or user data changed.

## Six outstanding public-release gates — execution status and next steps (2026-11-09)

The user explicitly authorized proceeding to **finish the six gates**.
This authorization is to prepare and run safe checks; it does **not**
authorize a merge, a signed public installer, use of a signing identity,
a tag, a publication, deletion of a user's existing data or access
to another Windows user's secrets.

### Gate 1: independent Origin enforcement — SOURCE READY; native run PENDING

New `scripts/windows_candidate_origin_isolated_probe.py` compares
four HTTP POSTs with controlled Origin/nonce values against a
**nonexistent** route only:

- correct Origin + valid local UI session nonce → 404;
- foreign Origin + **valid** nonce → 403;
- missing Origin + **valid** nonce → 403;
- correct Origin + invalid nonce → 403.

Nonce is extracted only from the *current local Work Center HTML*
into process memory and is never logged or saved. No actual Task,
Settings, model, or GitHub POST occurs. This isolates Origin from the
previous bad-nonce-only tests. Native results are required before PASS.

In PowerShell 1, keep the already-available isolated candidate running
using `scripts/windows-run-exclusion-candidate-isolated.ps1`.
Use its freshly printed `http://127.0.0.1:<port>/` URL in PowerShell 2:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
.\.venv\Scripts\python.exe .\scripts\windows_candidate_origin_isolated_probe.py --url "http://127.0.0.1:<actual-port>/"
```

The literal placeholder must be replaced with the current real port;
previous ports become invalid when the first window closes. Success
requires **4/4 PASS**; anything else blocks sign-off.

### Gate 2: GitHub no-write — STATIC CONTRACT prepared; independent proof pending

`scripts/github_readonly_transport_audit.py` parses the current
`github_readonly.py` adapter source without credentials or network.
It checks exactly two GitHub transport call sites, one REST GET and
one GraphQL POST, and that both constant GraphQL documents begin
with `query` rather than `mutation` or `subscription`, plus an
explicit query allowlist, no environment proxies and no redirects.

Run this source-only check (choose a fresh output filename; existing
reports are never overwritten):

```powershell
.\.venv\Scripts\python.exe .\scripts\github_readonly_transport_audit.py --source .\src\github_community_agent\github_readonly.py --output .\build\release-audit\github-readonly-transport-v1.json
```

This confirms only the **inspected source adapter contract**. GitHub's
GraphQL query legitimately uses HTTP POST; all POSTs must not be
misreported as publishing. Not every possible path through future
code/dependencies is proven by source inspection. Independent GitHub
server-side observation (e.g. before/after comment IDs and commit/
activity audit from an approved account) is a separate gate and must
be tied to the actual candidate runtime, not just app-reported
`posted=false`. Never generate a GitHub write or delete a comment
merely to test absence of writing.

### Gate 3: Windows cross-account DPAPI isolation — PENDING

Needs a **second separate real Windows user account** and permission
to test with benign throwaway credentials. Record the first user's
trial `settings.dpapi` ciphertext hash only; do not disclose or copy
actual production credentials. Test decrypt under the second user
using a separate throwaway trial file; success condition is
`CryptUnprotectData` fails under that user. Confirm application
cannot silently load or substitute another account's saved key.
Creating/using a real Windows test account requires the user's
explicit environment action. Same-user tests are insufficient.

### Gate 4: final installer/upgrade/uninstall continuity — PENDING

Prior installed-app continuity passed for the old unchanged-code
installer. To accept the optimized candidate, assign a real approved
version and validate an **actual change between installed builds** in
an independent Windows test account/profile. Verify install paths,
existing Task DB + encrypted settings SHA before/after, successful
saved-model live connection and task reuse, uninstall/reinstall
preservation, signing and malware scan. **Do not install the
unsigned optimized candidate over the user's current validated
installation**. Never copy the user's production DPAPI blob to a new
identity or overwrite existing data to simulate upgrade.

### Gate 5: frozen-component SBOM/licenses/NOTICE — PENDING

Current audit generated 958 onedir files and candidate module list
366; neither constitutes validated component provenance or a complete
SBOM. Produce a versioned list of the *actual new frozen build*,
including Python 3.13, Tcl/Tk, bundled binaries, certifi trust store,
PyInstaller bootloader, native dependencies, all bundled Python
distributions and exact license/NOTICE obligations. The source
dependency metadata inventory is auxiliary, not a substitute.
Coordinate packaging notices and copyright review before public use.

### Gate 6: official version/signing — AWAIT OWNER CONTROL

The project metadata remains `0.0.0.dev0`. A public version and
publisher signing identity, private-key custody, Authenticode validation,
signed installer, Defender/smart-screen acceptance and repository
release approval are **not yet authorized or completed**. Signing
requires user-controlled credentials/certificate or a signing
provider; this chat must not manufacture or impersonate signing.
No tag/merge/release without explicit owner approval.

**The next actionable user evidence is the 4/4 independent Origin
check and GitHub adapter static audit on real Windows.**
The repo and all parent PRs remain Draft/unmerged. Original
Nature AI Worker and existing GC Agent data untouched.

## Independent Origin enforcement — real optimized Windows EXE 4/4 PASS (2026-11-09)

The user provided native Windows PowerShell screenshots after pulling
the changes to the above independent Origin probe:

- `windows-test-regression.ps1`: **248 passed in 3.83s**,
  zero failures.
- The isolated optimized EXE self-check succeeded and launched a new
  Work Center on `http://127.0.0.1:60503/`, with a unique trial data
  directory and non-secret launch attestation. Candidate executable
  SHA256 stayed
  `620268DE3186CA97F7809001FA5EAFF4CF2D38EDDAD0632AA8E4664D59D3DA4E`.
- Live `windows_candidate_origin_isolated_probe.py` against the
  **current** port `60503` yielded **4/4 PASS**:
  - correct Origin + correct nonce at nonexistent route: HTTP 404;
  - foreign Origin + **correct** nonce: HTTP 403;
  - missing Origin + **correct** nonce: HTTP 403;
  - correct Origin + invalid nonce: HTTP 403.
- No valid nonce printed or saved; no authorized Task or Settings
  route, model request or GitHub request issued by this check.

**ACCEPT** independent Origin/nonce enforcement for the tested live
candidate. This resolves the earlier ambiguity from the combined
foreign-Origin/bad-nonce probe. Scope is restricted to the four negative
and control cases on the nonexistent local HTTP route, not a full
security certification.

**Not yet shown by the screenshots:** execution or output of
`github_readonly_transport_audit.py`; therefore Gate 2 source-level
read-only review and independent GitHub-side no-write evidence remain
OPEN. Cross-Windows-user DPAPI isolation, optimized installer upgrade,
real frozen SBOM/NOTICE and signing remain OPEN as well.

No code signing, PR merge, release tagging or publishing performed.

## Native Windows GitHub read-only transport source audit — PASS (2026-11-09)

The user ran `scripts/github_readonly_transport_audit.py` natively
from `C:\Users\aiuser\projects\github-community-agent` and
supplied the complete PowerShell result screenshot:

- `GitHub transport source audit: PASS`
- `Source send methods: GET, POST`
- `GraphQL fixed documents: DISCUSSIONS_QUERY, DISCUSSION_QUERY`
- Report saved to `build/release-audit/github-readonly-transport-v1.json`
- Tool explicitly confirms:
  `INDEPENDENT GITHUB NO-WRITE EVIDENCE STILL REQUIRED.`

**Gate 2 substep ACCEPTED:** static analysis of the current source
GitHub adapter's bounded REST GET and fixed GraphQL query transport
contract. GraphQL's HTTP POST is not a publication or mutation.
This is not a frozen-runtime network capture and not a GitHub
server-side before/after mutation audit. Therefore **Gate 2 as a
whole is still OPEN** until independently observed server-side
activity or a sufficiently controlled test can corroborate the lack
of writes without initiating a write.

Suggested next evidence path: use a dedicated, explicitly authorized
test repository and strictly read-only GitHub token; record server-side
comment/discussion/issue state or audit activity before and after
bounded live V1 read/draft/review runs. Do not perform a GitHub write
for the sake of testing, and do not claim a historical before-state
from a later snapshot. Where immutable/reliable audit visibility is
unavailable, document that uncertainty rather than marking independent
no-write as proven. All PRs remain Draft, no merge, signing, tag or
publication.

## Gate 2/3 next-stage evidence tools prepared (2026-11-09; Windows runs PENDING)

### Gate 2: bounded GitHub public Issue state before/after (NOT complete no-write proof)

New `scripts/github_public_issue_before_after_audit.py` uses ONLY unauthenticated
GitHub REST GET requests to the fixed `https://api.github.com` host,
with proxies and redirects disabled. It checks that the repository
is public and that the selected number refers to an Issue (not a PR).
It records the Issue's state/update timestamp plus bounded comment IDs
and timestamps, **never comment body or token**. Full pagination
beyond three pages refuses verification instead of claiming complete coverage.
Results are written create-only, with no overwrite.

A genuinely prospective test workflow:
1. BEFORE performing an authorized read-only V1 Task against a selected
   public test Issue, capture `before.json`.
2. Perform only the authorized GC Agent read or draft operation; no posting.
3. AFTER the run capture `after.json`.
4. Compare the two snapshots and retain the comparison result.

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
.\.venv\Scripts\python.exe .\scripts\github_public_issue_before_after_audit.py snapshot --repository owner/public-test-repository --issue 33 --output .\build\release-audit\issue-before-test.json
# ONLY AFTER taking the above snapshot: execute the authorized V1 read/draft test
.\.venv\Scripts\python.exe .\scripts\github_public_issue_before_after_audit.py snapshot --repository owner/public-test-repository --issue 33 --output .\build\release-audit\issue-after-test.json
.\.venv\Scripts\python.exe .\scripts\github_public_issue_before_after_audit.py compare --before .\build\release-audit\issue-before-test.json --after .\build\release-audit\issue-after-test.json --output .\build\release-audit\issue-comparison-test.json
```

Replace both the public test repo and the Issue number with the same
authorized target used for the task. Use unique filenames if reports
already exist; **never overwrite historical audit evidence**.
Matching snapshots are at most limited corroboration for one public
Issue. They do not cover Discussions, all Issues, GitHub audit events,
transient changes later reverted, or prove causation. Until the
server-side monitoring scope is sufficiently complete and correlated
with the candidate run, Gate 2 as a whole remains OPEN.

### Gate 3: real separate-Windows-account DPAPI deny test, disposable bytes only

New `scripts/windows_dpapi_two_account_throwaway.py` exercises the
same native Win32 DPAPI protection API as GC Agent, but encrypts only
32 random disposable bytes. It deliberately does not use the user's
real saved model key, GitHub token, original settings file or database.
A first Windows account creates the file using exclusive create; the
same account verifies decryption; then a **different Windows sign-in
identity** attempts decryption and must receive a denial. The
two accounts must be able to READ the test ciphertext, otherwise a
filesystem access denial alone is not a successful DPAPI test.

Operator selects an existing, appropriately accessible shared
folder, for example a temporary user-authorized folder under
`C:\Users\Public\Documents\GC-Agent-DPAPI-Test\`. The script
does not create an account, choose a directory, modify ACLs, elevate,
copy production data or clean up automatically.

Run as account A:

```powershell
.\.venv\Scripts\python.exe .\scripts\windows_dpapi_two_account_throwaway.py create --file "C:\Users\Public\Documents\GC-Agent-DPAPI-Test\gc-agent-dpapi-throwaway.bin"
.\.venv\Scripts\python.exe .\scripts\windows_dpapi_two_account_throwaway.py verify --file "C:\Users\Public\Documents\GC-Agent-DPAPI-Test\gc-agent-dpapi-throwaway.bin" --expect allowed
```

Sign in as a DIFFERENT Windows account B (using an authorized
Windows Python installation with this repo/imports available, or an
approved equivalent test runner), then run:

```powershell
python .\scripts\windows_dpapi_two_account_throwaway.py verify --file "C:\Users\Public\Documents\GC-Agent-DPAPI-Test\gc-agent-dpapi-throwaway.bin" --expect denied
```

Do not report PASS if the second account could not read the file or
if both commands ran as the same Windows identity. Actual native
two-account evidence is still required; do not paste/disclose tokens,
credentials or plaintext.

### Remaining gates

Gate 4 requires a real changed-code optimized installer upgrade in
a dedicated Windows test profile; Gate 5 requires exact optimized
frozen payload/version/binary-license mapping and appropriate NOTICE
redistribution; Gate 6 requires owner-approved official version
and trustworthy publisher Authenticode certificate/signature.
These cannot be accepted from source scripts alone. Existing
GC Agent install, Task records, DPAPI settings, original Worker
repository and Draft PR state are untouched; no merge, tag, signing
or release.

## Native Windows actual prospective GitHub no-write Issue before-snapshot — PASS (2026-11-10 00:59 UTC)

User pulled branch `feature/unified-task-home` through
`4802621`, executed all regression tests:
**252 passed in 3.90s**, zero failures.
Then ran read-only public GitHub REST Issue snapshot for
`nature-ai-corp/nature-ai-worker` Issue **#33**:

- `GitHub public Issue comment metadata REST GET snapshot acquired.`
- `Comment records: 2`
- Baseline evidence file:
  `build/release-audit/issue-before-test.json`
- Audit tool printed:
  `LIMITED evidence only; NOT independent proof of all GitHub no-write actions.`

This is a genuine **prospective** BEFORE snapshot of the Issue's
public comment IDs/timestamps and state. Preserve the file unchanged.
The absence of an AFTER snapshot means Gate 2 overall remains OPEN.
Next operator action should execute only a bounded authorized GC Agent
**Draft Issue Reply** for the same Issue #33 with the isolated
candidate, review it locally (never publish), and promptly collect
`issue-after-test.json` using the same read-only snapshot tool,
then compare with `issue-before-test.json`. If after state matches
it proves only no *observed persistent changes* to Issue #33 in
that window, not no write capability across GitHub or transient
writes/deletions.

Do not overwrite baseline or ask to regenerate a historical
before-state; don't use real production credentials in test logs.
This trial may require a fresh isolated test-authorized model API key
and may incur model cost. Do not merge, sign, tag, install or release.

## Prospective Issue #33 bounded no-write evidence — snapshots MATCH (2026-11-10)

User supplied actual GC Agent Work Center and PowerShell screenshots
showing a NEW real `Draft Issue Reply` Task #1 against
`nature-ai-corp/nature-ai-worker` Issue **#33**. The app displayed
`needs_attention` (not finished), `Draft Reply — Not Published`,
and an explicit notice that no GitHub reply had been posted. The
user did not report publishing.

The previously preserved genuine BEFORE snapshot
`build/release-audit/issue-before-test.json` contained **2**
Issue comments. User captured a prospective AFTER snapshot in
`build/release-audit/issue-after-test.json` with **2** Issue
comments, then ran a compare to
`build/release-audit/issue-comparison-test.json`:

- `Observed change categories: []`
- `Matching snapshots: True`
- The tool explicitly stated:
  `LIMITED evidence only; NOT independent proof of all GitHub no-write actions.`

**Accepted:** during this observed trial, no persistent differences
were detected in the bounded Issue #33 state/update metadata and its
two accessible comment IDs/timestamps, while GC Agent produced an
unposted reply draft awaiting human attention. This is useful
independent corroboration of the application read-only contract.

**Not accepted as an absolute guarantee:** a before/after match for
one public Issue cannot rule out transient changes later reverted,
other Issue/Discussion writes, unobserved GitHub activity, or
provide full GitHub audit-log coverage. The on-screen screenshot
alone does not supply a matching candidate launch attestation hash,
though earlier independent optimized process identity and isolated
trial evidence exist. Overall Gate 2 is **partially satisfied**,
with bounded runtime no-change evidence; retain explicit limits
instead of claiming global zero-write proof.

No write requests were deliberately issued. Do not overwrite the
before/after/compare evidence and do not merge, sign, tag or publish.

## Optimized frozen-bundle SBOM/NOTICE provenance audit prepared (2026-11-10; native run pending)

The user has no second Windows test account, so cross-account DPAPI
testing stays explicitly PENDING. Proceeding with the user-authorized
optimized-frozen SBOM and licensing review without modifying any
previously accepted build.

New `scripts/windows-optimized-frozen-sbom-review.ps1` analyzes the
EXISTING optimized candidate only:
`build/gc-agent-exclusion-candidate/dist/GitHubCommunityAgent`.
It invokes existing `frozen_bundle_inventory.py` to hash every
allowed onedir file, `pyi-archive_viewer.exe --brief --recursive`
to obtain actual embedded module names, existing
`frozen_archive_module_triage.py` to classify those module names,
and new `frozen_candidate_provenance_review.py` to prepare an explicit
candidate-component and compiled-binary license review report.
No file is extracted or executed; no Windows installed GC Agent or
user AppData, DPAPI, Task DB, signing certificate, or GitHub account is
touched.

It creates **only new** local audit files under:
`build/release-audit/optimized-candidate-sbom-review/`
and refuses to overwrite existing review outputs. Expected artifacts:
`actual-frozen-files.json`, `pyinstaller-embedded-archive.txt`,
`embedded-module-candidates.json`,
`component-provenance-review.json`.
The review ties actual file hashes/relative paths to module candidates,
but **Python package names and versions from the current .venv remain
CANDIDATES ONLY**, not verified frozen-package provenance. It
explicitly lists all native binaries as pending exact component
attribution and flags Python, Tcl/Tk, OpenSSL, SQLite, libffi, zlib,
C runtime, PyInstaller bootloader, certifi and redistribution NOTICE
obligations as open. Report fields `actual_package_versions_verified`,
`complete_third_party_notices_verified` and
`approved_public_redistribution` must stay FALSE without independent
license evidence.

On native Windows, from repo root:

```powershell
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-optimized-frozen-sbom-review.ps1
```

Do NOT delete an earlier audit folder to repeat the same filename;
retain prior output and select a new separately reviewed run if
necessary. The accepted optimized onedir should previously contain
approximately 958 files and 366 embedded module candidates, but
current results rather than assumed numbers must establish this.

**Gate 5 remains OPEN** after report creation until human review
resolves actual frozen distribution versions, native binary origins,
license texts, NOTICE placement in installer, and applicable license
requirements. Gate 4 installer and Gate 6 signing remain pending.
No PR merge/tag/sign/release without explicit owner authorization.

## Native Windows optimized frozen audit executed — 254 regression PASS, 7 candidate distributions (2026-11-10)

The user pulled branch `feature/unified-task-home` through
`6614030`, then executed `windows-test-regression.ps1` and
`windows-optimized-frozen-sbom-review.ps1` on native Windows.

**Observed output:**

- **254 passed in 2.54s, 0 failed.**
- Optimized onedir **958 actual files, 29,507,071 bytes**.
- File categories: **26 binary**, **1 archive**, **1
  license_or_notice_candidate**, **926 other**, **1 public certifi CA
  bundle**, **3 UI assets**.
- Embedded PyInstaller listing **372 lines**, **366 parsed unique
  modules**, **6 unmatched lines**; categories **117
  environment_distribution_candidate**, **11 first_party**, **228
  stdlib_candidate**, **10 unresolved** (previously identified as
  first-party launcher/PyInstaller runtime helpers).
- **Zero development-module candidates** in the optimized archive.
- Combined provenance report identifies **7 Python distribution
  candidates**, **26 native binary files**, **10 unresolved
  archive members**. Distribution *names*, exact frozen version
  matches, binary component origin and redistribution license text
  are **not** established by the console summary.
- Optimized EXE SHA256:
    `620268DE3186CA97F7809001FA5EAFF4CF2D38EDDAD0632AA8E4664D59D3DA4E`;
  This agrees with the previously accepted optimized candidate.
- Created four preserved reports under
  `build/release-audit/optimized-candidate-sbom-review/`:
  `actual-frozen-files.json`,
  `pyinstaller-embedded-archive.txt`,
  `embedded-module-candidates.json`, and
  `component-provenance-review.json`.

**Gate 5: actual frozen file/module inventory PASS; exact SBOM,
license/NOTICE and binary origin review STILL OPEN.** The single
`license_or_notice_candidate` file within the frozen bundle is
not proof of full redistributed notices. The console counts are
not license clearance.

**Next read-only check**: inspect just the seven candidate
distribution names plus their unverified environment metadata,
and the 26 native binary relative paths from the saved
`component-provenance-review.json`. Preserve and do not overwrite
all files; do not print secrets, which this review does not collect.

No changes to installed app, saved GC Tasks or credentials,
original Nature AI Worker, Draft PR states, signing or release.

## Seven Python candidates and 26 frozen native binaries — actual Windows report (2026-11-10)

User directly read `component-provenance-review.json` generated from
the optimized bundle and supplied all seven current-build-environment
candidate versions/licenses:

| Distribution | Candidate version (development venv ONLY) | Metadata license | Embedded modules |
|---|---|---|---:|
| anyio | 4.16.0 | MIT | 43 |
| certifi | 2026.10.23 | MPL-2.0 | 2 |
| h11 | 0.16.0 | MIT | 11 |
| httpcore | 1.0.9 | BSD-3-Clause | 31 |
| httpx | 0.28.1 | BSD-3-Clause | 23 |
| idna | 3.20 | BSD-3-Clause | 6 |
| typing-extensions | 4.16.0 | PSF-2.0 | 1 |

**These are build-venv metadata candidates, not exact immutable
component versions independently reconstructed from the frozen EXE.**
All individual binary origin/license verification flags remain FALSE.

The 26 native binaries in the optimized onedir are:

`_internal/_asyncio.pyd`, `_internal/_bz2.pyd`,
`_internal/_ctypes.pyd`, `_internal/_decimal.pyd`,
`_internal/_hashlib.pyd`, `_internal/_lzma.pyd`,
`_internal/_multiprocessing.pyd`,
`_internal/_overlapped.pyd`, `_internal/_queue.pyd`,
`_internal/_socket.pyd`, `_internal/_sqlite3.pyd`,
`_internal/_ssl.pyd`, `_internal/_tkinter.pyd`,
`_internal/libcrypto-3.dll`, `_internal/libffi-8.dll`,
`_internal/libssl-3.dll`, `_internal/pyexpat.pyd`,
`_internal/python313.dll`, `_internal/select.pyd`,
`_internal/sqlite3.dll`, `_internal/tcl86t.dll`,
`_internal/tk86t.dll`, `_internal/unicodedata.pyd`,
`_internal/VCRUNTIME140.dll`, `_internal/zlib1.dll`,
`GitHubCommunityAgent.exe`.

These file names suggest runtime origin categories (CPython extension
modules, OpenSSL, SQLite, Tcl/Tk, C runtime, libffi/zlib and PyInstaller
bootloader), **not legally verified provenance**. Actual file version
metadata, SHA256, linked import/data source and exact applicable
redistribution license text remain to be checked before Gate 5 PASS.

The source-level list and file manifest are not yet a signed,
version-locked final SBOM. Do not invent license obligations or claim
that seven package metadata entries cover all compiled runtime
libraries.

## Frozen 26-native-binary Windows VERSIONINFO evidence prepared (native run pending)

Following the native optimized frozen audit (254 tests PASS), the user
listed seven Python package candidates (anyio 4.16.0 MIT, certifi
2026.10.23 MPL-2.0, h11 0.16.0 MIT, httpcore 1.0.9 BSD-3-Clause,
httpx 0.28.1 BSD-3-Clause, idna 3.20 BSD-3-Clause,
typing-extensions 4.16.0 PSF-2.0) and the 26 actual binary filenames.
These are current build-venv metadata candidates and native file
names; no frozen package version/redistribution clearance implied.

A new read-only `scripts/windows-optimized-native-binary-versions.ps1`
checks the **existing optimized frozen bundle** against each of the
26 binary SHA256 values in previously generated
`actual-frozen-files.json`, then records Windows VERSIONINFO fields
(file/product version, company name, description) to a new,
create-only file:

`build/release-audit/optimized-candidate-sbom-review/native-binary-fileversion-evidence.json`

VERSIONINFO labels are **untrusted embedded metadata**, helpful in
investigating native binary origins but not proof of copyright,
license identity, or redistribution permission. The report must
leave all origin/license checks unverified. No executable, user
credential, installed app, or historic report is changed.

Native Windows next:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-test-regression.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-optimized-native-binary-versions.ps1
```

If the report path already exists, preserve it; this command refuses
overwrites. Do not infer a license from a version string. Gate 5
remains OPEN until actual version-locked component/NOTICE texts and
native binary redistribution rights have been assessed.

## Native Windows frozen 26-binary VERSIONINFO evidence created — hashes 26/26 PASS (2026-11-10)

User pulled branch `feature/unified-task-home` through `6e90ac4`
and ran the updated native Windows regression:

- **256 passed in 1.89s, 0 failed**.
- `windows-optimized-native-binary-versions.ps1` completed.
- **All 26 native executable/DLL/PYD SHA256 values matched the previously saved actual optimized bundle file manifest**.
- New file created (preserved): `build/release-audit/optimized-candidate-sbom-review/native-binary-fileversion-evidence.json`.
- Tool explicitly warned: `VERSIONINFO names are self-reported; legal origins and licenses still need verification.`

**Accepted:** hash integrity of 26 native binaries against the frozen
manifest, and a local report of embedded Windows VERSIONINFO metadata.
**Not accepted:** legally verified origin, exact upstream build
provenance, redistribution license text, third-party NOTICE coverage
or release-ready SBOM. The user has not yet supplied the individual
VERSIONINFO rows, so do not infer per-file company/product metadata
from the tool's success line.

Next read-only review: examine the saved JSON's `binaries` array,
particularly `path`, `file_version_string`,
`product_version_string`, `company_name_unverified`, and
`product_name_unverified`. Retain `third_party_licenses_verified=false`
until underlying authoritative source/redistribution evidence is
checked. No modified executable, production credentials or signed
installer involved.

## Actual optimized native VERSIONINFO records reviewed (2026-11-10)

The user ran the read-only Windows listing of all 26 entries in
`native-binary-fileversion-evidence.json`. Windows self-reported
VERSIONINFO establishes the following **version/provenance hints only**:

- 17 CPython-named binary files, including `python313.dll` and
  Python extension `.pyd` modules: file/product `3.13.14`,
  company field `Python Software Foundation`.
- `libcrypto-3.dll` and `libssl-3.dll`: `3.0.21`,
  company field `The OpenSSL Project, https://www.openssl.org/`.
- `sqlite3.dll`: `3.50.4.0`, company `SQLite3`.
- `tcl86t.dll` and `tk86t.dll`: `8.6.15`,
  company information blank.
- `VCRUNTIME140.dll`: `14.42.34438.0`,
  company `Microsoft Corporation`.
- `zlib1.dll`: `1.3.1`, company blank.
- `libffi-8.dll`: no version/company string in the output.
- `GitHubCommunityAgent.exe`: no version/company string in the output.
- The overall total remains **26 binary files** and their hashes
  have already been checked **26/26** against the frozen manifest.

This is **NOT** an independent verification of binary build origin,
the complete CPython runtime license chain, OpenSSL/Tcl/Tk/libffi/zlib
redistribution conditions, Microsoft runtime distribution conditions,
PyInstaller bootloader license/attribution or installer NOTICE
coverage. Do not infer that a missing field means the component lacks
a license; investigate the actual upstream distribution materials.
A component version printed by Windows is useful for source-matching,
but does not independently prove that exact upstream binary was
bundled.

**Next gate actions:** identify authoritative redistribution
LICENSE/NOTICE texts for the exact CPython 3.13.14 runtime and
bundled libraries, OpenSSL 3.0.21, Tcl/Tk 8.6.15, zlib 1.3.1,
SQLite 3.50.4, libffi and MS VC runtime. Confirm the PyInstaller
version/bootloader origin and whether third-party notices are
included within the installer. Keep the SBOM/NOTICE approval flag
FALSE until each item has concrete evidence.

All audit scripts remain read-only and non-overwriting; no
installed app, Task, DPAPI data, signed installer or release touched.
