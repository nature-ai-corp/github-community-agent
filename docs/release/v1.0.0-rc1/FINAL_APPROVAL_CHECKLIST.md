# GitHub Community Agent 1.0.0-rc1 — final approval checklist

Only these four items remain before the DRAFT marker and the "not yet
released" statement can be replaced and the Windows pre-release published.
Each is ticked by the named person, never by automation. Background:
[`LEGAL_DECISION_REPORT.md`](LEGAL_DECISION_REPORT.md).

## 1. GitHub trademark use in the product name — counsel

- **Facts:**
  - The product name "GitHub Community Agent" is kept (owner decision).
    Publisher: NATURE AI CORP.
  - No GitHub logos are used.
  - An independence disclaimer ships in `NOTICE`, `THIRD_PARTY_NOTICES.txt`,
    README, the EXE description and the license page.
- **Requirement:** GitHub brand rules: "Do not use GitHub trademarks, logos, or
  artwork without GitHub's prior written permission" and "Do not use the GitHub
  name … in a way that suggests … your offering or project is by GitHub."
- [ ] **Counsel:** Is the name, with the disclaimer, acceptable without GitHub's
  written permission? If not: request permission from GitHub, or advise a
  change. (A rename would reopen the owner decision.)

## 2. Microsoft redistribution and end-user conditions — counsel

**Source:** CPython `LICENSE.txt`, "Additional Conditions for this Windows
binary build". It applies because the official PSF Windows runtime, including
`VCRUNTIME140.dll`, is redistributed unmodified. No Visual Studio license is
assumed.

**Already met (verified):**
- (a) Microsoft notices are not altered.
- (c) The product is Windows-only.

**Open:**
- [ ] **Counsel, condition (b):** Does "GitHub" in the product name count as
  using "Microsoft's trademarks in your programs' names"? GitHub, Inc. is a
  Microsoft subsidiary. Decide together with item 1.
- [ ] **Counsel, condition (e):** Is the installer license page enough to meet
  "require distributors and external end users to agree to terms that protect
  the Microsoft Distributable Code at least as much as Microsoft's own
  requirements"?
  - Acceptance is required before installation.
  - §3 reproduces CPython's conditions verbatim.
  - The draft adds no Microsoft terms of its own.

  If it is not enough, supply the additional clause.

## 3. Owner's software legality attestation — owner

Covers Microsoft condition (d): "do not … include Microsoft Distributable Code
in malicious, deceptive or unlawful programs."

- [ ] **Owner (NATURE AI CORP), signed and dated:** "GitHub Community Agent
  1.0.0-rc1 is not malicious, deceptive or unlawful software. It is read-only
  toward GitHub and does not post, modify or delete GitHub content."

## 4. Final wording approval — owner, after items 1–2

- [ ] **Owner:** approve the final text of `packaging/windows/END_USER_TERMS.txt`:
  - remove the "DRAFT FOR LEGAL REVIEW" line;
  - add any counsel-supplied clause.
- [ ] **Owner:** approve replacement wording for the last paragraph of `NOTICE`
  ("This independent repository is not yet released. The third-party license
  package awaits human legal review before public distribution.").
- [ ] **Owner:** approve `RELEASE_NOTES.md`, including the unsigned and
  SmartScreen disclosure.

**After all four items:** one packaging commit with the approved text. Then
rebuild the installer; re-run the payload, license-page, upgrade and Defender
checks; regenerate `SHA256SUMS.txt`; confirm CI; then the owner's clean
Windows 11 test, the merges, the tag and the GitHub pre-release.
