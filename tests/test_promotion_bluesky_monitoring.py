"""Bluesky post engagement monitoring: public read-only observations, append-only history,
first-seen public replies, Improve on real observations. The publication and verification
evidence is never changed; nothing is ever replied to, liked, followed, reposted or published."""
from __future__ import annotations

import http.client
import json
import sqlite3
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from github_community_agent import bluesky as bs
from github_community_agent import promotion as pr
from github_community_agent import work_center as w
from github_community_agent.errors import ToolError

from test_promotion import NONCE, FakeModel, MemorySettings, env  # noqa: F401
from test_promotion_bluesky import DID_A, FakeBluesky, sky  # noqa: F401
from test_promotion_bluesky import _approved

OTHER = "did:plc:" + "q" * 24


def reply(rkey, parent=None, created="2026-11-12T10:00:00.000Z"):
    return {"$type": "app.bsky.feed.defs#threadViewPost",
            "post": {"uri": f"at://{OTHER}/app.bsky.feed.post/{rkey}", "cid": "bafyreireply",
                     "author": {"did": OTHER, "handle": "someone.bsky.social", "displayName": "Some One"},
                     "record": {"text": "a reply", "createdAt": created,
                                **({"reply": {"parent": {"uri": parent}, "root": {"uri": parent}}} if parent else {})},
                     "indexedAt": created}}


class Extra:
    """Adds app.bsky.feed.getPostThread and failure modes to the shared fake."""

    def __init__(self, fake):
        self.fake = fake
        self.replies: list[str] = []          # rkeys of direct replies
        self.extra_items: list[dict] = []
        self.thread_mode = "ok"               # ok | not_found | error_503
        self.post_mode = "ok"                 # ok | cid_changed
        self.gate: threading.Event | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        if url.host == "public.api.bsky.app" and url.path == "/xrpc/app.bsky.feed.getPostThread":
            self.fake.requests.append(request)
            assert "authorization" not in request.headers and request.method == "GET"
            if self.thread_mode == "error_503":
                return httpx.Response(503, json={})
            uri = url.params["uri"]
            if self.thread_mode == "not_found" or not any(r["uri"] == uri for r in self.fake.records.values()):
                return httpx.Response(400, json={"error": "NotFound", "message": "Post not found"})
            items = [reply(k, uri) for k in self.replies] + self.extra_items
            return httpx.Response(200, json={"thread": {"$type": "app.bsky.feed.defs#threadViewPost",
                                                        "post": {"uri": uri}, "replies": items}})
        if url.host == "public.api.bsky.app" and url.path == "/xrpc/app.bsky.feed.getPosts" and self.gate:
            self.gate.wait(5)
        resp = self.fake.handler(request)
        if self.post_mode == "cid_changed" and url.path == "/xrpc/app.bsky.feed.getPosts" and resp.status_code == 200:
            data = resp.json()
            for p in data.get("posts", []):
                p["cid"] = "bafyreichanged" + "d" * 40
            return httpx.Response(200, json=data)
        return resp


@pytest.fixture
def mon(sky, monkeypatch):
    extra = Extra(sky[0])
    monkeypatch.setattr(bs, "_transport", httpx.MockTransport(extra.handler))
    return (extra, *sky)


def _published(mon, verify=True):
    extra, fake, _, journal, creds, service, tmp = mon
    task_id, a = _approved(mon[1:])
    service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    if verify:
        service.bluesky_verify(task_id, a["id"])
    return task_id, service.detail(task_id)["actions"][0]


def _row(service, action_id):
    with sqlite3.connect(service.store.db) as con:
        con.row_factory = sqlite3.Row
        return dict(con.execute("SELECT * FROM promotion_actions WHERE id=?", (action_id,)).fetchone())


def _activity(journal, task_id):
    rows = [t for t in journal.list() if t["id"] == task_id][0]["activity"]
    return [e["event"].split(":", 1)[1] for e in rows if e["event"].startswith("action#")]


