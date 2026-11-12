"""DEV Community Work Type (released after Task #23): one exact, approved article; private draft read
back and compared; separate confirmation to publish; independent public verification."""
from __future__ import annotations

import base64
import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from github_community_agent import devto as dv
from github_community_agent import promotion as pr
from github_community_agent import work_center as w
from github_community_agent.encrypted_settings import SettingsError
from github_community_agent.errors import ToolError

from test_promotion import NONCE, REPO_A, TOKEN_A, VALID_BODY, FakeModel, MemorySettings, env  # noqa: F401

KEY = "AbCdEfGhIjKlMnOpQrStUvWx"           # shape of a DEV API key; not real
OTHER_KEY = "ZyXwVuTsRqPoNmLkJiHgFeDc"
USER_ID, USERNAME = 1234567, "natureai"
EMAIL = "owner@example.invalid"


class FakeDev:
    """dev.to-like Forem API v1: users/me, create, me/*, update (publish) and public show."""

    def __init__(self):
        self.users = {KEY: (USER_ID, USERNAME), OTHER_KEY: (7654321, "someoneelse")}
        self.articles: dict[int, dict] = {}
        self.next_id = 3000000
        self.requests: list[httpx.Request] = []
        self.create_mode = "ok"    # ok | timeout_before | timeout_after | 422 | 429 | 500_after
        self.publish_mode = "ok"   # ok | timeout_after | 422
        self.alter_body = False    # DEV stores something other than what was sent
        self.ai_disclosure = True  # production accepts ai_disclosure_level
        self.tamper_public = False
        self.public_error = False

    def writes(self, method=None):
        return [r for r in self.requests if r.method in ((method,) if method else ("POST", "PUT"))]

    def _user(self, request):
        return self.users.get(request.headers.get("api-key", ""))

    def _show(self, a):
        return {"type_of": "article", "id": a["id"], "title": a["title"], "description": a["description"],
                "slug": a["slug"], "path": "/" + a["url"].split("/", 3)[3], "url": a["url"],
                "published": a["published"], "published_at": a["published_at"], "tags": list(a["tags"]),
                "tag_list": ", ".join(a["tags"]), "body_markdown": a["body_markdown"], "body_html": "<p>x</p>",
                "ai_disclosure_level": a["ai_disclosure_level"], "organization": None,
                "user": {"user_id": a["user_id"], "username": a["username"], "name": "NATURE AI"}}

    def _me(self, a):
        out = self._show(a)
        out["tag_list"] = list(a["tags"])
        out.pop("tags")
        out.pop("ai_disclosure_level")
        return out

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.url.host == "dev.to" and request.url.scheme == "https"
        assert request.headers["accept"] == dv.ACCEPT
        path, user = request.url.path, self._user(request)
        if path == "/api/users/me":
            if not user:
                return httpx.Response(401, json={"error": "unauthorized", "status": 401})
            return httpx.Response(200, json={"type_of": "user", "id": user[0], "username": user[1],
                                             "name": "NATURE AI", "email": EMAIL})
        if path == "/api/articles" and request.method == "POST":
            if not user:
                return httpx.Response(401, json={"error": "unauthorized"})
            if self.create_mode == "timeout_before":
                raise httpx.ReadTimeout("timed out", request=request)
            if self.create_mode == "422":
                return httpx.Response(422, json={"error": "Title is too long", "status": 422})
            if self.create_mode == "429":
                return httpx.Response(429, json={"error": "Rate limit reached, try again in 30 seconds"})
            art = json.loads(request.content)["article"]
            assert isinstance(art["tags"], list) and art["published"] is False
            self.next_id += 1
            body = art["body_markdown"] + ("\n\nInjected." if self.alter_body else "")
            a = {"id": self.next_id, "title": art["title"], "description": art["description"],
                 "tags": art["tags"], "body_markdown": body, "published": False, "published_at": None,
                 "slug": f"draft-{self.next_id}-temp-slug", "user_id": user[0], "username": user[1],
                 "ai_disclosure_level": art.get("ai_disclosure_level") if self.ai_disclosure else "not_disclosed"}
            a["url"] = f"https://dev.to/{user[1]}/{a['slug']}"
            self.articles[a["id"]] = a
            if self.create_mode == "timeout_after":
                raise httpx.ReadTimeout("timed out", request=request)
            if self.create_mode == "500_after":
                return httpx.Response(502, text="bad gateway")
            return httpx.Response(201, json=self._show(a))
        if path.startswith("/api/articles/me/"):
            if not user:
                return httpx.Response(401, json={"error": "unauthorized"})
            which = path.rsplit("/", 1)[1]
            mine = [a for a in reversed(list(self.articles.values())) if a["user_id"] == user[0]
                    and (which == "all" or a["published"] == (which == "published"))]
            return httpx.Response(200, json=[self._me(a) for a in mine])
        if path.startswith("/api/articles/") and request.method == "PUT":
            aid = int(path.rsplit("/", 1)[1])
            a = self.articles.get(aid)
            if not user or not a or a["user_id"] != user[0]:
                return httpx.Response(404, json={"error": "not found"})
            if self.publish_mode == "422":
                return httpx.Response(422, json={"error": "Body markdown is invalid"})
            assert json.loads(request.content) == {"article": {"published": True}}
            a.update(published=True, published_at="2026-11-12T10:00:00Z", slug=f"designing-{aid}")
            a["url"] = f"https://dev.to/{a['username']}/{a['slug']}"
            if self.publish_mode == "timeout_after":
                raise httpx.ReadTimeout("timed out", request=request)
            return httpx.Response(200, json=self._show(a))
        if path.startswith("/api/articles/") and request.method == "GET":
            assert "api-key" not in request.headers  # the public check never uses the key
            if self.public_error:
                return httpx.Response(503, text="unavailable")
            a = self.articles.get(int(path.rsplit("/", 1)[1]))
            if not a or not a["published"]:
                return httpx.Response(404, json={"error": "not found"})
            shown = self._show(a)
            if self.tamper_public:
                shown["body_markdown"] += "\nEdited later."
            return httpx.Response(200, json=shown)
        return httpx.Response(404, json={"error": "not found"})


