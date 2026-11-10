# GC Agent V1 — License approval checklist (`1.0.0rc1`)

**Prepared 2026-11-10. Not legal advice. Nothing in this file is approved.**
Each item is ticked by the named human who decides it, never by automation.
The package keeps `legal_review_approved: false` in `MANIFEST.json`. No
`REVIEW_APPROVAL.json` or `LegalReviewEvidence` exists, and automation must
not create them.

Background: [`V1_LICENSE_REVIEW_REPORT.md`](V1_LICENSE_REVIEW_REPORT.md)
(DECISIONS 1–5) and
[`VCRUNTIME_REDISTRIBUTION_BASIS.md`](VCRUNTIME_REDISTRIBUTION_BASIS.md).

## Technical verification is not legal approval

| | Technical verification (done) | Legal approval (NOT done) |
|---|---|---|
| Question answered | "Is what we ship exactly what the documents say?" | "Is shipping it this way allowed, and is the wording adequate?" |
| Who | Automation and the agent, re-runnable | Owner and/or qualified counsel |
| Evidence | `third_party_notices.py check` PASS; installer payload PASS (978 files byte-verified); SBOM lists every bundled component; certifi sdist matches the frozen files | A signed and dated decision record, kept outside this repo's automation |
| Can it be automated? | Yes | **No** |

A PASS in the left column says nothing about the right column.

## Who decides what

- **Owner (business decision).** Owner approval is enough unless counsel advises otherwise:
  - keep or change the product name;
  - which VCRUNTIME option to fund (packaging work);
  - who governs the license and version pins;
  - whether to add optional courtesy text.
- **Qualified legal review (counsel).** These are judgments the owner and the agent should not make alone:
  - trademark use of "GitHub";
  - whether the Microsoft Distributable Code conditions are met;
  - MPL-2.0 §3.2 adequacy;
  - wording of the end-user terms and the disclaimer;
  - adequacy of the public-domain statements.

## Checklist

### 1. Product name "GitHub Community Agent" and trademark use (DECISION 3, part)
Technical facts:
- the name appears in the installer, the EXE `ProductName` and the docs;
- an independence disclaimer ("not affiliated with, sponsored by, or endorsed by GitHub, Inc. or Microsoft") ships in `NOTICE`, `THIRD_PARTY_NOTICES.txt`, `README.md` and the EXE `FileDescription`;
- no GitHub logos are bundled.

GitHub's published brand rules (brand.github.com/foundations/logo, checked 2026-11-10), verbatim:
- "Do not use the GitHub name or any GitHub logo in a way that suggests you are GitHub, your offering or project is by GitHub, or that GitHub is endorsing you or your offering or project."
- "Do not use GitHub trademarks, logos, or artwork without GitHub's prior written permission."
- "No adaptation or use of any kind of any of our registered trademarks or copyrights … is allowed without the express written permission of GitHub, Inc."

The page gives no explicit rule for naming ("GitHub X" versus "X for GitHub"). A name that **begins** with "GitHub" is the form most likely to be read as a GitHub product. The realistic choices are:
- (A) keep the name and seek GitHub's written permission;
- (B) rename to a descriptive form such as "Community Agent for GitHub", with counsel judging whether that is permissible referential use;
- (C) use a neutral name, with "works with GitHub" only in descriptive text.

- [ ] **Counsel:** Is "GitHub" in the product name acceptable under GitHub's trademark and logo policy? Recommend A, B or C.
- [ ] **Counsel:** Does it conflict with the CPython/Microsoft condition "do not use Microsoft's trademarks in your programs' names or in a way that suggests … endorsed by Microsoft"? (GitHub is a Microsoft subsidiary.)
- [ ] **Counsel:** Approve the disclaimer wording as written, or supply replacement text.
- [ ] **Owner:** Keep the name, or rename (for example "Community Agent for GitHub" or a neutral name) if counsel advises. A rename is a packaging change and requires re-running the installer and upgrade checks.

### 2. Microsoft `VCRUNTIME140.dll` redistribution (DECISION 3)
Technical facts:
- version 14.51.36247.0;
- byte-identical to the PSF CPython 3.13.17 copy;
- validly signed by Microsoft;
- obtained through the PSF runtime, not from Visual Studio;
- the installer has no end-user terms page.

