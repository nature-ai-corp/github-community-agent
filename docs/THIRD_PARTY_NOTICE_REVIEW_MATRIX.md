# GC Agent V1 — Third-party legal materials review matrix

**Status: provenance and installer payload VERIFIED by automation; human
license review NOT yet recorded; public distribution still BLOCKED.**
This is an internal traceability record, not legal advice.

Distribution package: `packaging/third-party-licenses/` (15 files:
`THIRD_PARTY_NOTICES.txt`, `sbom.cdx.json` CycloneDX 1.5, `MANIFEST.json`
SHA256 list, 12 verbatim license texts). Generated and verified by
`scripts/third_party_notices.py` from the optimized frozen bundle
`GitHubCommunityAgent.exe` SHA256
`620268DE3186CA97F7809001FA5EAFF4CF2D38EDDAD0632AA8E4664D59D3DA4E`
(958 files). `MANIFEST.json` keeps `legal_review_approved: false`.

## How provenance was established (2026-11-10, native Windows)

- **Python code:** all 355 PYZ modules and 11 CArchive entries are
  code-object-identical to the build-venv distribution, the CPython 3.13.14
  stdlib, PyInstaller 6.22.3 loader/run-time hooks, or first-party `src`.
  This upgrades the earlier "venv-only candidate" versions to verified
  frozen versions.
- **Native files:** 25/25 DLL/PYD files and 926/926 Tcl/Tk data files are
  byte-identical to the PSF CPython 3.13.14 Windows runtime used for the build.
- **Bootloader:** EXE `.text`, `.data`, `.pdata` sections identical to
  PyInstaller 6.22.3 stock `run.exe` (resources differ by design).
- **Other files:** `base_library.zip` is 154/154 stdlib entries; certifi
  `cacert.pem` matches certifi's own RECORD hash (unmodified); UI assets
  match `src`.
- **Library versions:** runtime-reported and pinned to CPython v3.13.14
  `PCbuild/get_externals.bat` (SHA256 `7f4ef6af…35fb5`).

## Python distributions (frozen, verified)

| Distribution | Version | License | Text in package | Installed verified |
|---|---|---|---|---|
| anyio | 4.16.0 | MIT | Yes (dist-info, verbatim) | Yes |
| certifi | 2026.10.23 | MPL-2.0 | Yes + full MPL-2.0 + source location | Yes |
| h11 | 0.16.0 | MIT | Yes | Yes |
| httpcore | 1.0.9 | BSD-3-Clause | Yes | Yes |
| httpx | 0.28.1 | BSD-3-Clause | Yes | Yes |
| idna | 3.20 | BSD-3-Clause | Yes | Yes |
| typing-extensions | 4.16.0 | PSF-2.0 | Yes | Yes |

## Runtime and native components

| Component | Version | License | Text in package |
|---|---|---|---|
| CPython runtime | 3.13.14 | PSF-2.0 | Windows-build `LICENSE.txt` + `Doc/license.rst` @ v3.13.14 |
| OpenSSL | 3.0.21 | Apache-2.0 | both CPython files |
| SQLite | 3.50.4 | Public domain | statement in notices |
| zlib | 1.3.1 | Zlib | `license.rst` |
| libffi | 3.4.4 | MIT | both CPython files |
| Tcl/Tk | 8.6.15 | TCL | `license.terms` + `LICENSE.txt` |
| expat / libmpdec / bzip2 (static) | 2.8.1 / 4.0.0 / 1.0.8 | MIT / BSD-2 / bzip2 | CPython files |
| liblzma (XZ Utils, static) | 5.2.5 | Public domain | statement in notices |
| VCRUNTIME140.dll | 14.42.34438.0 | Microsoft Distributable Code | CPython `LICENSE.txt` "Additional Conditions" |
| PyInstaller bootloader / rthooks | 6.22.3 | GPL-2.0+ w/ Bootloader exception / Apache-2.0 | `COPYING.txt` |

## Installer payload

`packaging/windows/gc-agent.iss` now installs the package to
`{app}\third-party-licenses` and has compile-time `#error` guards if
`THIRD_PARTY_NOTICES.txt` or `MANIFEST.json` is missing.
`scripts/windows-build-installer.ps1` refuses to compile unless
`third_party_notices.py check` proves the package matches the bundle being
packaged. The older `dist/GitHubCommunityAgent` baseline (which bundles
Pygments, packaging and pytest) is **rejected** by that check.

`scripts/windows-verify-installer-license-payload.ps1` builds the real
recipe with an isolated AppId, installs it silently into `build/`, compares
all 977 installed files byte-for-byte, uninstalls, and confirms the real
installation and user data hashes are unchanged. Three native runs PASSED
(2026-11-10): `run-20261110T024602Z`, `run-20261110T024957Z`,
`run-20261110T025259Z` (on committed `2475b58`, including the updated NOTICE).

## Still open (human decisions, not automatable)

1. **Human license review** of the package and sign-off recorded outside
   automation (superseded 2026-11-10: the RC spec and its `REVIEW_APPROVAL.json` / `LegalReviewEvidence` gate were removed; the earlier text read: the RC spec's `REVIEW_APPROVAL.json` / `LegalReviewEvidence`
   remain deliberately absent).
2. **MPL-2.0 source availability**: the notices point to the exact PyPI
   sdist (with SHA256) and upstream repository. A reviewer should confirm
   that a third-party URL is an acceptable means for this distribution, or
   decide to host or ship the certifi source.
3. **Microsoft Distributable Code**: VCRUNTIME140.dll is redistributed under
   the conditions in CPython's `LICENSE.txt`. Confirm these conditions are
   acceptable to the publisher (EULA terms that are at least as protective).
4. **Public-domain statements** for SQLite and liblzma are project-written
   summaries with upstream links, not upstream-authored texts.
5. **Rebuilds**: any change in dependencies, Python or PyInstaller version
   fails the check until a person updates the pins in
   `scripts/third_party_notices.py`, regenerates and reviews the package.
6. Unrelated release gates remain: signing, approved version, two-account
   DPAPI test, changed-code upgrade test, owner approval.