@pytest.fixture(autouse=True)
def _development(monkeypatch):
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")


@pytest.fixture
def dev(env, monkeypatch):
    fake_gh, journal, creds, service, tmp = env
    fake = FakeDev()
    monkeypatch.setattr(dv, "_transport", httpx.MockTransport(fake.handler))
    monkeypatch.setattr(dv.sys, "platform", "win32")
    monkeypatch.setattr(dv, "protect_for_current_user", lambda b: b"ENC_" + b[::-1])
    monkeypatch.setattr(dv, "unprotect_for_current_user", lambda b: b[len(b"ENC_"):][::-1])
    service.devto = dv.DevCredentials(tmp)
    return fake, fake_gh, journal, creds, service, tmp


def _task(service, creds, body=None, title="Designing Approval-Gated AI Agents for External Publishing"):
    creds.update(REPO_A, TOKEN_A)
    task_id = service.start(FakeModel(TOKEN_A), "promote_dev_community")
    a = service.detail(task_id)["actions"][0]
    if body is not None or title:
        service.edit(task_id, a["id"], title, body if body is not None else a["body"])
    return task_id, service.detail(task_id)["actions"][0]


def _connected(dev):
    fake, _, _, _, service, _ = dev
    service.devto_connect(KEY)
    return service


def _approved(dev, **kw):
    fake, _, _, creds, service, _ = dev
    _connected(dev)
    task_id, a = _task(service, creds, **kw)
    service.devto_approve(task_id, a["id"], a["devto"]["approval_sha256"])
    return task_id, service.detail(task_id)["actions"][0]


def _drafted(dev, **kw):
    service = dev[4]
    task_id, a = _approved(dev, **kw)
    out = service.devto_create_draft(task_id, a["id"], a["approved_sha256"])
    return task_id, service.detail(task_id)["actions"][0], out


def _in_order(expected, events):
    it = iter(events)
    return all(any(e == x for x in it) for e in expected)


def _activity(journal, task_id):
    rows = [t for t in journal.list() if t["id"] == task_id][0]["activity"]
    return [e["event"].split(":", 1)[1] for e in rows if e["event"].startswith("action#")]


ARTICLE = VALID_BODY["dev_community"].format(repo=REPO_A)


# -- article rules ------------------------------------------------------------------------------


def _issues(body=ARTICLE, title="A practical design"):
    return dv.article_issues(title, dv.parse_article(body))


