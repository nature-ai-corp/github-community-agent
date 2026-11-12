# GitHub Community Agent 2.0.0-b1 — release readiness record

Prepared 2026-11-12 for owner review. **Not a release approval.** Nothing merged, tagged,
signed or published.

**Candidate application commit:** `0048acea1f1fa86c80adba236f290d4c6e27c434`
(`feature/v2-promotion`, Draft PR #12). Later commits on the branch change documentation only.
**Installer (unsigned):** `GitHubCommunityAgent-2.0.0-b1-Setup-x64-unsigned.exe`,
SHA256 `eab0f6f27768f521903f2a69fdc868d4471577ba10a55b4f8b33dd98391eac21`, built by
`scripts/windows-build-installer.ps1` from the 2.0.0b1 release bundle of that commit
(frozen self-check PASS, EXE version metadata 2.0.0b1, third-party package check PASS).

## A. Scope

| Work Type | Status | Packaged build |
|---|---|---|
| GitHub Discussions | VERIFIED (Discussion #13) | offered |
| Repository Optimization | VERIFIED (Task #20, PR #15) | offered |
| Bluesky | VERIFIED (Task #22) | offered |
| DEV Community | VERIFIED (Task #23) | offered |
| Reddit Promotion | not verified; automated posting blocked | refused |
| Developer Forums | not verified | refused |
| Technical Articles, Social Media | legacy | refused for new Tasks; existing Tasks readable |

Evidence: release-gate tests; packaged-build smoke 14/14; isolated install trial (below)
checks the same in installed builds with `GCA_PROMOTION_DEV_WORK_TYPES=1` set.

## B. Security

- **M1 (fixed in `0048ace`):** technical review gate. Approval of any Promotion draft (GitHub
  Discussions, Bluesky, DEV Community, manual Reddit/Developer Forums) requires an insert-only
  review record of exactly that draft; never-reviewed or changed drafts are refused with a diff;
  an owner override must name that exact diff and is recorded. Tests:
  `tests/test_promotion_review_gate.py` (9), UI tests (3).
- Credential isolation (per-repository GitHub tokens, `bluesky.dpapi`, `devto.dpapi`, AI key in
  `settings.dpapi`), approvals bound to account and content, account switch and credential
  revocation (refused, nothing sent), outbox and reconciliation (no blind retries), concurrency
  and replay refusals, published vs. verified, no credentials in prompts/logs/records/API: see
  the Promotion test modules; request logging is disabled in code.
- Open, low severity: L1 GitHub Discussions approval/publish/refusal events are not in Activity
  History (internal event table only; M1 review and override events are recorded); L2 GitHub
  reconciliation searches only the 25 most recent Discussions; L3 DEV API keys have full account
  access (inherent; use a dedicated account and revoke when unused).

## C. Installation and upgrade

- **Isolated trial (random AppId, isolated folders), 42/42 PASS** on the final bundle
  (`scripts/windows_v1_to_v2_trial.py`, reusing `scripts/windows_upgrade_continuity_trial.py`): clean install and first run; v1.0.0-rc1 (frozen from
  the tag source) → 2.0.0-b1 upgrade with settings, encrypted settings bytes, Tasks, Activity
  History and archived Task preserved; additive migration (5 Promotion tables), V1 rows unchanged;
  rollback (V1 over V2 reads all data); uninstall keeps data; reinstall reads all Tasks; the real
  installation, real data and real AppId registry entry unchanged before/after.
- **Not yet performed:** production-AppId upgrade from the published v1.0.0-rc1 installer and the
  installer license-page Decline/Accept test. The development machine has no VM capability
  (Windows 11 Home) and its installed build is `0.0.1-devtrial`. Runbook:
  `VM_ACCEPTANCE_RUNBOOK.md`. The license-page test can also run isolated on any machine with
  `scripts/windows-manual-license-page-test.ps1 -Scenario Decline|Accept` (operated by a person).

## D. Packaging, licensing and versioning

- Version 2.0.0b1 (PEP 440); installer AppVersion 2.0.0-b1; EXE file version 2.0.0.0 (V1:
  1.0.0.0); same product AppId as V1 (upgrade in place).
- Third-party package regenerated from the candidate bundle: adds `_uuid.pyd`, `_wmi.pyd`
  (PSF CPython, byte-identical to the pinned runtime) and `VCRUNTIME140_1.dll` (byte-identical to
  the runtime's copy, version 14.51.36247.0, Microsoft-signed, same msvc-runtime component and
  terms as `VCRUNTIME140.dll`). License texts unchanged. File inventory completeness is not by
  itself a legal redistribution authorization; the existing runtime terms apply.
- Unsigned installer: SmartScreen warnings expected; SHA256 verification documented.

## E. Tests and CI

- Local full suite at `0048ace`: 636 passed, 3 skipped (the skips need the exact 3.13.17 build
  interpreter with pytest; their checks were run directly against the candidate bundle).
- CI run 43229514473 on `0048ace`: 7/7 success (Windows 635 passed / 4 skipped; Ubuntu 632
  passed / 7 skipped; Windows wheel packaging smoke success).

## F. Remaining before publication

1. Production-AppId VM upgrade test and license-page Decline/Accept test (owner-operated).
2. Owner decision on DEV article #5020275 (prepared update: `DEV_5020275` files in the local
   staging folder; not applied).
3. Owner decisions: unsigned beta accepted; merge PR #12; tag `v2.0.0-b1`; publish the GitHub
   pre-release with the installer and `SHA256SUMS.txt`; update README release status.
