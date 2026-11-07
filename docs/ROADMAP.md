# GitHub Community Agent roadmap

GitHub Community Agent is an **independently distributed** product in the NATURE AI Worker family. It may reuse a versioned, explicitly scoped Nature AI Worker Core, but must not share application data, credentials, mutable source checkouts, packaging or release identity with Nature AI Worker.

## V1 — Community management

Complete and verify four existing partially implemented workflows:
1. **Review Issues** — inspect and summarize issues, classify findings, link evidence.
2. **Review Discussions** — inspect discussions, questions and unanswered threads.
3. **Draft Replies** — generate contextual replies; supported publication requires explicit review/approval.
4. **Community Report** — produce evidence-backed reports and actionable follow-up.

V1 priority is integration, isolation, reliable behavior, independent install and real GitHub end-to-end testing — not rewriting the existing capabilities.

## V2 — Repository-based promotion

Add one reusable promotion workflow with two simple entry points:
- **Self-Promotion** — automatically use this product's official repository.
- **Product Promotion** — use a user-selected, authorized GitHub product repository.

Both follow the same workflow: research → plan → prepare → review → publish (where authorized) → measure → improve. The selected repository defines the promotion base, **not** GitHub write permissions. External posting must respect each community's rules.

V2 must not block V1 release. Promotion is a planned capability, not a V1 shipping claim.
