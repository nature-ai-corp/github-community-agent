"""V2 universal Promotion Agent: one workflow, repository + token as the only configuration.

Offline: GitHub is an httpx.MockTransport that behaves like GitHub's REST and
GraphQL APIs (including fine-grained token-to-repository binding), the AI model
is a recording fake, and DPAPI is faked as in test_encrypted_settings. Nothing
reaches GitHub or a model provider.
"""
from __future__ import annotations

import base64
import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from github_community_agent import github_readonly as gh
from github_community_agent import promotion as pr
from github_community_agent import work_center as w
from github_community_agent.errors import ToolError

REPO_A = "nature-ai-corp/github-community-agent"   # default target
REPO_B = "nature-ai-corp/nature-ai-worker"          # another authorized product repository
TOKEN_A = "github_pat_" + "A1" * 20
TOKEN_B = "github_pat_" + "B2" * 20
NONCE = "promotion-test-nonce-0123456789"


# -- fakes ---------------------------------------------------------------------------------


class FakeGitHub:
    """GitHub-like REST + GraphQL. A token only sees the repository it was issued for."""

    def __init__(self):
        self.repos = {
            REPO_A: {"token": TOKEN_A, "permission": "ADMIN", "discussions": True, "private": False},
            REPO_B: {"token": TOKEN_B, "permission": "WRITE", "discussions": True, "private": False},
        }
        self.discussions = {r: [] for r in self.repos}
        self.requests: list[tuple[str, str, str]] = []
        self.mutations: list[tuple[str, dict]] = []
        self.mode = "ok"          # ok | timeout_after_create | timeout_before_create | graphql_error
        self.scopes = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("authorization", "")
        token = auth.removeprefix("Bearer ")
        self.requests.append((request.method, request.url.path, token))
        if request.method == "GET":
            return self._rest(request.url.path)
        body = json.loads(request.content)
        query, v = body["query"], body["variables"]
        headers = {} if self.scopes is None else {"x-oauth-scopes": self.scopes}
        if query == pr.PERMISSION_QUERY:
            repo = f"{v['owner']}/{v['name']}"
            cfg = self.repos.get(repo)
            if not cfg or token != cfg["token"]:
                return httpx.Response(200, headers=headers, json={"errors": [{"type": "NOT_FOUND"}]})
            return httpx.Response(200, headers=headers, json={"data": {
                "viewer": {"login": "maintainer"},
                "repository": {"id": "R_" + repo, "nameWithOwner": repo, "isPrivate": cfg["private"],
                               "hasDiscussionsEnabled": cfg["discussions"], "viewerPermission": cfg["permission"],
                               "discussionCategories": {"nodes": [{"id": "C_ann", "name": "Announcements"},
                                                                  {"id": "C_gen", "name": "General"}]}}}})
        if query == pr.CREATE_DISCUSSION_MUTATION:
            self.mutations.append((token, v))
            repo = v["repositoryId"].removeprefix("R_")
            if self.mode == "timeout_before_create":
                raise httpx.ReadTimeout("timed out", request=request)
            if self.mode == "graphql_error":
                return httpx.Response(200, json={"errors": [{"type": "FORBIDDEN"}]})
            number = 100 + len(self.discussions[repo])
            node = {"id": f"D_{repo}_{number}", "number": number, "body": v["body"], "title": v["title"]}
            self.discussions[repo].insert(0, node)
            if self.mode == "timeout_after_create":
                raise httpx.ReadTimeout("timed out", request=request)
            return httpx.Response(200, json={"data": {"createDiscussion": {
                "clientMutationId": v["clientMutationId"],
                "discussion": {"id": node["id"], "number": number, "repository": {"nameWithOwner": repo}}}}})
        if query == pr.RECENT_DISCUSSIONS_QUERY:
            repo = f"{v['owner']}/{v['name']}"
            if token != self.repos[repo]["token"]:
                return httpx.Response(200, json={"errors": [{"type": "NOT_FOUND"}]})
            return httpx.Response(200, json={"data": {"repository": {
                "nameWithOwner": repo, "discussions": {"nodes": self.discussions[repo]}}}})
        if query == pr.METRICS_QUERY:
            node_id = v["id"]
            repo = node_id.split("_", 1)[1].rsplit("_", 1)[0]
            if token != self.repos[repo]["token"]:
                return httpx.Response(200, json={"errors": [{"type": "NOT_FOUND"}]})
            return httpx.Response(200, json={"data": {"node": {
                "number": 100, "upvoteCount": 4, "locked": False, "closed": False,
                "comments": {"totalCount": 3}, "reactions": {"totalCount": 7},
                "repository": {"nameWithOwner": repo}}}})
        return httpx.Response(400, json={"message": "unexpected document"})

    def _rest(self, path: str) -> httpx.Response:
        for repo, cfg in self.repos.items():
            if path == f"/repos/{repo}":
                return httpx.Response(200, json={"private": cfg["private"], "description": f"{repo} product",
                                                 "stargazers_count": 12, "forks_count": 3, "topics": ["ai"],
                                                 "license": {"spdx_id": "Apache-2.0"}, "has_discussions": True,
                                                 "open_issues_count": 2, "pushed_at": "2026-11-10T00:00:00Z"})
            if path == f"/repos/{repo}/readme":
                content = base64.b64encode(f"# {repo}\nReal README text.".encode()).decode()
                return httpx.Response(200, json={"encoding": "base64", "content": content})
            if path == f"/repos/{repo}/releases":
                return httpx.Response(200, json=[{"tag_name": "v1.0.0-rc1", "name": "RC1", "prerelease": True,
                                                  "draft": False, "published_at": "2026-11-10T20:54:07Z",
                                                  "body": "First pre-release."}])
        return httpx.Response(404, json={"message": "Not Found"})


