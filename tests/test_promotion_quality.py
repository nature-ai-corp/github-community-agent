"""V2 Promotion content quality: no silent truncation, Work-Type scope, content
validation, community rules, and controlled regeneration.

Regressions from docs/testing/V2_PROMOTION_SIX_WORK_TYPES_ACCEPTANCE.md:
truncated Repository Optimization / Technical Articles drafts, plans that proposed
GitHub Discussions for other Work Types, over-long social posts, a 124-character
title, guesses about unread Issues, stale "no installer" claims, and improvement
suggestions proposing incentives and testimonials.
"""
from __future__ import annotations

import json

import httpx
import pytest

from github_community_agent import model_provider as mp
from github_community_agent import promotion as pr
from github_community_agent.errors import ToolError

from test_promotion import REPO_A, VALID_BODY, FakeModel, env  # noqa: F401

KEY = "test_api_key_not_real_123456789012"
EVIDENCE = {"releases": [{"tag": "v1.0.0-rc1", "name": "RC1", "prerelease": True, "published_at": "2026-11-10",
                          "url": "https://github.com/o/r/releases/tag/v1.0.0-rc1", "assets": ["Setup.exe"]}],
            "facts": {"open_issues": 4}}
WT = pr.WORK_TYPES


@pytest.fixture(autouse=True)
def _development_work_types(monkeypatch):
    """These tests cover development code for ALL Work Types (release builds expose only verified ones)."""
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")


# -- provider: finish_reason and V1 limits -----------------------------------------------


def _provider(monkeypatch, reply: dict):
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [reply]})
    monkeypatch.setattr(mp, "_transport", httpx.MockTransport(handle))
    return mp.ChatCompletionsModel(mp.ModelSettings("openai", "gpt-4.1-mini"), lambda: KEY), requests


def test_v1_call_keeps_its_limits(monkeypatch):
    model, requests = _provider(monkeypatch, {"message": {"content": "x" * 7000}, "finish_reason": "stop"})
    assert model("i", "e") == "x" * 6000             # V1: unchanged 6000-character cap
    assert requests[0]["max_tokens"] == 1200          # V1: unchanged completion budget


def test_complete_reports_length_cutoff_and_uses_the_budget(monkeypatch):
    model, requests = _provider(monkeypatch, {"message": {"content": "partial"}, "finish_reason": "length"})
    c = model.complete("i", "e", max_tokens=3500, timeout=120, max_chars=30000)
    assert c.text == "partial" and c.finish_reason == "length" and c.complete is False
    assert requests[0]["max_tokens"] == 3500


def test_complete_flags_text_cut_to_the_character_limit(monkeypatch):
    model, _ = _provider(monkeypatch, {"message": {"content": "y" * 50}, "finish_reason": "stop"})
    c = model.complete("i", "e", max_chars=10)
    assert c.text == "y" * 10 and c.complete is False
    assert model.complete("i", "e", max_chars=100).complete is True


def test_generation_budget_is_configurable(monkeypatch):
    assert pr._budget(3500) == 3500
    monkeypatch.setenv("GCA_PROMOTION_MAX_TOKENS", "8000")
    assert pr._budget(3500) == 8000
    monkeypatch.setenv("GCA_PROMOTION_MAX_TOKENS", "999999")
    assert pr._budget(3500) == 16000


# -- engine: truncation is never a complete draft -----------------------------------------


class Completion:
    def __init__(self, text, complete, finish_reason="stop"):
        self.text, self.complete, self.finish_reason = text, complete, finish_reason


class ScriptedModel(FakeModel):
    """FakeModel with completion metadata; drafts can be scripted per call."""

    def __init__(self, drafts=(), plans=()):
        super().__init__()
        self.drafts, self.plans, self.budgets = list(drafts), list(plans), []

    def complete(self, instruction, evidence, *, max_tokens, timeout, max_chars):
        self.budgets.append(max_tokens)
        is_plan = instruction.startswith(pr.PLAN_INSTRUCTION)
        queue = self.plans if is_plan else self.drafts
        if queue:
            self.inputs.append(instruction + "\n" + evidence)
            return queue.pop(0)
        return Completion(self(instruction, evidence), True)


def _run(service, creds, definition_id, model):
    creds.update(REPO_A)
    task_id = service.start(model, definition_id)
    return task_id, service.detail(task_id)["actions"][0]