def test_refresh_appends_observations_and_never_changes_the_evidence(mon):
    extra, fake, _, journal, _, service, _ = mon
    task_id, a = _published(mon)
    before = _row(service, a["id"])
    first = service.bluesky_monitor(task_id, a["id"])
    assert (first["outcome"], first["likes"], first["replies"], first["reposts"], first["quotes"]) == \
        ("observed", 2, 1, 0, 0)
    service.bluesky_monitor(task_id, a["id"])
    assert _row(service, a["id"]) == before                    # status, verification snapshot, URI, CID
    obs = service.detail(task_id)["actions"][0]["bluesky"]["observations"]
    assert len(obs) == 2 and all(o["outcome"] == "observed" and o["likes"] == 2 for o in obs)
    assert obs[0]["observed_utc"] >= obs[1]["observed_utc"]   # newest first
    assert _activity(journal, task_id)[-2:] == ["bluesky_metrics_observed", "bluesky_metrics_observed"]
    with sqlite3.connect(service.store.db) as con:              # append-only
        for sql in ("UPDATE promotion_observations SET likes=99", "DELETE FROM promotion_observations"):
            with pytest.raises(sqlite3.DatabaseError, match="append-only"):
                con.execute(sql)


def test_new_replies_are_detected_once_and_store_only_identifiers_and_timestamps(mon):
    extra, fake, _, journal, _, service, _ = mon
    task_id, a = _published(mon)
    extra.replies = ["3reply1aaaaaa"]
    assert service.bluesky_monitor(task_id, a["id"])["new_replies"] == 1
    assert service.bluesky_monitor(task_id, a["id"])["new_replies"] == 0          # duplicate: not new again
    extra.replies = ["3reply1aaaaaa", "3reply2aaaaaa", "3reply2aaaaaa"]          # duplicate within one response
    extra.extra_items = [reply("3otherparent1", "at://did:plc:" + "z" * 24 + "/app.bsky.feed.post/3x"),  # not direct
                         {"$type": "app.bsky.feed.defs#blockedPost", "uri": "at://blocked", "blocked": True}]
    assert service.bluesky_monitor(task_id, a["id"])["new_replies"] == 1
    replies = service.detail(task_id)["actions"][0]["bluesky"]["replies"]
    assert [r["reply_uri"].rsplit("/", 1)[1] for r in replies] == ["3reply2aaaaaa", "3reply1aaaaaa"]
    assert set(replies[0]) == {"reply_uri", "created_at", "indexed_at", "first_seen_utc", "url"}
    assert replies[0]["url"] == f"https://bsky.app/profile/{OTHER}/post/3reply2aaaaaa"
    with sqlite3.connect(service.store.db) as con:
        stored = json.dumps(con.execute("SELECT * FROM promotion_replies").fetchall())
    assert "someone.bsky.social" not in stored and "Some One" not in stored and "a reply" not in stored
    assert _activity(journal, task_id).count("bluesky_new_replies") == 2
    with sqlite3.connect(service.store.db) as con:              # append-only
        for sql in ("UPDATE promotion_replies SET reply_uri='x'", "DELETE FROM promotion_replies"):
            with pytest.raises(sqlite3.DatabaseError, match="append-only"):
                con.execute(sql)


@pytest.mark.parametrize("mode, outcome", [("deleted", "not_found"), ("cid_changed", "changed"),
                                           ("error_503", "unavailable"), ("redirect", "unavailable")])
def test_changed_deleted_or_unreadable_posts_are_recorded_without_corrupting_records(mon, mode, outcome):
    extra, fake, _, journal, _, service, _ = mon
    task_id, a = _published(mon)
    before = _row(service, a["id"])
    if mode == "deleted":
        fake.records.clear()
    elif mode == "cid_changed":
        extra.post_mode = "cid_changed"
    else:
        fake.appview_mode = mode
    res = service.bluesky_monitor(task_id, a["id"])
    assert res["outcome"] == outcome
    assert _row(service, a["id"]) == before and before["status"] == "bluesky_verified"
    obs = service.detail(task_id)["actions"][0]["bluesky"]["observations"][0]
    assert obs["outcome"] == outcome
    if outcome in ("not_found", "unavailable"):
        assert obs["likes"] is None and obs["replies_checked"] == 0


