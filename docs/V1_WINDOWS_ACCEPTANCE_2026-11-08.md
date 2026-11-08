# GitHub Community Agent V1 — Real Windows Acceptance Record

**Evidence date:** 2026-11-08 (user-operated Windows application, not Claude Code as functional tester)  
**Repo:** `nature-ai-corp/github-community-agent`  
**Draft implementation PR:** [#11](https://github.com/nature-ai-corp/github-community-agent/pull/11) (stacked on draft PR #9, #8, #7, #6)  
**Target:** an independent Windows product based on the general UI of Nature AI Worker **v0.1.1**.  
**Scope:** V1 Community Management read-only GitHub and AI operations. V2 Promotion is *not implemented*.

## Actual V1 Work Type execution

| V1 Work Type | Actual app evidence | Result | Remaining qualifications |
| --- | --- | --- | --- |
| Review Discussions | Task #1, then #6; real Nature AI Worker Discussion #32 | **Functional PASS** — finished, source-linked AI review, user report visible | Only the fetched sample was reviewed; not a full community audit |
| Review Issues | Task #2; 9 fetched issue records, 5 detail reads and AI analyses | **Functional PASS** — finished, per-Issue findings, source links, AI priority/actions | Five of nine fetched records analyzed; priorities are AI assessments |
| Draft Issue Reply | Task #4, Issue #33 | **Functional PASS** — generated actual text, entered Needs My Attention, moved to Finished on user Mark reviewed | Review is **local status only**. Independently confirm no new GitHub comment; model asked a possibly redundant question |
| Draft Discussion Reply | Task #8, Discussion #32 | **Functional PASS** — generated actual text, Needs My Attention then Finished; no posting requested | Task #5 and #7 failed with generic GitHub transport error before bounded retry improvement; investigate if failures recur; independently confirm no new comment |
| Community Report | Task #9, includes recent Issues and one Discussion | **Functional PASS** — finished, real source-linked report, JSON exported | Report has `incomplete:true`; new structured report UI added after user screenshot and **requires new Windows visual verification** |

The evidence above is user-supplied screenshots and exported Task JSON files in
this conversation. It proves those **specific** app executions, not reliability
under all conditions, nor a general product release readiness PASS.

## UI / product contract

- [x] General navigation, Settings modal and style adapted from **AI Worker v0.1.1**; original Worker repository unchanged
- [x] Independent GC Agent app, local SQLite Work history, Windows DPAPI-encrypted settings shown restored and live AI Test connection shown successful
- [x] **Community Management** entry has 5 concrete Work Types
- [x] **Promotion** entry has two Domains: Self-Promotion (default), Product Promotion; V2 execution disabled
- [x] Work status history and failure entries visible; no auto-publishing path implemented
- [x] User-facing Review Issues and Review Discussions reports displayed on native Windows
- [x] Draft reply report displays real unposted text and user review action
- [x] Copy / Export JSON visible; actual Task #1, #2, #4 and #9 export files provided
- [ ] **Latest Community Report**: native Windows render with Task #9 (summary, distinct issues/discussions findings, recommendations, sources, partial coverage, Technical Details) — pending
- [ ] Cross-workflow Copy/Export after UI changes, long detail scrolling, restart persistence — final regression pending
- [ ] Clear, accurate error classification and repeatable connection test for GitHub Discussions — pending

## Security and release gates — NOT YET ACCEPTED

- [ ] Current branch **full native Windows pytest** result recorded with exact count, skips, and zero fails; previously reported results apply to older branches or revisions
- [ ] Native security tests for API key/GitHub token storage, CSP/Origin, localhost binding, DPAPI rollback/rotation, input validation, disk/log secret absence; automated tests alone insufficient
- [ ] Independent verification **no comments were posted** on Issue #33 and Discussion #32 as a result of Mark reviewed (application returns `posted:false`, but remote-state evidence is separate)
- [ ] Error and recovery scenarios: GraphQL timeout, 401/403, token expiry, interruption during Task, restart after running, clear terminal state, no unsafe replay
- [ ] Product-specific signed Windows packaging, installer/uninstaller, clean isolated install/upgrade and source provenance checks
- [ ] Stable branch/PR merge order, release versioning, license attribution and distribution checks
- [ ] V2 Promotion remains unavailable; future writing requires a separate explicit user approval + safe outbox and external policy review

**Go/no-go:** V1's five essential functions have *live functional evidence*, but
**V1 is not release-ready** until the above blocking gates are handled.
Keep PR #11 and stacked PRs Draft; do not merge/tag/publish based solely on
functional success.

## Native Windows next run

Stop the currently running GC Agent server with Ctrl+C, then:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\github-community-agent-home.exe
```

Open **My Work → Task #9 — Community Report** and confirm:

1. **Summary**: distinguish the five analyzed Issues from nine fetched Issue records; one Discussion; never call nine a page count.
2. **Findings**: Issue Activity, Discussion Activity, Key Observations each separated and faithful to the saved model output; do not claim past Issue plans are necessarily current.
3. **Recommended Actions** and **Next Step** clearly separated.
4. **Sources** link to the actual retrieved GitHub Issues/Discussion.
5. **Coverage** explicitly states incomplete sample / not full repository.
6. **Technical Details** stays collapsed until clicked; Copy JSON and Export JSON still work; no artificial AI rerun.

Record the exact pytest summary and screenshot. Security/release gates remain
separate even if that visual check passes.

## Release-preparation checkpoint — November 8, 2026

**Status: functional proof-of-concept validated; Windows release NOT approved.**

This branch adds a six-job cross-platform offline test matrix:
Ubuntu and Windows on Python 3.11, 3.12 and 3.13, plus a **separate Windows
wheel preflight**. GitHub Actions in this private repository previously had
billing restrictions; do not assume CI jobs ran just because a workflow file
exists. The source tests are not substitutes for a real Windows run.

The release preflight is **not an installer or code-signing step**. It builds
an ordinary Python wheel and installs it into a disposable temporary folder;
then checks console-script metadata and the packaged UI's HTML/CSS assets.
It neither launches the browser nor uses GitHub/OpenAI credentials.

### Run on the user's actual Windows testing computer

Stop the GC Agent local server before testing any new build. In PowerShell:

```powershell
cd C:\Users\aiuser\projects\github-community-agent
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-v1-preflight.ps1
```

Record the exact test count, any skipped tests and the wheel preflight's
PASS/FAIL output; do not paste or print API keys. The preflight selects the
repository's `.venv\Scripts\python.exe` if it exists.

Then restart the existing `github-community-agent-home.exe` and verify the
same retained Tasks #1, #2, #8, #10 and Archived Work remain accessible.
Confirm that Archived Work is **view-only**, not restorable; that API-key
Settings remain DPAPI encrypted; and that Technical Details, Copy, Export JSON
and Activity History remain usable.

### Important release blockers

1. **Development version** is still `0.0.0.dev0`; no GC Agent V1 release
   tag or final version approved. Do not distribute the wheel as official.
2. **No signed standalone Windows installer** has been produced or tested.
   PyPI/wheel packaging is *not* the same as a Windows installer.
3. **Full Windows pytest and preflight output for this latest head** have
   not yet been received.
4. **Windows signed installer trust/Smart App Control**, installation,
   uninstallation, upgrades, clean data isolation and Windows Defender tests
   remain to be designed and executed.
5. **GitHub non-posting verification**, least-privilege token handling,
   request error recovery and user-facing reports need final acceptance.
6. Hosted CI in the private repository might not run until billing is fixed.
7. Parent stacked Draft PRs remain unmerged. Review dependency order before
   any final merge or release.

No real GitHub comment/promotion posting is part of V1. Nature AI Worker
v0.1.1 remains unchanged.
