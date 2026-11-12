"""Release gate: "No real verification = no released Work Type."

Only Work Types with real-world acceptance evidence are listed, startable or
actionable in a release build: GitHub Discussions and Repository Optimization.
The four unverified Promotion Work Types remain development code: enabled only from source with GCA_PROMOTION_DEV_WORK_TYPES=1,
and never in a frozen (packaged) build. V1 Work Types are unaffected.
"""
from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from github_community_agent import promotion as pr
from github_community_agent import work_center as w
from github_community_agent.errors import ToolError

from test_promotion import NONCE, REPO_A, FakeModel, MemorySettings, env  # noqa: F401

VERIFIED = ["promote_repository", "promote_repository_optimization"]
UNVERIFIED = ["promote_reddit", "promote_developer_forums",
              "promote_technical_articles", "promote_bluesky", "promote_social_media"]
DEVELOPMENT_OFFERED = ["promote_reddit", "promote_developer_forums", "promote_technical_articles",
                       "promote_bluesky"]  # never the legacy generic "Social Media"
V1 = ["review_issues", "review_discussions", "draft_issue", "draft_discussion", "community_report"]


@pytest.fixture(autouse=True)
def _release_configuration(monkeypatch):
    monkeypatch.delenv(pr.DEV_WORK_TYPES_ENV, raising=False)


def test_only_verified_work_types_are_released():
    assert pr.RELEASE_VERIFIED_WORK_TYPES == set(VERIFIED)
    assert pr.enabled_work_types() == set(VERIFIED)


def test_release_definitions_expose_v1_and_verified_promotion_only(tmp_path):
    ids = [d["id"] for d in w.WorkService(w.Journal(tmp_path / "w.sqlite3")).definitions()]
    assert ids == V1 + VERIFIED
    assert [d.id for d in w.task_choices("domain", "Promotion")] == VERIFIED
    for v1 in V1:  # V1 Community Management unchanged
        assert w.task_choices("work_type", w.BY_ID[v1].work_type) == [w.BY_ID[v1]]


def test_development_new_task_lists_platform_work_types_never_legacy_social_media(monkeypatch):
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")
    assert [d.id for d in w.task_choices("domain", "Promotion")] == VERIFIED + DEVELOPMENT_OFFERED
    assert pr.startable_work_types() == set(VERIFIED + DEVELOPMENT_OFFERED)
    assert "promote_social_media" in pr.enabled_work_types()  # existing dev Tasks stay usable as drafts
    for future in ("promote_discord", "promote_mastodon", "promote_linkedin", "promote_dev_community"):
        assert future not in pr.WORK_TYPES and future not in w.BY_ID  # not implemented, not offered


def test_frozen_build_ignores_the_development_switch(monkeypatch):
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")
    assert pr.enabled_work_types() == frozenset(pr.WORK_TYPES)       # from source: development
    monkeypatch.setattr(pr.sys, "frozen", True, raising=False)
    assert pr.development_mode() is False
    assert pr.enabled_work_types() == set(VERIFIED)                    # packaged: release only
    assert [d.id for d in w.available_definitions() if d.workflow == "promotion"] == VERIFIED


@pytest.mark.parametrize("definition_id", UNVERIFIED)
def test_unverified_work_types_cannot_be_started(env, definition_id):
    _, journal, creds, service, _ = env
    with pytest.raises(ToolError, match="not available in this release"):
        service.start(FakeModel(), definition_id)
    with pytest.raises(ToolError, match="must match"):
        w.WorkService(journal, service).start(
            {"route": "domain", "selection": "Promotion", "definition_id": definition_id, "model_key": "k"})
    assert journal.list() == []


def test_existing_unverified_tasks_stay_viewable_but_not_actionable(env, monkeypatch):
    _, journal, creds, service, _ = env
    creds.update(REPO_A)
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")      # created earlier in development
    task_id = service.start(FakeModel(), "promote_reddit")
    a = service.detail(task_id)["actions"][0]
    monkeypatch.delenv(pr.DEV_WORK_TYPES_ENV)           # now running the release configuration
    detail = service.detail(task_id)
    assert detail["available"] is False and detail["actions"][0]["body"] == a["body"]  # history kept
    for call in (lambda: service.approve(task_id, a["id"], "", a["draft_sha256"]),
                 lambda: service.edit(task_id, a["id"], "T", "I maintain it."),
                 lambda: service.regenerate(task_id, a["id"], FakeModel()),
                 lambda: service.preflight(task_id, a["id"]),
                 lambda: service.publish(task_id, a["id"], a["draft_sha256"])):
        with pytest.raises(ToolError, match="not available in this release"):
            call()
    assert service.detail(task_id)["actions"][0]["status"] == "draft"


def test_release_http_api_refuses_unverified_work_types(env):
    _, journal, creds, service, _ = env
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, service), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port

    def call(method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers={
            "Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
            "Content-Type": "application/json", "X-App-Nonce": NONCE})
        r = conn.getresponse()
        data = r.read().decode()
        conn.close()
        return r.status, data
    try:
        status, text = call("GET", "/api/definitions")
        listed = [d["id"] for d in json.loads(text)["definitions"]]
        assert status == 200 and listed == V1 + VERIFIED
        for definition_id in UNVERIFIED:
            status, _ = call("POST", "/api/tasks", {"route": "domain", "selection": "Promotion",
                                                    "definition_id": definition_id})
            assert status == 400
        assert journal.list() == []
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_verified_github_discussions_still_works_end_to_end(env):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, "github_pat_" + "A1" * 20)
    task_id = service.start(FakeModel(), "promote_repository")
    a = service.detail(task_id)["actions"][0]
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    assert service.publish(task_id, a["id"], approved)["status"] == "published"
    assert len(fake.mutations) == 1
