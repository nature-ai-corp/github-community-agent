# GitHub Community Agent 2.0.0-b1 — release checklist

Same simplified procedure as `docs/release/v1.0.0-rc1/FINAL_APPROVAL_CHECKLIST.md`: no signed
attestation and no internal legal-approval record is required. This checklist is a procedure,
not authorization to publish. Each step needs the owner.

## A. Already done (evidence in `RELEASE_READINESS.md`)

- [x] Scope: only the four real-world-verified Promotion Work Types are offered in packaged builds.
- [x] M1 technical review gate implemented and tested.
- [x] Version metadata 2.0.0b1 / 2.0.0-b1; third-party package matches the bundle; installer
      builds with all gates; isolated install/upgrade/rollback/uninstall trial 42/42.
- [x] Release notes and `SHA256SUMS.txt` prepared.
- [x] CI green on the candidate application commit.

## B. Owner-operated before publication

- [ ] Production-AppId upgrade test in a clean Windows VM (`VM_ACCEPTANCE_RUNBOOK.md`).
- [ ] Installer license page: **Decline** (nothing installed) and **Accept** paths.
- [ ] Decide on DEV article #5020275 (prepared update not applied).
- [ ] Confirm the unsigned beta (SmartScreen warning; SHA256 verification in the notes).

## C. Publication (only after B, each step separately authorized)

1. Merge PR #12 (no force push), then build the installer from the merged commit **or** confirm
   the merged tree's `src/` and `packaging/` equal the candidate commit and reuse the verified
   installer; regenerate `SHA256SUMS.txt` if the installer changes and update `RELEASE_NOTES.md`.
2. Tag `v2.0.0-b1` on that commit.
3. Create a GitHub **pre-release** with only the installer and `SHA256SUMS.txt`; never upload
   `build/` or staging folders.
4. Confirm the published asset's SHA256 equals `SHA256SUMS.txt`.
5. Update the README release status (V1 and V2 sections).
