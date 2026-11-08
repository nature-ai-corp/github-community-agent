# Unified Work Center — New Task with ONE classification route

This independent GitHub Community Agent preview uses the **actual v0.1.1 base stylesheet and adapted home / Settings markup** from Nature AI Worker without depending on that product's backend,
installation, credentials or data. Product-specific Task definitions live in
`work_center.DEFINITIONS`, not in the shared Work Center UI.

## Work Type OR Domain — not two required choices

In **New Task**, choose **one entry route**:
- **Work Type**: Community Management or Product Promotion.
- **Domain**: Self-Promotion or Product Promotion. Domain represents
  promotion targets, not the V1 Issue/Discussion operation name.

Then select the concrete Task definition returned by that route. Each Task is shown through the route defined for it: V1 Community Management
through Work Type; V2 promotion choices through Work Type or Domain. Only one
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

1. Open **Settings**: a centered modal like the AI Worker Settings dialog
   appears (Provider, Model, API key, Advanced, Test connection, Cancel, Save).
   Enter OpenAI / `gpt-4.1-mini` and the API key. Expand **Advanced** to set
   repository `nature-ai-corp/nature-ai-worker` and optional GitHub Discussions
   READ token. Click **Test connection** to make a **real, billable model API
   request**; it does not post to GitHub. Click **Save** to retain settings in
   browser memory for this session. **Cancel** discards edits. Reopening Settings
   leaves the existing key in memory if the password field is left empty.
   This preview does **not** implement the AI Worker's encrypted persistent
   credential vault; do not infer persistence or security equivalence. Avoid
   sharing keys in screenshots.
2. Open **New Task**, select **Work Type → Community Management → Review
   Issues**. Click **Create & Run Task**. The real GitHub Issues + OpenAI
   call runs and creates a uniquely numbered Work entry. Read its analysis
   and sources in **My Work**.
3. Use **Work Type → Community Management → Review Discussions**. This runs
   the real GraphQL/OpenAI workflow. Verify actual public Discussion #32 and
   correct coverage.
4. Try **Work Type → Community Management → Draft Issue Reply**, enter #33. Work becomes
   **Needs My Attention**; reviewing the draft in Work Detail can mark it
   reviewed and Finished, **without publishing or authorizing publication**.
5. Verify **Work In Progress**, **Needs My Attention**, **Finished Work**.
   Try My Work classifications (Work Type and Domain filters).
6. Close/restart the app and confirm Work history remains via local SQLite
   journal. Refreshing or closing the browser discards in-memory credentials;
   settings secrets must be entered again. None are saved to the work journal.
7. Choose **Work Type → Product Promotion**, or switch to **Domain →
   Self-Promotion** / **Product Promotion**.
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

## Latest v0.1.1 UI regression gates

- Confirm the dark sidebar, Work Center, Recent Work area and light main workspace follow the Worker v0.1.1 UI.
- Confirm Settings is a dialog (not a separate page): Provider, Model, API key, Advanced, Test connection, Cancel and Save. Under Advanced, find the GC-specific public repository and Discussions READ token.
- Confirm Work Type and Domain remain mutually exclusive New Task discovery routes. Domain has exactly Self-Promotion and Product Promotion; V2 actions remain disabled.
- Restart the original loopback server with Ctrl+C after updating so it serves new CSS and markup.
- A full Windows test run and **human-operated real UI E2E** are still mandatory; source and syntax checks do not count as app E2E PASS.

## Persistent Settings: Windows DPAPI (new)

The GC Agent now uses an independent encrypted Settings file at
`%LOCALAPPDATA%\GitHubCommunityAgent\settings.dpapi`. This is **not** the
Nature AI Worker credentials file or key. Data is protected by current-user
Windows DPAPI. No plaintext API key or GitHub token should enter
`work.sqlite3`. Non-Windows platforms refuse persistent settings.

**Note:** Earlier paragraphs in this preexisting guide that describe
session-only settings are superseded by this new section.

Validation steps:
1. Open Settings → fill in Provider, Model, public GitHub repository and API
   key → Save. If needed expand Advanced for the repository and read token.
2. Stop server with Ctrl+C, relaunch the same home executable, reopen Settings.
3. Confirm the saved provider, model, repository and a "key stored encrypted"
   indicator appear while the password input stays empty. Do not re-enter key.
4. Click Test connection with API key field empty: backend must load saved key,
   perform a real provider request and show success.
5. Verify Settings GET never returns actual key/token; Task start uses backend
   protected settings. No keys/tokens in SQLite work history.
6. Switch provider (e.g. OpenAI → DeepSeek) without a new key; Save should
   refuse rather than reuse the previous provider's credential.
7. Ensure no plaintext keys are written anywhere. Do not show or paste
   credentials in screenshots or command logs.

DPAPI only protects secrets for the current Windows user. Other processes
running as the **same Windows identity** may decrypt them. Native Windows
pytest and real application restart E2E remain unverified for this change.

## Classification correction — concrete Work Types

Owner clarified that the **five V1 actions are Work Types themselves**, not
five choices under an extra `Community Management` Work Type. The New Task
selector now works as follows:

- **Work Type**: Review Issues; Review Discussions; Draft Issue Reply; Draft
  Discussion Reply; Community Report. Selecting a Work Type selects its one
  Task definition directly, with objective, steps, expected result, review
  and limits below. The redundant row of V1 task cards is removed.
- **Domain**: Self-Promotion (default) or Product Promotion. Self-Promotion
  describes GC Agent self-promotion; Product Promotion contains Nature AI
  Worker or another repository. These V2 tasks are described but disabled.
- All V1 tasks have a Work Type and no Domain; all current V2 tasks have a
  Domain and no Work Type. The classification is product-owned, not a forced
  two-field structure across other Worker-family products.

**Native Windows acceptance pending:** update/restart the app; ensure no
`Community Management` Work Type remains, verify all five types and two
Domains, and inspect the Task description for each before launching a real
read-only V1 Task.
