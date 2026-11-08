# V1 AI provider adapter — controlled Draft Replies acceptance

This development increment integrates a real **OpenAI-compatible chat-completions API** into the existing independent `CommunityRuntime` Draft Replies path. Explicitly supported provider choices:

- `openai` uses the fixed official endpoint `https://api.openai.com/v1`.
- `deepseek` uses the fixed official endpoint `https://api.deepseek.com`.
- `compatible` requires an explicitly supplied **HTTPS public hostname** endpoint ending in `/v1` (or a root path); the endpoint is supplied by the operator, never by a GitHub issue or AI output.

This is **not** a full model provider/settings UI. Local Ollama and native Anthropic/Gemini interfaces are not in this increment.

## Offline Windows verification (no API charges)

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git fetch origin
git switch feature/v1-ai-provider-adapter
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

The tests mock GitHub/model requests, use fake keys, and **do not spend real model API tokens**.

## Optional one-shot live acceptance (requires explicit operator consent)

You can later choose to run a real, billable model request; **do not share the API Key in chat, GitHub Issues, screenshots, recorded logs, or command-line arguments**. Use a locally managed secret. The development CLI only reads the dedicated environment variable `GITHUB_COMMUNITY_AGENT_MODEL_API_KEY`; it never reads `OPENAI_API_KEY`, `GITHUB_TOKEN`, or `GH_TOKEN` automatically.

When that dedicated environment variable has been securely provided in the current process environment:

```powershell
.\.venv\Scripts\github-community-agent-draft.exe --repo nature-ai-corp/nature-ai-worker --target issue --number 33 --provider deepseek --model deepseek-chat
```

This example makes one read-only GitHub REST request and one external AI provider request. **Public issue details are transmitted to the selected AI provider**, so only use an approved public repository. The model's result is presented as a **draft for human review**; the program has no GitHub posting method.

To connect an OpenAI API model, substitute `--provider openai --model gpt-4.1-mini`; for a user-chosen compatible API use `--provider compatible --model MODEL --endpoint https://YOUR_APPROVED_HOST/v1`.

## Limitations / next steps

- No key persistence/encrypted credential UI yet: use securely injected process environment only for developer acceptance.
- No real provider call has been verified until a developer explicitly runs the optional live command.
- No AI classification/review or Community Report synthesis is wired up by this PR.
- No automatic retries, streaming/chat history, pricing estimation or unattended actions.
- Model output is untrusted, potentially inaccurate and always requires human review.
- No GitHub posting, label mutation, approval or durable write outbox.

## Endpoint security review note (PR #6)

Production requests now perform a best-effort public-IP DNS check before obtaining
the API key. Endpoints resolving to localhost, RFC1918, link-local, loopback,
non-global IPv6 or mixed public/private addresses are rejected. The mocked
transport in tests bypasses live DNS; the dedicated DNS tests mock the resolver.

**Limitation:** this is *not* complete protection against DNS rebinding / DNS
time-of-check-to-time-of-use changes, because the HTTPS client resolves again
when connecting. Therefore only configure **trusted, operator-approved public
model-service domains**. Do not configure untrusted compatible endpoints or
expose this capability to GitHub issue authors. A future hardened deployment
can pin validated destination IPs while retaining hostname-based TLS SNI and
certificate verification, and/or restrict outbound traffic at a network layer.