def test_valid_article_parses_and_passes():
    art = dv.parse_article(ARTICLE)
    assert art["tags"] == ["ai", "security", "python", "opensource"]
    assert art["description"].startswith("How an AI agent") and art["markdown"].startswith("I maintain")
    assert _issues() == []


@pytest.mark.parametrize("change, expected", [
    (lambda b: b.replace("ARTICLE:\n", "ARTICLE:\n---\ntitle: Other\npublished: true\n---\n"), "front matter"),
    (lambda b: b.replace("## Limits", "{% embed https://example.com %}\n\n## Limits"), "Liquid"),
    (lambda b: b.replace("## Limits", "<script>alert(1)</script>\n\n## Limits"), "script"),
    (lambda b: b.replace("TAGS: ai, security, python, opensource", "TAGS: ai, security, python, opensource, web"),
     "at most 4 tags"),
    (lambda b: b.replace("TAGS: ai, security, python, opensource", "TAGS: ai, c++, open-source"), "lowercase letters"),
    (lambda b: b.replace("TAGS: ai, security, python, opensource\n", ""), "Missing 'TAGS:'"),
    (lambda b: b.replace("DESCRIPTION: How an AI agent can publish only what a person approved.\n", ""),
     "Missing 'DESCRIPTION:'"),
    (lambda b: b.replace("I maintain", "We describe"), "affiliation"),
    (lambda b: b.replace("written with the help of AI", "written carefully"), "AI-assistance disclosure"),
    (lambda b: b.replace("## Limits", "Sign up today for a free trial!\n\n## Limits"), "Advertising"),
    (lambda b: b.replace("## Limits", "Thanks @somebody for the idea.\n\n## Limits"), "@mention"),
    (lambda b: b.replace("https://github.com", "http://github.com").replace("The source is http",
                                                                           "The source is [repo](http"), "https"),
    (lambda b: b.split("## The problem")[0] + "## A\n\nShort.\n\n## B\n\nwritten with the help of AI", "words"),
])
def test_dev_rules_refuse_unsupported_or_promotional_articles(change, expected):
    assert any(expected in i for i in _issues(change(ARTICLE))), _issues(change(ARTICLE))


def test_title_limit_and_code_is_not_prose():
    assert any("128" in i for i in _issues(title="x" * 129))
    assert _issues(title="x" * 128) == []
    with_code = ARTICLE.replace("## Limits", "```python\n@dataclass\nclass A: pass\n```\n\n## Limits")
    assert _issues(with_code) == []  # a decorator in code is not an @mention


def test_approval_binds_account_title_body_description_tags_and_settings():
    art = dv.parse_article(ARTICLE)
    base = dv.approval_sha256(REPO_A, USER_ID, USERNAME, "T", art)
    variants = [dv.approval_sha256(REPO_A, 1, USERNAME, "T", art),
                dv.approval_sha256(REPO_A, USER_ID, "other", "T", art),
                dv.approval_sha256(REPO_A, USER_ID, USERNAME, "T2", art),
                dv.approval_sha256(REPO_A, USER_ID, USERNAME, "T", {**art, "description": "x"}),
                dv.approval_sha256(REPO_A, USER_ID, USERNAME, "T", {**art, "tags": ["ai"]}),
                dv.approval_sha256(REPO_A, USER_ID, USERNAME, "T", {**art, "markdown": art["markdown"] + "."}),
                dv.approval_sha256("o/other", USER_ID, USERNAME, "T", art)]
    assert base not in variants and len(set(variants)) == len(variants)
    assert dv.PUBLISH_SETTINGS == {"platform": "dev.to", "organization": None, "series": None,
                                   "canonical_url": None, "main_image": None, "ai_disclosure_level": "some_ai"}


def test_only_fixed_dev_paths_and_host_can_be_called(monkeypatch):
    for bad in ("/api/comments", "/api/articles/1/unpublish", "/api/admin", "/api/articles/me/../x"):
        with pytest.raises(dv.DevError) as exc:
            dv._request("GET", bad)
        assert exc.value.code == "path"
    assert dv.HOST == "https://dev.to"


# -- isolated credentials -------------------------------------------------------------------------


