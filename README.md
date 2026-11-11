# GitHub Community Agent

**An independent open-source GitHub community-management product, built on shared Nature AI Worker Core capabilities.**

GitHub Community Agent is a Windows desktop application that helps project maintainers understand and respond to their communities, using an AI model of their choice. It is **read-only toward GitHub**: V1 never posts, comments, labels, closes or edits anything.

> **Independence:** GitHub Community Agent is an independent product of NATURE AI CORP. It is not affiliated with, sponsored by, or endorsed by GitHub, Inc. or Microsoft Corporation. "GitHub" is a trademark of GitHub, Inc., used only to identify the service this software works with.

> **Release status:** **V1.0.0-rc1 has been publicly released** as a Windows pre-release:
> [v1.0.0-rc1](https://github.com/nature-ai-corp/github-community-agent/releases/tag/v1.0.0-rc1).
> It includes an **unsigned** Windows installer, `GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe`
> (SHA-256 `018eb04617d3a60314a79d08e0c22cb2cf4d61ee2916383d03cf6708e93db825`, also in `SHA256SUMS.txt`),
> for Windows 10 or 11, 64-bit. Because it is not code-signed, Windows SmartScreen may warn before it runs;
> verify the checksum first. **V2 Promotion is still under development** and is not part of this release.

## V1 — Community Management (released in v1.0.0-rc1)

V1 has exactly five Work Types, all read-only toward GitHub:

- **Review Issues:** prioritized findings from a bounded page of recent open Issues, with source links.
- **Review Discussions:** follow-up candidates from recent Discussions (needs a GitHub token with Discussions **read** access).
- **Draft Issue Reply:** an unposted AI reply draft for one Issue, held for your review.
- **Draft Discussion Reply:** an unposted AI reply draft for one Discussion, held for your review.
- **Community Report:** a summary of observed Issue and Discussion activity, with stated coverage limits and links to real GitHub evidence.

**Mark reviewed never posts to GitHub. V1 has no GitHub writing capability.** The Work Center also has
**My Work**, **Needs My Attention** and **Archived Work** views of your Tasks; these are views, not Work Types.

The app uses the general UI baseline of Nature AI Worker v0.1.1, with independent GC Agent functions, configuration, database, credentials and release process. It does not modify or ship the original Worker application.

## V2 — Promotion (under development, not released)

One Promotion Agent researches a product repository you are authorized to
promote, plans, drafts, and waits for you to approve the exact text. The only
settings are the target repository (default
`nature-ai-corp/github-community-agent`) and the GitHub token for that
repository. Nothing is published without your explicit approval.

**Release rule: no real-world verification, no released Work Type.** The only
Promotion Work Type that has passed real-world acceptance, and the only one a
V2 build will offer, is **GitHub Discussions**: an announcement Discussion in
that repository, published after your approval and a fresh permission check,
then monitored. Repository Optimization, Reddit Promotion, Developer Forums,
Technical Articles and Social Media are **development work, not released
capabilities**: they are not offered in the release configuration until each
passes its own real-world acceptance. See
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

## Windows installer

The public **v1.0.0-rc1** pre-release ships a per-user, **unsigned** Inno Setup
installer (see *Release status* above). Windows testing verified first
installation, upgrade, uninstall and reinstall while retaining work history
and encrypted settings. It is a release candidate, not a stable or signed
release. See [Windows Installer Acceptance](docs/WINDOWS_INSTALLER_ACCEPTANCE.md).

To build locally after Windows tests pass, install optional build tools with
`.\\.venv\\Scripts\\python.exe -m pip install -e ".[dev,build]"`, run
`scripts/windows-build-exe.ps1`, then with independently installed Inno
Setup 6 run `scripts/windows-build-installer.ps1`. The installer has its
own AppId and installs under the current user's program directory. Upgrade
and uninstall must preserve `%LOCALAPPDATA%\\GitHubCommunityAgent`
Work history and DPAPI-encrypted settings. Locally built installers are for
testing only; distribute only the published release asset. See
[V1 Security and License Gate](docs/V1_RELEASE_SECURITY_LICENSE_GATE.md)
for open release blockers and an offline dependency metadata audit.

A Windows isolated wheel-build/resource preflight is provided at
`scripts/windows-v1-preflight.ps1`. It is **not** an installer or code-signing
step. See [V1 Windows acceptance](docs/V1_WINDOWS_ACCEPTANCE_2026-11-08.md)
for verified functional evidence and remaining release gates.

Maintained by **NATURE AI CORP**. Apache-2.0 source and attribution are retained
as listed in LICENSE and NOTICE. Code signing and a stable (non-pre-release)
version are still pending.
