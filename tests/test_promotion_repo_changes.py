"""Repository Optimization: Research -> Propose -> Review -> Approve -> Apply -> Verify.

Offline: a GitHub-like mock with the REST endpoints the workflow may use. Covers
exact before/after proposals, per-change selection (skip), exact-change approval,
README through a NEW branch + pull request (never main, never merged), separate
approval for Description and Topics, permission and stale-state refusals,
uncertain outcomes resolved by verification, the allowlist, and the release gate.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from github_community_agent import promotion as pr
from github_community_agent import work_center as w
from github_community_agent.errors import ToolError

from test_promotion import (NONCE, REPO_A, REPO_B, TOKEN_A, TOKEN_B, FakeGitHub, FakeModel, MemorySettings,
                            env)  # noqa: F401

OLD_README = ("# Product\n\nIt is not affiliated with, sponsored by, or endorsed by GitHub, Inc.\n\n"
              "**No official independent Windows installer or V1 release has been published.**\n\n"
              "## Features\n\n- Review Issues\n- Review Discussions\n")
NEW_README = OLD_README.replace(
    "**No official independent Windows installer or V1 release has been published.**",
    "**v1.0.0-rc1 has been publicly released with an unsigned Windows installer.**")


def _sha(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()


class RepoGitHub(FakeGitHub):
    """Adds repository REST reads/writes. Writes need the repository's own token."""

    def __init__(self):
        super().__init__()
        self.state = {r: {"description": f"{r} product", "topics": [], "branches": {"main": "c0"},
                          "files": {"main": OLD_README}, "pulls": []} for r in self.repos}
        self.writes: list[tuple[str, str]] = []
        self.fail = None  # e.g. ("POST", "pulls", "timeout_after") to simulate an uncertain outcome

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/graphql":
            return super().handler(request)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        self.requests.append((request.method, path, token))
        repo = next((r for r in self.repos if path.startswith(f"/repos/{r}")), None)
        if repo is None:
            return httpx.Response(404, json={})
        st, cfg, rest = self.state[repo], self.repos[repo], path[len(f"/repos/{repo}"):]
        if request.method != "GET":
            if token != cfg["token"]:
                return httpx.Response(404, json={})
            self.writes.append((request.method, rest))
            if self.fail and self.fail[:2] == (request.method, rest):
                if self.fail[2] == "error_500":
                    return httpx.Response(500, json={})
        body = json.loads(request.content) if request.content else {}
        q = dict(request.url.params)
        if request.method == "GET" and rest == "":
            return httpx.Response(200, json={"private": False, "default_branch": "main",
                                             "description": st["description"], "topics": st["topics"],
                                             "stargazers_count": 0, "forks_count": 0, "open_issues_count": 4,
                                             "has_discussions": True, "license": {"spdx_id": "Apache-2.0"}})
        if rest == "/readme":
            return super()._rest(path)
        if rest == "/releases":
            return super()._rest(path)
        if rest == "/contents/README.md":
            branch = q.get("ref") or body.get("branch") or "main"
            if request.method == "GET":
                if branch not in st["files"]:
                    return httpx.Response(404, json={})
                text = st["files"][branch]
                return httpx.Response(200, json={"encoding": "base64", "sha": _sha(text),
                                                 "content": base64.b64encode(text.encode()).decode()})
            if branch == "main":
                raise AssertionError("the app must never commit to main")
            if body["sha"] != _sha(st["files"][branch]):
                return httpx.Response(409, json={})
            st["files"][branch] = base64.b64decode(body["content"]).decode()
            return httpx.Response(200, json={"commit": {"sha": "c1"}})
        if rest == "/git/ref/heads/main":
            return httpx.Response(200, json={"object": {"sha": st["branches"]["main"]}})
        if rest == "/git/refs" and request.method == "POST":
            name = body["ref"].removeprefix("refs/heads/")
            if name in st["branches"]:
                return httpx.Response(422, json={})
            st["branches"][name] = body["sha"]
            st["files"][name] = st["files"]["main"]
            return httpx.Response(201, json={"ref": body["ref"]})
        if rest == "/pulls" and request.method == "POST":
            number = 100 + len(st["pulls"])
            st["pulls"].append({"number": number, "state": "open", "merged": False,
                                "head": {"ref": body["head"]}, "base": {"ref": body["base"]}, "body": body["body"]})
            if self.fail and self.fail[:2] == ("POST", "/pulls") and self.fail[2] == "timeout_after":
                raise httpx.ReadTimeout("lost response")
            return httpx.Response(201, json={"number": number, "html_url": "https://evil.example/ignored"})
        if rest == "/pulls" and request.method == "GET":
            owner_branch = q.get("head", "")
            return httpx.Response(200, json=[p for p in st["pulls"]
                                             if f"{repo.split('/')[0]}:{p['head']['ref']}" == owner_branch])
        if rest.startswith("/pulls/") and request.method == "GET":
            found = [p for p in st["pulls"] if p["number"] == int(rest.split("/")[2])]
            return httpx.Response(200, json=found[0]) if found else httpx.Response(404, json={})
        if rest == "" and request.method == "PATCH":
            if cfg["permission"] != "ADMIN":
                return httpx.Response(403, json={})
            st["description"] = body["description"]
            return httpx.Response(200, json={})
        if rest == "/topics" and request.method == "PUT":
            if cfg["permission"] != "ADMIN":
                return httpx.Response(403, json={})
            st["topics"] = body["names"]
            return httpx.Response(200, json={"names": body["names"]})
        return httpx.Response(404, json={})


