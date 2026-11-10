# GitHub Community Agent 1.0.0-rc1 — legal decision report (Windows)

Prepared 2026-11-10 at `781769b`. **Not legal advice and not an approval.** It
lists only the obligations that apply to what NATURE AI CORP actually ships:
the installer with the frozen app, the official PSF CPython 3.13.17 Windows
runtime, the bundled packages and the Inno Setup runtime.

**Established facts (preserved):**
- The runtime is the official PSF CPython Windows distribution, and
  `VCRUNTIME140.dll` comes from it.
- No Microsoft Visual Studio license is assumed to be necessary.
- The product name "GitHub Community Agent" is retained, and so is the
  independence disclaimer.
- The app is licensed under Apache-2.0.

**Reviewed:**
- `LICENSE`: whitespace-identical to apache.org `LICENSE-2.0.txt`;
- `NOTICE`;
- `packaging/windows/END_USER_TERMS.txt`;
- `third-party-licenses/THIRD_PARTY_NOTICES.txt`;
- `V1_LICENSE_APPROVAL_CHECKLIST.md`, `V1_LICENSE_REVIEW_REPORT.md` and
  `VCRUNTIME_REDISTRIBUTION_BASIS.md`;
- the upstream Nature AI Worker `NOTICE` (read-only, for Apache §4(d));
- the Inno Setup `license.txt`.

No upstream license investigation was reopened.

## Decision table

| # | Requirement (exact) | Source, clause | What NATURE AI CORP does | Satisfied | Unresolved | Minimum corrective action | Legal review? |
|---|---|---|---|---|---|---|---|
| 1 | Give recipients a copy of the License | Apache-2.0 §4(a) (own app) | `LICENSE` (canonical text) installed and byte-verified | Yes | — | None | No |
| 2 | Retain upstream copyright/attribution notices; if the upstream Work has a NOTICE file, include its attribution notices | Apache-2.0 §4(c), §4(d); Nature AI Worker `NOTICE` ("Copyright 2026 The Nature AI Worker Authors") | Per-file SPDX headers (`The Nature AI Worker Authors`) kept in the 2 adapted source files; `NOTICE` says the code was adapted from Nature AI Worker under Apache-2.0 | Partly. Source headers yes; but the frozen EXE does not show them, and `NOTICE` lacks the Worker's attribution line | Worker attribution line missing from the installed `NOTICE` | Add to `NOTICE`: "Nature AI Worker — Copyright 2026 The Nature AI Worker Authors (Apache License 2.0)" | No (owner confirms) |
| 3 | Retain the PSF copyright notice; include "a brief summary of the changes made to Python" | CPython `LICENSE.txt`, PSF License Agreement clauses 2–3 | Full `LICENSE.txt` and `license.rst` shipped; notices state "changes: none" (runtime unmodified, verified) | Yes | — | None | Confirm only |
| 4 | Do not alter Microsoft notices; distribute only for Microsoft platforms | CPython `LICENSE.txt`, "Additional Conditions…", conditions (a) and (c) | `VCRUNTIME140.dll` byte-identical and Microsoft-signed; Windows x64 only; signing scripts never re-sign third-party binaries | Yes | — | None | No |
| 5 | "do not … use Microsoft's trademarks in your programs' names or in a way that suggests your programs come from or are endorsed by Microsoft" | Same, condition (b) | Name contains "GitHub" (a GitHub, Inc. mark; GitHub is a Microsoft subsidiary); the disclaimer denies affiliation with GitHub and Microsoft | Disclaimer yes | Whether "GitHub" counts as a "Microsoft trademark" under this condition | None technically; a counsel opinion | **Yes** |
| 6 | "do not … include Microsoft Distributable Code in malicious, deceptive or unlawful programs" | Same, condition (d) | V1 is read-only toward GitHub; no deceptive behavior known | Yes: this is a restriction on what is distributed, met by the product | — (owner decision 2026-11-10: no signed attestation required; an earlier attestation was withdrawn) | None | No |
| 7 | "require distributors and external end users to agree to terms that protect the Microsoft Distributable Code at least as much as Microsoft's own requirements" | Same, the paragraph before the conditions | Installer terms page (acceptance required) reproduces CPython's conditions **verbatim** and adds no Microsoft terms of its own | Mechanism yes (acceptance verified) | Whether verbatim CPython text is "at least as much as Microsoft's own requirements" for end users who do **not** redistribute | Counsel approves the wording as is, or supplies the extra clause; no other change | **Yes** |
| 8 | Do not use GitHub trademarks without prior written permission; do not suggest the offering is by or endorsed by GitHub | GitHub brand rules (brand.github.com/foundations/logo); trademark law | Name retained (owner decision); disclaimer in `NOTICE`, the notices, README, EXE `FileDescription` and the terms page; no GitHub logos | Disclaimer and no-logo, yes | Whether a name **beginning** with "GitHub" needs GitHub's permission | Counsel opinion, or request GitHub's written permission | **Yes** |
| 9 | Make the Source Code Form available and tell recipients how to get it; an executable may be under other terms only if they don't limit Source Code Form rights | MPL-2.0 §3.2(a), §3.2(b) (certifi) | Exact sdist shipped in `third-party-licenses/certifi-2026.10.23/source/` with SHA256 and upstream URLs; full MPL text; terms §2 defers to each component's own license | Yes | Confirmation only | None | Confirm only |
| 10 | Include license and copyright notices | MIT/BSD/PSF/Zlib/TCL/bzip2/Unicode-3.0 (anyio, h11, httpcore, httpx, idna, typing-extensions, libffi, expat, libmpdec, zlib, Tcl/Tk, UCD) | Full texts in `THIRD_PARTY_NOTICES.txt` and per-component files; SBOM | Yes | — | None | No |
| 11 | Include the license; carry any NOTICE file | Apache-2.0 §4(a), §4(d) (OpenSSL 3.5.9, PyInstaller run-time hooks) | License texts included; OpenSSL ships no NOTICE file | Yes | — | None | No |
| 12 | Bootloader exception: unmodified bootloader, no copyleft on the app | PyInstaller GPL-2.0+ with Bootloader exception | Stock bootloader (sections identical to `run.exe`); `COPYING.txt` included | Yes | — | None | No |
| 13 | No license obligation (public domain) | SQLite, liblzma 5.2.5 | Project-written statement plus upstream links | Yes | Wording approval (DECISION 4), optional | None required | Optional |
| 14 | Binary redistributions keep Inno's copyright notice and website "currently in place (for example, in the About boxes)"; acknowledgment optional | Inno Setup License, conditions 2–3 | Unmodified Inno runtime inside the setup EXE (its About box intact) | Yes | — | None (optional credit line in `NOTICE`) | No |
| 15 | Accurate release statements (avoid misleading recipients) | Not a license clause; consumer-accuracy hygiene | Installed `NOTICE` says "not yet released … awaits human legal review before public distribution"; the terms header says "DRAFT FOR LEGAL REVIEW" | — | Text is wrong for a public release | After decisions 5, 7 and 8, update both lines (and item 2) in one packaging commit; rebuild and re-verify | No (owner wording) |