class FakeModel:
    def __init__(self, *tokens):
        self.inputs: list[str] = []
        self.tokens = tokens

    def __call__(self, instruction: str, evidence: str) -> str:
        for t in self.tokens:
            assert t not in instruction and t not in evidence, "a GitHub token reached the AI model"
        self.inputs.append(instruction + "\n" + evidence)
        for wt in pr.WORK_TYPES.values():
            if instruction.startswith(wt.draft_instruction):
                repo = json.loads(evidence)["evidence"]["repository"]
                return f"TITLE: {repo} 1.0.0-rc1 is available\nBODY:\n" + VALID_BODY[wt.channel].format(repo=repo)
        if instruction.startswith(pr.PLAN_INSTRUCTION):
            return "Audience: maintainers (Verified: README). Approach: one post for this Work Type (Proposed)."
        return "Improve: post release notes earlier (targets comments)."


# Minimal content that passes each Work Type's checks (format, labels, disclosure).
VALID_BODY = {
    "github_discussion": "The first pre-release of {repo} is out.",
    "repository_optimization": "Current (verified): no topics.\nProposed: add topics.\nWhy: discoverability.",
    "reddit": "I maintain {repo}. The first pre-release is out.",
    "developer_forum": "I maintain {repo}. The first pre-release is out.",
    "technical_article": "Disclosure: I maintain {repo}. The first pre-release is out.",
    "bluesky": "I maintain {repo}: the first pre-release is out. https://github.com/{repo}",
    "social_media": "SHORT POST:\nI maintain {repo}: the first pre-release is out.\n"
                    "LONG POST:\nI maintain {repo}. The first pre-release is out.",
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    fake = FakeGitHub()
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(fake.handler))
    monkeypatch.setattr(pr.sys, "platform", "win32")
    monkeypatch.setattr(pr, "protect_for_current_user", lambda b: b"ENC_" + b[::-1])
    monkeypatch.setattr(pr, "unprotect_for_current_user", lambda b: b[len(b"ENC_"):][::-1])
    # Run the background research/draft step synchronously and deterministically,
    # replacing only promotion.py's reference (never the global threading module).
    import threading as real_threading
    from types import SimpleNamespace
    sync_thread = lambda target, args, daemon: SimpleNamespace(start=lambda: target(*args))
    monkeypatch.setattr(pr, "threading", SimpleNamespace(Thread=sync_thread, RLock=real_threading.RLock))
    db = tmp_path / "work.sqlite3"
    journal = w.Journal(db)
    creds = pr.PromotionCredentials(tmp_path)
    service = pr.PromotionService(journal, pr.PromotionStore(db), creds)
    return fake, journal, creds, service, tmp_path


