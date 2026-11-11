# GitHub Builder (GB) — V1-derived foundation

Status: bootstrap staging branch only. This branch is **not** a separate GitHub Builder repository, installer, or released application.

## Provenance

- Source repository: `nature-ai-corp/github-community-agent`
- Source branch: `main` (V1 baseline)
- Source commit: `e0dc19db3874e56e29070b1ed03b313739151e3d`
- Staging branch: `bootstrap/github-builder-from-v1`
- Excluded: `feature/v2-promotion` (reserved for Promoter / Nature GitHub Agent)

## Goal

Create a standalone, Windows-first **GitHub Builder** product, using proven V1 desktop shell, runtime, provider integration, GitHub connectivity, approval and audit patterns as a technical starting point. GB is for **building and improving repository presentation/configuration**, not community moderation or promotion.

## Reuse / replace

| Reuse or adapt | Replace / omit from GB application |
| --- | --- |
| Windows application skeleton and packaging | Community-specific title, branding and installer identity |
| AI provider setup / model abstraction | Community Issues / Discussions work types |
| Repository connection and read-only facts | Community reports and contributor moderation UI |
| Existing safe credentials and authentication patterns | V2 Promotion plan, drafts and publishing |
| Task execution and review/approval patterns | Hard-coded Community terminology / paths |

## Initial GB use cases

1. Read-only repository assessment: README, docs, topics, metadata and community profile files.
2. AI produces a source-grounded improvement plan for exactly the requested scope.
3. Generate proposed README/docs/metadata changes with explicit previews/diffs.
4. User approves an exact change set, destination repository and branch.
5. Apply only approved changes, preferably through a branch and reviewable pull request.
6. Verify actual GitHub results and retain an auditable outcome report.

## Security and isolation

- Distinct application identity, installer, data path and token store; never automatically import V1 settings or GitHub credentials.
- Read-first. No write or publish without explicit, scoped approval and permission checks.
- Idempotent writes and reconciliation for unknown outcomes; no blind retry.
- Separate repository/project context; never mix task evidence across repositories.
- Keep shared Core versioned; do not duplicate modules by copying permanent divergent implementations.

## Next implementation steps

- [ ] Create separate `nature-ai-corp/github-builder` repository with chosen visibility and access controls.
- [ ] Import the V1 baseline there, preserving license/attribution as appropriate, rather than use this staging branch indefinitely.
- [ ] Rename product identity, package/import names, installer and data directories; remove Community-specific functional routes.
- [ ] Implement GB repository assessment and preview-only workflow.
- [ ] Add safe approved writes, E2E Windows tests, packaging and release checks.
- [ ] Expose Builder module for independent Builder and future Nature GitHub Agent integrated use.

This file documents a development bootstrap and does not claim GB is implemented.
