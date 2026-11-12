"""Bluesky Work Type (released after Task #22): one exact, approved post; verified read-back.

Offline: a mock of the bsky.social entryway, the account's PDS and the public AppView.
Covers Lexicon text limits (graphemes, UTF-8 bytes), link facets with UTF-8 byte offsets,
isolated DPAPI credentials (app passwords only), exact-action approval bound to the account
DID, text and facets, ONE createRecord with a durable outbox, uncertain-outcome
reconciliation without blind retries, independent verification, Activity History,
credential-leak checks and the platform release gate.
"""
from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from github_community_agent import bluesky as bs
from github_community_agent import promotion as pr
from github_community_agent import work_center as w
from github_community_agent.encrypted_settings import SettingsError
from github_community_agent.errors import ToolError

from test_promotion import NONCE, REPO_A, TOKEN_A, FakeModel, MemorySettings, env  # noqa: F401

HANDLE = "natureai-project.bsky.social"
APP_PW = "abcd-efgh-ijkl-mnop"
DID_A = "did:plc:" + "a" * 24
DID_B = "did:plc:" + "b" * 24
PDS = "https://amanita.us-east.host.bsky.network"
JWT = "eyJ.access-token-not-real.sig"
LINK = "https://github.com/nature-ai-corp/github-community-agent"


class FakeBluesky:
    def __init__(self):
        self.did = DID_A
        self.pds = PDS
        self.records: dict[str, dict] = {}
        self.requests: list[httpx.Request] = []
        self.create_mode = "ok"   # ok | timeout_after | connect_error | error_400 | error_500_before
        self.appview_mode = "ok"  # ok | unindexed | tamper | error_503 | redirect

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url, path = request.url, request.url.path
        origin = f"{url.scheme}://{url.host}"
        body = json.loads(request.content) if request.content else {}
        if origin == bs.ENTRYWAY and path == "/xrpc/com.atproto.server.createSession":
            if body != {"identifier": HANDLE, "password": APP_PW}:
                return httpx.Response(401, json={"error": "AuthenticationRequired", "message": "Invalid"})
            return httpx.Response(200, json={
                "did": self.did, "handle": HANDLE, "accessJwt": JWT, "refreshJwt": "refresh", "active": True,
                "email": "not-stored@example.invalid",
                "didDoc": {"id": self.did, "service": [{"id": "#atproto_pds", "type": "AtprotoPersonalDataServer",
                                                          "serviceEndpoint": self.pds}]}})
        if origin == PDS and path == "/xrpc/com.atproto.repo.createRecord":
            assert request.method == "POST"
            if request.headers.get("authorization") != f"Bearer {JWT}":
                return httpx.Response(401, json={"error": "AuthenticationRequired"})
            if self.create_mode == "connect_error":
                raise httpx.ConnectError("refused", request=request)
            if self.create_mode == "error_400":
                return httpx.Response(400, json={"error": "InvalidRequest", "message": "bad record"})
            if self.create_mode == "error_500_before":
                return httpx.Response(500, json={"error": "InternalServerError"})
            assert body["repo"] == self.did and body["collection"] == bs.COLLECTION and body["validate"] is True
            uri = f"at://{self.did}/{bs.COLLECTION}/{body['rkey']}"
            cid = "bafyrei" + "c" * 52
            self.records[body["rkey"]] = {"uri": uri, "cid": cid, "value": body["record"]}
            if self.create_mode == "timeout_after":
                raise httpx.ReadTimeout("timed out", request=request)
            return httpx.Response(200, json={"uri": uri, "cid": cid, "validationStatus": "valid"})
        if origin == PDS and path == "/xrpc/com.atproto.repo.getRecord":
            assert "authorization" not in request.headers
            rec = self.records.get(url.params["rkey"])
            if not rec:
                return httpx.Response(400, json={"error": "RecordNotFound", "message": "Could not locate record"})
            return httpx.Response(200, json=rec)
        if origin == bs.APPVIEW and path == "/xrpc/app.bsky.feed.getPosts":
            assert "authorization" not in request.headers
            if self.appview_mode == "error_503":
                return httpx.Response(503, json={})
            if self.appview_mode == "redirect":
                return httpx.Response(302, headers={"location": "https://evil.example/"})
            uri = url.params["uris"]
            rec = next((r for r in self.records.values() if r["uri"] == uri), None)
            if not rec or self.appview_mode == "unindexed":
                return httpx.Response(200, json={"posts": []})
            value = dict(rec["value"])
            if self.appview_mode == "tamper":
                value["text"] = value["text"] + " (edited)"
            return httpx.Response(200, json={"posts": [{
                "uri": uri, "cid": rec["cid"], "author": {"did": self.did, "handle": HANDLE}, "record": value,
                "likeCount": 2, "replyCount": 1, "repostCount": 0, "quoteCount": 0,
                "indexedAt": "2026-11-11T16:00:00.000Z"}]})
        return httpx.Response(404, json={"error": "unexpected", "path": path})

    def creates(self):
        return [r for r in self.requests if r.url.path.endswith("createRecord")]


