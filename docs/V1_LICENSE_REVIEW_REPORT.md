# GC Agent V1 — Third-party license review report (for human approval)

**Prepared 2026-11-10 for the owner and license reviewer; updated the same day
for the CPython 3.13.17 / OpenSSL 3.5 runtime. Not legal advice. Nothing here
is approved: every item marked DECISION needs a named human.**

Approval checklist, separating technical verification from legal approval and
owner decisions from counsel decisions:
[`V1_LICENSE_APPROVAL_CHECKLIST.md`](V1_LICENSE_APPROVAL_CHECKLIST.md).
Re-checked against the committed `1.0.0rc1` package on 2026-11-10:
`third_party_notices.py check` PASS, and the facts below are unchanged.

Scope: the Windows distribution built from the clean release bundle
(`scripts/windows-build-release-bundle.ps1`: official PSF-signed CPython
3.13.17 x64, hash-locked build venv without test tools; 958 files; the exact
EXE SHA256 is recorded in `MANIFEST.json`) plus the installed `LICENSE`,
`NOTICE` and `third-party-licenses/` (16 files).
Package: `packaging/third-party-licenses/`, generated and checked by
`scripts/third_party_notices.py`; `MANIFEST.json` has
`legal_review_approved: false`.

## 1. What has been verified (evidence, not opinion)

| Claim | Evidence |
|---|---|
| Every bundled file is accounted for | Fail-closed generator classifies all 958 files; any unknown file blocks the build |
| Python packages are the stated versions | All 355 PYZ modules code-object-identical to the build venv sources |
| Native runtime is the unmodified PSF Python 3.13.17 build | All DLL/PYD and Tcl/Tk files byte-identical to it; runtime files Authenticode-signed by the PSF; MSI and NuGet copies cross-checked |
| Library versions | Runtime-reported and pinned to CPython v3.13.17 `PCbuild/get_externals.bat` (only OpenSSL changed vs 3.13.14: 3.0.21 → 3.5.9) |
| Bootloader is stock PyInstaller 6.22.3 | `.text/.data/.pdata` identical to `run.exe` |
| certifi `cacert.pem` unmodified | Matches certifi's RECORD hash and the file inside the shipped sdist |
| Shipped certifi sdist is the exact source of what is frozen | Generator compares the sdist's `cacert.pem` and every certifi `.py` with the bundled/frozen files; SHA256 pinned |
| Installer really installs the notices | Native runs on the 3.13.17 bundle: all 978 installed files byte-verified (`build/license-payload-verification/run-*`) |
| OpenSSL 3.5.9 has no Apache NOTICE file to carry | Upstream tag `openssl-3.5.9` root: `LICENSE.txt`, `AUTHORS.md`, `ACKNOWLEDGEMENTS.md`; no `NOTICE` |

## 2. Component obligations

| Component | Version | License | Main obligation for binary redistribution | How the package meets it | Needs decision? |
|---|---|---|---|---|---|
| anyio | 4.16.0 | MIT | Include copyright + permission notice | Verbatim LICENSE + notices | Confirm only |
| h11 | 0.16.0 | MIT | Same | Same | Confirm only |
| httpcore | 1.0.9 | BSD-3-Clause | Reproduce notice, conditions, disclaimer in docs | Same | Confirm only |
| httpx | 0.28.1 | BSD-3-Clause | Same | Same | Confirm only |
| idna | 3.20 | BSD-3-Clause | Same | Same | Confirm only |
| typing-extensions | 4.16.0 | PSF-2.0 | Retain PSF notice | Verbatim LICENSE | Confirm only |
| **certifi** | 2026.10.23 | **MPL-2.0** | §3.2: tell recipients how to get Source Code Form, reasonably and promptly | Exact sdist shipped in `certifi-2026.10.23/source/` + upstream URL + SHA256; full MPL text | **DECISION 2** |
| CPython | 3.13.17 | PSF-2.0 | Retain notice; clause 3 "brief summary of the changes made to Python" | Windows `LICENSE.txt` + `license.rst`; notices state "changes: none" | Confirm wording |
| **VCRUNTIME140.dll** | 14.51.36247.0 | Microsoft Distributable Code | See §3 and `VCRUNTIME_REDISTRIBUTION_BASIS.md` | Conditions reproduced from CPython `LICENSE.txt` | **DECISION 3** |
| OpenSSL | 3.5.9 (3.5 LTS) | Apache-2.0 | Include license; carry NOTICE if any (none upstream) | Apache text in CPython files | Confirm only |
| **SQLite** | 3.50.4 | Public domain | None legally; attribution courtesy | Project-written statement + upstream link | **DECISION 4** |
| **liblzma (XZ Utils)** | 5.2.5 | Public domain (5.2.x) | None legally | Project-written statement + upstream link | **DECISION 4** |
| Unicode Character Database (in CPython) | 15.1.0 data | Unicode-3.0 | Include notice | New `license.rst` section in 3.13.17 | Confirm only |
| zlib | 1.3.1 | Zlib | Do not misrepresent origin; keep notice in source | `license.rst` | Confirm only |
| libffi | 3.4.4 | MIT | Include notice | Both CPython files | Confirm only |
| Tcl/Tk | 8.6.15 | TCL | Retain copyright notice in all copies | `license.terms` + CPython `LICENSE.txt` | Confirm only |
| expat / libmpdec / bzip2 | 2.8.1 / 4.0.0 / 1.0.8 | MIT / BSD-2 / bzip2 | Include notices | CPython files | Confirm only |
| PyInstaller bootloader | 6.22.3 | GPL-2.0+ with Bootloader exception | None for unmodified bootloader linked into the app | `COPYING.txt`; stock bootloader verified | Confirm only |
| PyInstaller run-time hooks | 6.22.3 | Apache-2.0 | Include license | `COPYING.txt` | Confirm only |