def _start(service, creds, repo, model):
    creds.update(repo)
    task_id = service.start(model)
    action = service.detail(task_id)["actions"][0]
    return task_id, action


# -- architecture -------------------------------------------------------------------------


def test_promotion_work_types_share_one_agent():
    v2 = [d for d in w.DEFINITIONS if d.version == "V2"]
    assert [d.id for d in v2] == list(pr.WORK_TYPES)
    assert [d.title for d in v2] == ["GitHub Discussions", "Repository Optimization", "Reddit Promotion",
                                     "Developer Forums", "Technical Articles", "Bluesky",
                                     "Social Media (legacy)"]
    assert all(d.workflow == "promotion" and d.enabled and d.domain == "Promotion" for d in v2)
    assert all(w.BY_ID[k].title.removesuffix(" (legacy)") == wt.label for k, wt in pr.WORK_TYPES.items())
    assert pr.LEGACY_WORK_TYPES == {"promote_social_media"}
    # GitHub Discussions keeps the original id and channel (existing Tasks and evidence).
    assert pr.WORK_TYPES[pr.DEFINITION_ID].channel == pr.CHANNEL == "github_discussion"
    # Publishers: GitHub Discussions and Bluesky (both released); the rest are manual.
    assert [k for k, wt in pr.WORK_TYPES.items() if wt.automated_publishing] == [pr.DEFINITION_ID,
                                                                                 "promote_bluesky"]
    assert len({wt.channel for wt in pr.WORK_TYPES.values()}) == 7
    import inspect
    source = inspect.getsource(pr)
    for forbidden in ("self_promotion", "product_promotion", "SelfPromotion", "ProductPromotion"):
        assert forbidden not in source
    assert pr.DEFAULT_PROMOTION_REPOSITORY == REPO_A


def test_same_workflow_serves_any_repository(env):
    fake, journal, creds, service, _ = env
    model = FakeModel(TOKEN_A, TOKEN_B)
    for repo in (REPO_A, REPO_B):
        task_id, action = _start(service, creds, repo, model)
        task = journal.get(task_id)
        assert task["repository"] == repo and task["status"] == "needs_attention"
        assert task["result"]["evidence"]["repository"] == repo
        assert all(u.startswith(f"https://github.com/{repo}") for u in task["result"]["sources"])
        assert action["repository"] == repo and action["status"] == "draft"
        assert action["title"] == f"{repo} 1.0.0-rc1 is available"
    # Same instructions for both repositories: one workflow, not two modes.
    assert sum(pr.PLAN_INSTRUCTION in i for i in model.inputs) == 2
    assert fake.mutations == []  # research and drafting never write


# -- credentials ---------------------------------------------------------------------------