@pytest.fixture(autouse=True)
def _development(monkeypatch):
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")


@pytest.fixture
def sky(env, monkeypatch):
    fake_gh, journal, creds, service, tmp = env
    fake = FakeBluesky()
    monkeypatch.setattr(bs, "_transport", httpx.MockTransport(fake.handler))
    monkeypatch.setattr(bs.sys, "platform", "win32")
    monkeypatch.setattr(bs, "protect_for_current_user", lambda b: b"ENC_" + b[::-1])
    monkeypatch.setattr(bs, "unprotect_for_current_user", lambda b: b[len(b"ENC_"):][::-1])
    monkeypatch.setattr(pr, "RECONCILE_WAIT_SECONDS", 0)
    service.bluesky = bs.BlueskyCredentials(tmp)
    return fake, fake_gh, journal, creds, service, tmp


def _task(service, creds, short=f"I maintain GitHub Community Agent: v1.0.0-rc1 is out. {LINK}"):
    creds.update(REPO_A, TOKEN_A)
    task_id = service.start(FakeModel(TOKEN_A), "promote_bluesky")
    a = service.detail(task_id)["actions"][0]
    service.edit(task_id, a["id"], a["title"], short)  # the Bluesky Work Type's body IS the post
    return task_id, service.detail(task_id)["actions"][0]


def _connected(sky):
    fake, fake_gh, journal, creds, service, tmp = sky
    service.bluesky_connect(HANDLE, APP_PW)
    return service


def _activity(journal, task_id):
    task = next(t for t in journal.list() if t["id"] == task_id)
    return [e["event"].split(":", 1)[1] for e in task["activity"] if e["event"].startswith("action#")]


# -- Lexicon text rules ------------------------------------------------------------------------


@pytest.mark.parametrize("text,count", [
    ("", 0), ("abc", 3), ("é", 1), ("é", 1), ("\r\n", 1), ("a\r\nb", 3),
    ("\U0001F468‍\U0001F469‍\U0001F467", 1),                # family ZWJ sequence
    ("\U0001F44D\U0001F3FD", 1),                                      # skin-tone modifier
    ("\U0001F1FA\U0001F1F8", 1), ("\U0001F1FA\U0001F1F8\U0001F1E9", 2),  # flags: RI pairs
    ("❤️", 1),                                              # variation selector
    ("각", 1), ("각", 1), ("한국어", 3),  # Hangul
    ("\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F", 1),  # tag sequence
    ("a‍b", 2),                                                  # ZWJ not between pictographs
    ("कि", 1),                                              # Devanagari + spacing mark
])
def test_grapheme_count_follows_uax29_clusters(text, count):
    assert bs.grapheme_count(text) == count


def test_text_limits_use_graphemes_and_utf8_bytes():
    assert bs.text_issues("x" * 300) == []
    assert "301 characters" in bs.text_issues("x" * 301)[0]
    family = "\U0001F468‍\U0001F469‍\U0001F467"   # 1 grapheme, 18 bytes
    assert bs.grapheme_count(family * 166) == 166 and len((family * 166).encode()) == 2988
    assert bs.text_issues(family * 166) == []
    issues = bs.text_issues(family * 167)                      # 167 graphemes but 3006 bytes
    assert len(issues) == 1 and "3006 bytes" in issues[0]
    assert bs.text_issues("é" * 300) == []               # 600 code points, 300 graphemes
    assert bs.text_issues("   ") and bs.text_issues("a\x00")


def test_link_facets_use_utf8_byte_offsets():
    text = f"Café ✓ \U0001F680 {LINK}. More: (see {LINK}/releases) http://insecure.example x"
    facets = bs.link_facets(text)
    assert [f["features"][0]["uri"] for f in facets] == [LINK, LINK + "/releases"]
    raw = text.encode("utf-8")
    for f in facets:
        i = f["index"]
        assert raw[i["byteStart"]:i["byteEnd"]].decode() == f["features"][0]["uri"]
        assert f["features"][0]["$type"] == "app.bsky.richtext.facet#link"
    assert facets[0]["index"]["byteStart"] == len("Café ✓ \U0001F680 ".encode())  # 14, not 9 chars
    assert bs.link_facets("no links, http://example.com only") == []
    assert bs.link_facets("https://en.wikipedia.org/wiki/Foo_(bar)")[0]["features"][0]["uri"].endswith("(bar)")