**Status update (2026-11-10).** Corrected in packaging text; the installer
was rebuilt and re-verified (SHA256 `84454641…079430`):
- **#2:** `NOTICE` now reproduces the Nature AI Worker attribution verbatim
  ("Nature AI Worker / Copyright 2026 The Nature AI Worker Authors").
- **Terms §1:** now lists every Apache §2 right, including "prepare
  derivative works of (modify)".
- **Terms §3:** now says "the included VCRUNTIME140.dll is itself Microsoft
  Distributable Code".

Still pending by design:
- the terms stay **DRAFT** and the `NOTICE` "not yet released" paragraph stays
  until final wording is approved (#15);
- #5, #7 and #8 (counsel) and #6 (owner) are unchanged.

See [`FINAL_APPROVAL_CHECKLIST.md`](FINAL_APPROVAL_CHECKLIST.md).

**Procedure update (owner decision 2026-11-10).** The release now follows the
simplified Worker-style procedure in
[`FINAL_APPROVAL_CHECKLIST.md`](FINAL_APPROVAL_CHECKLIST.md):
- **#5, #7, #8:** "Legal review? Yes" now means **optional legal advice**
  behind an owner risk decision, not a mandatory approval step.
- **#6:** needs no document.
- **Internal approval records:** none are required.

The obligations in this table are unchanged.

**Summary (as originally written, before the procedure update).**
- **Counsel decisions needed:** only #5, #7 and #8, plus confirmations of #3
  and #9.
- **Owner actions:** #2 (one `NOTICE` line), #6 (attestation) and #15 (release
  wording).
- **Satisfied, no action:** everything else.

## Does the installer license page preserve the original terms accurately?

Checked line by line against `LICENSE`, `NOTICE` and CPython `LICENSE.txt`:

| Terms section | Verdict | Note |
|---|---|---|
| Header (product, version, publisher, DRAFT) | Accurate | The DRAFT line must go only after the decision (#15) |
| §1 Apache-2.0 | Accurate; no restriction added ("Nothing in these terms limits the rights…") | **Wording fix (recommended):** it says "use, reproduce and distribute", but Apache §2 also grants the right to **modify / prepare derivative works**. Change to "use, reproduce, modify and distribute" so the summary is not narrower than the license. The AS-IS sentence matches Apache's standard notice |
| §2 Third-party components | Accurate; each component "governed by its own license" | Satisfies MPL §3.2(b) (no limitation of Source Code Form rights) |
| §3 Microsoft Distributable Code | The conditions are **verbatim**, and a test enforces this. Nothing is invented: no Microsoft grant, no extra restriction, no Visual Studio reference | **Precision fix (recommended):** "embedded in that build's .exe, .dll and .pyd files, including VCRUNTIME140.dll" → "embedded in that build's .exe, .dll and .pyd files; VCRUNTIME140.dll is itself Microsoft Distributable Code". The open counsel question is #7 |
| §4 Independence and trademarks | The disclaimer is verbatim from `NOTICE`; "grant no right to use any trademark" is consistent with Apache §6 | — |
| Acceptance mechanism | Required ("I accept" gates Next; verified in an isolated wizard) | Silent installs (`/VERYSILENT`) skip the page, which is standard Inno behavior; enterprise deployers accept on their users' behalf |

**Conclusion.**
- The page faithfully preserves the Apache-2.0 terms, the third-party license
  precedence and the CPython/Microsoft conditions, and adds no new
  restrictions.
- Two small wording fixes are recommended: §1 "modify", and the §3
  `VCRUNTIME140.dll` phrasing.
- Whether the page is *sufficient* for condition #7 is a counsel decision.

## Path to publication (superseded 2026-11-10)

The earlier "minimum path" required counsel opinions, a signed owner
attestation and an internal approval record. It is **replaced** by the
simplified procedure in [`FINAL_APPROVAL_CHECKLIST.md`](FINAL_APPROVAL_CHECKLIST.md):
- **Owner risk decisions:** the name and terms sufficiency, with legal advice
  optional.
- **No attestation.**
- **One final release-text commit:** `NOTICE` paragraph, DRAFT line,
  `legal_review_approved` flag.
- **Then:** verify the exact binary, and publish on explicit authorization.

Already done: the `NOTICE` Worker attribution and the §1/§3 terms fixes
(`b6b31e2`).
