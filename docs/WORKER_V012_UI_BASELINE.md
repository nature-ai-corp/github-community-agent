# Product-family UI baseline: AI Worker v0.1.1, with GC extensions in v0.1.2

**Owner design decision (2026-11-07 ET):** Do not design another generic
Work Center or Settings interface for GitHub Community Agent. Reuse the
**existing general front-end UI of Nature AI Worker v0.1.1** and only customize the
product-specific parts.

## Version relationship

- **v0.1.1:** base, general-purpose Nature AI Worker. Its home, Work Center, Settings and general UI behavior are the reusable **product-family baseline**.
- **v0.1.2:** v0.1.1 extended with GitHub Community Agent-related functionality. Examine it to identify GC-specific additions, but **do not treat those extensions as generic base UI for every product**.
- **Independent GitHub Community Agent:** reuse/adapt the v0.1.1 general UI, add only the GC-specific Task definitions, repository settings, V1 Community Management and V2 Product Promotion. Remains a separate product and runtime.

## Actual source reviewed

Verified the actual `nature-ai-corp/nature-ai-worker` tag `v0.1.1` and compared its common UI to `release/v0.1.2-rc` (which contains GC extensions). For implementation, **v0.1.1** is the baseline:
- `src/nature_worker/static/index.html` — sidebar, Work Center, New Work,
  Work Detail, Settings modal
- `src/nature_worker/static/style.css` — standard Worker-family theme,
  layout, modal and responsive behavior
- `src/nature_worker/static/app.js` — Worker UI actions and state;
  **DO NOT copy Worker-specific API calls or runtime state unchanged**

The independent GitHub Community Agent may vendor/adapt the relevant
Apache-2.0 front-end assets within its own repository, preserving attribution,
license notices and source origin. It must not import the Worker package or
depend on a running Worker server.

## Same general UI as v0.1.1

- New Work / My Work / Work In Progress / Needs My Attention / Finished Work
- Standard Work list/detail presentation
- **The Worker v0.1.1-style Settings modal**, with Provider,
  Model, API Key, Advanced, Test connection, Cancel and Save.
- The same clear, simple navigation and front-end UI behavior.

## Product-specific additions ONLY

- App title/identity: GitHub Community Agent
- New Task definition selector (exclusive **Work Type OR Domain** discovery
  modes, not both simultaneously), with dynamically supplied task definitions
- Work classification filters sourced from product Task definitions
- V1: Review Issues, Review Discussions, Draft Reply, Community Report
- V2: Self-Promotion, Product Promotion choices, visible but disabled until
  actual Promotion workflow exists
- GitHub repository / Discussions READ token in Settings Advanced
- GitHub-backed source evidence and real Task results

## Isolation and acceptance

- **UI may be reused; Worker backend/runtime is NOT reused.** This product
  has its own Github + AI Runtime, database, credential handling and installer.
- Worker's encrypted credential behavior is NOT automatically inherited
  by copying UI, and must be reimplemented or securely adapted and tested.
- Do not edit the Nature AI Worker repo.
- **Implemented in this branch:** `worker_v011.css` is an exact copy of
  the Apache-2.0 Worker `v0.1.1` style.css (text equality checked); `home.html`
  has an adapted version of the v0.1.1 sidebar, Work Center and Settings
  dialog markup, with GC-specific tasks and real workflows. `gc.css` contains
  GC-specific styling rather than editing the original baseline CSS.
- **Not copied:** Worker's `app.js`, because its conversations, tools,
  messages, storage and API endpoints belong to a different runtime. GC
  browser actions are implemented locally against GC's independent backend.
- **Status:** code updated and JavaScript syntax validated, but no post-change
  Windows automated or real UI E2E results have been received. No claim of
  full feature-for-feature Worker UI parity; unnecessary Worker-only features
  (Workspace Files, general agent chat) are deliberately omitted.
- Original Nature AI Worker repository remains unchanged. Windows GUI E2E regression must follow.