class ChangeModel(FakeModel):
    def __init__(self, *tokens, changeset=None):
        super().__init__(*tokens)
        self.changeset = changeset or {"description": "Read-only AI assistant for GitHub community management.",
                                       "topics": ["github", "community-management", "windows"],
                                       "readme_markdown": NEW_README}

    def __call__(self, instruction, evidence):
        if instruction.startswith(pr.CHANGESET_INSTRUCTION):
            for t in self.tokens:
                assert t not in evidence
            self.inputs.append(instruction + "\n" + evidence)
            return json.dumps(self.changeset)
        return super().__call__(instruction, evidence)


@pytest.fixture
def repo_env(env, monkeypatch):
    monkeypatch.setenv(pr.DEV_WORK_TYPES_ENV, "1")  # Repository Optimization is development code
    fake = RepoGitHub()
    monkeypatch.setattr(pr.gh, "_transport", httpx.MockTransport(fake.handler))
    _, journal, creds, service, root = env
    return fake, journal, creds, service, root


def _task(service, creds, repo=REPO_A, model=None):
    creds.update(repo)
    task_id = service.start(model or ChangeModel(TOKEN_A, TOKEN_B), "promote_repository_optimization")
    return task_id, {c["kind"]: c for c in service.detail(task_id)["changes"]}


def test_proposals_show_live_before_and_exact_after_without_writing(repo_env):
    fake, journal, creds, service, _ = repo_env
    creds.update(REPO_A, TOKEN_A)
    task_id, ch = _task(service, creds)
    assert set(ch) == {"description", "topics", "readme"} and all(c["status"] == "proposed" for c in ch.values())
    assert ch["description"]["before_value"] == f"{REPO_A} product"
    assert json.loads(ch["topics"]["proposed_value"]) == ["community-management", "github", "windows"]
    assert ch["readme"]["before_value"] == OLD_README and ch["readme"]["proposed_value"] == NEW_README
    assert "+**v1.0.0-rc1 has been publicly released" in ch["readme"]["diff"]
    assert ch["readme"]["branch"] == f"gca/readme-t{task_id}-c{ch['readme']['id']}"
    assert "open a pull request into main" in ch["readme"]["action"] and "Nothing is merged" in ch["readme"]["action"]
    assert fake.writes == [] and all(t == "" for _, _, t in fake.requests)  # no token used to propose


def test_readme_change_creates_branch_commit_and_pull_request_then_verifies(repo_env):
    fake, journal, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    creds.update(REPO_A, TOKEN_A)
    c = ch["readme"]
    with pytest.raises(ToolError, match="Only an approved change"):
        service.apply_change(task_id, c["id"], c["change_sha256"])
    with pytest.raises(ToolError, match="does not match"):
        service.approve_change(task_id, c["id"], "0" * 64)
    approved = service.approve_change(task_id, c["id"], c["change_sha256"])
    assert fake.writes == []
    out = service.apply_change(task_id, c["id"], approved)
    st = fake.state[REPO_A]
    assert out["status"] == "applied" and out["pr_url"] == f"https://github.com/{REPO_A}/pull/100"
    assert fake.writes == [("POST", "/git/refs"), ("PUT", "/contents/README.md"), ("POST", "/pulls")]
    assert st["files"][c["branch"]] == NEW_README and st["files"]["main"] == OLD_README  # main untouched
    assert st["pulls"][0]["base"]["ref"] == "main" and st["pulls"][0]["merged"] is False
    v = out["verification"]
    assert v["branch_readme_matches_approved"] and v["base_branch_readme_unchanged"] and v["pr_state"] == "open"
    stored = {x["kind"]: x for x in service.detail(task_id)["changes"]}["readme"]
    assert stored["status"] == "applied" and stored["result"]["pr_url"] == out["pr_url"]
    events = [e["event"] for e in service.detail(task_id)["events"]]
    assert f"change#{c['id']}:approved" in events and f"change#{c['id']}:verified" in events


