"""V2 Promotion Work Types: six independently selectable Tasks on ONE shared engine.

Covers Work Type selection, scope isolation between Work Types, and approval
enforcement. Only GitHub Discussions has an automated publisher; the other five
are draft / manual-publication only and must never send anything or use the
GitHub token. Offline: reuses the GitHub mock and fakes from test_promotion.
"""
from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from github_community_agent import promotion as pr
from github_community_agent import work_center as w
from github_community_agent.errors import ToolError

from test_promotion import NONCE, REPO_A, REPO_B, TOKEN_A, TOKEN_B, FakeModel, MemorySettings, env  # noqa: F401

STARTABLE = [k for k in pr.WORK_TYPES if k not in pr.LEGACY_WORK_TYPES]
MANUAL = [k for k in STARTABLE if not pr.WORK_TYPES[k].automated_publishing]


def _start_type(service, creds, repo, model, definition_id):
    creds.update(repo)
    task_id = service.start(model, definition_id)
    return task_id, service.detail(task_id)["actions"][0]


@pytest.fixture(autouse=True)
def _development_work_types(monkeypatch):
    """These tests cover development code for ALL Work Types (release builds expose only verified ones)."""
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")


# -- selection -----------------------------------------------------------------------------


@pytest.mark.parametrize("definition_id", STARTABLE)
def test_each_work_type_runs_only_itself(env, definition_id):
    fake, journal, creds, service, _ = env
    model = FakeModel(TOKEN_A)
    task_id, action = _start_type(service, creds, REPO_A, model, definition_id)
    wt = pr.WORK_TYPES[definition_id]
    task = journal.get(task_id)
    assert task["definition_id"] == definition_id and task["status"] == "needs_attention"
    assert task["result"]["work_type"] == wt.label and task["result"]["channel"] == wt.channel
    assert task["result"]["publication"] == ("automated" if wt.automated_publishing else "manual")
    detail = service.detail(task_id)
    assert [a["channel"] for a in detail["actions"]] == [wt.channel] and action["status"] == "draft"
    # Shared research and plan; ONLY this Work Type's draft instruction ran.
    drafts = [i for i in model.inputs for other in pr.WORK_TYPES.values() if i.startswith(other.draft_instruction)]
    assert len(drafts) == 1 and drafts[0].startswith(wt.draft_instruction)
    assert sum(i.startswith(pr.PLAN_INSTRUCTION) for i in model.inputs) == 1
    assert json.loads(model.inputs[0].split("\n", 1)[1])["work_type"] == wt.label
    # Research and drafting never write and never use a token.
    assert fake.mutations == [] and all(t == "" for _, _, t in fake.requests)


def test_unselected_work_types_are_not_executed(env):
    _, journal, creds, service, _ = env
    _start_type(service, creds, REPO_A, FakeModel(), "promote_reddit")
    tasks = journal.list()
    assert [t["definition_id"] for t in tasks] == ["promote_reddit"]


def test_unknown_work_type_is_refused(env):
    _, journal, _, service, _ = env
    with pytest.raises(ToolError, match="Unknown Promotion Work Type"):
        service.start(FakeModel(), "review_issues")
    assert journal.list() == []


@pytest.mark.parametrize("definition_id", STARTABLE)
def test_http_create_starts_exactly_the_selected_work_type(env, definition_id):
    _, journal, creds, _, _ = env

    class Recording:
        def __init__(self):
            self.started = []

        def start(self, model, definition_id):
            self.started.append(definition_id)
            return 7

    rec = Recording()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, rec), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port

    def post(payload):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("POST", "/api/tasks", body=json.dumps(payload).encode(), headers={
            "Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
            "Content-Type": "application/json", "X-App-Nonce": NONCE})
        r = conn.getresponse()
        r.read()
        conn.close()
        return r.status
    try:
        assert post({"route": "domain", "selection": "Promotion", "definition_id": definition_id}) == 202
        # A Promotion Work Type cannot be started through the Community Management route.
        assert post({"route": "work_type", "selection": "Review Issues", "definition_id": definition_id}) == 400
        assert rec.started == [definition_id]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_ui_promotion_work_type_selector_and_manual_controls():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert '"Promotion — Work Type"' in html
    assert 'state.definitions.filter(d=>d.domain==="Promotion").map(d=>[d.id,d.title])' in html
    assert "promo-approve-manual" in html and "draft / manual publication only" in html
    # Manual drafts render their own controls and skip the GitHub preflight/publish block.
    manual_block = html[html.index("if(manual){"):html.index("continue;", html.index("if(manual){"))]
    assert "promo-publish" not in manual_block and "promo-preflight" not in manual_block


# -- scope isolation -----------------------------------------------------------------------


