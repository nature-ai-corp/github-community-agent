# GitHub Community Agent 1.0.0-rc1 — release checklist (simplified)

**Owner decision (2026-11-10).** The release follows the practical Nature AI
Worker open-source process (`nature-ai-worker` `docs/V0_1_1_PUBLICATION_CHECKLIST.md`,
`docs/RELEASES.md`), adjusted only for this product's real differences:
- the official PSF CPython runtime;
- an unsigned pre-release allowed;
- the third-party "GitHub" mark in the product name.

There is **no signed attestation and no internal legal-approval record**
requirement. This checklist is a procedure, not authorization to publish.

**Withdrawn:** the Software Release Attestation dated November 10, 2026,
signed outside this repository, has been withdrawn by the owner. It is **not**
release approval evidence and is not reproduced here.

## A. Genuine obligations (must hold in what is published)

| Obligation | Source | State in the verified build |
|---|---|---|
| Ship the Apache-2.0 license and the NOTICE, including the upstream attribution | Apache-2.0 §4(a), §4(d) | `LICENSE` (canonical) and `NOTICE` (with the Nature AI Worker attribution) installed and byte-verified ✓ |
| Ship third-party license texts and notices | MIT/BSD/PSF/Apache/Zlib/TCL/Unicode/MPL terms | `third-party-licenses/` and `THIRD_PARTY_NOTICES.txt`, plus the SBOM, installed and byte-verified ✓ |
| Make the certifi source available | MPL-2.0 §3.2 | Exact sdist shipped and checked ✓ |
| PSF notice and summary of changes | CPython PSF License clauses 2–3 | Shipped; "changes: none" ✓ |
| Don't alter Microsoft notices; Windows only | CPython "Additional Conditions" (a), (c) | Unmodified, Microsoft-signed DLL; Windows x64 only ✓ |
| Don't include Microsoft code in malicious, deceptive or unlawful programs | Same, (d) | A restriction on what is distributed, met by the product itself (read-only toward GitHub). **No document or signature is required** ✓ |
| Downstream distributors and end users agree to protective terms | Same, (e) | Installer license page, which must be accepted, reproduces the conditions verbatim ✓ (sufficiency: optional legal advice, see B) |
| Don't use Microsoft marks in program names / imply Microsoft endorsement; don't use the GitHub mark in a way that suggests origin or endorsement | Same, (b); GitHub brand rules; trademark law | Independence disclaimer everywhere, no logos ✓. The name decision rests with the owner (see B) |
| Inno Setup notices kept in the binary | Inno Setup License, cond. 2 | Unmodified Inno runtime ✓ |
| Accurate release statements | Avoid misleading recipients | **Done** (C3, final installer `018EB046…E93DB825`): final `NOTICE` wording; DRAFT line removed; internal approval flag removed ✓ |

## B. Owner decisions (risk choices; no document or signature required)

- [ ] **Product name.** Keep "GitHub Community Agent" (decided) and accept the
  trademark exposure, or seek GitHub's written permission or legal advice
  first. GitHub's rules ask for prior written permission for trademark use.
- [ ] **Terms page sufficiency, condition (e).** Publish the page as it is,
  minus the DRAFT line, or get legal advice first. The Worker's published
  v0.1.1 left this condition open and showed only Apache-2.0; this product
  already requires acceptance of the verbatim conditions.
- [ ] **Unsigned pre-release.** Allowed (decided). The release notes disclose
  it and give SmartScreen guidance.
- [ ] **Release-text wording** for `NOTICE` and the terms header (C3).

## C. Publication procedure (Worker-style)

1. **Freeze:** functionality is frozen at `1.0.0rc1`; the tree is clean; CI is
   7/7 on the release commit.
2. **Owner go-ahead for the release text** (B).
3. **Final release-text commit** (packaging text only):
   - replace the `NOTICE` "not yet released / awaits human legal review"
     paragraph;
   - remove the DRAFT line from the terms;
   - drop the internal `legal_review_approved` flag from the license package
     (generator, `MANIFEST.json`, tests).

   Then rebuild the installer **from the verified bundle**.
4. **Verify the exact final binary:**
   - package check;
   - isolated install, byte-verify and uninstall;
   - upgrade trial;
   - Defender scan;
   - the manual license page Decline and Accept tests
     (`scripts/windows-manual-license-page-test.ps1`);
   - regenerate `SHA256SUMS.txt` and update the hash in `RELEASE_NOTES.md`;
   - CI 7/7.
5. **Clean Windows 11 check** (recommended; not a legal requirement): download
   the asset, check the SHA256, record the SmartScreen prompt, install, run one
   task, uninstall.
6. **Public-asset review** (positive allowlist, as in the Worker): upload only
   the installer, `SHA256SUMS.txt` and the release notes. Never upload `build/`
   evidence, logs, test installers or private files.
7. **With explicit owner authorization:**
   - merge #6→#7→#8→#9→#11 with merge commits;
   - confirm `main` equals the release commit's tree;
   - create the immutable tag `v1.0.0-rc1` on `main`;
   - publish a GitHub Release marked **pre-release** with the verified asset.
     Publish the exact verified file; do not rebuild it for upload.
8. **Confirm:** the published asset's SHA256 equals `SHA256SUMS.txt`; record
   the commit, tag, checksum and release URL.

## D. Optional internal procedures (not required for publication)

| Item | Status |
|---|---|
| Signed owner attestation | **Removed** (no legal basis as a release gate) |
| Internal legal-approval record (`REVIEW_APPROVAL.json`, `LegalReviewEvidence`, `legal_review_approved`) | **Removed** from gates. The RC spec that required them is deleted; the flag goes in C3 |
| Counsel review of name or terms | Optional owner choice (B) |
| Code signing (Azure Artifact Signing) | Optional; prepared, not required for the pre-release |
| Inno Setup commercial-use license | Optional. The ISCC banner says "Non-commercial use only"; Inno's FAQ asks commercial users to buy a license but says it is not strictly required (same conclusion as the Worker review). Owner may buy one; it is not a publication blocker |
| Real-AppId upgrade on the owner's own PC | Recommended, not required |
