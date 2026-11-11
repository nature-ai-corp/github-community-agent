# V2 Promotion — real-world release acceptance gate

**Release rule (owner decision): no real-world verification, no released Work Type.** Only Work Types with real evidence are offered by a release build; the rest stay development code.

**Date:** 2026-11-11 · **Branch:** `feature/v2-promotion` (PR #12, Draft) · **Repository:** `nature-ai-corp/github-community-agent` · **AI provider:** `openai` / `gpt-4.1-mini` · Windows 11, isolated V2 test environment. Repository changes were made only by Repository Optimization Task #20, after the owner approved each exact change (see below).

## Acceptance matrix

| Work Type | Status | Real evidence | Operation | Released? |
|---|---|---|---|---|
| GitHub Discussions | **VERIFIED** | Owner-approved [Discussion #13](https://github.com/nature-ai-corp/github-community-agent/discussions/13) (category Announcements, created 2026-11-11T01:05:41Z), confirmed on GitHub today; monitoring re-run today: 1 upvote(s), 0 comments, 0 reactions | API-driven publication after approval | **Yes** |
| Repository Optimization | **VERIFIED** | Task #20 (2026-11-11), each change owner-selected and approved by exact action, applied by the Agent and read back from GitHub: **Description** (PATCH, verified 03:40:11Z; an earlier attempt failed with HTTP 403 before the owner added the Administration permission), **Topics** (PUT, 7 topics, verified 13:59:39Z), **README** via Agent-created branch `gca/readme-t20-c3` and [PR #15](https://github.com/nature-ai-corp/github-community-agent/pull/15) (verified open, branch README = approved text, main unchanged); PR #15 **merged by the owner** at 2026-11-11T15:39:40Z (merge commit `25d5568`), after which `main`'s README is byte-identical to the approved file | Owner-approved apply per change; README only by branch + pull request (the app never merges) | **Yes** |
| Reddit Promotion | **NOT VERIFIED** | Draft only (Task #15); no owner approval, no real publication or change | Manual publication by the owner (never performed) | **No** — excluded |
| Developer Forums | **NOT VERIFIED** | Draft only (Task #16); no owner approval, no real publication or change | Manual publication by the owner (never performed) | **No** — excluded |
| Technical Articles | **NOT VERIFIED** | Draft only (Task #17); no owner approval, no real publication or change | Manual publication by the owner (never performed) | **No** — excluded |
| Social Media | **NOT VERIFIED** | Draft only (Task #18); no owner approval, no real publication or change | Manual publication by the owner (never performed) | **No** — excluded |

No Work Type is FAILED: the remaining four were not attempted in the real world, because that needs the owner's approval of exact content and destination and the owner's own accounts, which this work must not invent.

## How exclusion is enforced

- `RELEASE_VERIFIED_WORK_TYPES = {"promote_repository", "promote_repository_optimization"}` in `promotion.py` — one engine, no duplicate.
- New Work lists only available definitions (`available_definitions()`); `/api/definitions` returns V1 + GitHub Discussions + Repository Optimization only.
- `POST /api/tasks` refuses the four unverified Work Types (400); `PromotionService.start` and every action (edit, approve, regenerate, preflight, publish, reconcile, monitor, improve) refuse them with "not available in this release". Existing Tasks stay viewable, read-only.
- Development use only from source with `GCA_PROMOTION_DEV_WORK_TYPES=1`; a frozen build ignores the variable.
- Tests: `tests/test_promotion_release_gate.py` (UI definitions, API, service, frozen-build switch, V1 unchanged, GitHub Discussions end to end); `tests/test_promotion_repo_changes.py` (Repository Optimization apply in the packaged configuration).
- **Packaged build check (two verified Work Types):** see *Packaged build check* below.
- Earlier check (GitHub Discussions only): a frozen bundle (`build/release-bundle-v2-gate2`) run with isolated data and `GCA_PROMOTION_DEV_WORK_TYPES=1` set: 10/10 PASS.

### Packaged build check (two verified Work Types)

A frozen V2 bundle built with `scripts/windows-build-release-bundle.ps1` from this branch (unsigned, still labelled 1.0.0rc1, for gate validation only; frozen self-check PASS) was run with isolated data and `GCA_PROMOTION_DEV_WORK_TYPES=1` deliberately set: **10/10 PASS**. UI served; `/api/definitions` = the five V1 Work Types + GitHub Discussions + Repository Optimization only; the development switch is ignored; `POST /api/tasks` is refused for Reddit Promotion, Developer Forums, Technical Articles and Social Media; no Task created; Promotion settings available.

## Acceptance contracts

### GitHub Discussions

- **Promise:** Announce the product in its own repository's GitHub Discussions and measure the response.
- **Operation:** Research (public REST) → plan → draft → owner edits/approves exact text + category → fresh permission check → one fixed `createDiscussion` GraphQL mutation in that repository → monitor (read-only GraphQL) → improvement suggestions (never published).
- **User receives:** Editable draft; after approval, the published Discussion URL; engagement metrics; suggestions.
- **Real-world evidence required:** A real Discussion created by the app after owner approval, readable on GitHub, plus a real monitoring read.
- **Security and approval:** Exact-text + category approval (fingerprint); repository-bound DPAPI token with WRITE+; fresh permission check per publish; durable outbox with reconcile; no other repository or site.

### Repository Optimization

- **Promise:** Propose concrete improvements to the repository's own presentation.
- **Operation:** Research → Propose Changes (Description, Topics, README with live before/after) → Review (edit or skip) → Approve one exact action → Apply (fresh permission check, unchanged-state check, fixed REST allowlist; README only via a new branch + pull request, never merged by the app) → Verify (GitHub read back).
- **User receives:** Exact proposed changes; after approval, the applied change or the README pull request URL, with verification facts and Activity History.
- **Real-world evidence required:** An owner-approved exact change actually applied to the authorized repository (settings or merged PR), and the resulting GitHub state read back.
- **Security and approval:** Separate exact-action approval per change (fingerprint); repository-bound DPAPI token; ADMIN for Description/Topics, WRITE for README; no merge or delete endpoint; duplicate applies refused; refusals and failures recorded in Activity History.
- **Verified (2026-11-11, Task #20):** Description and Topics applied by the Agent and read back as exactly the approved values; README [PR #15](https://github.com/nature-ai-corp/github-community-agent/pull/15) created by the Agent from `gca/readme-t20-c3` into `main` and verified; the owner reviewed and merged it (merge commit `25d5568`, 15:39:40Z); `main`'s README now equals the approved file byte for byte. Corrections entered through Claude Code: the owner-selected values were typed into each change with Save (Description re-entered after the 403); approve, apply and verify were the Agent's own workflow.

### Reddit Promotion

- **Promise:** One honest, disclosed Reddit post for a subreddit whose rules allow project posts.
- **Operation:** Research → plan (this channel only) → draft with first-sentence disclosure → owner approves the exact text **and the target subreddit** (both in the fingerprint) → owner posts by hand → **Record Manual Publication** → **Check on Reddit**. The app never posts and holds no Reddit credential.
- **Record Manual Publication (development, NOT VERIFIED):** the post URL is accepted only if it is a Reddit post permalink (`https://www.reddit.com/r/<subreddit>/comments/<id>/…`; short and share links refused) in the **approved** subreddit, the post ID is extracted, and the owner explicitly confirms the exact approved text was posted → status `published_user_confirmed`. `published_verified` is set **only** when one public, unauthenticated read (`/by_id/t3_<id>.json`) shows the same post ID and subreddit, the approved title and body, and no removal. An unreadable post (blocked, rate-limited, network) never upgrades the record; a later failed check withdraws `published_verified`. Every record, refusal and check is in Task Activity History (`action#<id>:…`). A recorded URL alone is **not** acceptance evidence.
- **User receives:** Post text and a rules checklist.
- **Real-world evidence required:** The owner-approved exact text posted manually by the owner in a subreddit whose rules were checked, and the real post URL verified.
- **Security and approval:** Owner approval of text and subreddit; owner's own account; one post, no cross-posting, no vote requests.
- **Needed to verify:** Owner's Reddit account; owner selects a subreddit and confirms its rules allow project posts; owner approves the corrected exact text; owner posts by hand; the post URL is verified.

### Developer Forums

- **Promise:** One disclosed project announcement for a forum section that allows it.
- **Operation:** Research → plan (this channel only) → draft with first-sentence disclosure. No forum integration.
- **User receives:** Post text and a rules checklist.
- **Real-world evidence required:** The owner-approved exact text posted manually in an appropriate forum section, and the public URL verified.
- **Security and approval:** Owner approval of text and forum; owner's own account; never as an answer to someone else's question.
- **Needed to verify:** Owner chooses a forum and section that allows project announcements and an account; approves corrected text; posts by hand; URL verified.

### Technical Articles

- **Promise:** One factual technical article about the product.
- **Operation:** Research → plan (this channel only) → article with opening disclosure. No publishing integration.
- **User receives:** Article text and a publication checklist.
- **Real-world evidence required:** The owner-approved article published through an authorized account, and the URL verified.
- **Security and approval:** Owner approval of text and publication; publication's promotional-content rules.
- **Needed to verify:** Owner chooses a publication/blog and account; approves the corrected article; publishes; URL verified.

### Social Media

- **Promise:** A short and a longer factual post for accounts the owner controls.
- **Operation:** Research → plan (this channel only) → two posts with disclosure, length-checked. No social integration.
- **User receives:** Short post (≤ 280 characters) and long post (≤ 1,200 characters) with a checklist.
- **Real-world evidence required:** The owner-approved post published through an authorized account, and the post URL verified.
- **Security and approval:** Owner approval of text and account; no tagging without consent; no repeated or automated posting.
- **Needed to verify:** Owner chooses the platform and an account they control; approves the corrected posts; publishes; post URL verified.

## Quality defects from the first acceptance report — fixed and re-tested

| Defect (docs/testing/V2_PROMOTION_SIX_WORK_TYPES_ACCEPTANCE.md) | Fix | Re-run result |
|---|---|---|
| Outdated README | README rewritten on this branch: v1.0.0-rc1 public, unsigned installer + SHA-256, five V1 Work Types, V2 under development | Fixed on the branch; **`main` still serves the old README to research until PR #12 (or a README-only PR) is merged** — the main remaining source of wrong claims |
| Silent truncation (1,200-token cap, `finish_reason` ignored, 6,000-char cut, body trimmed in parsing) | `ChatCompletionsModel.complete()` reports `finish_reason`; V1 limits unchanged; per-Work-Type budgets (1,500–3,500 tokens, configurable); cut-off output → one retry → `incomplete` (not approvable) with reason; **Regenerate draft** (max 5) | No truncation in the re-run (article 4,618 chars complete) |
| Wrong-channel planning | Work-Type-specific plan focus; check refuses GitHub Discussion publication in other Work Types' plans; one corrective retry | All five re-run plans in scope |
| Incorrect capability claims | Authoritative release facts from the API override README; checks for "no release/installer" claims, unread-Issue guesses | Partly fixed — automatic checks caught several, **owner review still finds errors** (below) |
| Length limits | Word targets; hard character checks; retry told how much to cut | All within limits (social short 238 / long 727 characters) |
| Incentives / testimonials in improvements | Shared rules + refusal check; latest cumulative metrics only (an interim run said "2 upvotes" by adding two observations — fixed) | Re-run suggestions comply and report 1 upvote correctly |

The first live re-run (Tasks #9–#13) exercised the new checks: four drafts were correctly held as `incomplete` (plans without Verified/Proposed labels, over-length bodies, a stale "no installer" claim). After the instruction fixes, the second re-run (Tasks #14–#18) passed all automatic checks.

## Re-run outputs (verbatim)

### GitHub Discussions — re-verification on a scratch copy of the V2 data (release configuration)

Monitoring of Discussion #13 and improvement suggestions were run for real against GitHub and the AI provider on a copy of the data, so the owner's archived Task #2 was not modified. A fresh plan and draft were generated; nothing was approved or published.

- Monitoring result: `{"comments": 0, "upvotes": 1, "reactions": 0, "locked": false, "closed": false}`
- New draft quality: `{"passed": true, "plan_issues": [], "draft_issues": []}`
- Review: compliant; one stale phrase ("use the Windows installer for internal preview").

<details><summary>Improvement suggestions (verbatim)</summary>

````text
The announcement titled "Announcing GitHub Community Agent v1.0.0-rc1 Windows Pre-release (Unsigned)" was published as a GitHub Discussion in the repository nature-ai-corp/github-community-agent. It introduces a Windows desktop pre-release version (v1.0.0-rc1) of the GitHub Community Agent, an open-source tool under the Apache-2.0 license that provides AI-powered review and summarization of GitHub issues and discussions to assist open-source project maintainers. Key capabilities include generating AI-assisted summaries and draft replies (which remain local and unposted for human review), and producing community activity reports with links to real GitHub data. The announcement clearly states the pre-release and unsigned status of the Windows build.

As of the latest observation (2026-11-11), the announcement has received 1 upvote and no comments or reactions.

Suggestions to improve future announcements:

1. Explicitly invite users to provide feedback and ask questions within the announcement text to encourage comments and discussions (target metric: increase comments from 0 to at least 10 within 2 months).

2. Include clear installation and testing instructions or direct links to relevant documentation for the Windows pre-release to reduce barriers for adoption and testing (target metric: increase number of testers from 0 to at least 5).

3. Add a concise summary of key features and benefits at the beginning of the announcement to facilitate quick understanding by maintainers (target metric: improve reader comprehension and engagement).

4. Provide a direct link to a dedicated feedback discussion or issue tracker to simplify user input collection (target metric: increase feedback volume and quality).

5. Consider aligning announcement timing with relevant community events or forums focused on Windows users and open-source maintainers to enhance visibility among the target audience (target metric: increase engagement beyond current levels).
````

</details>

<details><summary>New GitHub Discussions draft (verbatim)</summary>

````text
TITLE: Announcing GitHub Community Agent v1.0.0-rc1: AI-Assisted Review of GitHub Discussions

We are excited to announce the pre-release of **GitHub Community Agent v1.0.0-rc1**, an independent open-source Windows desktop application designed to help maintainers better understand and respond to their GitHub communities using AI assistance.

**Key Features for GitHub Discussions:**

- **Review Discussions:** Analyze recent GitHub Discussions to identify questions, requests, and unanswered topics. This requires a GitHub token with Discussions read access.
- **Draft Discussion Reply:** Generate AI-powered draft replies for individual Discussions. These drafts remain local and unposted until reviewed by a human maintainer.
- **Read-Only and Human Reviewed:** The agent never posts, comments, or modifies GitHub content automatically. All AI outputs stay within the app for your review and approval.
- **Community Report:** Summarize community activity with links to real GitHub evidence, helping maintainers prioritize follow-up actions.

**About GitHub Community Agent:**

- Built on the Nature AI Worker Core, this product is independent and not affiliated with GitHub, Inc. or Microsoft Corporation.
- It supports Windows 10 or 11 (64-bit) and is currently provided as an unsigned pre-release installer for testing and feedback.
- The v1.0.0-rc1 release includes the Windows setup executable and SHA256 checksums for verification.

**Try it now:**

Download the pre-release and learn more here:  
[GitHub Community Agent v1.0.0-rc1 Release](https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)

**Getting Started:**

- Use a clean Python 3.11–3.13 virtual environment on Windows for local testing.
- The app provides a UI to review Discussions and draft replies without posting.
- See the README and documentation for detailed usage and development notes:  
  https://github.com/nature-ai-corp/github-community-agent#readme

**Note:** This is a pre-release version intended for evaluation and feedback. It is unsigned and not yet an official stable release. Please do not distribute the unsigned installer.

We welcome your feedback and questions here in Discussions to help improve the product for future stable releases.

Thank you for your interest and support!

— The NATURE AI CORP Team

---

References:  
- https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1  
- https://github.com/nature-ai-corp/github-community-agent#readme
````

</details>

### Repository Optimization — Task #14 (NOT VERIFIED)

- Automatic checks: `{"passed": true, "plan_issues": [], "draft_issues": []}`; status `draft`; title 79 / body 4073 characters
- Sources: https://github.com/nature-ai-corp/github-community-agent, https://github.com/nature-ai-corp/github-community-agent#readme, https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1
- Authoritative facts: Published pre-release v1.0.0-rc1 on 2026-11-10 with assets GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe, SHA256SUMS.txt
- Owner-review findings (must be corrected before approval):
  - **Factual error:** states "No contradictions found between README and release data", but the README on `main` says no installer or V1 release has been published while v1.0.0-rc1 is public.
  - Quick Start proposal repeats the stale "do not distribute unsigned installer".
  - Plan labels some proposals (e.g. adding topics) as `Verified`.
  - Useful and well structured otherwise: description, topics, templates are concrete and applicable.

<details><summary>Plan (verbatim)</summary>

````text
Audience:
- Repository maintainers and developers focused on improving the presentation and clarity of their GitHub repositories, specifically those interested in AI tools for GitHub community management. (Verified: https://github.com/nature-ai-corp/github-community-agent#readme)

Value proposition:
- Enhance repository discoverability and clarity by updating the repository description to explicitly mention it is an open-source AI agent for GitHub community management built on Nature AI Worker Core. (Verified: https://github.com/nature-ai-corp/github-community-agent)
- Add relevant topics/tags to the repository to improve searchability and categorization on GitHub, currently none are set. (Verified: https://github.com/nature-ai-corp/github-community-agent)
- Improve the README by emphasizing the current V1 capabilities (review issues, discussions, draft replies, community report) and clearly stating the pre-release status and Windows-only support, including installation instructions and security notes. (Verified: https://github.com/nature-ai-corp/github-community-agent#readme)
- Create or update issue and pull request templates to guide contributors on reporting bugs or suggesting features, given there are 4 open issues and ongoing development. (Verified: https://github.com/nature-ai-corp/github-community-agent)
- Publish a stable official release when ready, as currently only a pre-release (v1.0.0-rc1) Windows unsigned installer is available, to improve user confidence and adoption. (Verified: https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)

Channel approach:
- Optimize the repository metadata (description, topics) and README content to clearly communicate project scope, status, and usage instructions. (Proposed)
- Add or refine contribution templates to streamline community engagement and issue reporting. (Proposed)
- Prepare for a stable release by documenting release notes and signing installers to enhance trustworthiness. (Proposed)

Schedule:
- Immediate update of description and topics within 1 week. (Proposed)
- README improvements and addition of templates within 2 weeks. (Proposed)
- Plan stable release documentation and signing process within 1 month. (Proposed)

Measurable objectives:
- Increased clarity and completeness of repository metadata and README as measured by checklist completion. (Proposed)
- Reduction in ambiguous or incomplete issue reports due to improved templates. (Proposed)
- Preparation of a signed stable release with verified installation instructions documented. (Proposed)
````

</details>

<details><summary>Draft (verbatim)</summary>

````text
TITLE: Improve GitHub Community Agent repo metadata, README, and templates for clarity

**Description**  
Current (verified):  
Open-source AI agent for GitHub community management and product promotion. Built on Nature AI Worker Core.  
Proposed:  
Open-source AI agent for GitHub community management, built on Nature AI Worker Core. Supports Windows desktop with read-only GitHub analysis and draft reply capabilities.  
Why:  
Clarifies current V1 scope (community management only, Windows desktop, read-only) and avoids implying product promotion is included now.

**Topics**  
Current (verified):  
None set.  
Proposed:  
Add topics: `ai-agent`, `community-management`, `github`, `windows`, `open-source`, `nature-ai`, `github-community-agent`  
Why:  
Improves discoverability and categorization on GitHub for users searching AI tools, GitHub community management, and Windows apps.

**Homepage Link**  
Current (verified):  
Empty.  
Proposed:  
Add homepage URL if available, e.g., project documentation or corporate site. If none, omit.  
Why:  
A homepage link helps users find more info beyond GitHub, but only if a relevant site exists.

**README Overview Section**  
Current (verified):  
Detailed explanation of V1 and V2, independence, development status, and disclaimers.  
Proposed:  
Keep existing overview but add a clear, concise summary at top:  
> GitHub Community Agent is an independent, open-source Windows desktop app by NATURE AI CORP that helps maintainers review GitHub community activity with AI. V1 is a pre-release focused on read-only issue and discussion review, draft replies, and community reports. No GitHub write actions or official signed releases yet.  
Why:  
Provides immediate clarity on project purpose, platform, and current status for new visitors.

**README Quick Start / Install**  
Current (verified):  
Instructions for local Windows developer testing with Python virtual environment and unsigned Windows installer preview.  
Proposed:  
Add a distinct "Quick Start" section summarizing:  
- Windows 10/11 x64 required  
- Use Python 3.11–3.13 venv for testing (commands provided)  
- Unsigned Windows installer available as pre-release (link to v1.0.0-rc1)  
- No official signed release yet; do not distribute unsigned installer  
Why:  
Improves user onboarding by highlighting platform and installation options upfront.

**README Status**  
Current (verified):  
States V1 is pre-release with no official signed installer or GitHub write capability; V2 promotion planned but not shipped.  
Proposed:  
Add a "Status" badge or clear note at top:  
> ⚠️ Pre-release (v1.0.0-rc1) Windows-only, unsigned installer. No GitHub write actions. Use for evaluation only.  
Why:  
Sets user expectations immediately about maturity and limitations.

**Release Notes**  
Current (verified):  
One pre-release v1.0.0-rc1 published on 2026-11-10 with unsigned Windows installer and SHA256 sums.  
Proposed:  
Maintain detailed release notes with:  
- Explicit pre-release label  
- Windows requirements  
- Summary of features (five Work Types, read-only, draft replies)  
- Security and signing disclaimers  
- Link to SHA256SUMS.txt  
Why:  
Clear, accurate release notes build trust and inform users about what to expect.

**Issue and Discussion Templates**  
Current (verified):  
No evidence of existing templates.  
Proposed:  
Add issue templates for:  
- Bug report (with fields for environment, steps to reproduce, expected vs actual behavior)  
- Feature request (with description, use case, benefits)  
- Question or discussion starter (guidelines for clear questions)  
Add pull request template encouraging description of changes, testing, and related issues.  
Why:  
Guides contributors to provide useful, structured information, improving maintainers’ ability to triage and respond.

---

No contradictions found between README and release data; README correctly states no official signed release and no GitHub write capability, matching the pre-release unsigned installer published.

These improvements will enhance clarity, usability, and community engagement for the GitHub Community Agent repository.
````

</details>

### Reddit Promotion — Task #15 (NOT VERIFIED)

- Automatic checks: `{"passed": true, "plan_issues": [], "draft_issues": []}`; status `draft`; title 83 / body 2034 characters
- Sources: https://github.com/nature-ai-corp/github-community-agent, https://github.com/nature-ai-corp/github-community-agent#readme, https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1
- Authoritative facts: Published pre-release v1.0.0-rc1 on 2026-11-10 with assets GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe, SHA256SUMS.txt
- Owner-review findings (must be corrected before approval):
  - **Factual error:** "without … requiring cloud-based services" — the app calls the configured cloud AI provider.
  - Compliant otherwise: disclosure in the first sentence, no subreddit named, no vote requests, release link and SHA-256 included.

<details><summary>Plan (verbatim)</summary>

````text
**Audience**  
This post targets GitHub project maintainers and community managers who use Windows 10 or 11 (64-bit) and seek an AI-assisted tool to review and understand their GitHub community activity without automated posting or editing on GitHub. They value independent, open-source software under Apache-2.0 license that supports read-only analysis of issues and discussions. (Verified: https://github.com/nature-ai-corp/github-community-agent, https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)

**Value proposition**  
GitHub Community Agent is an open-source Windows desktop application that helps maintainers analyze GitHub community activity with AI assistance. It supports five work types: reviewing issues, reviewing discussions, drafting replies (held locally without posting), and generating community reports with source links. It is read-only toward GitHub, ensuring no automated changes occur. The current version is a pre-release (v1.0.0-rc1) and unsigned, intended for testing and evaluation. (Verified: https://github.com/nature-ai-corp/github-community-agent, https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)

**Channel approach**  
Craft a single Reddit post that clearly states the product’s independent status, open-source Apache-2.0 license, and current pre-release state. Emphasize its AI-powered read-only community management capabilities for GitHub maintainers on Windows. Include a direct link to the v1.0.0-rc1 pre-release download and SHA256 checksum for transparency. Avoid claims about promotion features, which are planned for a future version. (Proposed)

**Schedule**  
Post once after thoroughly reviewing the subreddit’s rules to ensure project posts are allowed. Schedule the post during peak activity hours for the target audience’s time zone to maximize visibility and engagement quality. Monitor the post for community questions or feedback for a week after posting. (Proposed)

**Measurable objectives**  
Aim for meaningful engagement such as detailed comments or questions about the tool’s capabilities, constructive feedback on the pre-release, and expressions of interest in testing or contributing. Track the number of substantive replies and discussion threads generated by the post as indicators of engagement quality. (Proposed)
````

</details>

<details><summary>Draft (verbatim)</summary>

````text
TITLE: Open-source AI tool for GitHub community review on Windows — pre-release v1.0.0-rc1

I maintain **GitHub Community Agent**, an independent open-source Windows desktop application designed to help GitHub project maintainers and community managers analyze their repository’s community activity using AI assistance. This tool is built on the Nature AI Worker Core and is licensed under Apache-2.0.

The current version, **v1.0.0-rc1**, is a pre-release published on November 10, 2026, and is available as an unsigned Windows installer for 64-bit Windows 10 or 11. It is strictly **read-only** toward GitHub, meaning it does not post, comment, label, or modify anything on GitHub. All AI-generated outputs remain local and require human review before any action.

Key features in this pre-release include five work types:  
- **Review Issues:** Prioritize and summarize recent GitHub issues with direct source links.  
- **Review Discussions:** Analyze recent GitHub discussions (requires a token with read access).  
- **Draft Issue Reply / Draft Discussion Reply:** Generate AI-assisted reply drafts held locally for review; no automatic posting.  
- **Community Report:** Summarize community activity with coverage limits and evidence links.

This tool is intended for maintainers who want AI-powered insights into their GitHub community without risking automated changes or requiring cloud-based services.

You can find the pre-release and its SHA256 checksum here:  
[GitHub Community Agent v1.0.0-rc1 (Windows pre-release, unsigned)](https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)  
SHA256: `018eb04617d3a60314a79d08e0c22cb2cf4d61ee2916383d03cf6708e93db825`

Please note this is an early release for testing and evaluation. Official signed installers and stable releases are pending further security, packaging, and release acceptance steps.

I welcome feedback from maintainers and community managers interested in AI-assisted community management on GitHub, especially regarding usability, feature requests, or integration ideas. Feel free to ask questions or share your thoughts!
````

</details>

### Developer Forums — Task #16 (NOT VERIFIED)

- Automatic checks: `{"passed": true, "plan_issues": [], "draft_issues": []}`; status `draft`; title 89 / body 2847 characters
- Sources: https://github.com/nature-ai-corp/github-community-agent, https://github.com/nature-ai-corp/github-community-agent#readme, https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1
- Authoritative facts: Published pre-release v1.0.0-rc1 on 2026-11-10 with assets GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe, SHA256SUMS.txt
- Owner-review findings (must be corrected before approval):
  - **Factual error:** "No official independent Windows installer or stable release is available yet" contradicts the published installer (passed the automatic check because of the word "stable" — a validator gap).
  - Clear technical structure, disclosure in the first sentence, not written as an answer to another post.

<details><summary>Plan (verbatim)</summary>

````text
**Audience**  
Developers and maintainers active in GitHub community management who participate in developer forums focused on open-source tools for repository maintenance and community engagement. These users are interested in AI-assisted tools that help analyze and summarize GitHub issues and discussions without automated posting. (Verified: https://github.com/nature-ai-corp/github-community-agent)

**Value proposition**  
Announcing the GitHub Community Agent 1.0.0-rc1, a Windows desktop application that provides AI-powered review and summarization of GitHub community activity in a read-only manner. It supports five work types: reviewing issues, reviewing discussions, drafting replies for issues and discussions (held locally for human review), and generating community reports with links to source data. This tool helps maintainers understand and respond to their communities more effectively while ensuring no automated changes are made on GitHub. It is open-source under Apache-2.0 and built on Nature AI Worker Core. (Verified: https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)

**Channel approach**  
Post a single detailed announcement in the project announcements section of a developer forum dedicated to open-source GitHub tools or AI-assisted development utilities. The post will highlight the pre-release status, capabilities, installation notes for Windows users, and the read-only safety model. Include direct links to the GitHub repository and the pre-release assets for users to explore and test. (Proposed)

**Schedule**  
Publish the forum announcement shortly after the pre-release publication date (post-release on or soon after 2026-11-10). Monitor initial engagement for two weeks to gather feedback and answer questions. (Proposed)

**Measurable objectives**  
- Quality engagement measured by the number of substantive questions or comments about usage, installation, or capabilities in the forum thread.  
- Evidence of users downloading the pre-release installer and reporting testing experiences or issues.  
- Feedback that indicates understanding of the tool’s read-only AI-assisted community management focus and its current pre-release status. (Proposed)
````

</details>

<details><summary>Draft (verbatim)</summary>

````text
TITLE: Announcing GitHub Community Agent 1.0.0-rc1: AI-Powered Read-Only GitHub Community Review

I maintain the GitHub Community Agent, an open-source Windows desktop application designed to assist maintainers in managing and understanding their GitHub communities through AI-powered analysis. We have just published the pre-release version 1.0.0-rc1, available here:  
https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1

**What GitHub Community Agent Does**  
This tool provides five distinct read-only Work Types to help you review and summarize community activity without making any automated changes on GitHub:  
- **Review Issues:** Prioritize and summarize recent open issues with direct source links.  
- **Review Discussions:** Analyze recent discussions requiring a GitHub token with read access to Discussions.  
- **Draft Issue Reply / Draft Discussion Reply:** Generate AI-drafted replies held locally for human review; no automatic posting occurs.  
- **Community Report:** Produce summaries of community activity with clear coverage limits and links to evidence.

**Technical Highlights**  
- Built on the Nature AI Worker Core, the agent runs as a standalone Windows application (tested on Windows 11 x64, compatible with Windows 10 x64).  
- It is strictly read-only toward GitHub—no posting, commenting, labeling, or editing is performed by the AI or app.  
- The pre-release includes an unsigned Windows installer executable (`GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe`) and SHA256 checksums for verification.  
- Installation and testing require a clean Python 3.11–3.13 virtual environment if running from source; detailed instructions are in the repository README.  
- The project is licensed under Apache-2.0 and is independent of GitHub, Inc. or Microsoft.

**Current Status and Limitations**  
- This is a pre-release candidate; security, packaging, regression testing, and official signing remain pending.  
- No official independent Windows installer or stable release is available yet.  
- The app does not currently support automated posting or editing on GitHub; all AI outputs require manual human review and action.  
- Product promotion features are planned for a future V2 release and are not included in V1.

**Call for Technical Feedback**  
We invite developers and maintainers active in GitHub community management to explore this pre-release, test its capabilities, and provide feedback on usability, AI output quality, and installation experience. Your insights will help us refine the product toward a stable release.

Repository and source code:  
https://github.com/nature-ai-corp/github-community-agent

Pre-release download and details:  
https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1

Thank you for considering this tool to assist your GitHub community workflows. We look forward to your technical feedback and discussion.
````

</details>

### Technical Articles — Task #17 (NOT VERIFIED)

- Automatic checks: `{"passed": true, "plan_issues": [], "draft_issues": []}`; status `draft`; title 83 / body 4618 characters
- Sources: https://github.com/nature-ai-corp/github-community-agent, https://github.com/nature-ai-corp/github-community-agent#readme, https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1
- Authoritative facts: Published pre-release v1.0.0-rc1 on 2026-11-10 with assets GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe, SHA256SUMS.txt
- Owner-review findings (must be corrected before approval):
  - **Factual error:** lists *Archived Work* among the "five read-only Work Types" (it is a view).
  - Repeats the stale "internal preview and testing only" wording for the published installer.
  - Complete this time (4,618 characters, disclosure first, install steps from the README), no truncation.

<details><summary>Plan (verbatim)</summary>

````text
Audience:  
Technical article readers who are GitHub project maintainers and community managers interested in AI-assisted tools for community management on Windows platforms. These readers seek solutions to analyze and summarize GitHub issues and discussions without automated posting or editing capabilities. (Verified: https://github.com/nature-ai-corp/github-community-agent#readme)

Value proposition:  
The article will present GitHub Community Agent as an independent, open-source Windows desktop application that helps maintainers review and understand community activity on GitHub repositories using AI models. It emphasizes read-only interaction with GitHub, ensuring no automated posting or changes occur without human review. The tool supports five work types: reviewing issues, reviewing discussions, drafting replies (held locally for review), and generating community reports with source links. The article will clarify that product promotion features are planned for a future version and not included in the current release. (Verified: https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1, https://github.com/nature-ai-corp/github-community-agent#readme)

Channel approach:  
Publish a detailed technical article on a reputable developer blog or publication focused on open-source tools and GitHub community management. The article will include installation guidance for the Windows pre-release, usage scenarios for each work type, and security considerations regarding the unsigned pre-release status. It will also reference the Apache-2.0 license and clarify the product’s independence from GitHub and Microsoft. (Proposed)

Schedule:  
Publish the article within two weeks following the November 10, 2026 pre-release publication to leverage initial interest and provide timely information for early adopters testing the Windows pre-release. (Proposed)

Measurable objectives:  
- Achieve high-quality engagement measured by in-depth comments or questions on the article regarding use cases and integration with existing workflows.  
- Track downloads of the pre-release installer linked in the article as an indirect measure of interest and adoption.  
- Monitor feedback quality through follow-up emails or discussion threads linked from the article to assess clarity and usefulness of the content. (Proposed)
````

</details>

<details><summary>Draft (verbatim)</summary>

````text
TITLE: GitHub Community Agent: AI-Powered Read-Only GitHub Community Management on Windows

_Disclosure: I maintain the GitHub Community Agent project._

Managing a GitHub repository’s community can be challenging as issue volumes and discussion threads grow. To help maintainers better understand and prioritize community activity, **GitHub Community Agent** offers an AI-assisted, read-only desktop application for Windows that analyzes GitHub issues and discussions without making any changes on GitHub itself.

## Overview

GitHub Community Agent is an open-source product by NATURE AI CORP, built on the Nature AI Worker Core. It is independent and not affiliated with GitHub, Inc. or Microsoft Corporation. The product uses AI models to assist maintainers in reviewing community activity on public GitHub repositories, focusing on analysis and draft preparation without automated posting or editing.

The current version is a **v1.0.0-rc1 pre-release**, published on November 10, 2026, as an unsigned Windows installer targeting Windows 10 and 11 (64-bit). This release supports five read-only Work Types:

- **Review Issues:** Inspects a bounded page of recent open GitHub issues, prioritizes them, and summarizes key findings with direct source links.
- **Review Discussions:** Analyzes recent GitHub Discussions to identify questions, requests, and unanswered threads. Requires a GitHub token with Discussions read access.
- **Draft Issue Reply / Draft Discussion Reply:** Generates AI-based draft replies for individual issues or discussions. Drafts remain local and unposted, requiring human review.
- **Community Report:** Produces a summary of observed community activity, highlighting needs and suggested follow-up actions, all linked to real GitHub evidence.
- **Archived Work:** Provides a view-only record of previously completed or failed tasks, preserving reports and sources locally.

## Installation and Getting Started

### Windows Pre-release Installer

- Download the unsigned Windows installer executable from the official release page:  
  [GitHub Community Agent v1.0.0-rc1](https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)  
  Assets include `GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe` and `SHA256SUMS.txt`.

- The installer uses Inno Setup 6 and installs under the current user’s program directory, preserving work history and encrypted settings on upgrade or uninstall/reinstall.

- **Important:** This installer is unsigned and intended for internal preview and testing only. It is not a stable or officially approved release.

### Local Development Setup

For developers or testers who prefer running from source:

1. Use a clean Python 3.11–3.13 virtual environment on Windows.
2. Run the following PowerShell commands:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\github-community-agent-home.exe
   ```

This launches the application using the Nature AI Worker v0.1.1 UI baseline with independent configuration and credentials.

## Usage Highlights

- The agent connects to GitHub repositories with read-only permissions.
- It does **not** post, comment, label, close, or edit any GitHub content.
- AI-generated drafts are held locally for human review and manual posting.
- Community reports provide maintainers with actionable summaries and links to source issues or discussions.
- Archived Work allows maintainers to review past AI analyses and reports without restoring them to active workflow.

## Limitations and Current Status

- The current release is a pre-release candidate with ongoing work on security, packaging, regression testing, and release acceptance.
- No official signed Windows installer or stable release is available yet.
- Product promotion features are planned for a future v2 release and are not included in v1.
- The repository currently has open issues, but their details are not specified here.
- The product is licensed under Apache-2.0.

## Additional Resources

- Source code and documentation:  
  https://github.com/nature-ai-corp/github-community-agent

- Release details and downloads:  
  https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1

- Related Nature AI Worker Core repository:  
  https://github.com/nature-ai-corp/nature-ai-worker

---

GitHub Community Agent provides maintainers with AI-powered insights into their GitHub communities while ensuring full manual control over any interactions. Its read-only design and local draft handling make it a secure tool for early adopters interested in AI-assisted community management on Windows.
````

</details>

### Social Media — Task #18 (NOT VERIFIED)

- Automatic checks: `{"passed": true, "plan_issues": [], "draft_issues": []}`; status `draft`; title 63 / body 994 characters
- Sources: https://github.com/nature-ai-corp/github-community-agent, https://github.com/nature-ai-corp/github-community-agent#readme, https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1
- Authoritative facts: Published pre-release v1.0.0-rc1 on 2026-11-10 with assets GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe, SHA256SUMS.txt
- Owner-review findings (must be corrected before approval):
  - Says "five work types" but lists four items (the two Draft Reply types merged).
  - Lengths now within limits; disclosure in both posts; two hashtags; repository link.

<details><summary>Plan (verbatim)</summary>

````text
Audience:  
- GitHub repository maintainers and open-source project managers who use Windows 10 or 11 (64-bit) and want AI-assisted tools to understand and manage their GitHub community activity without automatic posting or editing on GitHub. (Verified: https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)  
- Developers interested in open-source AI tools for community management built on Nature AI Worker Core. (Verified: https://github.com/nature-ai-corp/github-community-agent#readme)  

Value proposition:  
- GitHub Community Agent is a Windows desktop application that helps maintainers review and summarize GitHub community issues and discussions using AI, while keeping all AI outputs local and requiring human review before any action. (Verified: https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)  
- It supports five work types focused on community management: reviewing issues, reviewing discussions, drafting replies (unposted), and generating community reports with links to real GitHub evidence. (Verified: https://github.com/nature-ai-corp/github-community-agent#readme)  
- The product is independent, open-source under Apache-2.0 license, and currently available as a Windows pre-release (unsigned) installer for testing. (Verified: https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1)  

Channel approach:  
- Short post on Twitter or LinkedIn announcing the availability of the v1.0.0-rc1 Windows pre-release, highlighting AI-powered community review features and emphasizing the read-only, human-reviewed workflow. (Proposed)  
- Longer post on a personal or company blog or LinkedIn article detailing the capabilities of GitHub Community Agent v1, its open-source nature, Windows compatibility, and how it helps maintainers understand and manage their GitHub communities without automatic posting. Include links to the GitHub repository and release. (Proposed)  

Schedule:  
- Short post: within one week of the pre-release publication date (around mid-November 2026). (Proposed)  
- Longer post: within two weeks after the short post to provide more detailed information and encourage exploration. (Proposed)  

Measurable objectives:  
- Monitor engagement quality by tracking meaningful comments or direct messages asking about usage, installation, or capabilities. (Proposed)  
- Assess the number of downloads or clones of the pre-release installer linked in the posts as an indirect measure of interest. (Proposed)  
- Evaluate feedback received through GitHub Discussions or direct contact for insights on user experience and potential improvements. (Proposed)
````

</details>

<details><summary>Draft (verbatim)</summary>

````text
TITLE: GitHub Community Agent v1.0.0-rc1 Windows Pre-release Available

SHORT POST:  
I maintain GitHub Community Agent, an open-source AI tool for reviewing GitHub community activity on Windows. Try the v1.0.0-rc1 pre-release: https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1 #OpenSource #AI

LONG POST:  
I maintain GitHub Community Agent, an independent open-source Windows desktop app that helps maintainers review GitHub community issues and discussions using AI. The v1.0.0-rc1 pre-release supports five work types: reviewing issues, reviewing discussions, drafting unposted replies, and generating community reports with links to real GitHub evidence. It is read-only toward GitHub, requiring human review before any action. This unsigned Windows installer is available for testing on Windows 10 or 11 (64-bit). The project is built on Nature AI Worker Core and licensed under Apache-2.0. Explore the repository and download the pre-release here: https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1
````

</details>

## Remaining limitations

- Automatic checks cannot guarantee factual accuracy; owner review of the exact text remains mandatory and still finds errors in four of the five drafts.
- The research step reads the README from the default branch (`main`), which is still outdated.
- No engagement tracking for manually published content.

## Release recommendation

**Do not release V2 yet.** A V2 release may include only GitHub Discussions (VERIFIED) and V1. Before any release: merge the README correction to `main`, bump the version, rebuild and re-verify the packaged release configuration and installer, and regenerate the third-party license package. The other five Work Types stay excluded until each passes its own real-world acceptance with owner approval.
