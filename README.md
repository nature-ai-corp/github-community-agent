# GitHub Community Agent

**An independent open-source GitHub community-management product, built on shared Nature AI Worker Core capabilities.**

GitHub Community Agent helps project maintainers understand and respond to their communities. Product promotion is planned for V2; it is **not** part of V1.

> **Development status:** V1 has real Windows application execution evidence for all five read-only Work Types. Security, packaging, regression and release acceptance remain pending. **No official independent Windows installer or V1 release has been published.**

## V1 — Community Management

- **Review Issues:** inspect open GitHub issues, identify priorities and summarize findings.
- **Review Discussions:** understand questions, requests, and unanswered discussions.
- **Draft Issue Reply / Draft Discussion Reply:** prepare unposted, source-grounded AI drafts and route them through local human review. **Mark reviewed never posts to GitHub. V1 has no GitHub writing capability.**
- **Community Report:** summarize community needs and suggested follow-up, with links to real GitHub evidence.

The app uses the general UI baseline of Nature AI Worker v0.1.1, with independent GC Agent functions, configuration, database, credentials and release process. It does not modify or ship the original Worker application.

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

## Local Windows developer testing (not an official installer)

Use a clean Python 3.11–3.13 virtual environment on Windows. This is source
testing only and must not be represented as a signed Windows application:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\github-community-agent-home.exe
```

## Windows independent installer — internal preview only

This repository now contains **source-only build recipes** for a separate
per-user GC Agent EXE and an unsigned Inno Setup 6 installer. The build output
has **not yet been verified on the target Windows machine** and is **not**
an official downloadable release. See
[Windows Installer Acceptance](docs/WINDOWS_INSTALLER_ACCEPTANCE.md).

To build locally after Windows tests pass, install optional build tools with
`.\\.venv\\Scripts\\python.exe -m pip install -e ".[dev,build]"`, run
`scripts/windows-build-exe.ps1`, then with independently installed Inno
Setup 6 run `scripts/windows-build-installer.ps1`. The installer has its
own AppId and installs under the current user's program directory. Upgrade
and uninstall must preserve `%LOCALAPPDATA%\\GitHubCommunityAgent`
Work history and DPAPI-encrypted settings. **Do not distribute this unsigned
developer installer**.

A Windows isolated wheel-build/resource preflight is provided at
`scripts/windows-v1-preflight.ps1`. It is **not** an installer or code-signing
step. See [V1 Windows acceptance](docs/V1_WINDOWS_ACCEPTANCE_2026-11-08.md)
for verified functional evidence and remaining release gates.

Work Center provides **Archived Work**, a view-only record of previously
completed or failed tasks, with retained reports, sources, and limited local
Activity History. Archived records cannot be restored from the UI.

Maintained by **NATURE AI CORP**. Apache-2.0 source and attribution are retained
as listed in LICENSE and NOTICE. Official independent Windows distribution,
versioning and signing are pending acceptance.
