# GitHub Promotor — Work Register & Execution Log

> Canonical tracker for **GitHub Promotor only**. Maintained on the existing `feature/v2-promotion` branch as an interim home; move into an independent GitHub Promotor repository when one is established. Do not use this register for GitHub Builder or GC Agent work.
>
> Initiated: 2026-11-14. Last verified baseline: repository documentation inspected on 2026-11-14. **No new Bluesky Search/Valuation code or acceptance run is claimed by this document.**

## Project principles and delivery order
- **Bluesky first:** deliver a complete working Bluesky opportunity-discovery/valuation workflow with real-world acceptance, then extract any general multi-channel engine. No generalization-first rewrite.
- **Practical acceptance:** test on real Bluesky discussions against a real project/repository; record actual URLs, inputs, execution times, outputs, and failures. A mock-only green test is not sufficient.
- **Scope:** initially **read-only discovery, valuation and ranking**. No autonomous public reply, unsolicited mention, like, follow, or post.
- Maintain a trustworthy evidence chain. Separate observed facts from AI inferences. Do not invent engagement, scores, or live test results.
- Default opportunity threshold **80/100**, optionally configurable to **75/100**; return up to **five** ranked opportunities. Five scoring dimensions and weights need to be documented before scoring is considered accepted.
- Each task has one named outcome, implementation reference (commit/PR), evidence and a clear next action.

## Status values
`BACKLOG` (not started) · `IN PROGRESS` (work underway, no acceptance) · `BLOCKED` (dependency recorded) · `TESTING` (implementation ready, validation underway) · `VERIFIED` (evidence-backed acceptance) · `DONE` (verified, integrated and closed).

## Baseline (reused implementation, not a new Promotor release)
| Reference | Status | Evidence |
|---|---|---|
| Existing Bluesky account + exact-approved publishing + public read-back | VERIFIED (historical, scope limited to posting) | `docs/testing/V2_PROMOTION_RELEASE_GATE.md` Task #22, 2026-11-12; https://bsky.app/profile/did:plc:c3nlceuqshyilc3zeps4vwlq/post/3n23dccbqbt3h |
| Existing implementation | INSPECTED | `src/github_community_agent/bluesky.py`, `src/github_community_agent/promotion.py`, `docs/V2_PROMOTION.md`, branch `feature/v2-promotion` |
| Existing promotion work PR | DRAFT / NOT RELEASED | https://github.com/nature-ai-corp/github-community-agent/pull/12 |
| Search + opportunity valuation implementation | NOT VERIFIED | No acceptance evidence located in the inspected code/documents as of 2026-11-14 |

## Work list — Bluesky-first
| ID | Task / deliverable | Status | Exit evidence | Depends on |
|---|---|---|---|---|
| GP-001 | Audit Bluesky reusable HTTP client, authentication/read-only access, test coverage and source boundaries | VERIFIED | Code map + gap list with file/line references | — |
| GP-002 | Bluesky public discussion search: keywords, pagination, time bounds, deduplication and source URLs | TESTING | Deterministic tests + real query and post URLs | GP-001 |
| GP-003 | Opportunity record schema + evidence capture (author, timestamp, content, metrics, canonical URL; missing fields explicit) | BACKLOG | Example records from public posts, validation tests | GP-002 |
| GP-004 | Five-dimension valuation rubric, weights, hard filters, missing-data policy and explanations | BACKLOG | Reviewed scoring specification with worked real cases | GP-003 |
| GP-005 | Compute 0–100 value scores; threshold defaults to 80 (can set 75); stable top-5 ranking and ties | BACKLOG | Repeatable tests, score breakdown and ordering | GP-004 |
| GP-006 | GitHub repository cross-check and topical fit for actual Nature AI Worker promotion | BACKLOG | Verified repository facts and citations; no invented features | GP-003 |
| GP-007 | Read-only end-to-end Bluesky Search → Value → Rank with user-facing results | BACKLOG | Real run showing up to 5 source links, numeric scores, explanations and rejected candidates | GP-002–GP-006 |
| GP-008 | Negative/security checks: rate limits, malformed content, API failure, credentials isolation, safe logging and no external writes | BACKLOG | Test log including failure and recovery behavior | GP-007 |
| GP-009 | Real-world acceptance and improvements over multiple runs | BACKLOG | Dated run logs, observed errors, fixes, final owner acceptance | GP-007–GP-008 |
| GP-010 | Bluesky engagement workflow (context-aware comments, exact approval, publication verification and monitoring) | BACKLOG | Separate owner-approved live acceptance; no unsolicited publication | GP-009 |
| GP-011 | Extract general engine from proven Bluesky implementation | BLOCKED (BY DESIGN) | Abstraction tests preserve Bluesky behavior, zero regressions | GP-009, GP-010 |
| GP-012 | Add next platform adapter | BLOCKED (BY DESIGN) | Actual platform-specific acceptance | GP-011 |