TID = __import__("re").compile(r"^[234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12}$")  # AT Protocol spec


def _tid_value(key):
    return int("".join(f"{'234567abcdefghijklmnopqrstuvwxyz'.index(c):05b}" for c in key), 2)


def _clock(monkeypatch, *micros):
    """Replace bluesky.py's clock (only its own reference) with fixed microsecond readings."""
    from types import SimpleNamespace
    readings = iter(micros)
    last = [micros[0]]

    def time_ns():
        last[0] = next(readings, last[0])
        return last[0] * 1000
    monkeypatch.setattr(bs, "time", SimpleNamespace(time_ns=time_ns))
    monkeypatch.setattr(bs, "_tid_last_us", 0)


def test_record_keys_are_valid_unique_increasing_tids():
    keys = [bs.new_rkey() for _ in range(2000)]
    assert len(set(keys)) == 2000 and keys == sorted(keys)
    assert all(TID.fullmatch(k) and bs.RKEY.fullmatch(k) for k in keys)
    value = _tid_value(keys[0])
    assert value >> 63 == 0                                     # top bit is zero
    assert abs((value >> 10) / 1e6 - __import__("time").time()) < 60  # microseconds since the epoch
    assert len({_tid_value(k) & 1023 for k in keys}) == 1        # one clock identifier per process


def test_record_keys_stay_unique_and_ordered_with_a_frozen_clock(monkeypatch):
    _clock(monkeypatch, 1_762_900_000_000_000)                  # the clock never advances
    keys = [bs.new_rkey() for _ in range(500)]
    assert len(set(keys)) == 500 and keys == sorted(keys) and all(TID.fullmatch(k) for k in keys)
    assert [_tid_value(k) >> 10 for k in keys[:3]] == [1_762_900_000_000_000 + i for i in range(3)]


def test_record_keys_never_go_backwards_when_the_clock_does(monkeypatch):
    now = 1_762_900_000_000_000
    _clock(monkeypatch, now, now + 10, now - 5_000_000, now - 5_000_000, now + 20, now + 11)
    keys = [bs.new_rkey() for _ in range(6)]
    assert keys == sorted(keys) and len(set(keys)) == 6
    assert [_tid_value(k) >> 10 for k in keys] == [now, now + 10, now + 11, now + 12, now + 20, now + 21]


