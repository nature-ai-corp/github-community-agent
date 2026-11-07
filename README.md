# GitHub Community Agent

**An independent open-source GitHub community-management product, built on shared Nature AI Worker Core capabilities.**

GitHub Community Agent helps project maintainers understand and respond to their communities. Product promotion is planned for V2; it is **not** part of V1.

> **Development status:** Independent repository initialized. Existing community tooling and starter workflows are being inventoried for migration. No independently installable V1 release is published yet.

## V1 — Community Management

- **Review Issues:** inspect open GitHub issues, identify priorities and summarize findings.
- **Review Discussions:** understand questions, requests, and unanswered discussions.
- **Draft Replies:** prepare evidence-based replies; posting supported comments requires precise approval.
- **Community Report:** summarize community needs and suggested follow-up, with links to real GitHub evidence.

We will reuse and finish the relevant work already prototyped in Nature AI Worker. This is an **independent product**, not an optional AI Worker module.

## V2 — Promotion

A single promotion mechanism uses a GitHub repository as its product information base:
- **Self-Promotion:** this product's official repository is selected automatically.
- **Product Promotion:** the user selects a GitHub repository for their product.

Planning, writing, approval, publication (where authorized), monitoring and improvement share the same engine. There are no V2 shipping claims in the V1 scope.

## Project boundaries

This project must have its **own** installation, UI/product identity, configuration, data, GitHub credentials, test suite, CI, versioning and releases. Shared Worker Core functionality must be explicitly versioned and dependency-audited. Enterprise Platform Server and S–C client code are outside scope. Existing Nature AI Worker source remains untouched while migration is verified.

## Development

- [V1/V2 roadmap](docs/ROADMAP.md)
- [Migration sources, boundaries and acceptance criteria](docs/MIGRATION_PLAN.md)
- [Nature AI Worker source repository](https://github.com/nature-ai-corp/nature-ai-worker)

Maintained by **NATURE AI CORP**. Open-source distribution is planned; license and third-party notices will be finalized alongside the reviewed source migration.
