# GC Agent V1 — Third-party legal materials review matrix (NOT CLEARED)

**Status: blocked for public distribution.** This is an internal traceability
record, not legal advice or a completed software bill of materials.

Evidence: Optimized frozen bundle `GitHubCommunityAgent.exe` SHA256
`620268DE3186CA97F7809001FA5EAFF4CF2D38EDDAD0632AA8E4664D59D3DA4E`;
958 files, 366 embedded modules; 26 native binaries hashes match.
Windows regression most recently **261 PASS**.
These results verify file integrity, not license compliance.

## Current Python distribution candidates

| Distribution | Venv version candidate | Venv license metadata | Text staged | Frozen exact version verified | Installer inclusion verified |
|---|---|---|---|---|---|
| anyio | 4.16.0 | MIT | Yes, review only | No | No |
| certifi | 2026.10.23 | MPL-2.0 | Yes, review only | No | No |
| h11 | 0.16.0 | MIT | Yes, review only | No | No |
| httpcore | 1.0.9 | BSD-3-Clause | Yes, review only | No | No |
| httpx | 0.28.1 | BSD-3-Clause | Yes, review only | No | No |
| idna | 3.20 | BSD-3-Clause | Yes, review only | No | No |
| typing-extensions | 4.16.0 | PSF-2.0 | Yes, review only | No | No |

**Important:** The above are CURRENT development-venv candidate versions and
self-declared license metadata; they have NOT been established independently
as immutable versions originating from the actual optimized EXE. A staged
license text file is not automatically an installed NOTICE.

## Native-binary review groups

| Component | Observed Windows VERSIONINFO | Provenance/license text status | Official reference |
|---|---|---|---|
| CPython .pyd + python313.dll | 3.13.14, PSF | Open: Python license plus incorporated materials | https://docs.python.org/3.13/license.html |
| OpenSSL libcrypto/libssl | 3.0.21 | Open: Apache-2.0, upstream notices and exact DLL provenance | https://openssl-library.org/source/license/index.html |
| Tcl/Tk tcl86t/tk86t | 8.6.15 | Open: Tcl/Tk license.terms and packaged data | https://www.tcl-lang.org/software/tcltk/license.html |
| SQLite sqlite3.dll | 3.50.4.0 | Open: verify exact binary source; SQLite core public domain | https://www.sqlite.org/copyright.html |
| zlib zlib1.dll | 1.3.1 | Open: exact upstream zlib attribution/material | https://zlib.net/zlib_license.html |
| libffi libffi-8.dll | Blank | Open: exact origin/version/license | https://github.com/libffi/libffi/blob/master/LICENSE |
| VCRUNTIME140.dll | 14.42.34438.0 | Open: redistribution eligibility and provenance | https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files |
| PyInstaller bootloader EXE | Blank | Open: exact bootloader provenance and GPL exception obligations | https://www.pyinstaller.org/en/stable/license.html |

## Independent legal-review package and blocking conditions

The current `packaging/windows/gc-agent.iss` is a separate
**unsigned internal test** installer source. It includes root LICENSE
and NOTICE but does not explicitly package third-party license files.
The candidate staging folder at
`build/release-audit/optimized-candidate-sbom-review/venv-license-candidates-for-review`
contains seven files and `REVIEW_MANIFEST.json`, **for review only**.

A **separate**, currently non-buildable
`packaging/windows/gc-agent-release-candidate.iss` requires:
a non-dev `AppVersion`; an independently reviewed `ReviewedLegalDir`
containing `THIRD_PARTY_NOTICES.txt` and `REVIEW_APPROVAL.json`;
and explicit `LegalReviewEvidence`. The source also packages all files
under that reviewed legal directory into `{app}/third-party-licenses`
and references only the already-built optimized candidate.
**No approved legal directory or approval file has been created.**

The preprocessor checks merely prevent accidental builds with omitted
files; they cannot authenticate an approval, guarantee the written
text is correct, or substitute for human legal/provenance review.

Before approval, a reviewer must establish the actual source and
complete notices for all embedded components, certify any MPL-2.0
covered-source availability and redistribution statements, and inspect
the final built installer files. The frozen EXE must also be rebuilt
from the approved source if the application changes; a different
source commit and old EXE do not constitute a validated new version.
Never label the package release-ready solely because automated gates pass.

**Other open gates:** true changed-build optimized install/upgrade
and user-data continuity, two-account Windows DPAPI separation,
official version authorization, trusted Authenticode signing, final
owner approval. Do not merge PR #11 or publish unsigned artifacts.
