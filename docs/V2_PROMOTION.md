# V2 Promotion: one Promotion Agent, platform Work Types

**Status:** implemented on `feature/v2-promotion`, Windows. Not released. V1
(`v1.0.0-rc1`) is unchanged.

## Architecture

There is **one** Promotion Agent and **one** shared engine
(`src/github_community_agent/promotion.py`, `PromotionService`). New Work →
Promotion offers **independently selectable Work Types** (each social platform is its own), using the same
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

**Release gate.** Only Work Types with real-world acceptance evidence are offered in a
release build (`RELEASE_VERIFIED_WORK_TYPES` in `promotion.py`; evidence in
[V2_PROMOTION_RELEASE_GATE.md](testing/V2_PROMOTION_RELEASE_GATE.md)). Today that is
**GitHub Discussions, Repository Optimization and Bluesky**. The others are development code: they are hidden from
New Work, refused by the backend API and service (create and every action), and can be
enabled only when running from source with `GCA_PROMOTION_DEV_WORK_TYPES=1`. A packaged
(frozen) build ignores that variable. Existing Tasks of an excluded Work Type stay
viewable, read-only.

| Work Type | Task definition | Expected result | Publishing |
|---|---|---|---|
| GitHub Discussions (**released: VERIFIED**) | `promote_repository` | Announcement Discussion in the target repository, then engagement metrics | **Automated**, after exact approval and a fresh permission check |
| Repository Optimization (**released: VERIFIED**) | `promote_repository_optimization` | Exact proposed changes with live before/after: Description, Topics, README (diff) | **Owner-approved apply, per change**: README only via a new branch + pull request into the default branch (never merged, never pushed to it); Description and Topics each by separate exact-action approval (ADMIN); every result read back from GitHub |
| Reddit Promotion (development: NOT VERIFIED) | `promote_reddit` | One disclosed post for a subreddit that allows project posts | **Draft / manual publication only** |
| Developer Forums (development: NOT VERIFIED) | `promote_developer_forums` | One disclosed project announcement for a forum section that allows it | **Draft / manual publication only** |
| Technical Articles (legacy) | `promote_technical_articles` | Existing drafts only | Not offered in New Task, cannot be started; existing Tasks stay draft-only |
| Bluesky (**released: VERIFIED**, Task #22) | `promote_bluesky` | One post (Bluesky limits: 300 graphemes, 3000 bytes) with the repository link | **Agent publishes** from the connected project account after exact approval; public read-back verification |
| DEV Community (development: NOT VERIFIED) | `promote_dev_community` | One original, educational Markdown article on dev.to, from an optional topic and cited repository documents | **Agent publishes** from the connected DEV account: private draft, read-back comparison, separate confirmation, publish, public read-back |
| Social Media (legacy) | `promote_social_media` | Existing drafts only | Not offered in New Task, cannot be started; existing Tasks stay draft-only |

GitHub Discussions and Bluesky have real publishers, and DEV Community has one in development.
Reddit and Developer Forums have **no** integration, and no fake one:
approving their text only records the exact version you will post or apply
yourself (status `ready_manual`). Each shows a checklist (for example: read
the community's rules, keep the affiliation disclosure, post once, never as an
answer to someone else's question). Each social platform is its own Work Type; the
first is **Bluesky** (released after Task #22's real-world acceptance): the post is approved as one exact action
(account DID, text, link facets), published with one `createRecord` from the
connected project account (app password, own DPAPI file) and verified through the
public AppView. Platforms are released one by one after real-world acceptance.
Reddit Promotion additionally approves the
target subreddit with the text and, after you post by hand, can **record the
post URL** (validated against the approved subreddit; status
`published_user_confirmed`) and **check it on Reddit** with one public read
(`published_verified` only if subreddit, title and body match and it was not
removed). Because nothing is sent, **no channel
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

## Content quality

All six Work Types share one rule set (`_SHARED_RULES` in `promotion.py`): facts only from
the evidence; GitHub API release data (`authoritative_facts`) overrides conflicting README
text; no invented features, metrics, testimonials or endorsements; never describe unread
Issues; no requests for votes, stars or follows; no incentives, testimonials or influencer
outreach; one post per community and no cross-posting. Each Work Type adds only its own
channel focus, so a plan covers only the selected Work Type.

| Check | Applies to |
|---|---|
| Output complete (provider `finish_reason` is not `length`/`content_filter`, nothing cut) | Plans, drafts, improvement suggestions |
| Plan stays in scope (no GitHub Discussion publication outside GitHub Discussions) and marks statements Verified / Proposed | Plans |
| Title at most 120 characters; body within the Work Type's limit (4000–5500) | Drafts |
| At most 300 grapheme clusters and 3000 UTF-8 bytes (Bluesky Lexicon); must contain the https repository link | Bluesky |
| `Current (verified):` and `Proposed:` labels | Repository Optimization |
| Affiliation disclosure ("I maintain …") at the start of each post | Reddit, Developer Forums, Bluesky, DEV Community |
| DEV: title ≤ 128, ≤ 4 lowercase alphanumeric tags, no front matter / Liquid / unsafe HTML, https links, ≥ 500 words and two `##` sections, AI-assistance disclosure, no advertising language or @mentions | DEV Community |
| No claim that no release or installer exists when a release is published; no description of unread Issues; no engagement bait, incentives or testimonials | All |

Generation budgets are per Work Type (1,500–3,500 completion tokens, 120-second timeout;
`GCA_PROMOTION_MAX_TOKENS` overrides them, 500–16,000). V1 keeps its own limits (1,200 tokens,
30 seconds, 6,000 characters). A failed check triggers **one** corrective retry with the
problems listed. If the output still fails, the draft is stored as **incomplete** with the
reasons: it is never shown as a ready draft and cannot be approved. The owner can edit it
(edits are re-checked) or use **Regenerate draft** (plan and draft again, at most five
times per draft). Approval re-checks the exact content. Improvement suggestions that fail
the rules are not stored.

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

## Repository Optimization workflow (released: VERIFIED with Task #20 and PR #15)

Research → Propose Changes → Review → Approve → Apply → Verify, in the same engine:

1. **Propose**: the live repository state is read (public reads, no token): description,
   topics, default branch, full README and its blob SHA. The model proposes exact values;
   each becomes one change item (`promotion_changes`), validated (topic names, one-line
   description, README keeps the independence disclaimer and at least 60% of its content,
   no stale release claims). Invalid items are `incomplete`.
2. **Review**: before/after for each item, a unified diff for README; edit (re-checked,
   cancels approval) or skip.
3. **Approve**: one item at a time; the fingerprint covers repository, kind, default
   branch, before state (and README SHA), new value and the exact action text.
4. **Apply**: only the approved item, once: fresh permission check (WRITE for README,
   ADMIN for Description/Topics), then a check that GitHub still has the "before" state
   (otherwise nothing is written). Fixed REST allowlist (`_REST_ROUTES`), no merge or
   delete endpoint. README: create `gca/readme-t<task>-c<change>` from the default branch →
   commit `README.md` there → open a pull request. Lost responses are `uncertain`.
5. **Verify**: read GitHub back — PR open from that branch into the default branch, the
   branch's README equals the approved text, the default branch is unchanged; or the
   description/topics equal the approved values. PR URL, facts and events are stored.
