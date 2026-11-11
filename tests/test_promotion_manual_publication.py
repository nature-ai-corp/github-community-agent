"""Reddit Promotion: Record Manual Publication.

The person posts the approved text by hand. The app records the post URL only after
URL validation, subreddit validation (the subreddit approved with the text), post-ID
extraction and an explicit confirmation -> "user-confirmed". It is "independently
verified" ONLY when one public, unauthenticated read of the post matches subreddit,
title and body and the post is not removed. Nothing is ever posted; a URL alone is
never success. Every step, refusal and check is in the Task's Activity History.
Offline: Reddit is a mock transport.
"""
from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from github_community_agent import promotion as pr
from github_community_agent import work_center as w
from github_community_agent.errors import ToolError

from test_promotion import NONCE, REPO_A, TOKEN_A, FakeModel, MemorySettings, env  # noqa: F401

POST_ID = "1abc2de"
URL = f"https://www.reddit.com/r/coolgithubprojects/comments/{POST_ID}/readonly_ai_assisted_issue_review/"


@pytest.fixture(autouse=True)
def _development_work_types(monkeypatch):
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")


class FakeReddit:
    """Public by_id endpoint only. Records every request so tests can prove nothing else is sent."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.post = None          # dict for the t3 data, or None (no such post)
        self.status = 200
        self.raise_error = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.raise_error:
            raise httpx.ConnectError("blocked", request=request)
        if self.status != 200:
            return httpx.Response(self.status, text="blocked")
        children = [{"kind": "t3", "data": self.post}] if self.post else []
        return httpx.Response(200, json={"kind": "Listing", "data": {"children": children}})


@pytest.fixture
def reddit(monkeypatch):
    fake = FakeReddit()
    monkeypatch.setattr(pr, "_reddit_transport", httpx.MockTransport(fake.handler))
    return fake


def _approved(service, creds, subreddit="r/coolgithubprojects"):
    creds.update(REPO_A, TOKEN_A)
    task_id = service.start(FakeModel(TOKEN_A), "promote_reddit")
    a = service.detail(task_id)["actions"][0]
    approved = service.approve(task_id, a["id"], subreddit, a["draft_sha256"])
    return task_id, service.detail(task_id)["actions"][0], approved


def _live_post(a, **over):
    post = {"id": POST_ID, "subreddit": "coolgithubprojects", "author": "someone", "removed_by_category": None,
            "title": a["title"], "selftext": a["body"], "score": 5, "num_comments": 2, "locked": False}
    post.update(over)
    return post


def _activity(journal, task_id):
    task = next(t for t in journal.list() if t["id"] == task_id)
    return [e["event"] for e in task["activity"] if e["event"].startswith("action#")]


# -- URL and subreddit validation ------------------------------------------------------------


@pytest.mark.parametrize("url", [
    URL,
    f"https://reddit.com/r/coolgithubprojects/comments/{POST_ID}/",
    f"https://old.reddit.com/r/coolgithubprojects/comments/{POST_ID}/x/?utm_source=share#top",
    f"https://www.reddit.com/r/coolgithubprojects/comments/{POST_ID}",
])
def test_post_url_is_parsed_to_subreddit_and_post_id(url):
    assert pr.parse_reddit_post_url(url) == {
        "subreddit": "coolgithubprojects", "post_id": POST_ID,
        "url": f"https://www.reddit.com/r/coolgithubprojects/comments/{POST_ID}/"}


@pytest.mark.parametrize("url,code", [
    ("", "url_invalid"), (None, "url_invalid"), ("x" * 600, "url_invalid"),
    (URL.replace("https://", "http://"), "url_invalid"),
    (f"https://www.reddit.com.evil.example/r/coolgithubprojects/comments/{POST_ID}/", "url_invalid"),
    (f"https://evil.example/https://www.reddit.com/r/coolgithubprojects/comments/{POST_ID}/", "url_invalid"),
    (f"https://www.reddit.com/r/coolgithubprojects/comments/{POST_ID}/slug/kx9z2a1/", "url_invalid"),  # a comment
    (f"https://www.reddit.com/user/someone/comments/{POST_ID}/", "url_invalid"),
    ("https://www.reddit.com/r/coolgithubprojects/", "url_invalid"),
    (f"https://redd.it/{POST_ID}", "url_share_link"),
    ("https://www.reddit.com/r/coolgithubprojects/s/AbCdEf123", "url_share_link"),
])
def test_invalid_or_ambiguous_urls_are_refused(url, code):
    with pytest.raises(pr.ChangeRefused) as exc:
        pr.parse_reddit_post_url(url)
    assert exc.value.code == code


def test_reddit_text_comparison_ignores_escaping_line_endings_and_trailing_spaces():
    assert pr._reddit_text("A &amp; B &lt;x&gt;  \r\nC\n") == "A & B <x>\nC"
    assert pr._reddit_text(None) == ""


def test_subreddit_names_are_normalized_or_refused():
    for value in ("r/coolgithubprojects", "/r/coolgithubprojects/", "coolgithubprojects", " R/coolgithubprojects "):
        assert pr.normalize_subreddit(value) == "coolgithubprojects"
    for value in ("", None, "r/", "r/a", "r/has space", "r/x/../y", "https://evil.example/r/x", "r/" + "a" * 30):
        with pytest.raises(pr.ChangeRefused):
            pr.normalize_subreddit(value)


# -- approval binds the subreddit (separate from recording) ---------------------------------


def test_reddit_approval_requires_and_binds_the_subreddit(env):
    _, _, creds, service, _ = env
    creds.update(REPO_A)
    task_id = service.start(FakeModel(), "promote_reddit")
    a = service.detail(task_id)["actions"][0]
    with pytest.raises(ToolError, match="target subreddit"):
        service.approve(task_id, a["id"], "", a["draft_sha256"])
    approved = service.approve(task_id, a["id"], "r/coolgithubprojects", a["draft_sha256"])
    ready = service.detail(task_id)["actions"][0]
    assert ready["status"] == "ready_manual" and ready["category"] == "coolgithubprojects"
    assert approved == pr.content_sha256(REPO_A, "coolgithubprojects", a["title"], a["body"], "reddit")
    assert approved != pr.content_sha256(REPO_A, "", a["title"], a["body"], "reddit")
    # Approval alone records no publication.
    assert ready["published_url"] is None and ready["post_id"] is None and ready["verification"] is None


def test_other_manual_work_types_still_have_no_destination_field(env):
    _, _, creds, service, _ = env
    creds.update(REPO_A)
    task_id = service.start(FakeModel(), "promote_developer_forums")
    a = service.detail(task_id)["actions"][0]
    with pytest.raises(ToolError, match="no Discussion category"):
        service.approve(task_id, a["id"], "r/coolgithubprojects", a["draft_sha256"])
    with pytest.raises(ToolError, match="Reddit Promotion only"):
        service.record_manual_publication(task_id, a["id"], URL, True, "x")


# -- recording: user-confirmed ---------------------------------------------------------------


def test_record_requires_url_subreddit_and_confirmation_then_is_user_confirmed(env, reddit):
    fake_gh, journal, creds, service, _ = env
    task_id, a, approved = _approved(service, creds)
    refusals = [
        (dict(url="https://redd.it/" + POST_ID, confirmed=True, sha=approved), "url_share_link"),
        (dict(url=URL.replace("coolgithubprojects", "programming"), confirmed=True, sha=approved),
         "subreddit_mismatch"),
        (dict(url=URL, confirmed=False, sha=approved), "not_confirmed"),
        (dict(url=URL, confirmed="yes", sha=approved), "not_confirmed"),
        (dict(url=URL, confirmed=True, sha="0" * 64), "approval_mismatch"),
    ]
    for kwargs, code in refusals:
        with pytest.raises(pr.ChangeRefused) as exc:
            service.record_manual_publication(task_id, a["id"], kwargs["url"], kwargs["confirmed"], kwargs["sha"])
        assert exc.value.code == code
        assert service.detail(task_id)["actions"][0]["status"] == "ready_manual"
    out = service.record_manual_publication(task_id, a["id"], URL + "?utm_source=share", True, approved)
    assert out == {"status": "published_user_confirmed", "verified": False, "post_id": POST_ID,
                   "subreddit": "coolgithubprojects",
                   "url": f"https://www.reddit.com/r/coolgithubprojects/comments/{POST_ID}/"}
    rec = service.detail(task_id)["actions"][0]
    assert rec["status"] == "published_user_confirmed" and rec["post_id"] == POST_ID
    assert rec["verification"] is None  # NOT verified by recording
    with pytest.raises(pr.ChangeRefused) as exc:
        service.record_manual_publication(task_id, a["id"], URL, True, approved)
    assert exc.value.code == "already_recorded"
    # Persistent Task Activity History: approval, every refusal, the record.
    assert _activity(journal, task_id) == [
        f"action#{a['id']}:approved_manual",
        f"action#{a['id']}:manual_record_refused:url_share_link",
        f"action#{a['id']}:manual_record_refused:subreddit_mismatch",
        f"action#{a['id']}:manual_record_refused:not_confirmed",
        f"action#{a['id']}:manual_record_refused:not_confirmed",
        f"action#{a['id']}:manual_record_refused:approval_mismatch",
        f"action#{a['id']}:manual_recorded_user_confirmed",
        f"action#{a['id']}:manual_record_refused:already_recorded"]
    # Recording never contacts Reddit or GitHub-with-token and never posts.
    assert reddit.requests == [] and fake_gh.mutations == [] and all(t == "" for _, _, t in fake_gh.requests)


def test_record_needs_an_approval_and_an_edit_cancels_it(env, reddit):
    _, _, creds, service, _ = env
    creds.update(REPO_A)
    task_id = service.start(FakeModel(), "promote_reddit")
    a = service.detail(task_id)["actions"][0]
    with pytest.raises(pr.ChangeRefused) as exc:
        service.record_manual_publication(task_id, a["id"], URL, True, a["draft_sha256"])
    assert exc.value.code == "not_approved"
    approved = service.approve(task_id, a["id"], "coolgithubprojects", a["draft_sha256"])
    service.edit(task_id, a["id"], a["title"], a["body"] + " Edited.")
    with pytest.raises(pr.ChangeRefused) as exc:
        service.record_manual_publication(task_id, a["id"], URL, True, approved)
    assert exc.value.code == "not_approved"


def test_the_same_post_cannot_be_recorded_for_two_drafts(env, reddit):
    _, _, creds, service, _ = env
    t1, a1, s1 = _approved(service, creds)
    t2, a2, s2 = _approved(service, creds)
    service.record_manual_publication(t1, a1["id"], URL, True, s1)
    with pytest.raises(pr.ChangeRefused) as exc:
        service.record_manual_publication(t2, a2["id"], URL, True, s2)
    assert exc.value.code == "duplicate_post"


def test_a_recorded_publication_can_no_longer_be_edited_or_regenerated(env, reddit):
    _, _, creds, service, _ = env
    task_id, a, approved = _approved(service, creds)
    service.record_manual_publication(task_id, a["id"], URL, True, approved)
    with pytest.raises(ToolError, match="can be edited"):
        service.edit(task_id, a["id"], "Other", "I maintain it. Other.")
    with pytest.raises(ToolError, match="unapproved draft"):
        service.regenerate(task_id, a["id"], FakeModel())


# -- independent verification ----------------------------------------------------------------


def _recorded(env, reddit):
    fake_gh, journal, creds, service, _ = env
    task_id, a, approved = _approved(service, creds)
    service.record_manual_publication(task_id, a["id"], URL, True, approved)
    return journal, service, task_id, a


def test_verified_only_when_subreddit_title_and_body_match(env, reddit):
    journal, service, task_id, a = _recorded(env, reddit)
    # Reddit returns HTML-escaped text and may differ in line endings / trailing spaces.
    reddit.post = _live_post(a, title=a["title"].replace("&", "&amp;"),
                             selftext=a["body"].replace("\n", "  \r\n") + "\n")
    out = service.verify_manual_publication(task_id, a["id"])
    assert out["verified"] is True and out["outcome"] == "verified" and out["status"] == "published_verified"
    rec = service.detail(task_id)["actions"][0]
    assert rec["status"] == "published_verified"
    assert rec["verification"]["outcome"] == "verified" and rec["verification"]["score"] == 5
    assert all(rec["verification"]["checks"].values())
    # Exactly one public GET of the fixed endpoint; no credentials, cookies or writes.
    [req] = reddit.requests
    assert req.method == "GET" and str(req.url) == f"https://www.reddit.com/by_id/t3_{POST_ID}.json"
    assert "authorization" not in req.headers and "cookie" not in req.headers
    assert _activity(journal, task_id)[-1] == f"action#{a['id']}:manual_verified"


@pytest.mark.parametrize("change,outcome,failed", [
    (dict(selftext="I maintain it. A different body."), "mismatch", "body"),
    (dict(title="A different title"), "mismatch", "title"),
    (dict(subreddit="programming"), "mismatch", "subreddit"),
    (dict(removed_by_category="moderator"), "removed", "not_removed"),
    (dict(selftext="[removed]"), "removed", "not_removed"),
])
def test_differences_or_removal_are_not_verified(env, reddit, change, outcome, failed):
    journal, service, task_id, a = _recorded(env, reddit)
    reddit.post = _live_post(a, **change)
    out = service.verify_manual_publication(task_id, a["id"])
    assert out["verified"] is False and out["outcome"] == outcome and out["checks"][failed] is False
    assert service.detail(task_id)["actions"][0]["status"] == "published_user_confirmed"
    assert _activity(journal, task_id)[-1] == f"action#{a['id']}:manual_verify_failed:{outcome}"


def test_post_not_found_is_not_verified(env, reddit):
    _, service, task_id, a = _recorded(env, reddit)
    reddit.post = None
    out = service.verify_manual_publication(task_id, a["id"])
    assert out["verified"] is False and out["outcome"] == "not_found"


@pytest.mark.parametrize("status,error,code", [(403, False, "unavailable_http_403"),
                                               (429, False, "unavailable_http_429"),
                                               (200, True, "unavailable_network")])
def test_unreadable_reddit_never_upgrades_the_record(env, reddit, status, error, code):
    journal, service, task_id, a = _recorded(env, reddit)
    reddit.status, reddit.raise_error = status, error
    out = service.verify_manual_publication(task_id, a["id"])
    assert out["verified"] is False and out["outcome"] == "unavailable"
    rec = service.detail(task_id)["actions"][0]
    assert rec["status"] == "published_user_confirmed"
    assert rec["verification"]["outcome"] == "unavailable" and rec["verification"]["reason"] == code
    assert _activity(journal, task_id)[-1] == f"action#{a['id']}:manual_verify_unavailable:{code}"


def test_a_later_failed_check_withdraws_verified_but_unreadable_keeps_it(env, reddit):
    _, service, task_id, a = _recorded(env, reddit)
    reddit.post = _live_post(a)
    assert service.verify_manual_publication(task_id, a["id"])["verified"] is True
    reddit.status = 503
    assert service.verify_manual_publication(task_id, a["id"])["status"] == "published_verified"
    reddit.status = 200
    reddit.post = _live_post(a, removed_by_category="moderator")
    out = service.verify_manual_publication(task_id, a["id"])
    assert out["status"] == "published_user_confirmed" and out["verified"] is False


def test_verify_before_recording_is_refused_and_logged(env, reddit):
    _, journal, creds, service, _ = env
    task_id, a, _ = _approved(service, creds)
    with pytest.raises(ToolError, match="Record the Reddit post URL first"):
        service.verify_manual_publication(task_id, a["id"])
    assert reddit.requests == []
    assert _activity(journal, task_id)[-1] == f"action#{a['id']}:manual_verify_refused:not_recorded"


# -- release gate and HTTP routes ------------------------------------------------------------


def test_reddit_is_still_not_released_and_recording_is_gated(env, reddit, monkeypatch):
    _, _, creds, service, _ = env
    task_id, a, approved = _approved(service, creds)
    assert "promote_reddit" not in pr.RELEASE_VERIFIED_WORK_TYPES
    monkeypatch.setattr(pr.sys, "frozen", True, raising=False)  # packaged build ignores the dev switch
    with pytest.raises(ToolError):
        service.record_manual_publication(task_id, a["id"], URL, True, approved)
    with pytest.raises(ToolError):
        service.verify_manual_publication(task_id, a["id"])
    assert reddit.requests == []


def test_record_and_verify_over_http(env, reddit):
    _, journal, creds, service, _ = env
    task_id, a, approved = _approved(service, creds)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, service), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port

    def post(verb, body, nonce=NONCE):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("POST", f"/api/promotion/tasks/{task_id}/actions/{a['id']}/{verb}",
                     body=json.dumps(body).encode(), headers={
                         "Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
                         "Content-Type": "application/json", "X-App-Nonce": nonce})
        r = conn.getresponse()
        data = json.loads(r.read().decode() or "{}")
        conn.close()
        return r.status, data
    try:
        assert post("record_publication", {"url": URL, "confirmed": True, "sha256": approved}, "bad")[0] == 403
        status, data = post("record_publication", {"url": URL, "confirmed": True,
                                                   "sha256": approved})
        assert status == 200 and data["status"] == "published_user_confirmed" and data["verified"] is False
        reddit.post = _live_post(a)
        status, data = post("verify_publication", {})
        assert status == 200 and data["verified"] is True
        status, data = post("record_publication", {"url": URL, "confirmed": True, "sha256": approved})
        assert status == 400 and "already recorded" in data["error"]
    finally:
        httpd.shutdown()
        httpd.server_close()
