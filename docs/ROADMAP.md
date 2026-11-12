# GitHub Community Agent roadmap

GitHub Community Agent is an **independently distributed** product in the NATURE AI Worker family. It may reuse a versioned, explicitly scoped Nature AI Worker Core, but must not share application data, credentials, mutable source checkouts, packaging or release identity with Nature AI Worker.

## V1 — Community management

Complete and verify four existing partially implemented workflows:
1. **Review Issues** — inspect and summarize issues, classify findings, link evidence.
2. **Review Discussions** — inspect discussions, questions and unanswered threads.
3. **Draft Replies** — generate contextual replies; supported publication requires explicit review/approval.
4. **Community Report** — produce evidence-backed reports and actionable follow-up.

V1 priority is integration, isolation, reliable behavior, independent install and real GitHub end-to-end testing — not rewriting the existing capabilities.

## V2 — Repository-based promotion (one Promotion Agent, platform Work Types)

There is **one** Promotion Agent and **one** Promotion Workflow. There are no
separate self-promotion and product-promotion modes. The only configuration is:
1. the target GitHub repository (default `nature-ai-corp/github-community-agent`;
   any other authorized product repository, such as
   `nature-ai-corp/nature-ai-worker`, can be selected);
2. the GitHub token the user authorized for that repository.

Every repository uses the same Work Center, engine, research, planning, content
generation, approval and publishing controls, monitoring, improvement, security
and audit behavior. The workflow is: research → plan → draft → review and
approve the exact text → publish (permission re-checked) → monitor → improve.

Release rule: no real-world verification, no released Work Type. The release
configuration offers only **GitHub Discussions** (verified with Discussion #13)
and **Repository Optimization** (verified with Task #20 and the merged README PR #15)
and **Bluesky** (verified with Task #22: an Agent-published post read back from the public index)
and **DEV Community** (verified with Task #23: an Agent-published article, private draft checked first,
read back from the public API).
Reddit Promotion and Developer Forums
exist as development code on the same engine and are excluded
from release builds until each passes real-world acceptance
([release gate](testing/V2_PROMOTION_RELEASE_GATE.md)).

The selected repository is the promotion base, **not** permission to post
elsewhere. V2 publishes only an approved GitHub Discussion in that repository
itself. Design and security details: [V2_PROMOTION.md](V2_PROMOTION.md).
V1 (released `v1.0.0-rc1`) is unchanged.