## Process recording rule
For **every** work session, append a dated entry below with:
1. Scope/goal and status transition (ID, before → after).
2. Exact code locations, branch and commit or PR.
3. Commands/tests executed (real vs mocked), outcome PASS/FAIL/NOT RUN, environment.
4. Real-world evidence: URLs, timestamps, search parameters, candidate counts and score breakdowns, redacted of secrets.
5. Defects/blockers, resolution, and next concrete action.
6. No retroactive `VERIFIED` without independently inspectable evidence.

## Session log
### 2026-11-14 — Tracker initialization / baseline review
- Scope: establish a persistent, project-specific work list and evidence recording process.
- Existing repository: `nature-ai-corp/github-community-agent`, branch `feature/v2-promotion` (interim, **not** a dedicated Promotor repository).
- Inspected: `docs/V2_PROMOTION.md`, `docs/testing/V2_PROMOTION_RELEASE_GATE.md`, `src/github_community_agent/promotion.py`, `src/github_community_agent/bluesky.py`.
- Confirmed historical Task #22 Bluesky publication and public read-back; this is **not** Search + Valuation acceptance.
- Searched for dedicated `github-promotor` / `github-promoter` repositories through linked GitHub access; none surfaced.
- Tests executed this session: **NOT RUN**. No publishing or repository application writes performed.
- Next action: GP-001 audit, then GP-002 read-only search prototype with real evidence. Keep GitHub Builder and GC Agent task tracking in their own places.

### 2026-11-14 — GP-001 audited, GP-002 first implementation committed
- **GP-001 → VERIFIED (code-inspection only):** inspected existing `src/github_community_agent/bluesky.py`. Historical code is a single-post writer, not a searcher. It uses DPAPI-managed credentials and the `public.api.bsky.app` AppView for post read-back. No new publishing endpoint is needed for search. The new read-only search implementation is deliberately isolated in a separate module.
- **GP-002 → TESTING:** added `src/github_community_agent/bluesky_discovery.py` (commit `79a800ea3d28672346256204cd230ac752dd84c3`) and `tests/test_bluesky_discovery.py` (commit `19ecc3c03689a3c7b7a3f14e8a0560d2ae523613`). Corrected the AT URI regex escaping in `a632ddf196f1dc3a2bee8cd36cb419efaf41a7f0`.
- **Discovery contract:** public GET only to `https://api.bsky.app/xrpc/app.bsky.feed.searchPosts`; query/page/candidate ceilings; latest-first, `until` pagination (no anonymous cursor dependency), timestamp cutoff, URI deduplication across keywords, canonical URLs, missing engagement metrics preserved as `None`, no valuation and no API credential use. No publishing action.
- **Test cases committed but not executed:** query deduplication, source URL and GET-only boundary, missing metrics, local cutoff, malformed URI discard, HTTP error refusal, invalid query refusal, and timestamp pagination. **CI not verified; do not report PASS.**
- **External API note:** Bluesky source describes `searchPosts` GET. An independent community report notes that anonymous pagination with `cursor` can be rejected, and `public.api.bsky.app` search can return 403 while `api.bsky.app` works. Require real-world validation, not an assumption about current availability.
- **No live search executed**, no code executed on the owner's Windows machine, no repository merge, and no social publication.
- **Next:** run `python -m pytest tests/test_bluesky_discovery.py -q` on the Windows development checkout, fix any failures, then run actual bounded search requests and record redacted outcomes and real URLs. GP-003 follows after a verified live search.