Narrowed on 2026-11-10 (`VCRUNTIME_REDISTRIBUTION_BASIS.md` §5a):
- **No Visual Studio purchase needed:** the permission comes through the PSF's
  conditional grant, so NATURE AI CORP does not need its own Visual Studio
  license.
- **The conditions cover the whole runtime:** the CPython license says the
  Microsoft Distributable Code is embedded in **every** CPython `.exe`, `.dll`
  and `.pyd`, so not bundling `VCRUNTIME140.dll` would not remove the
  conditions.
- **Only one condition is open:** end-user terms.

- [ ] **Counsel:** Confirm that redistribution under the PSF's conditional grant is sufficient (no separate Microsoft license).
- [ ] **Counsel:** Draft or approve the end-user terms clause that protects the Microsoft Distributable Code "at least as much as Microsoft's own requirements".
- [ ] **Owner, on counsel's advice:** Authorize adding those terms as an installer license page that users accept (Inno `LicenseFile`). This is a small packaging change, followed by re-running the installer, payload and upgrade checks.
- [ ] **Owner:** Attest that the program is not malicious, deceptive or unlawful (V1 is read-only toward GitHub).

### 3. certifi MPL-2.0 source distribution (DECISION 2)
Technical facts:
- certifi 2026.10.23 is unmodified;
- the exact PyPI sdist ships at `third-party-licenses/certifi-2026.10.23/source/certifi-2026.10.23.tar.gz` (SHA256 `a9895e6e…36cd`);
- the build fails unless the bundled `cacert.pem` and all certifi `.py` files match that archive;
- the full MPL-2.0 text ships with it.

- [ ] **Counsel:** Does shipping the source in the installer, with notices that name it, satisfy MPL-2.0 §3.2 (Source Code Form available "by reasonable means in a timely manner")?
- [ ] **Owner (optional):** Also mirror the sdist on the eventual release page.

### 4. SQLite and liblzma public-domain notices (DECISION 4)
Technical facts:
- SQLite 3.50.4 (`sqlite3.dll`) and liblzma from XZ Utils 5.2.5 (statically linked in `_lzma.pyd`);
- the notices carry short project-written statements with upstream links;
- liblzma 5.2.5 is not the backdoored 5.6.0/5.6.1.

- [ ] **Counsel:** Approve the public-domain statements, or require upstream text (for example SQLite's dedication or blessing).
- [ ] **Owner/counsel:** Accept or align the SBOM license identifiers:
  - SQLite is tagged SPDX `blessing`;
  - liblzma is tagged `LicenseRef-public-domain`.

  Both are defensible, but they are inconsistent in style. Changing either is a generator change plus regeneration; no app change.

### 5. Third-party notices and SBOM completeness (DECISIONS 1 and 5)
Technical facts:
- the fail-closed generator classifies all 958 bundle files;
- the SBOM (CycloneDX 1.5) lists the app (`1.0.0rc1`, EXE SHA256), the 7 Python packages and the 14 runtime components with their files;
- the installed payload was byte-verified;
- the Unicode Character Database (Unicode-3.0) is covered in CPython's `license.rst` but is not a separate SBOM component;
- CPython's "brief summary of changes" is stated as "none".

- [ ] **Counsel:** Review `THIRD_PARTY_NOTICES.txt` and every listed file, and approve the package as a whole (DECISION 1).
- [ ] **Counsel:** Confirm the CPython clause 3 wording ("changes: none") and the PyInstaller bootloader exception reading (unmodified bootloader).
- [ ] **Owner:** Decide whether the SBOM must list sub-components such as the Unicode data separately. Today it is "complete for licensing via the notices", not an exhaustive SBOM.
- [ ] **Owner:** Name who may change the reviewed pins in `scripts/third_party_notices.py`. Any dependency or toolchain change fails the build until that person re-reviews it (DECISION 5).
- [ ] **Owner:** Record the reviewer, the date and the `MANIFEST.json` SHA256 set of the approved package. Approval covers only that exact set: a rebuild changes the EXE hash and needs the package check (and, where content changed, review) again.

## Re-verify before any approval is recorded

```powershell
.\build\release-bundle\venv\Scripts\python.exe .\scripts\third_party_notices.py check --bundle .\build\release-bundle\dist\GitHubCommunityAgent
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-verify-installer-license-payload.ps1
```

Both must print PASS on the exact build that will be signed.