def test_reply_check_failure_keeps_the_counts(mon):
    extra, *_ = mon
    service = mon[5]
    task_id, a = _published(mon)
    extra.thread_mode = "error_503"
    res = service.bluesky_monitor(task_id, a["id"])
    assert res["outcome"] == "observed" and res["likes"] == 2 and res["replies_checked"] is False
    assert res["reason"] == "replies_http_503"
    obs = service.detail(task_id)["actions"][0]["bluesky"]["observations"][0]
    assert obs["replies_checked"] == 0 and obs["new_replies"] is None


def test_concurrent_refreshes_are_refused_not_duplicated(mon):
    extra, *_ = mon
    service = mon[5]
    task_id, a = _published(mon)
    extra.gate = threading.Event()
    results = []
    t1 = threading.Thread(target=lambda: results.append(service.bluesky_monitor(task_id, a["id"])))
    t1.start()
    import time
    for _ in range(50):          # wait until the first refresh holds the per-post lock
        if a["id"] in service._monitoring:
            break
        time.sleep(0.02)
    with pytest.raises(ToolError, match="already being refreshed"):
        service.bluesky_monitor(task_id, a["id"])
    extra.gate.set()
    t1.join(5)
    assert results[0]["outcome"] == "observed"
    assert len(service.detail(task_id)["actions"][0]["bluesky"]["observations"]) == 1
    assert a["id"] not in service._monitoring                 # lock released
    service.bluesky_monitor(task_id, a["id"])                 # a later refresh works again


def test_monitoring_uses_no_credentials_and_only_public_read_endpoints(mon):
    extra, fake, _, journal, _, service, tmp = mon
    task_id, a = _published(mon)
    service.bluesky_disconnect()                              # credentials removed: public reads still work
    assert not (tmp / "bluesky.dpapi").exists()
    fake.requests.clear()
    assert service.bluesky_monitor(task_id, a["id"])["outcome"] == "observed"
    seen = {(r.method, r.url.host, r.url.path) for r in fake.requests}
    assert seen == {("GET", "public.api.bsky.app", "/xrpc/app.bsky.feed.getPosts"),
                    ("GET", "public.api.bsky.app", "/xrpc/app.bsky.feed.getPostThread")}
    assert all("authorization" not in r.headers for r in fake.requests)
    assert fake.creates() == []


def test_only_published_posts_can_be_monitored(mon):
    service = mon[5]
    task_id, a = _approved(mon[1:])
    with pytest.raises(ToolError, match="Only a published Bluesky post"):
        service.bluesky_monitor(task_id, a["id"])


def test_improve_uses_real_bluesky_observations_and_never_acts(mon):
    extra, fake, _, journal, _, service, _ = mon
    task_id, a = _published(mon)
    extra.replies = ["3reply1aaaaaa"]
    service.bluesky_monitor(task_id, a["id"])
    model = FakeModel()
    text = service.improve(task_id, model)
    assert text
    sent = [i for i in model.inputs if i.startswith(pr.IMPROVE_INSTRUCTION)]
    payload = json.loads(sent[-1].split("\n", 1)[1])
    entry = payload["published"][0]
    assert entry["platform"] == "Bluesky" and entry["latest_metrics"]["likes"] == 2
    assert entry["observations"] == 1 and entry["public_replies_recorded"] == 1
    assert "does not reply, like, follow, repost or publish" in pr.IMPROVE_INSTRUCTION
    assert len(fake.creates()) == 1     # only the original publication; monitoring and Improve wrote nothing


def test_monitor_over_http(mon):
    extra, fake, _, journal, creds, service, _ = mon
    task_id, a = _published(mon)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, service), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("POST", f"/api/promotion/tasks/{task_id}/actions/{a['id']}/bluesky_monitor", body=b"{}",
                     headers={"Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
                              "Content-Type": "application/json", "X-App-Nonce": NONCE})
        r = conn.getresponse()
        data = json.loads(r.read())
        conn.close()
        assert r.status == 200 and data["outcome"] == "observed" and data["likes"] == 2
    finally:
        httpd.shutdown()
        httpd.server_close()