def test_connect_checks_users_me_and_stores_only_key_id_and_username(dev):
    fake, _, _, creds, service, tmp = dev
    creds.update(REPO_A, TOKEN_A)
    github_file = (tmp / "promotion.dpapi").read_bytes()
    for bad in ("", "short", "has spaces in it 1234567890", TOKEN_A):
        with pytest.raises(SettingsError, match="DEV API key"):
            service.devto_connect(bad)
    assert fake.requests == []  # refused before any network call
    with pytest.raises(dv.DevError) as exc:
        service.devto_connect("Q" * 24)                              # unknown key: DEV answers 401
    assert exc.value.code == "unauthorized" and not (tmp / "devto.dpapi").exists()
    out = service.devto_connect(KEY)
    assert out == {"available": True, "connected": True, "username": USERNAME, "user_id": USER_ID}
    stored = (tmp / "devto.dpapi").read_bytes()
    assert stored.startswith(b"ENC_") and KEY.encode() not in stored
    plain = json.loads(dv.unprotect_for_current_user(stored))
    assert set(plain) == {"api_key", "user_id", "username"} and EMAIL not in json.dumps(plain)
    assert (tmp / "promotion.dpapi").read_bytes() == github_file  # GitHub tokens untouched
    assert KEY not in json.dumps(service.devto_account()) and EMAIL not in json.dumps(service.devto_account())
    assert service.devto_disconnect() == {"available": True, "connected": False}
    assert not (tmp / "devto.dpapi").exists() and (tmp / "promotion.dpapi").read_bytes() == github_file


def test_credentials_never_reach_the_database_the_api_the_model_or_github(dev):
    fake, fake_gh, journal, creds, service, tmp = dev
    task_id, a, _ = _drafted(dev)
    service.devto_publish(task_id, a["id"], a["approved_sha256"])
    service.devto_verify(task_id, a["id"])
    db = (tmp / "work.sqlite3").read_bytes()
    detail = json.dumps(service.detail(task_id)) + json.dumps(journal.list())
    for secret in (KEY, EMAIL):
        assert secret.encode() not in db and secret not in detail
    assert all(KEY not in str(r.headers) for r in fake_gh.requests if hasattr(r, "headers"))
    assert all(KEY not in str(req) for req in fake_gh.requests)
    # The key goes only to dev.to's authenticated calls; the public check has no key.
    keyed = {(r.method, r.url.path) for r in fake.requests if "api-key" in r.headers}
    assert ("GET", f"/api/articles/{a['devto']['article_id'] or service.detail(task_id)['actions'][0]['devto']['article_id']}") not in keyed


def test_model_inputs_never_contain_the_api_key(dev):
    fake, _, _, creds, service, _ = dev
    _connected(dev)
    creds.update(REPO_A, TOKEN_A)
    model = FakeModel(TOKEN_A)
    service.start(model, "promote_dev_community")
    assert model.inputs and all(KEY not in i for i in model.inputs)


# -- staged publication ----------------------------------------------------------------------------


def test_approve_sends_nothing_and_binds_the_account(dev):
    fake, _, journal, creds, service, _ = dev
    task_id, a = _task(service, creds)
    assert a["devto"]["approval_sha256"] is None  # no account connected yet
    sha = dv.approval_sha256(REPO_A, USER_ID, USERNAME, a["title"], dv.parse_article(a["body"]))
    with pytest.raises(dv.DevError) as exc:
        service.devto_approve(task_id, a["id"], sha)
    assert exc.value.code == "no_account"
    _connected(dev)
    a = service.detail(task_id)["actions"][0]
    assert a["devto"]["approval_sha256"] == sha
    with pytest.raises(dv.DevError) as exc:
        service.devto_approve(task_id, a["id"], "0" * 64)
    assert exc.value.code == "approval_mismatch"
    out = service.devto_approve(task_id, a["id"], sha)
    assert out["status"] == "dev_approved" and out["user_id"] == USER_ID
    a = service.detail(task_id)["actions"][0]
    assert a["category"] == f"devto:{USER_ID}:{USERNAME}" and fake.writes() == []
    # The generic manual approval and the GitHub publisher refuse DEV actions.
    with pytest.raises(ToolError, match="DEV"):
        service.approve(task_id, a["id"], "", a["draft_sha256"])
    with pytest.raises(ToolError, match="DEV"):
        service.publish(task_id, a["id"], a["approved_sha256"])
    # Any edit cancels the approval.
    service.edit(task_id, a["id"], a["title"], a["body"].replace("documented design", "documented approach"))
    assert service.detail(task_id)["actions"][0]["status"] == "draft"
    assert _activity(journal, task_id)[-3:] == ["dev_approve_refused:no_account",
                                                "dev_approve_refused:approval_mismatch", "dev_approved"]