def test_default_target_and_per_repository_tokens_without_fallback(env):
    _, _, creds, _, tmp_path = env
    assert creds.selected() == REPO_A and creds.token_for(REPO_A) is None
    creds.update(REPO_B, TOKEN_B)
    assert creds.selected() == REPO_B and creds.token_for(REPO_B) == TOKEN_B
    assert creds.token_for(REPO_A) is None  # never another repository's token
    creds.update(REPO_A, TOKEN_A)
    public = creds.public()
    assert public["selected"] == REPO_A and public["selected_has_token"] is True
    assert {r["repository"] for r in public["repositories"]} == {REPO_A, REPO_B}
    assert TOKEN_A not in json.dumps(public) and TOKEN_B not in json.dumps(public)
    raw = (tmp_path / "promotion.dpapi").read_bytes()
    assert TOKEN_A.encode() not in raw and TOKEN_B.encode() not in raw
    creds.update(REPO_B, remove_token=True)  # removes ONLY B's token
    assert creds.token_for(REPO_B) is None and creds.token_for(REPO_A) == TOKEN_A
    with pytest.raises(Exception, match="owner/name"):
        creds.update("https://evil.example/x")


@pytest.mark.skipif(__import__("sys").platform != "win32", reason="native Windows DPAPI required")
def test_native_windows_dpapi_per_repository_tokens(tmp_path):
    creds = pr.PromotionCredentials(tmp_path)
    creds.update(REPO_A, TOKEN_A)
    creds.update(REPO_B, TOKEN_B)
    raw = (tmp_path / "promotion.dpapi").read_bytes()
    assert TOKEN_A.encode() not in raw and TOKEN_B.encode() not in raw and REPO_A.encode() not in raw
    restarted = pr.PromotionCredentials(tmp_path)
    assert restarted.token_for(REPO_A) == TOKEN_A and restarted.token_for(REPO_B) == TOKEN_B
    assert restarted.selected() == REPO_B


def test_credentials_refuse_unencrypted_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(pr.sys, "platform", "linux")
    creds = pr.PromotionCredentials(tmp_path)
    with pytest.raises(pr.SettingsError, match="DPAPI"):
        creds.update(REPO_A, TOKEN_A)
    assert not (tmp_path / "promotion.dpapi").exists()


# -- approval and publication --------------------------------------------------------------


def test_publish_only_the_exactly_approved_text_after_permission_check(env):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)
    task_id, a = _start(service, creds, REPO_A, FakeModel(TOKEN_A))
    with pytest.raises(ToolError, match="approved"):
        service.publish(task_id, a["id"], a["draft_sha256"])            # no approval yet
    with pytest.raises(ToolError, match="does not match"):
        service.approve(task_id, a["id"], "Announcements", "0" * 64)    # wrong fingerprint
    preflight = service.preflight(task_id, a["id"])
    assert preflight["can_publish"] and "Announcements" in preflight["categories"]
    assert not any(k.startswith("_") for k in preflight)
    approved = service.approve(task_id, a["id"], "Announcements", a["draft_sha256"])
    service.edit(task_id, a["id"], a["title"], a["body"] + " Edited.")    # edit cancels approval
    with pytest.raises(ToolError, match="approved"):
        service.publish(task_id, a["id"], approved)
    a = service.detail(task_id)["actions"][0]
    approved = service.approve(task_id, a["id"], "Announcements", a["draft_sha256"])
    assert fake.mutations == []
    result = service.publish(task_id, a["id"], approved)
    assert result == {"status": "published", "url": f"https://github.com/{REPO_A}/discussions/100"}
    assert len(fake.mutations) == 1
    token, sent = fake.mutations[0]
    assert token == TOKEN_A and sent["repositoryId"] == "R_" + REPO_A and sent["categoryId"] == "C_ann"
    assert sent["title"] == a["title"]
    assert sent["body"].startswith(a["body"] + "\n\n<!-- gc-agent-action:")
    with pytest.raises(ToolError):
        service.publish(task_id, a["id"], approved)                      # never twice
    assert len(fake.mutations) == 1