def test_record_keys_are_unique_across_threads():
    keys, lock = [], threading.Lock()

    def make():
        mine = [bs.new_rkey() for _ in range(300)]
        with lock:
            keys.extend(mine)
    threads = [threading.Thread(target=make) for _ in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert len(set(keys)) == 1200


def test_record_key_refuses_an_out_of_range_clock(monkeypatch):
    _clock(monkeypatch, 1 << 53)
    with pytest.raises(bs.BlueskyError) as exc:
        bs.new_rkey()
    assert exc.value.code == "clock"


# -- isolated credentials ---------------------------------------------------------------------


def test_connect_accepts_only_app_passwords_and_stores_them_separately(sky):
    fake, _, _, creds, service, tmp = sky
    creds.update(REPO_A, TOKEN_A)
    github_file = (tmp / "promotion.dpapi").read_bytes()
    for bad in ("my-account-password", "abcd-efgh-ijkl", ""):
        with pytest.raises(SettingsError, match="APP password"):
            service.bluesky_connect(HANDLE, bad)
    with pytest.raises(SettingsError, match="handle"):
        service.bluesky_connect("not a handle", APP_PW)
    assert fake.requests == []  # refused before any network call
    out = service.bluesky_connect("@" + HANDLE.upper(), APP_PW.upper())
    assert out == {"available": True, "connected": True, "handle": HANDLE, "did": DID_A}
    stored = (tmp / "bluesky.dpapi").read_bytes()
    assert stored.startswith(b"ENC_") and APP_PW.encode() not in stored and JWT.encode() not in stored
    plain = json.loads(bs.unprotect_for_current_user(stored))
    assert set(plain) == {"handle", "did", "pds", "app_password"}  # no access token, no e-mail
    assert (tmp / "promotion.dpapi").read_bytes() == github_file  # GitHub tokens untouched
    assert APP_PW not in json.dumps(service.bluesky_account())
    assert service.bluesky_disconnect() == {"available": True, "connected": False}
    assert not (tmp / "bluesky.dpapi").exists()


def test_wrong_app_password_and_non_bluesky_hosting_are_refused(sky):
    fake, _, _, _, service, tmp = sky
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_connect(HANDLE, "zzzz-zzzz-zzzz-zzzz")
    assert exc.value.code == "authenticationrequired" and APP_PW not in str(exc.value)
    fake.pds = "https://pds.self-hosted.example"
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_connect(HANDLE, APP_PW)
    assert exc.value.code == "pds_not_allowed" and not (tmp / "bluesky.dpapi").exists()


# -- approval -----------------------------------------------------------------------------------


def test_approval_binds_account_did_text_and_facets(sky):
    fake, _, journal, creds, service, _ = sky
    task_id, a = _task(service, creds)
    assert a["bluesky"]["approval_sha256"] is None  # no account yet
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_approve(task_id, a["id"], "0" * 64)
    assert exc.value.code == "no_account"
    _connected(sky)
    a = service.detail(task_id)["actions"][0]
    b = a["bluesky"]
    assert b["text"].endswith(LINK) and len(b["facets"]) == 1 and b["account_did"] == DID_A
    assert b["approval_sha256"] == bs.approval_sha256(REPO_A, DID_A, b["text"], b["facets"])
    assert bs.approval_sha256(REPO_A, DID_B, b["text"], b["facets"]) != b["approval_sha256"]
    assert bs.approval_sha256(REPO_A, DID_A, b["text"], []) != b["approval_sha256"]
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_approve(task_id, a["id"], bs.approval_sha256(REPO_A, DID_B, b["text"], b["facets"]))
    assert exc.value.code == "approval_mismatch"
    out = service.bluesky_approve(task_id, a["id"], b["approval_sha256"])
    assert out["did"] == DID_A and out["status"] == "bluesky_approved"
    ready = service.detail(task_id)["actions"][0]
    assert ready["status"] == "bluesky_approved" and ready["category"] == "bluesky:" + DID_A
    assert ready["bluesky"]["approved_did"] == DID_A and fake.creates() == []  # approval sends nothing
    # Any edit cancels the approval.
    service.edit(task_id, a["id"], a["title"], a["body"].replace("is out", "is available"))
    assert service.detail(task_id)["actions"][0]["status"] == "draft"
    assert _activity(journal, task_id) == ["bluesky_approve_refused:no_account",
                                           "bluesky_approve_refused:approval_mismatch", "bluesky_approved"]


def test_text_over_the_lexicon_limit_cannot_be_approved(sky, monkeypatch):
    _, _, _, creds, service, _ = sky
    _connected(sky)
    long = "I maintain GitHub Community Agent. " + "é́" * 270  # 305 graphemes
    task_id, a = _task(service, creds, short=long)
    b = a["bluesky"]
    assert b["issues"] and b["approval_sha256"] is None
    sha = bs.approval_sha256(REPO_A, DID_A, b["text"], b["facets"])
    # Layer 1: the Bluesky Work Type's draft check (Lexicon limits) already marks it incomplete.
    assert a["status"] == "incomplete" and "Bluesky allows 300" in (a["error"] or "")
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_approve(task_id, a["id"], sha)
    assert exc.value.code == "state"
    # Layer 2: the Bluesky Lexicon check refuses on its own, even if the draft checks passed.
    service.store._transition(a["id"], task_id, ("incomplete",), "test", status="draft", error=None)
    monkeypatch.setattr(pr, "check_draft", lambda *args: [])
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_approve(task_id, a["id"], sha)
    assert exc.value.code == "text_limits"


# -- publish, outbox, verification ------------------------------------------------------------


def _approved(sky, **kw):
    fake, fake_gh, journal, creds, service, _ = sky
    _connected(sky)
    task_id, a = _task(service, creds, **kw)
    service.bluesky_approve(task_id, a["id"], a["bluesky"]["approval_sha256"])
    return task_id, service.detail(task_id)["actions"][0]


def test_publish_creates_exactly_one_record_and_verify_reads_it_back(sky):
    fake, fake_gh, journal, creds, service, _ = sky
    task_id, a = _approved(sky)
    out = service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    [create] = fake.creates()
    body = json.loads(create.content)
    rkey = body["rkey"]
    assert bs.RKEY.fullmatch(rkey) and body["record"]["text"] == a["bluesky"]["text"]
    assert body["record"]["facets"] == a["bluesky"]["facets"] and body["record"]["langs"] == ["en"]
    assert body["record"]["$type"] == bs.COLLECTION and body["record"]["createdAt"].endswith("Z")
    uri = f"at://{DID_A}/{bs.COLLECTION}/{rkey}"
    assert out == {"status": "bluesky_published", "uri": uri, "cid": "bafyrei" + "c" * 52,
                   "url": f"https://bsky.app/profile/{DID_A}/post/{rkey}", "verified": False}
    rec = service.detail(task_id)["actions"][0]
    assert rec["status"] == "bluesky_published" and rec["bluesky"]["uri"] == uri
    assert rec["bluesky"]["cid"] == out["cid"] and rec["bluesky"]["url"] == out["url"]
    with pytest.raises(bs.BlueskyError) as exc:  # never a second post
        service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    assert exc.value.code == "already_published" and len(fake.creates()) == 1
    v = service.bluesky_verify(task_id, a["id"])
    assert v["verified"] is True and v["outcome"] == "verified" and all(v["checks"].values())
    rec = service.detail(task_id)["actions"][0]
    assert rec["status"] == "bluesky_verified" and rec["verification"]["likeCount"] == 2
    assert _activity(journal, task_id) == ["bluesky_approved", "bluesky_publish_requested", "bluesky_published",
                                           "bluesky_publish_refused:already_published", "bluesky_verified"]
    # Hosts: entryway (login), the account's PDS (write), public AppView (read). Nothing else.
    hosts = {(r.url.host, r.url.path) for r in fake.requests}
    assert hosts <= {("bsky.social", "/xrpc/com.atproto.server.createSession"),
                     ("amanita.us-east.host.bsky.network", "/xrpc/com.atproto.repo.createRecord"),
                     ("public.api.bsky.app", "/xrpc/app.bsky.feed.getPosts")}
    assert fake_gh.mutations == []


def test_publish_refuses_another_account_or_a_changed_action(sky):
    fake, _, journal, creds, service, _ = sky
    task_id, a = _approved(sky)
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_publish(task_id, a["id"], "0" * 64)
    assert exc.value.code == "approval_mismatch"
    fake.did = DID_B  # the stored credentials now log in to a different account
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    assert exc.value.code == "account_mismatch"
    assert fake.creates() == [] and service.detail(task_id)["actions"][0]["status"] == "bluesky_approved"


def test_uncertain_outcome_is_reconciled_by_the_outbox_record_never_retried(sky):
    fake, _, journal, creds, service, _ = sky
    task_id, a = _approved(sky)
    fake.create_mode = "timeout_after"  # created on Bluesky, but the answer was lost
    assert service.bluesky_publish(task_id, a["id"], a["approved_sha256"])["status"] == "bluesky_uncertain"
    for call in (lambda: service.bluesky_publish(task_id, a["id"], a["approved_sha256"]),
                 lambda: service.bluesky_approve(task_id, a["id"], a["bluesky"]["approval_sha256"])):
        with pytest.raises(bs.BlueskyError):
            call()
    with pytest.raises(ToolError, match="can be edited"):
        service.edit(task_id, a["id"], a["title"], a["body"])
    assert len(fake.creates()) == 1
    out = service.bluesky_reconcile(task_id, a["id"])
    assert out["status"] == "bluesky_published" and out["cid"] == "bafyrei" + "c" * 52
    assert service.bluesky_verify(task_id, a["id"])["verified"] is True
    assert len(fake.creates()) == 1
    assert "bluesky_reconciled_published" in _activity(journal, task_id)


def test_uncertain_outcome_not_created_becomes_retryable(sky):
    fake, _, journal, creds, service, _ = sky
    task_id, a = _approved(sky)
    fake.create_mode = "error_500_before"
    assert service.bluesky_publish(task_id, a["id"], a["approved_sha256"])["status"] == "bluesky_uncertain"
    assert service.bluesky_reconcile(task_id, a["id"]) == {"status": "bluesky_failed"}
    rec = service.detail(task_id)["actions"][0]
    assert rec["status"] == "bluesky_failed" and rec["bluesky"]["uri"] is None
    fake.create_mode = "ok"
    service.bluesky_approve(task_id, a["id"], rec["bluesky"]["approval_sha256"])  # new explicit approval
    again = service.detail(task_id)["actions"][0]
    assert service.bluesky_publish(task_id, a["id"], again["approved_sha256"])["status"] == "bluesky_published"


def test_reconcile_waits_before_concluding_not_created(sky, monkeypatch):
    fake, _, _, creds, service, _ = sky
    task_id, a = _approved(sky)
    fake.create_mode = "error_500_before"
    service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    monkeypatch.setattr(pr, "RECONCILE_WAIT_SECONDS", 3600)
    with pytest.raises(ToolError, match="Wait at least"):
        service.bluesky_reconcile(task_id, a["id"])
    assert service.detail(task_id)["actions"][0]["status"] == "bluesky_uncertain"


@pytest.mark.parametrize("mode,code", [("error_400", "invalidrequest"), ("connect_error", "network")])
def test_definite_failures_post_nothing_and_allow_a_new_approval(sky, mode, code):
    fake, _, journal, creds, service, _ = sky
    task_id, a = _approved(sky)
    fake.create_mode = mode
    out = service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    assert out["status"] == "bluesky_failed" and fake.records == {}
    assert _activity(journal, task_id)[-1] == f"bluesky_failed:{code}"
    assert service.detail(task_id)["actions"][0]["status"] == "bluesky_failed"


@pytest.mark.parametrize("mode,outcome", [("tamper", "mismatch"), ("unindexed", "not_found")])
def test_verification_fails_when_the_public_post_differs_or_is_missing(sky, mode, outcome):
    fake, _, journal, creds, service, _ = sky
    task_id, a = _approved(sky)
    service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    fake.appview_mode = mode
    v = service.bluesky_verify(task_id, a["id"])
    assert v["verified"] is False and v["outcome"] == outcome
    assert service.detail(task_id)["actions"][0]["status"] == "bluesky_published"
    assert _activity(journal, task_id)[-1] == f"bluesky_verify_failed:{outcome}"


@pytest.mark.parametrize("mode", ["error_503", "redirect"])
def test_unreadable_appview_never_upgrades_or_downgrades(sky, mode):
    fake, _, _, creds, service, _ = sky
    task_id, a = _approved(sky)
    service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    assert service.bluesky_verify(task_id, a["id"])["verified"] is True
    fake.appview_mode = mode
    v = service.bluesky_verify(task_id, a["id"])
    assert v["outcome"] == "unavailable" and v["status"] == "bluesky_verified"
    assert not any(r.url.host == "evil.example" for r in fake.requests)  # redirects never followed


# -- security ---------------------------------------------------------------------------------


def test_credentials_never_reach_the_database_the_api_the_model_or_github(sky):
    fake, fake_gh, journal, creds, service, tmp = sky
    task_id, a = _approved(sky)
    service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    service.bluesky_verify(task_id, a["id"])
    db = (tmp / "work.sqlite3").read_bytes()
    detail = json.dumps(service.detail(task_id)) + json.dumps(journal.list())
    for secret in (APP_PW, JWT, "refresh"):
        assert secret.encode() not in db and secret not in detail
    # The GitHub token never goes to Bluesky; the Bluesky session never goes to GitHub.
    assert all(TOKEN_A not in str(r.headers) for r in fake.requests)
    assert all(t in ("", TOKEN_A) for _, _, t in fake_gh.requests) and all(JWT != t for _, _, t in fake_gh.requests)
    # The token is sent only to the account's PDS create call.
    authed = [r for r in fake.requests if "authorization" in r.headers]
    assert [r.url.path for r in authed] == ["/xrpc/com.atproto.repo.createRecord"]


def test_bluesky_is_released_after_real_world_acceptance(sky, monkeypatch):
    """Task #22 (2026-11-12) verified Bluesky: a packaged build offers and runs it."""
    fake, _, _, creds, service, _ = sky
    assert "promote_bluesky" in pr.RELEASE_VERIFIED_WORK_TYPES
    assert "promote_social_media" not in pr.RELEASE_VERIFIED_WORK_TYPES
    monkeypatch.delenv(pr.DEV_WORK_TYPES_ENV)
    monkeypatch.setattr(pr.sys, "frozen", True, raising=False)  # packaged build: release configuration
    assert service.bluesky_account() == {"available": True, "connected": False}
    task_id, a = _approved(sky)
    out = service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    assert out["status"] == "bluesky_published" and len(fake.creates()) == 1
    assert service.bluesky_verify(task_id, a["id"])["outcome"] == "verified"


def test_bluesky_is_still_gated_by_the_release_allowlist(sky, monkeypatch):
    """Exposure follows RELEASE_VERIFIED_WORK_TYPES: without it, a packaged build refuses Bluesky."""
    fake, _, _, creds, service, _ = sky
    task_id, a = _approved(sky)
    monkeypatch.setattr(pr, "RELEASE_VERIFIED_WORK_TYPES", pr.RELEASE_VERIFIED_WORK_TYPES - {"promote_bluesky"})
    monkeypatch.setattr(pr.sys, "frozen", True, raising=False)
    assert service.bluesky_account() == {"available": False, "connected": False}
    for call in (lambda: service.bluesky_connect(HANDLE, APP_PW),
                 lambda: service.bluesky_publish(task_id, a["id"], a["approved_sha256"])):
        with pytest.raises(ToolError):
            call()
    assert fake.creates() == []


def test_bluesky_routes_over_http(sky):
    fake, _, journal, creds, service, _ = sky
    creds.update(REPO_A, TOKEN_A)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, service), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port

    def call(method, path, body=None, nonce=NONCE):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers={
            "Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
            "Content-Type": "application/json", "X-App-Nonce": nonce})
        r = conn.getresponse()
        text = r.read().decode()
        conn.close()
        return r.status, text
    try:
        assert call("POST", "/api/promotion/bluesky", {"handle": HANDLE, "app_password": APP_PW}, "bad")[0] == 403
        status, text = call("POST", "/api/promotion/bluesky", {"handle": HANDLE, "app_password": "password1"})
        assert status == 400 and "APP password" in text and "password1" not in text
        status, text = call("POST", "/api/promotion/bluesky", {"handle": HANDLE, "app_password": APP_PW})
        assert status == 200 and APP_PW not in text and json.loads(text)["did"] == DID_A
        status, text = call("GET", "/api/promotion/bluesky")
        assert status == 200 and APP_PW not in text and json.loads(text)["connected"] is True
        task_id, a = _task(service, creds)
        base = f"/api/promotion/tasks/{task_id}/actions/{a['id']}/"
        status, text = call("GET", f"/api/promotion/tasks/{task_id}/detail")
        d = json.loads(text)
        assert d["bluesky_available"] is True and APP_PW not in text
        sha = d["actions"][0]["bluesky"]["approval_sha256"]
        assert call("POST", base + "bluesky_approve", {"sha256": sha})[0] == 200
        approved = service.detail(task_id)["actions"][0]["approved_sha256"]
        status, text = call("POST", base + "bluesky_publish", {"sha256": approved})
        assert status == 200 and json.loads(text)["status"] == "bluesky_published"
        status, text = call("POST", base + "bluesky_verify", {})
        assert status == 200 and json.loads(text)["verified"] is True
        status, text = call("POST", base + "bluesky_publish", {"sha256": approved})
        assert status == 400 and len(fake.creates()) == 1
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_github_and_bluesky_settings_are_saved_and_removed_independently(sky):
    """Settings → Promotion platform switching: each platform's credentials live in their own
    DPAPI file; saving or removing one never deletes, overwrites or reveals the other, and
    never changes an existing Task's platform or status."""
    from test_promotion import REPO_B, TOKEN_B
    fake, fake_gh, journal, creds, service, tmp = sky
    task_id, action = _task(service, creds)
    service.bluesky_connect(HANDLE, APP_PW)
    gh_file, bs_file = tmp / "promotion.dpapi", tmp / "bluesky.dpapi"
    bs_before = bs_file.read_bytes()

    creds.update(REPO_B, TOKEN_B)                      # GitHub: save another repository's token
    creds.update(REPO_A, "", remove_token=True)        # GitHub: remove one repository's token
    assert bs_file.read_bytes() == bs_before
    assert service.bluesky_account()["connected"] and service.bluesky.account()["app_password"] == APP_PW

    gh_before = gh_file.read_bytes()
    service.bluesky_disconnect()                       # Bluesky: remove its account
    assert not bs_file.exists() and gh_file.read_bytes() == gh_before
    assert creds.token_for(REPO_B) == TOKEN_B and creds.token_for(REPO_A) is None and creds.selected() == REPO_A

    service.bluesky_connect(HANDLE, APP_PW)            # reconnect: GitHub tokens still untouched
    assert gh_file.read_bytes() == gh_before

    # Neither file holds the other platform's secret; public views hold no secret at all.
    gh_plain = pr.unprotect_for_current_user(gh_file.read_bytes()).decode()
    bs_plain = bs.unprotect_for_current_user(bs_file.read_bytes()).decode()
    assert APP_PW not in gh_plain and HANDLE not in gh_plain
    assert TOKEN_B not in bs_plain and TOKEN_A not in bs_plain and "github" not in bs_plain.lower()
    public = json.dumps([creds.public(), service.bluesky_account()])
    assert APP_PW not in public and TOKEN_A not in public and TOKEN_B not in public

    # The existing Task keeps its own platform and status.
    after = service.detail(task_id)["actions"][0]
    assert (after["channel"], after["status"]) == (action["channel"], action["status"])


