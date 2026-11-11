# GitHub Community Agent

**An independent open-source GitHub community-management product, built on shared Nature AI Worker Core capabilities.**

GitHub Community Agent helps project maintainers understand and respond to their communities. Product promotion is planned for V2; it is **not** part of V1.

> **Independence:** GitHub Community Agent is an independent product of NATURE AI CORP. It is not affiliated with, sponsored by, or endorsed by GitHub, Inc. or Microsoft Corporation. "GitHub" is a trademark of GitHub, Inc., used only to identify the service this software works with.

> **Development status:** V1 has real Windows application execution evidence for all five read-only Work Types. Security, packaging, regression and release acceptance remain pending. **No official independent Windows installer or V1 release has been published.**

## V1 — Community Management

- **Review Issues:** inspect open GitHub issues, identify priorities and summarize findings.
- **Review Discussions:** understand questions, requests, and unanswered discussions.
- **Draft Issue Reply / Draft Discussion Reply:** prepare unposted, source-grounded AI drafts and route them through local human review. **Mark reviewed never posts to GitHub. V1 has no GitHub writing capability.**
- **Community Report:** summarize community needs and suggested follow-up, with links to real GitHub evidence.

The app uses the general UI baseline of Nature AI Worker v0.1.1, with independent GC Agent functions, configuration, database, credentials and release process. It does not modify or ship the original Worker application.

## V2 — Promotion (in development, not released)

**One** Promotion Agent with one shared engine serves any product repository
you are authorized to promote, through six independently selectable Work
Types: **GitHub Discussions**, **Repository Optimization**, **Reddit
Promotion**, **Developer Forums**, **Technical Articles** and **Social
Media**. The only settings are the target repository (default
`nature-ai-corp/github-community-agent`) and the GitHub token for that
repository. Each Work Type researches the repository's real README and
releases, plans, drafts, and waits for you to approve the exact text. Only
GitHub Discussions publishes automatically (in that repository, after a fresh
permission check); the other five are drafts you publish or apply yourself.
Nothing is published without your explicit approval. See
[V2 Promotion design](docs/V2_PROMOTION.md). The released V1 (`v1.0.0-rc1`)
does not include V2.

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

This repository contains a separate per-user GC Agent EXE and unsigned
Inno Setup 6 developer installer. Actual Windows testing has verified
first installation, installer-version replacement, uninstall and reinstall
while retaining work history and encrypted settings. This **does not**
constitute a stable, signed or publicly approved release. See
[Windows Installer Acceptance](docs/WINDOWS_INSTALLER_ACCEPTANCE.md).

To build locally after Windows tests pass, install optional build tools with
`.\\.venv\\Scripts\\python.exe -m pip install -e ".[dev,build]"`, run
`scripts/windows-build-exe.ps1`, then with independently installed Inno
Setup 6 run `scripts/windows-build-installer.ps1`. The installer has its
own AppId and installs under the current user's program directory. Upgrade
and uninstall must preserve `%LOCALAPPDATA%\\GitHubCommunityAgent`
Work history and DPAPI-encrypted settings. **Do not distribute this unsigned
developer installer**. See
[V1 Security and License Gate](docs/V1_RELEASE_SECURITY_LICENSE_GATE.md)
for open release blockers and an offline dependency metadata audit.

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