def test_cut_off_draft_is_retried_once_then_marked_incomplete(env):
    _, journal, creds, service, _ = env
    cut = Completion("TITLE: T\nBODY:\nDisclosure: I maintain it. Half an artic", False, "length")
    model = ScriptedModel(drafts=[cut, cut])
    task_id, a = _run(service, creds, "promote_technical_articles", model)
    assert a["status"] == "incomplete" and "cut off" in a["error"]
    result = journal.get(task_id)["result"]
    assert result["quality"]["passed"] is False
    assert any("cut off" in i for i in result["quality"]["draft_issues"])
    assert sum(i.startswith(WT["promote_technical_articles"].draft_instruction) for i in model.inputs) == 2
    assert model.budgets[-1] == WT["promote_technical_articles"].max_tokens == 3500
    with pytest.raises(ToolError, match="incomplete"):
        service.approve(task_id, a["id"], "", a["draft_sha256"])
    events = [e["event"] for e in service.detail(task_id)["events"]]
    assert events == ["draft_incomplete"]


def test_retry_that_completes_produces_a_ready_draft(env):
    _, journal, creds, service, _ = env
    cut = Completion("TITLE: T\nBODY:\nI maintain it. Half", False, "length")
    model = ScriptedModel(drafts=[cut])
    task_id, a = _run(service, creds, "promote_reddit", model)
    assert a["status"] == "draft" and a["error"] is None
    retry = [i for i in model.inputs if pr.RETRY_SUFFIX in i]
    assert len(retry) == 1 and "cut off" in retry[0]
    assert journal.get(task_id)["result"]["quality"]["passed"] is True


def test_controlled_regeneration_replaces_an_incomplete_draft(env):
    _, journal, creds, service, _ = env
    cut = Completion("TITLE: T\nBODY:\nI maintain it. Half", False, "length")
    task_id, a = _run(service, creds, "promote_developer_forums", ScriptedModel(drafts=[cut, cut]))
    assert a["status"] == "incomplete"
    out = service.regenerate(task_id, a["id"], ScriptedModel())
    assert out == {"status": "draft", "issues": []}
    fixed = service.detail(task_id)["actions"][0]
    assert fixed["status"] == "draft" and fixed["error"] is None and fixed["body"].startswith("I maintain")
    assert journal.get(task_id)["result"]["quality"]["passed"] is True
    service.approve(task_id, a["id"], "", fixed["draft_sha256"])
    with pytest.raises(ToolError, match="Only an unapproved draft"):
        service.regenerate(task_id, a["id"], ScriptedModel())


def test_regeneration_is_capped(env, monkeypatch):
    _, _, creds, service, _ = env
    monkeypatch.setattr(pr, "MAX_REGENERATIONS", 2)
    task_id, a = _run(service, creds, "promote_reddit", ScriptedModel())
    service.regenerate(task_id, a["id"], ScriptedModel())
    service.regenerate(task_id, a["id"], ScriptedModel())
    with pytest.raises(ToolError, match="regenerated 2 times"):
        service.regenerate(task_id, a["id"], ScriptedModel())


# -- engine: Work-Type scope --------------------------------------------------------------


@pytest.mark.parametrize("definition_id", [k for k, w in WT.items()
                                           if not w.automated_publishing and k not in pr.LEGACY_WORK_TYPES]
                         + ["promote_bluesky"])
def test_plan_proposing_a_discussion_for_another_work_type_is_corrected(env, definition_id):
    _, journal, creds, service, _ = env
    bad = Completion("Channel approach: Publish an approved GitHub Discussion (Proposed). Audience (Verified).", True)
    model = ScriptedModel(plans=[bad])
    task_id, a = _run(service, creds, definition_id, model)
    plans = [i for i in model.inputs if i.startswith(pr.PLAN_INSTRUCTION)]
    assert len(plans) == 2 and "GitHub Discussion publication outside" in plans[1]
    assert WT[definition_id].plan_focus in plans[0]
    assert a["status"] == "draft" and journal.get(task_id)["result"]["quality"]["plan_issues"] == []


def test_plan_that_stays_out_of_scope_blocks_the_draft(env):
    _, journal, creds, service, _ = env
    bad = Completion("Publish the article as a GitHub Discussion (Proposed). Audience (Verified).", True)
    task_id, a = _run(service, creds, "promote_technical_articles", ScriptedModel(plans=[bad, bad]))
    assert a["status"] == "incomplete" and "outside the Technical Articles" in a["error"]


def test_github_discussions_plan_may_plan_a_discussion():
    plan = "Channel approach: Publish an approved GitHub Discussion (Proposed). Audience (Verified)."
    assert pr.check_plan(WT["promote_repository"], plan, EVIDENCE) == []


