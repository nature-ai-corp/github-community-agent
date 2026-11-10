# Real Review Discussions verification — Windows-first

This PR adds a **read-only, model-assisted Review Discussions** workflow to the
independent GitHub Community Agent. It reads public GitHub Discussions through
the official GitHub GraphQL API, then uses the operator-selected AI model to
summarize **actual Discussion detail and comments**. Model output is never posted.

## Offline Windows tests (no token, no API fees)

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git fetch origin
git switch feature/v1-review-discussions-ai
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
git status
```

## Live acceptance prerequisites

- An explicitly authorized **public** repository with Discussions enabled.
- A narrowly scoped GitHub token authorized to **read Discussions** in the
  selected repository. The GitHub GraphQL reader rejects broad classic scopes;
  a compatible fine-grained token is preferred. Do not paste the token in chat,
  an issue, screenshots or command-line arguments. An existing `GITHUB_TOKEN`
  is deliberately **not** inherited.
- OpenAI API key for `gpt-4.1-mini` (user has already verified this provider).
- One real execution reads a single Discussion list plus up to five Discussion
  detail+comment records, and makes one billable OpenAI API request.

Supply the **two dedicated variables locally in the same PowerShell process**:

```powershell
$readSecure = Read-Host "GitHub Discussions READ token" -AsSecureString
$readPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($readSecure)
try { $env:GITHUB_COMMUNITY_AGENT_READ_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($readPtr) }
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($readPtr)
    Remove-Variable readSecure, readPtr -ErrorAction SilentlyContinue
}

$modelSecure = Read-Host "OpenAI API Key" -AsSecureString
$modelPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($modelSecure)
try { $env:GITHUB_COMMUNITY_AGENT_MODEL_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($modelPtr) }
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($modelPtr)
    Remove-Variable modelSecure, modelPtr -ErrorAction SilentlyContinue
}

try {
    .\.venv\Scripts\github-community-agent-analyze.exe `
      --repo nature-ai-corp/nature-ai-worker `
      --workflow review_discussions `
      --provider openai `
      --model gpt-4.1-mini
}
finally {
    Remove-Item Env:\GITHUB_COMMUNITY_AGENT_READ_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:\GITHUB_COMMUNITY_AGENT_MODEL_API_KEY -ErrorAction SilentlyContinue
}
```

## Required REAL evidence

- Actual Discussion IDs, categories, source URLs and body/comment details
  match the public GitHub Discussions.
- Source token never appears in the AI prompt/output. Review uses the repository
  and permission explicitly chosen by the operator.
- Output: `read_only: true`, `posted: false`,
  `requires_human_review: true`, `discussions_analyzed <= 5`;
  page counts refer to **records**, not GitHub pagination page totals.
- Check analysis against real Discussion content, not simply plausible prose.
  If there are no public Discussions, accept factual empty coverage but **do not**
  claim nonempty Discussion analysis has passed.
- No GitHub write/approval path in this PR. This developer CLI verification
  is not the final independent installed Windows GUI end-to-end test.

A scoped token may lack GraphQL Discussions access even if it is valid for
REST Issues; treat that as a permission/setup failure, not a model success.