@pytest.mark.parametrize("definition_id", MANUAL)
def test_manual_work_types_never_publish_or_use_the_github_token(env, definition_id):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)  # a valid GitHub token IS stored; it must still never be used
    task_id, a = _start_type(service, creds, REPO_A, FakeModel(TOKEN_A), definition_id)
    for call in (lambda: service.preflight(task_id, a["id"]),
                 lambda: service.publish(task_id, a["id"], a["draft_sha256"]),
                 lambda: service.reconcile(task_id, a["id"]),
                 lambda: service.monitor(task_id, a["id"])):
        with pytest.raises(ToolError, match="draft/manual-publication only"):
            call()
    destination = "r/example" if definition_id == "promote_reddit" else ""  # Reddit binds the subreddit
    approved = service.approve(task_id, a["id"], destination, a["draft_sha256"])
    with pytest.raises(ToolError, match="draft/manual-publication only"):
        service.publish(task_id, a["id"], approved)
    assert service.detail(task_id)["actions"][0]["status"] == "ready_manual"
    assert fake.mutations == []
    assert all(t == "" for _, _, t in fake.requests), "the GitHub token was used by a manual Work Type"


def test_actions_cannot_cross_work_types_or_tasks(env):
    _, _, creds, service, _ = env
    gh_task, gh_action = _start_type(service, creds, REPO_A, FakeModel(), pr.DEFINITION_ID)
    rd_task, rd_action = _start_type(service, creds, REPO_A, FakeModel(), "promote_reddit")
    with pytest.raises(ToolError, match="not found"):
        service.approve(gh_task, rd_action["id"], "General", rd_action["draft_sha256"])
    with pytest.raises(ToolError, match="not found"):
        service.edit(rd_task, gh_action["id"], "T", "B")
    # Even an action stored under the right Task is refused if its channel is not the Task's Work Type.
    rogue = service.store.add_draft(rd_task, REPO_A, "T", "B", pr.CHANNEL)
    with pytest.raises(ToolError, match="not found"):
        service.preflight(rd_task, rogue)


def test_work_type_tasks_stay_bound_to_their_repository(env):
    _, journal, creds, service, _ = env
    task_id, a = _start_type(service, creds, REPO_B, FakeModel(), "promote_bluesky")
    creds.update(REPO_A)  # switching the selected repository does not move the Task
    assert journal.get(task_id)["repository"] == REPO_B
    assert service.detail(task_id)["actions"][0]["repository"] == REPO_B


# -- approval enforcement ------------------------------------------------------------------


def test_manual_approval_covers_the_exact_text_and_edits_cancel_it(env):
    _, _, creds, service, _ = env
    task_id, a = _start_type(service, creds, REPO_A, FakeModel(), "promote_developer_forums")
    with pytest.raises(ToolError, match="does not match"):
        service.approve(task_id, a["id"], "", "0" * 64)
    with pytest.raises(ToolError, match="no Discussion category"):
        service.approve(task_id, a["id"], "General", a["draft_sha256"])
    # The GitHub-channel fingerprint of the same text is not accepted for another channel.
    with pytest.raises(ToolError, match="does not match"):
        service.approve(task_id, a["id"], "", pr.draft_sha256(REPO_A, a["title"], a["body"]))
    service.approve(task_id, a["id"], "", a["draft_sha256"])
    ready = service.detail(task_id)["actions"][0]
    assert ready["status"] == "ready_manual" and ready["approved_sha256"]
    with pytest.raises(ToolError, match="cannot be approved"):
        service.approve(task_id, a["id"], "", a["draft_sha256"])
    service.edit(task_id, a["id"], "New title", "Disclosure: I maintain it. New body.")
    edited = service.detail(task_id)["actions"][0]
    assert edited["status"] == "draft" and edited["approved_sha256"] is None
    # An edit that breaks a content rule (no disclosure) is stored but cannot be approved.
    service.edit(task_id, a["id"], "New title", "New body without disclosure.")
    broken = service.detail(task_id)["actions"][0]
    assert broken["status"] == "incomplete" and "disclosure" in broken["error"]
    with pytest.raises(ToolError, match="incomplete"):
        service.approve(task_id, a["id"], "", broken["draft_sha256"])
    events = [e["event"] for e in service.detail(task_id)["events"]]
    assert events == ["draft_created", "technical_review", "approved_for_manual_publication", "draft_edited",
                      "draft_edited"]


def test_github_discussions_still_requires_category_permission_and_exact_approval(env):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)
    task_id, a = _start_type(service, creds, REPO_A, FakeModel(TOKEN_A), pr.DEFINITION_ID)
    with pytest.raises(ToolError, match="Choose a Discussion category"):
        service.approve(task_id, a["id"], "", a["draft_sha256"])
    with pytest.raises(ToolError, match="Only an approved action"):
        service.publish(task_id, a["id"], a["draft_sha256"])
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    assert fake.mutations == []
    result = service.publish(task_id, a["id"], approved)
    assert result["status"] == "published" and len(fake.mutations) == 1
    assert result["url"].startswith(f"https://github.com/{REPO_A}/discussions/")


def test_existing_github_discussion_records_remain_valid(env):
    """Tasks created before Work Types (definition promote_repository, channel
    github_discussion, fingerprint without an explicit channel) keep working."""
    _, journal, creds, service, _ = env
    creds.update(REPO_A)
    task_id = journal.create("promote_repository", REPO_A)
    action_id = service.store.add_draft(task_id, REPO_A, "Old title", "Old body")  # pre-Work-Type call shape
    a = service.detail(task_id)["actions"][0]
    assert a["id"] == action_id and a["channel"] == "github_discussion"
    assert a["draft_sha256"] == pr._sha([REPO_A, "github_discussion", "Old title", "Old body"])
    assert service.detail(task_id)["work_type"] == "GitHub Discussions"
