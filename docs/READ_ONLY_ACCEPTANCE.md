# Read-only acceptance CLI (development only)

This command is a temporary **independent code-verification entry point**, not the finished GitHub Community Agent product UI or Agent runtime. It performs no GitHub mutations. It reads only one explicitly selected **public** repository.

After installing from this repository with `python -m pip install -e ".[dev]"`:

```powershell
# Example: read publicly available Issues without a GitHub token
github-community-agent-read --repo nature-ai-corp/nature-ai-worker --resource issues --mode list

# Read a particular public Issue
github-community-agent-read --repo nature-ai-corp/nature-ai-worker --resource issues --mode issue --number 33
```

Discussions require a **separate read-only** GitHub credential, supplied as `GITHUB_COMMUNITY_AGENT_READ_TOKEN` in the process environment. The command never accepts a token in arguments, never reads generic `GITHUB_TOKEN` or `GH_TOKEN`, and never stores the token. Do not put a token in a GitHub Issue, PR, chat, command line, or log. Prefer an interactive, local secret entry mechanism when one is available; a future end-user app will need a scoped encrypted credential store. Do not use an elevated token.

```powershell
# Only after setting the dedicated environment variable securely in your local session:
github-community-agent-read --repo owner/public-project --resource discussions --mode list
```

The tool permits only fixed GitHub API hosts, rejects redirects and oversized responses, and uses fixed read-only GraphQL documents. The model must not be allowed to override the repository configuration.

## Evidence policy

- `pytest` uses fake GitHub responses (offline unit/security checks).
- Executing the CLI against a public GitHub Issue is a **real network acceptance test** for its scoped read-only code path.
- This CLI does **not** prove that the four V1 AI workflows, a user UI, authorization and approval-bound posting are functional.
- Results should record source commit, exact commands, success/failure and whether a real GitHub endpoint was used.
