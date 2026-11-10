# V2 Promotion: one universal Promotion Agent

**Status:** implemented on `feature/v2-promotion`, Windows. Not released. V1
(`v1.0.0-rc1`) is unchanged.

## Architecture

There is **one** Promotion Agent (`src/github_community_agent/promotion.py`,
`PromotionService`) and **one** Task definition (`promote_repository`, the
"Promotion" Domain in New Work). Self-promotion and product promotion are not
separate workflows, engines or code paths. The only configuration is:

| Setting | Where | Default |
|---|---|---|
| Target GitHub repository | Settings → Promotion | `nature-ai-corp/github-community-agent` |
| GitHub token for **that** repository | Settings → Promotion | none (research and drafting do not need one) |

Every repository uses the same Work Center, research, planning, content
generation, approval and publishing controls, monitoring, improvement, security
and audit behavior.

## Workflow

| Step | What happens | Writes to GitHub? |
|---|---|---|
| 1. Research | Reads the public repository's facts, README and recent releases. Links are rebuilt from the repository name, not taken from responses | No |
| 2. Plan | AI plan: audience, value proposition, channels, schedule, measurable objectives. Statements are marked Verified (with source) or Proposed | No |
| 3. Draft | AI announcement for a GitHub Discussion in the same repository, from evidence only | No |
| 4. Review and approve | The user edits the text, runs **Check publishing permission**, chooses a category and approves the **exact** draft (fingerprinted) | No |
| 5. Publish | Separately confirmed. The permission is re-checked; then the fixed `createDiscussion` mutation runs once | **Yes, only this step** |
| 6. Monitor | Reads the published Discussion's comments, upvotes and reactions | No |
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

- **One channel:** a GitHub Discussion in the target repository. Other channels
  appear in plans only as manual suggestions; the app never posts to
  third-party sites.
- **Discussions must be enabled** in the target repository. On 2026-11-10,
  `nature-ai-corp/github-community-agent` had Discussions **disabled**, so
  publishing there is refused until the owner enables them.
  `nature-ai-corp/nature-ai-worker` had them enabled.
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
- **Live read-only research** against both real repositories succeeded. No
  live publication was made: that needs the owner's token and explicit
  approval.
