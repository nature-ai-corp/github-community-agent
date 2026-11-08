# Unified Work Center — New Task with ONE classification route

This independent GitHub Community Agent preview shares the **home navigation
concept** with Nature AI Worker without depending on that product's backend,
installation, credentials or data. Product-specific Task definitions live in
`work_center.DEFINITIONS`, not in the shared Work Center UI.

## Work Type OR Domain — not two required choices

In **New Task**, choose **one entry route**:
- **Work Type**: Community Management or Product Promotion.
- **Domain**: Issues, Discussions, Community Reports, Self-Promotion,
  Product Promotion, Other Repository Promotion.

Then select the concrete Task definition returned by that route. The same
Task, e.g. Review Issues, can be discovered through either route; only one
route is active and validated when creating the Task. The Task record retains
the product-defined classification metadata for **My Work** filtering. Other
products may supply entirely different classification names and schemes.

**V1 enabled:** Review Issues, Review Discussions, Draft Issue Reply, Draft
Discussion Reply, Community Report. Uses the *real* existing GitHub read
adapters and model provider, with `posted:false`.

**V2 planned only:** Promote GitHub Community Agent, Promote Nature AI Worker,
Promote Other Repository. These choices are visible but disabled. No V2
analysis/publishing runtime has been implemented or simulated.

## Windows developer preview

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git fetch origin
git switch feature/unified-task-home
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\github-community-agent-home.exe
```

A local address such as `http://127.0.0.1:<random-port>/` opens in the
default browser. The server binds **only** to 127.0.0.1 and uses a fresh port
and session nonce each startup. Keep the PowerShell process running while
using the UI; Ctrl+C exits.

### Actual application E2E walkthrough

1. Open **Settings**: repository `nature-ai-corp/nature-ai-worker`,
   OpenAI / `gpt-4.1-mini`, enter model API key, and optional GitHub
   Discussions READ token. These keys are input fields for the local session,
   not persisted to the database. Avoid sharing keys in screenshots.
2. Open **New Task**, select **Work Type → Community Management → Review
   Issues**. Click **Create & Run Task**. The real GitHub Issues + OpenAI
   call runs and creates a uniquely numbered Work entry. Read its analysis
   and sources in **My Work**.
3. Switch to **Domain → Discussions → Review Discussions**. This resolves a
   product-defined Task through a different entry route, using real GraphQL
   and OpenAI. Verify actual public Discussion #32 and correct coverage.
4. Try **Domain → Issues → Draft Issue Reply**, enter #33. Work becomes
   **Needs My Attention**; reviewing the draft in Work Detail can mark it
   reviewed and Finished, **without publishing or authorizing publication**.
5. Verify **Work In Progress**, **Needs My Attention**, **Finished Work**.
   Try My Work classifications (Work Type and Domain filters).
6. Close/restart the app and confirm Work history remains via local SQLite
   journal. Settings secrets must be entered again; none are saved.
7. Choose **Work Type → Product Promotion** or **Domain → Self-Promotion**.
   V2 choices must be visible and **disabled**; no mock execution or
   misleading “Finished” status for an unimplemented workflow.

### Security and honest limits

- The browser UI communicates with one localhost-bound Python server.
  POST operations require both current app session nonce and exact Origin.
  Host is verified for all requests. Results are produced by the existing
  real model/GitHub adapters, never by UI mock content.
- The Work database lives at `%LOCALAPPDATA%\GitHubCommunityAgent\work.sqlite3`
  on native Windows. It contains Task IDs, classifications via definition
  IDs, status, public GitHub results and AI text. **No configured API keys,
  GitHub tokens or provider credentials** should be written to this journal.
  Database files are local private working data, **not encrypted**.
- This is a **Windows app browser-based preview**, not a signed standalone
  installer, secure vault or production-grade hardened native window. The
  older Tk preview remains available under its separate launcher.
- There is no GitHub writing/outbox, no V2 Promotion execution and no
  enterprise-grade task engine. Restarting while a job runs can leave an
  unfinished `running` record; crash recovery is a later gate.
- `My Work` filters read product classification definitions; they do not
  establish fixed domain fields for the wider product family.
- App-generated JSON and real source checking are required for final
  end-to-end acceptance; offline pytest green alone does not prove it.
