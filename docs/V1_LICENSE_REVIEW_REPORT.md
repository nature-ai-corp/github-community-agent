# GC Agent V1 — Third-party license review report (for human approval)

**Prepared 2026-11-10 for the owner and license reviewer. Not legal advice.
Nothing here is approved: every item marked DECISION needs a named human.**

Scope: the Windows distribution built from the optimized frozen bundle
(`GitHubCommunityAgent.exe` SHA256 `620268DE…3DA4E`, 958 files) plus the
installed `LICENSE`, `NOTICE` and `third-party-licenses/` (15 files).
Package: `packaging/third-party-licenses/`, generated and checked by
`scripts/third_party_notices.py`; `MANIFEST.json` has
`legal_review_approved: false`.

## 1. What has been verified (evidence, not opinion)

| Claim | Evidence |
|---|---|
| Every bundled file is accounted for | Fail-closed generator classifies all 958 files; any unknown file blocks the build |
| Python packages are the stated versions | All 355 PYZ modules code-object-identical to the build venv sources |
| Native runtime is the unmodified PSF Python 3.13.14 build | 25/25 DLL/PYD and 926/926 Tcl/Tk files byte-identical to it |
| Library versions | Runtime-reported and pinned to CPython v3.13.14 `PCbuild/get_externals.bat` |
| Bootloader is stock PyInstaller 6.22.3 | `.text/.data/.pdata` identical to `run.exe` |
| certifi `cacert.pem` unmodified | Matches certifi's own RECORD hash |
| Installer really installs the notices | 3 native runs: all 977 installed files byte-verified |
| OpenSSL 3.0.21 has no Apache NOTICE file to carry | Upstream tag root: `LICENSE.txt`, `AUTHORS.md` only |

## 2. Component obligations

| Component | Version | License | Main obligation for binary redistribution | How the package meets it | Needs decision? |
|---|---|---|---|---|---|
| anyio | 4.16.0 | MIT | Include copyright + permission notice | Verbatim LICENSE + notices | Confirm only |
| h11 | 0.16.0 | MIT | Same | Same | Confirm only |
| httpcore | 1.0.9 | BSD-3-Clause | Reproduce notice, conditions, disclaimer in docs | Same | Confirm only |
| httpx | 0.28.1 | BSD-3-Clause | Same | Same | Confirm only |
| idna | 3.20 | BSD-3-Clause | Same | Same | Confirm only |
| typing-extensions | 4.16.0 | PSF-2.0 | Retain PSF notice | Verbatim LICENSE | Confirm only |
| **certifi** | 2026.10.23 | **MPL-2.0** | §3.2: tell recipients how to get Source Code Form, reasonably and promptly | PyPI sdist URL + SHA256 + repo; full MPL text | **DECISION 2** |
| CPython | 3.13.14 | PSF-2.0 | Retain notice; clause 3 "brief summary of the changes made to Python" | Windows `LICENSE.txt` + `license.rst`; notices state "changes: none" | Confirm wording |
| **VCRUNTIME140.dll** | 14.42.34438.0 | Microsoft Distributable Code | See §3 below | Conditions reproduced from CPython `LICENSE.txt` | **DECISION 3** |
| OpenSSL | 3.0.21 | Apache-2.0 | Include license; carry NOTICE if any (none upstream) | Apache text in CPython files | Confirm only |
| **SQLite** | 3.50.4 | Public domain | None legally; attribution courtesy | Project-written statement + upstream link | **DECISION 4** |
| **liblzma (XZ Utils)** | 5.2.5 | Public domain (5.2.x) | None legally | Project-written statement + upstream link | **DECISION 4** |
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
Options:
- (a) Accept the third-party links. Common practice, but they depend on PyPI
  staying available for the life of each release.
- (b) Mirror the exact sdist on the project's own release page. *Recommended:
  this keeps the duty under your control.*
- (c) Ship the sdist inside the installer (about 0.2 MB).

**DECISION 3 — Microsoft Distributable Code (VCRUNTIME140.dll).** CPython's
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

- **OpenSSL 3.0 is past upstream support.** OpenSSL's release strategy page
  states that "Versions 3.0, 1.1.1 and 1.0.2 are no longer supported". The
  bundled 3.0.21 comes from the CPython 3.13.14 Windows build. This is a
  security decision for the owner, for example moving to a Python build with
  a supported OpenSSL line before V1, or accepting and documenting the risk.
- Trademark (product name), see DECISION 3.

## 5. How to re-verify before signing

```powershell
cd C:\Users\aiuser\projects\github-community-agent
.\.venv\Scripts\python.exe .\scripts\third_party_notices.py check --bundle .\build\gc-agent-exclusion-candidate\dist\GitHubCommunityAgent
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-verify-installer-license-payload.ps1
```
Both must print PASS. The reviewer reads `packaging\third-party-licenses\THIRD_PARTY_NOTICES.txt`.