# -- Work Type restructuring: Bluesky is its own Work Type; Social Media is legacy ---------------


def test_bluesky_is_its_own_work_type_published_by_the_agent(sky):
    wt = pr.WORK_TYPES["promote_bluesky"]
    assert (wt.label, wt.channel, wt.automated_publishing) == ("Bluesky", "bluesky", True)
    assert wt.draft_instruction == pr.BLUESKY_INSTRUCTION and "by hand" not in pr.BLUESKY_INSTRUCTION
    details = w.TASK_DETAILS["promote_bluesky"]
    assert "Agent publishes" in " ".join(details["steps"]) and "yourself" not in json.dumps(details)
    fake, _, journal, creds, service, _ = sky
    task_id, a = _task(service, creds)
    assert journal.get(task_id)["result"]["publication"] == "automated"
    assert "publish it from this application" in journal.get(task_id)["result"]["next_step"]
    # The generic manual approval is not the Bluesky approval: it never marks a Bluesky post ready_manual.
    with pytest.raises(ToolError, match="Bluesky post"):
        service.approve(task_id, a["id"], "", a["draft_sha256"])
    with pytest.raises(ToolError, match="Bluesky actions"):
        service.publish(task_id, a["id"], a["draft_sha256"])
    assert service.detail(task_id)["actions"][0]["status"] == "draft" and fake.creates() == []


