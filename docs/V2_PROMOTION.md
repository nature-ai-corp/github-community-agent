# V2 Promotion: one Promotion Agent, six Work Types

**Status:** implemented on `feature/v2-promotion`, Windows. Not released. V1
(`v1.0.0-rc1`) is unchanged.

## Architecture

There is **one** Promotion Agent and **one** shared engine
(`src/github_community_agent/promotion.py`, `PromotionService`). New Work →
Promotion offers **six independently selectable Work Types**, using the same
pattern as Community Management: choosing a Work Type selects its own Task
definition. A Task runs only its own Work Type; unselected Work Types never
run. Self-promotion and product promotion are not separate workflows. The
only configuration is:

| Setting | Where | Default |
|---|---|---|
| Target GitHub repository | Settings → Promotion | `nature-ai-corp/github-community-agent` |
| GitHub token for **that** repository | Settings → Promotion | none (research and drafting do not need one) |

Every repository and Work Type uses the same Work Center, research,
planning, drafting, exact-text approval, audit, and (where applicable)
publishing, monitoring and improvement.

## Work Types

| Work Type | Task definition | Expected result | Publishing |
|---|---|---|---|
| GitHub Discussions | `promote_repository` | Announcement Discussion in the target repository, then engagement metrics | **Automated**, after exact approval and a fresh permission check |
| Repository Optimization | `promote_repository_optimization` | Proposed description, topics, README, release and template changes | **Proposals only**; the app never writes to the repository |
| Reddit Promotion | `promote_reddit` | One disclosed post for a subreddit that allows project posts | **Draft / manual publication only** |
| Developer Forums | `promote_developer_forums` | One disclosed project announcement for a forum section that allows it | **Draft / manual publication only** |
| Technical Articles | `promote_technical_articles` | One article draft (tutorial or deep dive) | **Draft / manual publication only** |
| Social Media | `promote_social_media` | A short (max 280 characters) and a longer post | **Draft / manual publication only** |

Only GitHub Discussions has a real publisher. The other five have **no**
integration with Reddit, forums, blogs or social networks, and no fake one:
approving their text only records the exact version you will post or apply
yourself (status `ready_manual`). Each shows a checklist (for example: read
the community's rules, keep the affiliation disclosure, post once, never as an
answer to someone else's question). Because nothing is sent, **no channel
credentials are collected**, and the GitHub token is never used for them:
permission check, publish, reconcile and monitor are refused for those Work
Types. If a channel integration is added later, its credentials must be stored
separately from GitHub tokens.

## Workflow

| Step | What happens | Writes to GitHub? |
|---|---|---|
| 1. Research | Reads the public repository's facts, README and recent releases. Links are rebuilt from the repository name, not taken from responses | No |
| 2. Plan | AI plan: audience, value proposition, channels, schedule, measurable objectives. Statements are marked Verified (with source) or Proposed | No |
| 3. Draft | AI draft for the selected Work Type only, from evidence only | No |
| 4. Review and approve | The user edits the text and approves the **exact** draft (fingerprinted, including its channel). GitHub Discussions also needs **Check publishing permission** and a category | No |
| 5. Publish | GitHub Discussions only: separately confirmed, permission re-checked, then the fixed `createDiscussion` mutation runs once. Other Work Types: you publish by hand | **Yes, only this step, only GitHub Discussions** |
| 6. Monitor | GitHub Discussions only: reads comments, upvotes and reactions | No |
| 7. Improve | AI suggestions from the plan and the measured engagement; never publishes | No |

## Security and isolation

- **Task binding.** A Task is bound to the repository selected when it is
  created. Changing the selection later never moves its evidence, drafts,
  approvals, publications or metrics. Every action call is checked against the
  Task's repository.
- **Tokens per repository.** Tokens are stored encrypted with Windows DPAPI in
  `promotion.dpapi`, separate from V1 settings. Each is used only for its own
  repository. There is no fallback to another repository's token or to the V1
  read token. Tokens are never written to the work database, never sent to the
  AI model and never returned by the API.
- **Least privilege.** Classic tokens with scopes beyond `public_repo`,
  `write:discussion` or `read:discussion` are refused. Use a fine-grained token
  limited to the one repository, with Discussions read and write.
- **Permission per publication.** Each publish re-checks four things: the
  repository is public, Discussions are enabled, the token's user has WRITE,
  MAINTAIN or ADMIN, and the approved category exists.
- **Explicit approval.**
  - Approval echoes the fingerprint of the exact repository, channel, title and
    body the user saw. The server then records a fingerprint that also covers
    the category.
  - Any edit cancels the approval.
  - Publishing requires the approved fingerprint and a confirmation.
- **Durable outbox and idempotency.**
  - The action is marked `publishing` with a unique key before the request.
    The key is embedded as an invisible HTML comment in the post.
  - Anything that may have reached GitHub (a timeout, a server error, an
    unreadable response) is recorded as `uncertain`, never retried
    automatically. **Check whether it was published** looks for the key in the
    repository's recent Discussions.
- **Fixed documents only.** Only four fixed GraphQL documents can be sent;
  model text is only ever variable data, after approval.
- **Audit.** Append-only `promotion_events` (event names and times only).

## Scope limits (smallest complete V2)

- **One automated channel:** a GitHub Discussion in the target repository.
  The app never posts to third-party sites.
- **Discussions must be enabled** in the target repository (they are now
  enabled in `nature-ai-corp/github-community-agent`).
- **Public repositories only.**

## Verification

- `tests/test_promotion.py`: offline, with a GitHub-like mock that binds tokens
  to repositories. It covers:
  - one definition, one agent, the same workflow for two repositories;
  - per-repository tokens without fallback;
  - task binding after switching repositories;
  - exact-text approval and approval invalidation on edit;
  - permission re-checks;
  - broad-token refusal;
  - the uncertain → reconcile path, with no blind retry;
  - monitoring, improvement and the audit trail;
  - no token in the database, API, model input or files;
  - HTTP nonce checks and size limits.
- `tests/test_promotion_work_types.py`: Work Type selection (each runs only
  itself; unselected types never run; HTTP route binding), scope isolation
  (manual types never publish or use the GitHub token; actions cannot cross
  Work Types, Tasks or repositories) and approval enforcement (exact text,
  channel-bound fingerprints, edits cancel approval; existing GitHub
  Discussion records stay valid).
- **Live acceptance (owner-approved):** a GitHub Discussions Task in the
  isolated V2 test environment published
  `https://github.com/nature-ai-corp/github-community-agent/discussions/13`
  on 2026-11-11, and monitoring and improvement ran on it.