def test_description_and_topics_need_their_own_approvals(repo_env):
    fake, _, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    creds.update(REPO_A, TOKEN_A)
    d, t = ch["description"], ch["topics"]
    service.apply_change(task_id, d["id"], service.approve_change(task_id, d["id"], d["change_sha256"]))
    assert fake.state[REPO_A]["description"] == "Read-only AI assistant for GitHub community management."
    assert fake.state[REPO_A]["topics"] == []  # topics untouched: not approved
    with pytest.raises(ToolError, match="Only an approved change"):
        service.apply_change(task_id, t["id"], t["change_sha256"])
    out = service.apply_change(task_id, t["id"], service.approve_change(task_id, t["id"], t["change_sha256"]))
    assert out["status"] == "applied" and fake.state[REPO_A]["topics"] == ["community-management", "github", "windows"]
    assert fake.writes == [("PATCH", ""), ("PUT", "/topics")]


def test_metadata_requires_admin(repo_env):
    fake, _, creds, service, _ = repo_env
    task_id, ch = _task(service, creds, repo=REPO_B)  # REPO_B token has WRITE only
    creds.update(REPO_B, TOKEN_B)
    d = ch["description"]
    approved = service.approve_change(task_id, d["id"], d["change_sha256"])
    with pytest.raises(ToolError, match="ADMIN is required"):
        service.apply_change(task_id, d["id"], approved)
    assert fake.writes == []
    r = ch["readme"]  # WRITE is enough for a branch + pull request
    assert service.apply_change(task_id, r["id"], service.approve_change(task_id, r["id"], r["change_sha256"]))[
        "status"] == "applied"


def test_selection_skip_and_edit_cancel_approval(repo_env):
    fake, _, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    creds.update(REPO_A, TOKEN_A)
    service.skip_change(task_id, ch["topics"]["id"])
    d = ch["description"]
    approved = service.approve_change(task_id, d["id"], d["change_sha256"])
    service.edit_change(task_id, d["id"], "Edited description.")
    now = {c["kind"]: c for c in service.detail(task_id)["changes"]}
    assert now["topics"]["status"] == "skipped"
    assert now["description"]["status"] == "proposed" and now["description"]["approved_sha256"] is None
    with pytest.raises(ToolError, match="Only an approved change"):
        service.apply_change(task_id, d["id"], approved)
    assert fake.writes == []


def test_invalid_generated_values_are_incomplete_until_edited(repo_env):
    _, _, creds, service, _ = repo_env
    bad = ChangeModel(changeset={"description": "Line one\nline two", "topics": ["AI", "GitHub-agent"],
                                 "readme_markdown": "# Short"})
    task_id, ch = _task(service, creds, model=bad)
    assert all(c["status"] == "incomplete" for c in ch.values())
    assert "Invalid topic names" in ch["topics"]["error"]
    assert "independence disclaimer" in ch["readme"]["error"]
    with pytest.raises(ToolError, match="Only a proposed"):
        service.approve_change(task_id, ch["topics"]["id"], ch["topics"]["change_sha256"])
    service.edit_change(task_id, ch["topics"]["id"], "ai, github-agent")
    assert {c["kind"]: c for c in service.detail(task_id)["changes"]}["topics"]["status"] == "proposed"


def test_stale_repository_state_is_never_overwritten(repo_env):
    fake, _, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    creds.update(REPO_A, TOKEN_A)
    d = ch["description"]
    approved = service.approve_change(task_id, d["id"], d["change_sha256"])
    fake.state[REPO_A]["description"] = "Changed by someone else"
    out = service.apply_change(task_id, d["id"], approved)
    assert out["status"] == "failed" and "changed since this proposal" in out["error"]
    assert fake.writes == [] and fake.state[REPO_A]["description"] == "Changed by someone else"