def test_private_draft_is_read_back_then_published_only_after_a_separate_confirmation(dev):
    fake, _, journal, creds, service, _ = dev
    task_id, a, out = _drafted(dev)
    assert out["status"] == "dev_draft_ready" and out["ai_disclosure_metadata"] == "accepted"
    posts = fake.writes("POST")
    assert len(posts) == 1 and fake.writes("PUT") == []          # ONE create; nothing published
    sent = json.loads(posts[0].content)["article"]
    assert sent["published"] is False and sent["tags"] == ["ai", "security", "python", "opensource"]
    assert sent["ai_disclosure_level"] == "some_ai" and sent["title"] == a["title"]
    assert set(sent) == {"title", "body_markdown", "published", "description", "tags", "ai_disclosure_level"}
    assert a["status"] == "dev_draft_ready" and a["devto"]["check"]["outcome"] == "matched"
    assert all(a["devto"]["check"]["checks"].values())
    article_id = a["devto"]["article_id"]
    assert fake.articles[int(article_id)]["published"] is False
    # Publishing is a separate call with the approved fingerprint.
    with pytest.raises(dv.DevError):
        service.devto_publish(task_id, a["id"], "0" * 64)
    res = service.devto_publish(task_id, a["id"], a["approved_sha256"])
    assert res["status"] == "dev_published" and res["url"] == f"https://dev.to/{USERNAME}/designing-{article_id}"
    assert len(fake.writes("PUT")) == 1 and len(fake.writes("POST")) == 1
    v = service.devto_verify(task_id, a["id"])
    assert v["outcome"] == "verified" and all(v["checks"].values())
    a = service.detail(task_id)["actions"][0]
    assert a["status"] == "dev_verified" and a["devto"]["url"] == res["url"]
    assert a["devto"]["check"]["ai_disclosure_level"] == "some_ai"
    assert _in_order(["dev_approved", "dev_draft_requested", "dev_draft_verified", "dev_publish_requested",
                      "dev_published", "dev_verified"], _activity(journal, task_id))
    with pytest.raises(dv.DevError) as exc:  # never twice
        service.devto_publish(task_id, a["id"], a["approved_sha256"])
    assert exc.value.code == "already_published" and len(fake.writes()) == 2


def test_publish_requires_a_verified_draft(dev):
    fake, _, _, _, service, _ = dev
    task_id, a = _approved(dev)
    with pytest.raises(dv.DevError) as exc:
        service.devto_publish(task_id, a["id"], a["approved_sha256"])
    assert exc.value.code == "no_draft" and fake.writes() == []


def test_draft_that_differs_is_never_published(dev):
    fake = dev[0]
    fake.alter_body = True
    task_id, a, out = _drafted(dev)
    assert out["status"] == "dev_draft_mismatch" and out["checks"]["body"] is False
    assert a["status"] == "dev_draft_mismatch" and "NOT published" in a["error"]
    with pytest.raises(dv.DevError):
        dev[4].devto_publish(task_id, a["id"], a["approved_sha256"])
    assert fake.writes("PUT") == []


def test_draft_changed_on_dev_after_the_check_is_not_published(dev):
    fake, _, _, _, service, _ = dev
    task_id, a, _ = _drafted(dev)
    fake.articles[int(a["devto"]["article_id"])]["body_markdown"] += "\nChanged on DEV."
    with pytest.raises(dv.DevError) as exc:
        service.devto_publish(task_id, a["id"], a["approved_sha256"])
    assert exc.value.code == "draft_changed" and fake.writes("PUT") == []
    assert service.detail(task_id)["actions"][0]["status"] == "dev_draft_mismatch"


def test_ai_disclosure_metadata_that_dev_ignores_is_recorded_not_hidden(dev):
    dev[0].ai_disclosure = False
    task_id, a, out = _drafted(dev)
    assert out["status"] == "dev_draft_ready" and out["ai_disclosure_metadata"] == "not_accepted"
    assert a["devto"]["check"]["ai_disclosure_returned"] == "not_disclosed"