## 3. Decisions that require human approval

**DECISION 1 — Approve the package as a whole.** Review
`THIRD_PARTY_NOTICES.txt` and the files it lists. If approved, record the
reviewer, date and the `MANIFEST.json` SHA256 set in a review record outside
this repository's automation. Only then may a `REVIEW_APPROVAL.json` and
`LegalReviewEvidence` be supplied to `gc-agent-release-candidate.iss`. Neither
file has been created, and automation must not create them.

**DECISION 2 — certifi (MPL-2.0) source availability.** certifi is unmodified,
and its data file is shipped in source form with the MPL notice. The notices
point to the exact PyPI sdist (with SHA256) and the upstream repository.
**Implemented (pending approval): option (c).** The exact sdist (136,225
bytes, SHA256 `a9895e6e…36cd`) is now inside the installed
`third-party-licenses/certifi-2026.10.23/source/`, and the notices name it.
The generator fails the build unless the bundled `cacert.pem` and all certifi
Python sources are identical to the files in that archive. The reviewer should
confirm that this satisfies MPL-2.0 §3.2. Option (b), also mirroring the sdist
on the release page, is optional extra assurance.

**DECISION 3 — Microsoft Distributable Code (VCRUNTIME140.dll).** Facts,
verbatim terms and options are in `docs/VCRUNTIME_REDISTRIBUTION_BASIS.md`. CPython's
`LICENSE.txt` says redistributing its unmodified Windows build "complies with
this agreement, provided that you do not … use Microsoft's trademarks in your
programs' names or in a way that suggests your programs come from or are
endorsed by Microsoft". It also says distributors must "require distributors
and external end users to agree to terms that protect the Microsoft
Distributable Code at least as much as Microsoft's own requirements".
**Open questions for counsel:**
- **"GitHub" is a trademark of GitHub, Inc., a Microsoft subsidiary, and it
  appears in the product name "GitHub Community Agent".** Decide whether this
  conflicts with the condition, and separately whether the name complies with
  GitHub's own trademark/logo policy.
- Decide whether the Apache-2.0 terms alone are adequate. The alternative is
  an end-user terms page in the installer (Inno Setup `LicenseFile`) that
  includes the Microsoft-protective clause.
- An alternative is to rely on the system's Microsoft Visual C++
  Redistributable instead of bundling the DLL. That is a packaging change with
  compatibility risk; the trial would need to be repeated.
- **Narrowed 2026-11-10** (`VCRUNTIME_REDISTRIBUTION_BASIS.md` §5a):
  - The PSF's conditional grant is the basis, so no Visual Studio license is
    assumed.
  - CPython's license states the Distributable Code is embedded in every
    CPython `.exe`, `.dll` and `.pyd`. The system-redistributable alternative
    therefore would not remove the conditions, and is dropped.
  - The open items are now only the end-user terms (a recommended installer
    terms page) and the name.

**DECISION 4 — Public-domain statements (SQLite, liblzma).** The notices hold
short project-written statements with upstream links, not upstream text.
Approve the wording. Optionally add SQLite's dedication text. Note: liblzma
5.2.5 is **not** an XZ Utils 5.6.0/5.6.1 release (the 2024 backdoor,
CVE-2024-3094), so that issue does not apply.

**DECISION 5 — Pin governance.** `scripts/third_party_notices.py` holds the
reviewed license and version table. Name who may change those pins: any
dependency or toolchain change fails the build until a person updates them and
re-reviews the package.

## 4. Related non-license risk raised during review

- **OpenSSL: remediated in the build, owner to accept.** The 3.13.14 runtime
  shipped OpenSSL 3.0.21, which is past upstream support. The release bundle
  now uses the official CPython 3.13.17 build, which ships OpenSSL 3.5.9 (3.5
  LTS line). Every other bundled library version is unchanged. No DLL was
  replaced by hand: the whole runtime is the PSF's signed build.
- **CPython 3.13 support window.** 3.13 receives binary bugfix releases only
  for a limited time; plan the move to 3.14 for V1.x. That change brings Tcl/Tk
  9.0 and zlib-ng and needs a full re-verification.
- **SBOM review notes (2026-11-10).** These need reviewer decisions; nothing is wrong technically:
  - SQLite is tagged SPDX `blessing`, while liblzma is tagged
    `LicenseRef-public-domain` (same legal basis, different style);
  - the Unicode Character Database (Unicode-3.0) is covered only through
    CPython's `license.rst`, not as its own SBOM component.
- **GitHub independence disclaimer** added (`NOTICE`, notices, README, EXE
  description). Wording to be approved with DECISION 3.

## 5. How to re-verify before signing

```powershell
cd C:\Users\aiuser\projects\github-community-agent
.\build\release-bundle\venv\Scripts\python.exe .\scripts\third_party_notices.py check --bundle .\build\release-bundle\dist\GitHubCommunityAgent
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-verify-installer-license-payload.ps1
```
Both must print PASS. The reviewer reads `packaging\third-party-licenses\THIRD_PARTY_NOTICES.txt`.