def test_lost_pull_request_response_is_uncertain_then_verified(repo_env):
    fake, _, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    creds.update(REPO_A, TOKEN_A)
    r = ch["readme"]
    fake.fail = ("POST", "/pulls", "timeout_after")
    out = service.apply_change(task_id, r["id"], service.approve_change(task_id, r["id"], r["change_sha256"]))
    assert out == {"status": "uncertain"}
    fake.fail = None
    v = service.verify_change(task_id, r["id"])
    assert v["status"] == "applied" and v["pr_url"].endswith("/pull/100")
    assert len(fake.state[REPO_A]["pulls"]) == 1  # never retried blindly


def test_failed_pull_request_without_result_is_not_claimed(repo_env):
    fake, _, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    creds.update(REPO_A, TOKEN_A)
    r = ch["readme"]
    fake.fail = ("POST", "/pulls", "error_500")
    fake.state[REPO_A]["pulls"] = []
    out = service.apply_change(task_id, r["id"], service.approve_change(task_id, r["id"], r["change_sha256"]))
    assert out["status"] == "uncertain"
    fake.state[REPO_A]["pulls"] = []  # GitHub really has no pull request
    assert service.verify_change(task_id, r["id"])["status"] == "failed"


def test_only_allowlisted_requests_and_no_merge_endpoint():
    assert all(m in ("GET", "PATCH", "PUT", "POST") for m, _ in pr._REST_ROUTES)
    assert not any("merge" in path for path in pr._REST_ROUTES.values())
    assert pr._REST_ROUTES[("PUT", "readme")].endswith("/contents/README.md")
    with pytest.raises(ToolError, match="fixed repository-change"):
        pr._rest("PUT", "merge", REPO_A, TOKEN_A)
    with pytest.raises(ToolError, match="fixed repository-change"):
        pr._rest("DELETE", "repo", REPO_A, TOKEN_A)


def test_changes_are_excluded_from_the_release_build(repo_env, monkeypatch):
    _, _, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    monkeypatch.delenv(pr.DEV_WORK_TYPES_ENV)
    d = ch["description"]
    with pytest.raises(ToolError, match="not available in this release"):
        service.approve_change(task_id, d["id"], d["change_sha256"])


def test_change_routes_over_http(repo_env):
    fake, journal, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    creds.update(REPO_A, TOKEN_A)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), w.handler_factory(
        w.WorkService(journal, service), NONCE, MemorySettings(), creds))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_port

    def post(path, body, nonce=NONCE):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.request("POST", path, body=json.dumps(body).encode(), headers={
            "Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}",
            "Content-Type": "application/json", "X-App-Nonce": nonce})
        r = conn.getresponse()
        data = r.read().decode()
        conn.close()
        return r.status, data
    try:
        c = ch["readme"]
        base = f"/api/promotion/tasks/{task_id}/changes/{c['id']}"
        assert post(base + "/approve", {"sha256": c["change_sha256"]}, nonce="wrong")[0] == 403
        status, text = post(base + "/edit", {"value": NEW_README + "\nMore.\n" + "x" * 50000})
        assert status == 200  # a large README edit fits the promotion request limit
        status, text = post(base + "/approve", {"sha256": c["change_sha256"]})
        assert status == 400 and "does not match" in text  # the edit changed the exact change
        now = {x["kind"]: x for x in service.detail(task_id)["changes"]}["readme"]
        status, text = post(base + "/approve", {"sha256": now["change_sha256"]})
        assert status == 200
        status, text = post(base + "/apply", {"sha256": json.loads(text)["approved_sha256"]})
        assert status == 200 and json.loads(text)["status"] == "applied"
        assert TOKEN_A not in text
    finally:
        httpd.shutdown()
        httpd.server_close()


# --- Apply feedback, Activity History and duplicate prevention -------------------------

def _activity(journal, task_id):
    return [e["event"] for e in next(t for t in journal.list() if t["id"] == task_id)["activity"]]