def test_duplicate_title_and_other_account_are_refused_before_sending(dev):
    fake, _, journal, creds, service, tmp = dev
    task_id, a = _approved(dev)
    fake.articles[1] = {"id": 1, "title": a["title"], "description": "", "tags": [], "body_markdown": "old",
                        "published": True, "published_at": "2026-01-01T00:00:00Z", "slug": "old",
                        "url": f"https://dev.to/{USERNAME}/old", "user_id": USER_ID, "username": USERNAME,
                        "ai_disclosure_level": "no_ai"}
    with pytest.raises(dv.DevError) as exc:
        service.devto_create_draft(task_id, a["id"], a["approved_sha256"])
    assert exc.value.code == "duplicate_title" and fake.writes() == []
    del fake.articles[1]
    fake.users[KEY] = (999, "someoneelse")  # the stored key now belongs to another account
    with pytest.raises(dv.DevError) as exc:
        service.devto_create_draft(task_id, a["id"], a["approved_sha256"])
    assert exc.value.code == "account_mismatch" and fake.writes() == []
    assert service.detail(task_id)["actions"][0]["status"] == "dev_approved"


@pytest.mark.parametrize("mode, code", [("422", "http_422"), ("429", "rate_limited")])
def test_definite_create_failures_publish_nothing_and_allow_a_new_approval(dev, mode, code):
    fake = dev[0]
    fake.create_mode = mode
    task_id, a, out = _drafted(dev)
    assert out["status"] == "dev_failed" and a["status"] == "dev_failed" and fake.articles == {}
    assert _activity(dev[2], task_id)[-1] == f"dev_draft_failed:{code}"
    fake.create_mode = "ok"
    a = dev[4].detail(task_id)["actions"][0]
    assert dev[4].devto_approve(task_id, a["id"], a["devto"]["approval_sha256"])["status"] == "dev_approved"


def test_uncertain_create_is_reconciled_from_the_account_never_retried(dev):
    fake, _, journal, _, service, _ = dev
    fake.create_mode = "timeout_after"     # DEV created the draft, the answer was lost
    task_id, a, out = _drafted(dev)
    assert out["status"] == "dev_uncertain" and a["status"] == "dev_uncertain"
    for call in (lambda: service.devto_create_draft(task_id, a["id"], a["approved_sha256"]),
                 lambda: service.devto_approve(task_id, a["id"], a["approved_sha256"]),
                 lambda: service.devto_publish(task_id, a["id"], a["approved_sha256"])):
        with pytest.raises(ToolError):
            call()
    assert len(fake.writes("POST")) == 1
    res = service.devto_reconcile(task_id, a["id"])
    assert res["status"] == "dev_draft_ready" and len(fake.writes("POST")) == 1
    assert _in_order(["dev_uncertain:draft", "dev_reconciled_draft_verified"], _activity(journal, task_id))


def test_uncertain_create_that_never_arrived_becomes_a_failure(dev):
    fake, _, _, _, service, _ = dev
    fake.create_mode = "timeout_before"
    task_id, a, out = _drafted(dev)
    assert out["status"] == "dev_uncertain"
    assert service.devto_reconcile(task_id, a["id"])["status"] == "dev_failed" and fake.articles == {}


def test_server_error_on_create_is_uncertain(dev):
    dev[0].create_mode = "500_after"
    _, a, out = _drafted(dev)
    assert out["status"] == "dev_uncertain" and len(dev[0].writes("POST")) == 1


def test_uncertain_publish_is_reconciled_never_retried(dev):
    fake, _, _, _, service, _ = dev
    task_id, a, _ = _drafted(dev)
    fake.publish_mode = "timeout_after"
    assert service.devto_publish(task_id, a["id"], a["approved_sha256"])["status"] == "dev_uncertain"
    with pytest.raises(ToolError):
        service.devto_publish(task_id, a["id"], a["approved_sha256"])
    res = service.devto_reconcile(task_id, a["id"])
    assert res["status"] == "dev_published" and len(fake.writes("PUT")) == 1


def test_definite_publish_failure_keeps_the_private_draft(dev):
    fake, _, _, _, service, _ = dev
    task_id, a, _ = _drafted(dev)
    fake.publish_mode = "422"
    res = service.devto_publish(task_id, a["id"], a["approved_sha256"])
    assert res["status"] == "dev_draft_ready" and "422" in res["error"]
    assert fake.articles[int(a["devto"]["article_id"])]["published"] is False


