# AI Issues review and Community Report — real acceptance

This development increment adds `github-community-agent-analyze` to the independent
GitHub Community Agent. It uses the existing operator-chosen OpenAI-compatible model
adapter and reads real GitHub public Issues. It does not post comments, execute
model suggestions, persist credentials or change Nature AI Worker.

## What is actually analyzed

- One live GitHub API issue LIST page, up to ten reference entries.
- **Up to five individual issue DETAIL requests**, because GitHub issue-list API
  does not supply full body text. Only these five detailed Issues are sent to AI
  for classification or synthesis. The source URLs and the actual numbers are
  retained for human verification. Reports describe this bounded sample only.
- Community Report optionally includes a recent Discussions listing **only when**
  the user provides a separate narrowly scoped read-only GitHub token. Otherwise
  `incomplete: true` and `discussions_checked: false` must be reported.
- GitHub issue bodies and discussions are untrusted. AI output is a proposed
  analysis, not verified product truth.

## Offline Windows regression (mocked; no API charge)

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git fetch origin
git switch feature/v1-ai-reviews-report
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
git status
```

## Optional REAL verification with OpenAI

Supply the key **locally**, never in chat, code, arguments or public logs.
Use the same dedicated `GITHUB_COMMUNITY_AGENT_MODEL_API_KEY` process environment
variable from the previously successful PR #6 live Draft Replies test.
One CLI execution reads the public issue list and at most five issue details,
then makes one billable OpenAI model API request.

```powershell
try {
    .\.venv\Scripts\github-community-agent-analyze.exe `
      --repo nature-ai-corp/nature-ai-worker `
      --workflow review_issues `
      --provider openai `
      --model gpt-4.1-mini
}
finally {
    Remove-Item Env:\GITHUB_COMMUNITY_AGENT_MODEL_API_KEY -ErrorAction SilentlyContinue
}
```

Re-enter the secret securely before this command, as the previous test cleaned up
the key afterward. The command returns JSON containing the exact read-only
evidence references, AI analysis, sample size, and `posted: false`.

Community Report also supports `--workflow community_report`, but will
explicitly say Discussions were not checked without the dedicated
`GITHUB_COMMUNITY_AGENT_READ_TOKEN` environment variable. **Do not** use a
broad classic GitHub token or send a token into ChatGPT.

## Acceptance gates
1. Windows package import and tests pass on the current branch head.
2. Real public repo list + up to five issue detail reads demonstrated.
3. Real OpenAI response has specific, grounded issue numbers and source links;
   classifications are checked against the actual issues, with uncertainty noted.
4. No GitHub writes, no secret output, no private repo access.
5. No unearned full historical-coverage claim; partial report clearly labeled.
6. Final independent Windows UI and application-generated end-to-end evidence
   remain necessary before V1 release, beyond this CLI-level acceptance.