def test_plan_may_link_discussions_for_feedback():
    plan = "Invite feedback via the GitHub Discussions page (Proposed). Audience (Verified)."
    assert pr.check_plan(WT["promote_reddit"], plan, EVIDENCE) == []


# -- validation ---------------------------------------------------------------------------


def test_social_posts_must_fit_their_limits():
    body = "SHORT POST:\nI maintain X. " + "a" * 300 + "\nLONG POST:\nI maintain X. " + "b" * 1300
    issues = pr.check_draft(WT["promote_social_media"], "T", body, EVIDENCE)
    assert any("Short post is" in i and "limit is 280" in i for i in issues)
    assert any("Long post is" in i and "limit is 1200" in i for i in issues)
    assert pr.check_draft(WT["promote_social_media"], "T", VALID_BODY["social_media"].format(repo="o/r"),
                          EVIDENCE) == []
    assert "Body is missing the 'LONG POST:' section." in pr.check_draft(
        WT["promote_social_media"], "T", "SHORT POST:\nI maintain X.", EVIDENCE)


def test_bluesky_post_is_checked_against_the_lexicon_and_needs_the_link():
    wt = WT["promote_bluesky"]
    assert pr.check_draft(wt, "T", VALID_BODY["bluesky"].format(repo="o/r"), EVIDENCE) == []
    # Exactly 300 grapheme clusters (562 code points): counted as Bluesky counts them, so allowed.
    combining = "I maintain o/r https://github.com/o/r " + "e\u0301" * 262
    assert not any("graphemes" in i for i in pr.check_draft(wt, "T", combining, EVIDENCE))
    over = "I maintain o/r https://github.com/o/r " + "x" * 270
    assert any("Bluesky allows 300" in i for i in pr.check_draft(wt, "T", over, EVIDENCE))
    assert "The post must include the repository's https:// link." in pr.check_draft(
        wt, "T", "I maintain o/r. The first pre-release is out.", EVIDENCE)
    assert any("disclosure" in i for i in pr.check_draft(
        wt, "T", "The first pre-release is out. https://github.com/o/r", EVIDENCE))


def test_title_and_body_limits():
    issues = pr.check_draft(WT["promote_repository_optimization"], "t" * 124,
                            "Current (verified): x\nProposed: y\n" + "z" * 5000, EVIDENCE)
    assert "Title is 124 characters; the limit is 120." in issues
    assert any(i.startswith("Body is") and "limit is 5000" in i for i in issues)


def test_repository_optimization_separates_verified_facts_from_proposals():
    issues = pr.check_draft(WT["promote_repository_optimization"], "T", "Add topics. Improve README.", EVIDENCE)
    assert "Body is missing the required 'Current (verified):' labels." in issues
    assert "Body is missing the required 'Proposed:' labels." in issues


@pytest.mark.parametrize("definition_id", ["promote_reddit", "promote_developer_forums",
                                           "promote_technical_articles"])
def test_manual_posts_need_an_affiliation_disclosure_at_the_start(definition_id):
    late = "A great tool. " * 60 + "I maintain it."
    assert any("disclosure" in i for i in pr.check_draft(WT[definition_id], "T", late, EVIDENCE))
    assert pr.check_draft(WT[definition_id], "T", "I maintain it. A tool.", EVIDENCE) == []


def test_unread_issues_are_never_described():
    text = "Current (verified): 4 open issues exist, some likely related to documentation.\nProposed: templates"
    assert "Describes what open issues are about, but no Issue was read." in pr.check_draft(
        WT["promote_repository_optimization"], "T", text, EVIDENCE)
    ok = "Current (verified): 4 open issues.\nProposed: add issue templates."
    assert pr.check_draft(WT["promote_repository_optimization"], "T", ok, EVIDENCE) == []


@pytest.mark.parametrize("text,flagged", [
    ("No official independent Windows installer or V1 release has been published.", True),
    ("Note: no official installer or GitHub write access yet.", True),
    ("No official signed installer has been published yet; an unsigned pre-release installer is available.", False),
    ("The v1.0.0-rc1 pre-release includes an unsigned installer.", False),
])
def test_stale_no_release_claims_are_flagged_when_a_release_exists(text, flagged):
    issues = pr.check_draft(WT["promote_developer_forums"], "T", "I maintain it. " + text, EVIDENCE)
    assert ("Claims no release or installer is available, but a published release exists." in issues) is flagged
    assert pr.check_draft(WT["promote_developer_forums"], "T", "I maintain it. " + text, {"releases": []}) == []