@pytest.mark.parametrize("change,reason", [
    ({"permission": "READ"}, "WRITE, MAINTAIN or ADMIN"),
    ({"discussions": False}, "Discussions are not enabled"),
    ({"private": True}, "not public"),
])
def test_every_publish_rechecks_permission(env, change, reason):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)
    task_id, a = _start(service, creds, REPO_A, FakeModel())
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    fake.repos[REPO_A].update(change)                                    # permission changed after approval
    with pytest.raises(ToolError, match=reason):
        service.publish(task_id, a["id"], approved)
    assert fake.mutations == [] and service.detail(task_id)["actions"][0]["status"] == "approved"


def test_broad_classic_token_is_refused(env):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)
    task_id, a = _start(service, creds, REPO_A, FakeModel())
    fake.scopes = "repo, admin:org, delete_repo"
    with pytest.raises(ToolError, match="more access than promotion needs"):
        service.preflight(task_id, a["id"])
    assert fake.mutations == []


# -- repository and credential isolation ---------------------------------------------------


def test_switching_repository_never_moves_tasks_or_tokens(env):
    fake, journal, creds, service, tmp_path = env
    creds.update(REPO_A, TOKEN_A)
    creds.update(REPO_B, TOKEN_B)
    task_a, a = _start(service, creds, REPO_A, FakeModel(TOKEN_A, TOKEN_B))
    creds.update(REPO_B)                       # user switches the selected target afterwards
    assert journal.get(task_a)["repository"] == REPO_A
    approved = service.approve(task_a, a["id"], "General", a["draft_sha256"])
    service.publish(task_a, a["id"], approved)
    write_tokens = {t for (m, p, t) in fake.requests if m == "POST"}
    assert write_tokens == {TOKEN_A}           # B's token never used for A's Task
    assert fake.discussions[REPO_B] == []      # nothing published in the other repository
    task_b, b = _start(service, creds, REPO_B, FakeModel(TOKEN_A, TOKEN_B))
    with pytest.raises(ToolError, match="not found for this Task"):
        service.approve(task_a, b["id"], "General", b["draft_sha256"])   # cross-Task action refused
    assert [x["repository"] for x in service.detail(task_b)["actions"]] == [REPO_B]
    raw_db = (tmp_path / "work.sqlite3").read_bytes()
    assert TOKEN_A.encode() not in raw_db and TOKEN_B.encode() not in raw_db


def test_missing_token_for_the_task_repository_never_falls_back(env):
    fake, _, creds, service, _ = env
    creds.update(REPO_B, TOKEN_B)              # only the OTHER repository has a token
    task_id, a = _start(service, creds, REPO_A, FakeModel())
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    with pytest.raises(ToolError, match=f"No GitHub token is saved for {REPO_A}"):
        service.publish(task_id, a["id"], approved)
    assert not any(t == TOKEN_B for (_, _, t) in fake.requests) and fake.mutations == []


# -- outbox, reconciliation, monitoring, improvement ---------------------------------------


def test_uncertain_outcome_is_reconciled_never_retried(env):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)
    task_id, a = _start(service, creds, REPO_A, FakeModel())
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    fake.mode = "timeout_after_create"
    assert service.publish(task_id, a["id"], approved) == {"status": "uncertain"}
    with pytest.raises(ToolError, match="approved"):
        service.publish(task_id, a["id"], approved)                      # no blind retry
    assert len(fake.mutations) == 1
    fake.mode = "ok"
    assert service.reconcile(task_id, a["id"])["status"] == "published"
    assert service.detail(task_id)["actions"][0]["published_url"] == f"https://github.com/{REPO_A}/discussions/100"


def test_uncertain_outcome_not_found_becomes_retryable_failure(env):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)
    task_id, a = _start(service, creds, REPO_A, FakeModel())
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    fake.mode = "timeout_before_create"
    assert service.publish(task_id, a["id"], approved)["status"] == "uncertain"
    fake.mode = "ok"
    assert service.reconcile(task_id, a["id"]) == {"status": "failed"}
    assert service.approve(task_id, a["id"], "General", a["draft_sha256"])   # re-approval required