@pytest.mark.parametrize("mode, outcome", [("tamper", "mismatch"), ("error", "unavailable")])
def test_public_verification_never_upgrades_on_mismatch_or_error(dev, mode, outcome):
    fake, _, _, _, service, _ = dev
    task_id, a, _ = _drafted(dev)
    service.devto_publish(task_id, a["id"], a["approved_sha256"])
    fake.tamper_public, fake.public_error = mode == "tamper", mode == "error"
    v = service.devto_verify(task_id, a["id"])
    assert v["outcome"] == outcome and v["verified"] is False
    assert service.detail(task_id)["actions"][0]["status"] == "dev_published"


# -- brief: topic and cited repository documents --------------------------------------------------


def test_brief_is_validated_and_only_for_dev(dev):
    _, _, journal, creds, service, _ = dev
    creds.update(REPO_A, TOKEN_A)
    for bad in ({"topic": "x" * 161}, {"documents": ["../secrets.md"]}, {"documents": ["a.txt"]},
                {"documents": ["a.md"] * 5}, {"documents": ["a.md@bad ref"]}, "text"):
        with pytest.raises(ToolError):
            service.start(FakeModel(), "promote_dev_community", brief=bad)
    with pytest.raises(ToolError, match="Only DEV Community"):
        service.start(FakeModel(), "promote_bluesky", brief={"topic": "x"})
    assert journal.list() == []
    assert pr.parse_brief({"topic": " T ", "documents": "docs/A.md@feature/x\n\nREADME.md"}) == {
        "topic": "T", "documents": [{"path": "docs/A.md", "ref": "feature/x"}, {"path": "README.md", "ref": ""}]}


def test_brief_documents_are_read_pinned_and_cited(dev, monkeypatch):
    fake, fake_gh, journal, creds, service, _ = dev
    sha = "a" * 40
    original = fake_gh._rest

    def rest(path):
        if path == f"/repos/{REPO_A}/commits/feature/v2-promotion":
            return httpx.Response(200, json={"sha": sha})
        if path == f"/repos/{REPO_A}/contents/docs/V2_PROMOTION.md":
            content = base64.b64encode(b"# V2 Promotion\nExact-action approval before every write.").decode()
            return httpx.Response(200, json={"encoding": "base64", "content": content})
        return original(path)
    monkeypatch.setattr(fake_gh, "_rest", rest)
    creds.update(REPO_A, TOKEN_A)
    model = FakeModel(TOKEN_A)
    task_id = service.start(model, "promote_dev_community", brief={
        "topic": "Designing Approval-Gated AI Agents for External Publishing",
        "documents": ["docs/V2_PROMOTION.md@feature/v2-promotion"]})
    evidence = journal.get(task_id)["result"]["evidence"]
    doc = evidence["documents"][0]
    assert doc["commit"] == sha and doc["url"] == f"https://github.com/{REPO_A}/blob/{sha}/docs/V2_PROMOTION.md"
    assert "Exact-action approval" in doc["excerpt"] and doc["url"] in evidence["source_urls"]
    assert evidence["article_brief"] == {"topic": "Designing Approval-Gated AI Agents for External Publishing"}
    drafted = [i for i in model.inputs if i.startswith(pr.DEV_COMMUNITY_INSTRUCTION)]
    assert drafted and "Exact-action approval" in drafted[0] and "Approval-Gated" in drafted[0]
    detail = service.detail(task_id)
    assert detail["documents"] == [{"path": "docs/V2_PROMOTION.md", "ref": "feature/v2-promotion", "commit": sha,
                                    "url": doc["url"]}]
    # A missing document fails the Task instead of drafting without its evidence.
    task2 = service.start(model, "promote_dev_community", brief={"documents": ["docs/MISSING.md"]})
    assert journal.get(task2)["status"] == "failed"


# -- release gate and legacy ------------------------------------------------------------------------


def test_dev_community_is_released_after_real_world_acceptance(dev, monkeypatch):
    """Task #23 (2026-11-12) verified DEV Community: a packaged build offers and runs it."""
    fake, _, _, _, service, _ = dev
    assert "promote_dev_community" in pr.RELEASE_VERIFIED_WORK_TYPES
    monkeypatch.delenv(pr.DEV_WORK_TYPES_ENV)
    monkeypatch.setattr(pr.sys, "frozen", True, raising=False)  # packaged build: release configuration
    assert service.devto_account() == {"available": True, "connected": False}
    assert "promote_dev_community" in [d.id for d in w.available_definitions()]
    task_id, a, out = _drafted(dev)
    assert out["status"] == "dev_draft_ready"
    assert service.devto_publish(task_id, a["id"], a["approved_sha256"])["status"] == "dev_published"
    assert service.devto_verify(task_id, a["id"])["outcome"] == "verified"


