"""M1: technical review gate. Approval requires a recorded technical review of exactly the
draft presented for approval; a never-reviewed or changed draft is refused by default, with
its diff; an explicit owner override must name exactly that diff and is recorded. Review
records are immutable. Applies to every external publishing approval path."""
from __future__ import annotations

import http.client
import json
import sqlite3
import threading
from http.server import ThreadingHTTPServer

import pytest

from github_community_agent import bluesky as bs
from github_community_agent import devto as dv
from github_community_agent import promotion as pr
from github_community_agent import work_center as w
from github_community_agent.errors import ToolError

from test_promotion import NONCE, REPO_A, TOKEN_A, FakeModel, MemorySettings, env  # noqa: F401
from test_promotion_bluesky import FakeBluesky, sky  # noqa: F401
from test_promotion_bluesky import _connected as bsky_connected, _task as bsky_task
from test_promotion_devto import FakeDev, dev  # noqa: F401
from test_promotion_devto import _connected as dev_connected, _task as dev_task

pytestmark = pytest.mark.real_review_gate


def _start(service, creds, definition_id=pr.DEFINITION_ID):
    creds.update(REPO_A, TOKEN_A)
    task_id = service.start(FakeModel(TOKEN_A), definition_id)
    return task_id, service.detail(task_id)["actions"][0]


def _action(service, task_id):
    return service.detail(task_id)["actions"][0]


def _reviews(service, action_id):
    with sqlite3.connect(service.store.db) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute("SELECT * FROM promotion_reviews WHERE action_id=? ORDER BY id",
                                             (action_id,))]


def _activity(journal, task_id):
    rows = [t for t in journal.list() if t["id"] == task_id][0]["activity"]
    return [e["event"].split(":", 1)[1] for e in rows if e["event"].startswith("action#")]


def test_unreviewed_draft_is_refused_then_approved_after_review(env):
    _, journal, creds, service, _ = env
    task_id, a = _start(service, creds)
    assert a["review"]["state"] == "not_reviewed" and "+TITLE: " + a["title"] in a["review"]["diff"]
    with pytest.raises(pr.ReviewRequired) as exc:
        service.approve(task_id, a["id"], "General", a["draft_sha256"])
    assert exc.value.code == "review_required" and _action(service, task_id)["status"] == "draft"
    with pytest.raises(ToolError, match="not the current draft"):
        service.mark_reviewed(task_id, a["id"], "0" * 64)
    assert service.mark_reviewed(task_id, a["id"], a["draft_sha256"])["state"] == "current"
    a = _action(service, task_id)
    assert a["review"]["state"] == "current" and a["review"]["diff"] == "" and a["review"]["reviewed_utc"]
    assert service.approve(task_id, a["id"], "General", a["draft_sha256"])
    assert _action(service, task_id)["status"] == "approved"
    assert [r["kind"] for r in _reviews(service, a["id"])] == ["review"]
    assert _activity(journal, task_id) == ["approve_refused:review_required", "technical_review_complete"]
    with pytest.raises(ToolError, match="unapproved draft"):  # only before approval
        service.mark_reviewed(task_id, a["id"], a["draft_sha256"])


def test_change_after_review_shows_the_diff_and_needs_an_exact_recorded_override(env):
    _, journal, creds, service, _ = env
    task_id, a = _start(service, creds)
    service.mark_reviewed(task_id, a["id"], a["draft_sha256"])
    reviewed_sha = a["draft_sha256"]
    service.edit(task_id, a["id"], a["title"], a["body"] + "\nAdded after the review.")
    a = _action(service, task_id)
    view = a["review"]
    assert view["state"] == "changed" and view["reviewed_sha256"] == reviewed_sha
    assert "+Added after the review." in view["diff"] and view["diff"].startswith("--- technically reviewed")
    with pytest.raises(pr.ReviewRequired) as exc:
        service.approve(task_id, a["id"], "General", a["draft_sha256"])
    assert exc.value.code == "changed_since_review"
    for bad in ({"acknowledged": True, "diff_sha256": "0" * 64}, {"acknowledged": False, "diff_sha256": view["diff_sha256"]},
                {"diff_sha256": view["diff_sha256"]}, "yes", True):
        with pytest.raises(pr.ReviewRequired):
            service.approve(task_id, a["id"], "General", a["draft_sha256"], bad)
    assert _action(service, task_id)["status"] == "draft"
    service.approve(task_id, a["id"], "General", a["draft_sha256"],
                    {"acknowledged": True, "diff_sha256": view["diff_sha256"]})
    assert _action(service, task_id)["status"] == "approved"
    reviews = _reviews(service, a["id"])
    assert [r["kind"] for r in reviews] == ["review", "override"]
    assert reviews[1]["reviewed_sha256"] == reviewed_sha and reviews[1]["diff_sha256"] == view["diff_sha256"]
    assert reviews[1]["draft_sha256"] == a["draft_sha256"]
    events = _activity(journal, task_id)
    assert "approve_refused:changed_since_review" in events
    assert events[-1] == "approved_over_review:changed_since_review"


