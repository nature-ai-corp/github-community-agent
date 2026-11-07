# V1 migration inventory and boundaries

Source project: [Nature AI Worker](https://github.com/nature-ai-corp/nature-ai-worker) (Apache-2.0). Retain relevant copyright notices, LICENSE and NOTICE attribution when carrying source into this product. Do not copy credentials, test outputs, local data, or Platform Server/private implementation material.

## Existing source references

| Source | Relevant code | Migration treatment |
|---|---|---|
| [PR #34](https://github.com/nature-ai-corp/nature-ai-worker/pull/34), `feature/github-community-readonly-mvp` | GitHub Issues and Discussions read tools, associated tests | Extract with dependencies and test contracts; do not copy an entire Worker runtime |
| [PR #38](https://github.com/nature-ai-corp/nature-ai-worker/pull/38), `feature/github-issue-comment-approval-v2` | Guarded issue comment publishing, approvals, outbox and reconciliation | Separate code from original storage/UI integrations; preserve denial and unknown-outcome guarantees |
| [PR #39](https://github.com/nature-ai-corp/nature-ai-worker/pull/39), `feature/github-community-agent-profile` | Four starter tasks, instructions and work-center UI entry | Convert into default product experience, not optional Standalone profile |
| [docs/GITHUB_COMMUNITY_AGENT.md](https://github.com/nature-ai-corp/nature-ai-worker/blob/main/docs/GITHUB_COMMUNITY_AGENT.md) | Earlier profile documentation | Use as migration reference, rewrite for independent product |

## Required boundary

- Source ownership and versioning are independent: no joint release branches, shared mutable checkout, shared credentials or shared local data directories.
- Evaluate Core extraction with a dependency inventory before choosing pinned package versus a narrowly scoped vendored snapshot. **Do not claim a separately versioned Worker Core package exists before it is built and verified.**
- Do **not** bring Platform Client S–C functionality into this project. Standalone-versus-enterprise separation remains enforced in Worker.
- Real GitHub network outcomes must be distinguished from simulated tests. Treat community text as untrusted and require exact-action approval for writes.
- Keep the original Worker PRs and source untouched until independent V1 migration passes its tests and the owner approves cleanup.

## Acceptance evidence to collect

- V1 starts independently on clean Windows without an AI Worker installation, with its own product identity and data root.
- Each starter task works through this product's own runtime and UI against the authorized GitHub repository.
- No write without approval; correct behavior on refusal, timeout, duplicate requests and unknown posting outcome.
- Positive and negative security tests, clean install/upgrade/uninstall, and an independent CI run.
- Separate signing, release notes and version/tag/release provenance.

**Status:** Inventory prepared; application code has **not** yet been migrated or validated.