def test_dev_community_is_still_gated_by_the_release_allowlist(dev, monkeypatch):
    """Exposure follows RELEASE_VERIFIED_WORK_TYPES: without it, a packaged build refuses DEV."""
    fake, _, _, _, service, _ = dev
    task_id, a, _ = _drafted(dev)
    monkeypatch.setattr(pr, "RELEASE_VERIFIED_WORK_TYPES", pr.RELEASE_VERIFIED_WORK_TYPES - {"promote_dev_community"})
    monkeypatch.setattr(pr.sys, "frozen", True, raising=False)  # packaged build
    assert service.devto_account() == {"available": False, "connected": False}
    writes = len(fake.writes())
    for call in (lambda: service.devto_connect(KEY),
                 lambda: service.devto_publish(task_id, a["id"], a["approved_sha256"])):
        with pytest.raises(ToolError):
            call()
    assert len(fake.writes()) == writes
    assert "promote_dev_community" not in [d.id for d in w.available_definitions()]


def test_legacy_technical_articles_tasks_keep_their_work_type_and_get_no_destination(dev):
    fake, _, journal, creds, service, _ = dev
    _connected(dev)
    creds.update(REPO_A, TOKEN_A)
    task_id = journal.create("promote_technical_articles", REPO_A)
    body = "Disclosure: I maintain it. A tutorial."
    action_id = service.store.add_draft(task_id, REPO_A, "Tutorial", body, "technical_article")
    journal.finish(task_id, "needs_attention", result={"work_type": "Technical Articles",
                                                        "channel": "technical_article"})
    assert "promote_technical_articles" not in [d.id for d in w.available_definitions()]
    assert "promote_dev_community" in [d.id for d in w.available_definitions()]
    assert w.BY_ID["promote_technical_articles"].title == "Technical Articles (legacy)"
    with pytest.raises(ToolError, match="no longer a Work Type"):
        service.start(FakeModel(TOKEN_A), "promote_technical_articles")
    detail = service.detail(task_id)
    assert detail["channel"] == "technical_article" and "devto_account" not in detail
    assert detail["actions"][0]["body"] == body and "devto" not in detail["actions"][0]
    with pytest.raises(ToolError, match="DEV Community Work Type only"):
        service.devto_approve(task_id, action_id, "0" * 64)
    service.edit(task_id, action_id, "Tutorial", body + " Edited.")  # still the editable manual draft
    assert service.detail(task_id)["actions"][0]["status"] == "draft" and fake.writes() == []


# -- HTTP ----------------------------------------------------------------------------------------------


def test_devto_routes_over_http_never_return_the_key(dev):
    fake, _, journal, creds, service, _ = dev
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
        assert call("GET", "/api/promotion/devto") == (200, json.dumps({"available": True, "connected": False}))
        status, text = call("POST", "/api/promotion/devto", {"api_key": KEY})
        assert status == 200 and KEY not in text and json.loads(text)["username"] == USERNAME
        status, text = call("GET", "/api/promotion/devto")
        assert KEY not in text and EMAIL not in text
        task_id, a = _task(service, creds)
        base = f"/api/promotion/tasks/{task_id}/actions/{a['id']}/"
        status, text = call("POST", base + "devto_approve", {"sha256": a["devto"]["approval_sha256"]})
        assert status == 200 and json.loads(text)["status"] == "dev_approved"
        sha = json.loads(text)["approved_sha256"]
        status, text = call("POST", base + "devto_create_draft", {"sha256": sha})
        assert status == 200 and json.loads(text)["status"] == "dev_draft_ready"
        status, text = call("POST", base + "devto_publish", {"sha256": sha})
        assert status == 200 and json.loads(text)["status"] == "dev_published"
        status, text = call("POST", base + "devto_verify", {})
        assert status == 200 and json.loads(text)["outcome"] == "verified"
        status, text = call("GET", f"/api/promotion/tasks/{task_id}/detail")
        assert status == 200 and KEY not in text and EMAIL not in text
        assert call("POST", "/api/promotion/devto", {"remove": True})[0] == 200
    finally:
        httpd.shutdown()
        httpd.server_close()
