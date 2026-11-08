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

The previously inspected source was `nature-ai-corp/nature-ai-worker` @ `release/v0.1.2-rc` (which contains GC extensions). For implementation, **compare the actual v0.1.1 sources** and use their common UI as the baseline:
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
- Existing `home.html` is an intermediate prototype and does **not yet**
  satisfy this actual v0.1.1 base UI-reuse decision. Avoid claiming it does.
- Next change should replace duplicated custom generic front-end pieces with
  vendored/adapted v0.1.1 UI assets; keep only product-specific selectors,
  workflows and APIs. Windows GUI E2E regression must follow.