def test_review_records_are_immutable(env):
    _, _, creds, service, _ = env
    task_id, a = _start(service, creds)
    service.mark_reviewed(task_id, a["id"], a["draft_sha256"])
    with sqlite3.connect(service.store.db) as con:
        for sql in ("UPDATE promotion_reviews SET draft_sha256='x'", "DELETE FROM promotion_reviews"):
            with pytest.raises(sqlite3.DatabaseError, match="immutable"):
                con.execute(sql)
    assert _reviews(service, a["id"])[0]["draft_sha256"] == a["draft_sha256"]


def test_existing_approvals_and_histories_are_preserved(env):
    fake, journal, creds, service, _ = env
    task_id, a = _start(service, creds)
    # An approval made before the review gate existed (no review record): it stays valid.
    sha = pr.content_sha256(REPO_A, "General", a["title"], a["body"])
    assert service.store.approve(a["id"], task_id, "General", sha)
    assert service.publish(task_id, a["id"], sha)["status"] == "published"
    assert len(fake.mutations) == 1 and _reviews(service, a["id"]) == []


def test_store_migration_adds_review_table_without_touching_existing_rows(tmp_path):
    db = tmp_path / "old.sqlite3"
    pr.PromotionStore(db)
    with sqlite3.connect(db) as con:
        con.execute("DROP TABLE promotion_reviews")      # a database from before M1
        con.execute("INSERT INTO promotion_actions(task_id,repository,channel,title,body,status,created_utc,"
                    "updated_utc) VALUES (1,'o/r','github_discussion','T','B','approved','t','t')")
    pr.PromotionStore(db)
    with sqlite3.connect(db) as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','trigger')")}
        row = con.execute("SELECT title,body,status FROM promotion_actions").fetchone()
    assert {"promotion_reviews", "promotion_reviews_no_update", "promotion_reviews_no_delete"} <= tables
    assert row == ("T", "B", "approved")


def test_manual_publication_approval_is_gated(env, monkeypatch):
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")
    _, journal, creds, service, _ = env
    task_id, a = _start(service, creds, "promote_reddit")
    with pytest.raises(pr.ReviewRequired):
        service.approve(task_id, a["id"], "r/example", a["draft_sha256"])
    service.mark_reviewed(task_id, a["id"], a["draft_sha256"])
    service.approve(task_id, a["id"], "r/example", a["draft_sha256"])
    assert _action(service, task_id)["status"] == "ready_manual"


def test_bluesky_approval_is_gated_and_sends_nothing(sky):
    fake, _, journal, creds, service, _ = sky
    bsky_connected(sky)
    task_id, a = bsky_task(service, creds)
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_approve(task_id, a["id"], a["bluesky"]["approval_sha256"])
    assert exc.value.code == "review_required" and fake.creates() == []
    assert _activity(journal, task_id)[-1] == "bluesky_approve_refused:review_required"
    service.mark_reviewed(task_id, a["id"], a["draft_sha256"])
    assert service.bluesky_approve(task_id, a["id"], a["bluesky"]["approval_sha256"])["status"] == "bluesky_approved"


def test_dev_approval_is_gated_and_sends_nothing(dev):
    fake, _, journal, creds, service, _ = dev
    dev_connected(dev)
    task_id, a = dev_task(service, creds)
    with pytest.raises(dv.DevError) as exc:
        service.devto_approve(task_id, a["id"], a["devto"]["approval_sha256"])
    assert exc.value.code == "review_required" and fake.writes() == []
    service.edit(task_id, a["id"], a["title"], a["body"])        # no change: still not reviewed
    service.mark_reviewed(task_id, a["id"], a["draft_sha256"])
    service.edit(task_id, a["id"], a["title"] + " (v2)", a["body"])  # changed after review
    a = _action(service, task_id)
    with pytest.raises(dv.DevError) as exc:
        service.devto_approve(task_id, a["id"], a["devto"]["approval_sha256"])
    assert exc.value.code == "changed_since_review" and "+TITLE: " + a["title"] in a["review"]["diff"]
    out = service.devto_approve(task_id, a["id"], a["devto"]["approval_sha256"],
                                {"acknowledged": True, "diff_sha256": a["review"]["diff_sha256"]})
    assert out["status"] == "dev_approved" and fake.writes() == []
    assert _activity(journal, task_id)[-2:] == ["approved_over_review:changed_since_review", "dev_approved"]


def test_review_and_override_over_http(env):
    _, journal, creds, service, _ = env
    task_id, a = _start(service, creds)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, service), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port

    def post(verb, body):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("POST", f"/api/promotion/tasks/{task_id}/actions/{a['id']}/{verb}", body=json.dumps(body).encode(),
                     headers={"Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
                              "Content-Type": "application/json", "X-App-Nonce": NONCE})
        r = conn.getresponse()
        data = r.read().decode()
        conn.close()
        return r.status, data
    try:
        status, text = post("approve", {"category": "General", "sha256": a["draft_sha256"]})
        assert status == 400 and "Technical review required" in text
        view = service.detail(task_id)["actions"][0]["review"]
        status, _ = post("approve", {"category": "General", "sha256": a["draft_sha256"],
                                     "review_override": {"acknowledged": True, "diff_sha256": view["diff_sha256"]}})
        assert status == 200 and _action(service, task_id)["status"] == "approved"
        assert _reviews(service, a["id"])[0]["kind"] == "override"
        assert post("review", {"sha256": a["draft_sha256"]})[0] == 400   # approved: no longer reviewable
    finally:
        httpd.shutdown()
        httpd.server_close()