@pytest.mark.parametrize("text", [
    "Please upvote this post!",
    "Give us a star on GitHub.",
    "Obtain at least 5 new stars from Reddit traffic.",
    "Offer incentives such as small rewards for detailed feedback.",
    "Share testimonials or early user quotes to build trust.",
    "Collaborate with relevant influencers to amplify reach.",
])
def test_engagement_bait_incentives_and_testimonials_are_refused(text):
    assert pr.check_improvement(text, EVIDENCE)


def test_honest_improvement_passes():
    text = "1. Put the install steps first (targets comments). 2. Ask one specific question (targets comments)."
    assert pr.check_improvement(text, EVIDENCE) == []


def test_improve_refuses_suggestions_that_break_the_rules(env):
    fake, journal, creds, service, _ = env
    creds.update(REPO_A, "github_pat_" + "A1" * 20)
    task_id, a = _run(service, creds, pr.DEFINITION_ID, ScriptedModel())
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    assert service.publish(task_id, a["id"], approved)["status"] == "published"
    bad = Completion("Offer incentives such as small rewards for feedback.", True)
    with pytest.raises(ToolError, match="did not pass quality checks"):
        service.improve(task_id, ScriptedModel(drafts=[bad, bad]))
    assert service.detail(task_id)["improvements"] == []
    good = service.improve(task_id, ScriptedModel(drafts=[bad]))
    assert good == "Improve: post release notes earlier (targets comments)."


def test_research_evidence_includes_release_assets_and_authoritative_facts(env):
    fake, _, _, _, _ = env
    evidence = pr.research(REPO_A)
    facts = pr.authoritative_facts(evidence)
    assert facts["release_status"].startswith("Published pre-release v1.0.0-rc1")
    assert facts["open_issue_subjects"] == "not read"


def test_regenerate_route_and_ui_controls(env):
    import http.client
    import threading
    from http.server import ThreadingHTTPServer
    from pathlib import Path

    from github_community_agent import work_center as w
    from test_promotion import NONCE, MemorySettings
    _, journal, creds, service, _ = env
    task_id, a = _run(service, creds, "promote_reddit", ScriptedModel())
    calls = []
    service.regenerate = lambda t, aid, model: calls.append((t, aid, type(model).__name__)) or {"status": "draft", "issues": []}
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, service), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("POST", f"/api/promotion/tasks/{task_id}/actions/{a['id']}/regenerate", body=b"{}", headers={
            "Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
            "Content-Type": "application/json", "X-App-Nonce": NONCE})
        r = conn.getresponse()
        assert r.status == 200 and json.loads(r.read()) == {"status": "draft", "issues": []}
        conn.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert calls == [(task_id, a["id"], "ChatCompletionsModel")]
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert "promo-regenerate" in html and '<h4>Quality checks</h4>' in html
    assert '(a.status!=="incomplete"?\'<button type="button" class="promo-copy">' in html


def test_repository_optimization_may_report_what_the_readme_says():
    text = ("Current (verified): README states no official Windows installer or V1 release has been published.\n"
            "Proposed: state that v1.0.0-rc1 is published with an unsigned installer.")
    assert pr.check_draft(WT["promote_repository_optimization"], "T", text, EVIDENCE) == []
    # Other Work Types may not repeat the stale claim, even attributed.
    assert pr.check_draft(WT["promote_developer_forums"], "T", "I maintain it. " + text, EVIDENCE)


def test_length_problems_say_how_much_to_cut():
    issues = pr.check_draft(WT["promote_technical_articles"], "T", "Disclosure: I maintain it. " + "x" * 5900,
                            EVIDENCE)
    assert any("Shorten it by at least" in i for i in issues)


def test_plan_instruction_requires_labels_on_every_statement():
    assert "'(Proposed)'" in pr.PLAN_INSTRUCTION and "'(Verified: <source URL>)'" in pr.PLAN_INSTRUCTION


def test_improvement_receives_only_the_latest_cumulative_metrics(env):
    _, _, creds, service, _ = env
    creds.update(REPO_A, "github_pat_" + "A1" * 20)
    task_id, a = _run(service, creds, pr.DEFINITION_ID, ScriptedModel())
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    service.publish(task_id, a["id"], approved)
    service.monitor(task_id, a["id"])
    service.monitor(task_id, a["id"])
    model = ScriptedModel()
    service.improve(task_id, model)
    sent = json.loads(model.inputs[-1].split("\n", 1)[1])["published"][0]
    assert sent["observations"] == 2 and "metrics" not in sent
    assert sent["latest_metrics"]["upvotes"] == 4  # the latest total, never a sum of observations
