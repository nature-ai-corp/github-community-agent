# GitHub Community Agent 2.0.0-b1 (beta pre-release) — release notes (draft until the owner publishes)

**Status:** prepared for owner review. Not tagged, not released, not signed.
**Candidate application commit:** `0048acea1f1fa86c80adba236f290d4c6e27c434` (branch `feature/v2-promotion`, PR #12; later commits change documentation only)
**Asset (unsigned):** `GitHubCommunityAgent-2.0.0-b1-Setup-x64-unsigned.exe`
**SHA256:** `eab0f6f27768f521903f2a69fdc868d4471577ba10a55b4f8b33dd98391eac21` (also in `SHA256SUMS.txt`)

This is the first public pre-release of V2. It keeps everything in V1 (v1.0.0-rc1) and adds
**Promotion**: one agent that researches a public repository you are authorized to promote,
drafts content and, only after you approve the exact action, publishes it.

## Included Promotion Work Types (each verified in real use)

| Work Type | What the Agent does after your exact approval | Real-world acceptance |
|---|---|---|
| GitHub Discussions | Publishes one announcement Discussion (GraphQL), re-checks permission first, then reads engagement | Discussion #13 |
| Repository Optimization | Applies one approved change: Description or Topics (REST), or README through a new branch and pull request that you merge | Task #20, PR #15 |
| Bluesky | Publishes one post from your connected project account (AT Protocol), then verifies it from the public index | Task #22 |
| DEV Community | Saves one technical article as a private draft, compares it, publishes after a separate confirmation, then verifies it publicly | Task #23 |

Not included: Reddit (automated posting blocked by Reddit's authorization requirements),
Developer Forums (unverified). The former generic "Technical Articles" and "Social Media"
Work Types are legacy: existing Tasks stay readable, new ones cannot be created.

## Safety model

- Nothing is published without approval of the exact action (destination, account, text);
  any edit cancels the approval.
- Every draft needs a recorded **technical review** of its exact text before it can be approved.
  If it changed after the review, approval is refused and the change is shown; approving anyway
  is an explicit, recorded owner decision.
- Each platform has its own encrypted credential (Windows DPAPI, current user): per-repository
  GitHub tokens, a Bluesky app password, a DEV API key. Credentials are never sent to the AI
  model, never shown back by the application and never logged.
- An uncertain outcome (for example a timeout after a publish request) is reconciled by reading
  the platform, never retried blindly. These mechanisms reduce, but cannot eliminate, the risk of
  duplicate or unrecorded publications.
- "Published" and "independently verified" are shown separately.

Know before you connect accounts: a DEV API key has full account access and no scopes; a
Bluesky app password can post as the account; Repository Optimization needs GitHub
administration permission for Description and Topics. Use dedicated project accounts and revoke
credentials you no longer need.

## Upgrading from V1

Install over V1. Settings, encrypted credentials, Tasks, archived Tasks and Activity History are
kept; the database gains new Promotion tables only. Uninstalling keeps your data.
(Isolated trial: V1.0.0-rc1 source build → 2.0.0-b1, rollback, uninstall and reinstall —
42/42 checks passed. A production-AppId upgrade test in a clean VM is part of the release
checklist; see `RELEASE_READINESS.md`.)

## Unsigned installer

The installer and application are **not code-signed**. Windows SmartScreen may warn
("Windows protected your PC"). Verify the SHA256 above before running:

```powershell
Get-FileHash .\GitHubCommunityAgent-2.0.0-b1-Setup-x64-unsigned.exe -Algorithm SHA256
```

## Third-party software

License texts, notices and the SBOM are installed in the `third-party-licenses` folder.
New in this version's inventory: `_uuid.pyd`, `_wmi.pyd` and `VCRUNTIME140_1.dll` from the same
PSF CPython 3.13.17 Windows runtime, covered by the existing runtime terms.

## Changelog since v1.0.0-rc1

- Technical review gate before every Promotion approval (insert-only review records, diff of
  changes since review, recorded owner override).
- Promotion domain with four verified Work Types (above), exact-action approvals, per-platform
  credentials, outbox/reconciliation, public verification and Task Activity History entries.
- Settings → Promotion: platform selector (GitHub, Bluesky, DEV Community).
- New Task: Promotion Work Types; DEV Community article brief (topic, cited repository documents).
- Release gate: only real-world-verified Work Types are offered in packaged builds.
- Version 2.0.0b1 (installer 2.0.0-b1); third-party inventory updated.