def test_apply_refusals_and_failures_are_recorded_in_activity_history(repo_env):
    fake, journal, creds, service, _ = repo_env
    task_id, ch = _task(service, creds, repo=REPO_B)  # REPO_B token has WRITE only: metadata is refused
    creds.update(REPO_B, TOKEN_B)
    d = ch["description"]
    with pytest.raises(ToolError, match="Only an approved change"):
        service.apply_change(task_id, d["id"], d["change_sha256"])  # not approved yet
    approved = service.approve_change(task_id, d["id"], d["change_sha256"])
    with pytest.raises(ToolError, match="not the approved change"):
        service.apply_change(task_id, d["id"], "0" * 64)
    with pytest.raises(ToolError, match="ADMIN is required"):
        service.apply_change(task_id, d["id"], approved)
    r = ch["readme"]  # WRITE is enough for README, but main changed after the proposal
    approved_r = service.approve_change(task_id, r["id"], r["change_sha256"])
    fake.state[REPO_B]["files"]["main"] = OLD_README + "Edited elsewhere."
    assert service.apply_change(task_id, r["id"], approved_r)["status"] == "failed"  # stale: nothing written
    assert fake.writes == []
    events = _activity(journal, task_id)
    i = d["id"]
    assert [e for e in events if e.startswith(f"change#{i}:")] == [
        f"change#{i}:apply_requested", f"change#{i}:apply_refused:not_approved", f"change#{i}:approved",
        f"change#{i}:apply_requested", f"change#{i}:apply_refused:approval_mismatch",
        f"change#{i}:apply_requested", f"change#{i}:apply_refused:permission"]
    assert f"change#{r['id']}:apply_failed_stale" in events
    # Fixed codes only: no error text, tokens or repository content in Activity History.
    assert all(w._SAFE_EVENT.fullmatch(e) for e in events)
    assert not any(TOKEN_B in e or "ADMIN" in e for e in events)
    # Refusals are also in the promotion event log shown with the change.
    detail_events = [e["event"] for e in service.detail(task_id)["events"]]
    assert f"change#{i}:apply_refused:permission" in detail_events
    assert {c["kind"]: c for c in service.detail(task_id)["changes"]}["description"]["status"] == "approved"


def test_missing_token_refusal_is_recorded(repo_env):
    fake, journal, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)  # no token saved for REPO_A
    d = ch["description"]
    approved = service.approve_change(task_id, d["id"], d["change_sha256"])
    with pytest.raises(ToolError, match="No GitHub token"):
        service.apply_change(task_id, d["id"], approved)
    assert f"change#{d['id']}:apply_refused:no_token" in _activity(journal, task_id) and fake.writes == []


def test_successful_apply_and_verify_are_recorded(repo_env):
    fake, journal, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    creds.update(REPO_A, TOKEN_A)
    d = ch["description"]
    assert service.apply_change(task_id, d["id"], service.approve_change(
        task_id, d["id"], d["change_sha256"]))["status"] == "applied"
    assert service.verify_change(task_id, d["id"])["status"] == "applied"
    i = d["id"]
    assert [e for e in _activity(journal, task_id) if e.startswith(f"change#{i}:")] == [
        f"change#{i}:approved", f"change#{i}:apply_requested", f"change#{i}:applied_verified", f"change#{i}:verified"]


def test_duplicate_apply_is_refused_and_github_is_written_once(repo_env):
    fake, journal, creds, service, _ = repo_env
    task_id, ch = _task(service, creds)
    creds.update(REPO_A, TOKEN_A)
    d = ch["description"]
    approved = service.approve_change(task_id, d["id"], d["change_sha256"])
    entered, release = threading.Event(), threading.Event()

    def slow(request):  # hold the first request inside its GitHub write
        if request.method == "PATCH":
            entered.set()
            assert release.wait(10)
        return fake.handler(request)
    pr.gh._transport = httpx.MockTransport(slow)  # restored by monkeypatch at teardown
    results = {}
    first = threading.Thread(target=lambda: results.setdefault("first", service.apply_change(task_id, d["id"], approved)))
    first.start()
    assert entered.wait(10)
    with pytest.raises(ToolError, match="already being applied"):
        service.apply_change(task_id, d["id"], approved)  # second click while the first is running
    release.set()
    first.join(10)
    assert results["first"]["status"] == "applied"
    with pytest.raises(ToolError, match="Only an approved change"):
        service.apply_change(task_id, d["id"], approved)  # and never again after it was applied
    assert fake.writes == [("PATCH", "")]
    events = _activity(journal, task_id)
    assert f"change#{d['id']}:apply_refused:duplicate" in events
    assert f"change#{d['id']}:apply_refused:already_applied" in events


def test_journal_activity_accepts_only_fixed_event_codes(env):
    _, journal, _, _, _ = env
    task_id = journal.create("review_issues", REPO_A)
    assert journal.record_event(task_id, "change#1:apply_refused:permission") is True
    for bad in ("Refused: ADMIN is required", "x" * 81, "change#1:<script>", ""):
        with pytest.raises(ValueError):
            journal.record_event(task_id, bad)
    assert journal.record_event(999999, "change#1:approved") is False