def test_definite_github_refusal_marks_failed(env):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)
    task_id, a = _start(service, creds, REPO_A, FakeModel())
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    fake.mode = "graphql_error"
    assert service.publish(task_id, a["id"], approved)["status"] == "failed"


def test_monitor_and_improve_without_any_new_publication(env):
    fake, _, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)
    model = FakeModel(TOKEN_A)
    task_id, a = _start(service, creds, REPO_A, model)
    with pytest.raises(ToolError, match="Publish and monitor"):
        service.improve(task_id, model)
    approved = service.approve(task_id, a["id"], "General", a["draft_sha256"])
    service.publish(task_id, a["id"], approved)
    assert service.monitor(task_id, a["id"]) == {"comments": 3, "upvotes": 4, "reactions": 7,
                                                "locked": False, "closed": False}
    text = service.improve(task_id, model)
    detail = service.detail(task_id)
    assert detail["improvements"][0]["text"] == text
    assert detail["actions"][0]["metrics"][0]["reactions"] == 7
    assert len(fake.mutations) == 1
    events = [e["event"] for e in detail["events"]]
    assert events == ["draft_created", "approved", "publishing", "published",
                      "metrics_observed", "improvement_suggested"]
    assert TOKEN_A not in json.dumps(detail)


def test_research_refuses_private_repository_and_rebuilds_links(env):
    fake, _, _, _, _ = env
    evidence = pr.research(REPO_B)
    assert evidence["releases"][0]["url"] == f"https://github.com/{REPO_B}/releases/tag/v1.0.0-rc1"
    assert "Real README text." in evidence["readme_excerpt"]
    fake.repos[REPO_B]["private"] = True
    with pytest.raises(ToolError, match="public repositories"):
        pr.research(REPO_B)


def test_only_fixed_documents_can_be_sent():
    with pytest.raises(ToolError, match="fixed promotion"):
        pr._graphql("mutation { deleteRepository }", {}, TOKEN_A)


# -- HTTP routes ---------------------------------------------------------------------------


class MemorySettings:
    def __init__(self):
        self.data = {"provider": "openai", "model": "gpt-4.1-mini", "repository": "o/r",
                     "model_key": "sk-test-model-key-not-real-0001", "read_token": ""}

    def load(self):
        return dict(self.data)

    def public(self):
        return {"provider": "openai", "model": "gpt-4.1-mini", "repository": "o/r",
                "has_model_key": True, "has_read_token": False}