def test_legacy_social_media_tasks_keep_their_work_type_and_get_no_destination(sky, tmp_path):
    fake, _, journal, creds, service, _ = sky
    _connected(sky)
    # A Task created before the restructuring (historical identifier, SHORT/LONG POST draft).
    creds.update(REPO_A, TOKEN_A)
    task_id = journal.create("promote_social_media", REPO_A)
    body = f"SHORT POST:\nI maintain it. {LINK}\nLONG POST:\nI maintain it. The first pre-release is out. {LINK}"
    action_id = service.store.add_draft(task_id, REPO_A, "Launch", body, "social_media")
    journal.finish(task_id, "needs_attention", result={"work_type": "Social Media", "channel": "social_media"})
    # New Task no longer offers it and it cannot be started, from the engine or over the API.
    assert "promote_social_media" not in [d.id for d in w.available_definitions()]
    assert "promote_bluesky" in [d.id for d in w.available_definitions()]
    with pytest.raises(ToolError, match="no longer a Work Type"):
        service.start(FakeModel(TOKEN_A), "promote_social_media")
    with pytest.raises(ToolError, match="must match"):
        w.WorkService(journal, service).start({"route": "domain", "selection": "Promotion",
                                               "definition_id": "promote_social_media", "model_key": "k"})
    # The existing Task keeps its identifier, channel and text; it gets NO Bluesky destination.
    detail = service.detail(task_id)
    assert journal.get(task_id)["definition_id"] == "promote_social_media"
    assert detail["channel"] == "social_media" and "bluesky_account" not in detail
    a = detail["actions"][0]
    assert a["body"] == body and "bluesky" not in a and w.BY_ID["promote_social_media"].title == "Social Media (legacy)"
    sha = bs.approval_sha256(REPO_A, DID_A, f"I maintain it. {LINK}", bs.link_facets(f"I maintain it. {LINK}"))
    for call in (lambda: service.bluesky_approve(task_id, action_id, sha),
                 lambda: service.bluesky_publish(task_id, action_id, sha)):
        with pytest.raises(ToolError, match="Bluesky Work Type only"):
            call()
    # It stays the editable, manual draft it always was.
    service.edit(task_id, action_id, "Launch", body.replace("is out", "is available"))
    assert service.detail(task_id)["actions"][0]["status"] == "draft"
    assert fake.creates() == []


def test_app_password_revoked_after_approval_refuses_publishing_and_sends_nothing(sky, monkeypatch):
    fake, _, journal, _, service, _ = sky
    task_id, a = _approved(sky)
    monkeypatch.setitem(globals(), "APP_PW", "revoked-on-bluesky")   # Bluesky now rejects the stored password
    with pytest.raises(bs.BlueskyError) as exc:
        service.bluesky_publish(task_id, a["id"], a["approved_sha256"])
    assert exc.value.code == "authenticationrequired" and fake.creates() == []
    assert service.detail(task_id)["actions"][0]["status"] == "bluesky_approved"   # still approved, nothing sent
    assert _activity(journal, task_id)[-1] == "bluesky_publish_refused:authenticationrequired"