def test_promotion_routes_require_nonce_and_never_return_tokens(env):
    fake, journal, creds, service, _ = env
    creds.update(REPO_A, TOKEN_A)
    task_id, a = _start(service, creds, REPO_A, FakeModel())
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, service), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port

    def call(method, path, body=None, nonce=NONCE):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        headers = {"Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
                   "Content-Type": "application/json"}
        if nonce:
            headers["X-App-Nonce"] = nonce
        conn.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=headers)
        r = conn.getresponse()
        data = r.read().decode()
        conn.close()
        return r.status, data
    try:
        assert call("GET", "/api/promotion/settings", nonce=None)[0] == 403
        status, text = call("GET", "/api/promotion/settings")
        assert status == 200 and TOKEN_A not in text and REPO_A in text
        assert call("POST", f"/api/promotion/tasks/{task_id}/actions/{a['id']}/approve",
                    {"category": "General", "sha256": a["draft_sha256"]}, nonce="wrong")[0] == 403
        status, text = call("GET", f"/api/promotion/tasks/{task_id}/detail")
        assert status == 200 and TOKEN_A not in text and json.loads(text)["repository"] == REPO_A
        status, text = call("POST", f"/api/promotion/tasks/{task_id}/actions/{a['id']}/approve",
                            {"category": "General", "sha256": a["draft_sha256"]})
        assert status == 200
        approved = json.loads(text)["approved_sha256"]
        status, text = call("POST", f"/api/promotion/tasks/{task_id}/actions/{a['id']}/publish",
                            {"sha256": approved})
        assert status == 200 and json.loads(text)["status"] == "published"
        # A large edited announcement fits the promotion limit; V1 routes keep 12000 bytes.
        # (the action is already published, so the parsed edit is refused by state, not by size)
        big = {"title": "T", "body": "x" * 13000}
        status, text = call("POST", f"/api/promotion/tasks/{task_id}/actions/{a['id']}/edit", big)
        assert status == 400 and "max 6000" in text
        assert call("POST", "/api/settings", {"pad": "y" * 13000})[0] == 413
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_create_promotion_task_over_http_starts_service(env):
    """Regression: POST /api/tasks for Promotion raised UnboundLocalError (ModelSettings
    shadowed by a function-local import), the connection dropped and the browser
    showed "Failed to fetch"."""
    _, journal, creds, _, _ = env

    class RecordingPromotion:
        def __init__(self):
            self.models = []
            self.definitions = []

        def start(self, model, definition_id):
            self.models.append(model)
            self.definitions.append(definition_id)
            return 42

    promo = RecordingPromotion()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, promo), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("POST", "/api/tasks", body=json.dumps({
            "route": "domain", "selection": "Promotion", "definition_id": "promote_repository",
        }).encode(), headers={"Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
                              "Content-Type": "application/json", "X-App-Nonce": NONCE})
        r = conn.getresponse()
        body = json.loads(r.read().decode())
        conn.close()
        assert r.status == 202 and body == {"id": 42, "status": "running"}
        assert len(promo.models) == 1 and promo.definitions == ["promote_repository"]
        assert promo.models[0].settings.provider == "openai"
        assert promo.models[0].settings.model == "gpt-4.1-mini"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_preflight_without_token_is_a_clear_error_and_saved_token_survives_restart(env):
    """Regression for the endless "Checking…" state: with no token saved the
    preflight returns a clear 400 (never hangs); once saved via the settings route
    the token persists across a server restart (a new credentials instance on the
    same data directory) and the same preflight then succeeds."""
    _, journal, creds, service, root = env
    task_id, a = _start(service, creds, REPO_A, FakeModel())
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, service), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port

    def post(path, body):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("POST", path, body=json.dumps(body).encode(), headers={
            "Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
            "Content-Type": "application/json", "X-App-Nonce": NONCE})
        r = conn.getresponse()
        data = r.read().decode()
        conn.close()
        return r.status, data
    preflight = f"/api/promotion/tasks/{task_id}/actions/{a['id']}/preflight"
    try:
        status, text = post(preflight, {})
        assert status == 400
        assert json.loads(text)["error"] == f"No GitHub token is saved for {REPO_A}. Add it in Settings → Promotion."
        status, text = post("/api/promotion/settings", {"repository": REPO_A, "token": TOKEN_A})
        assert status == 200 and json.loads(text)["selected_has_token"] is True and TOKEN_A not in text
    finally:
        httpd.shutdown()
        httpd.server_close()
    restarted = pr.PromotionCredentials(root)
    assert restarted.public()["selected_has_token"] is True
    assert TOKEN_A.encode() not in (root / "promotion.dpapi").read_bytes()
    service2 = pr.PromotionService(journal, pr.PromotionStore(root / "work.sqlite3"), restarted)
    assert service2.preflight(task_id, a["id"])["can_publish"] is True


def test_route_parser_accepts_only_known_shapes():
    assert w._promotion_route("/api/promotion/tasks/7/detail") == (7, None, "detail")
    assert w._promotion_route("/api/promotion/tasks/7/actions/3/publish") == (7, 3, "publish")
    for bad in ("/api/promotion/tasks/x/detail", "/api/promotion/tasks/7/actions/x/publish",
                "/api/promotion/tasks/7/actions/3/publish/extra", "/api/tasks/7/detail"):
        assert w._promotion_route(bad) is None
