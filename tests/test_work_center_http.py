"""Exercise the REAL Work Center HTTP handler over loopback.

These tests start ``handler_factory`` on 127.0.0.1:0 and send real HTTP
requests, so the Host / Origin / nonce checks, size limits and error handling
are executed rather than matched as source text. No test reaches GitHub or a
model provider: only invalid Task payloads are submitted, which are rejected
before any workflow thread starts.
"""
from __future__ import annotations

import http.client
import json
import sys
import threading
from http.server import ThreadingHTTPServer

import pytest

from github_community_agent import work_center as w

NONCE = "test-nonce-0123456789abcdef"
SECRET = "sk-should-never-be-echoed-0f1e2d3c"


class MemorySettings:
    """Duck-typed stand-in for EncryptedSettings (DPAPI is Windows-only)."""

    def __init__(self):
        self.data = {"provider": "openai", "model": "gpt-4.1-mini", "repository": "o/r",
                     "model_key": SECRET, "read_token": ""}
        self.saves = 0

    def load(self):
        return dict(self.data)

    def public(self):
        return {"provider": self.data["provider"], "model": self.data["model"],
                "repository": self.data["repository"], "has_model_key": bool(self.data["model_key"]),
                "has_read_token": bool(self.data["read_token"])}

    def save(self, payload):
        self.saves += 1
        self.data.update({k: v for k, v in payload.items() if k in self.data})
        return self.public()


@pytest.fixture
def server(tmp_path):
    journal = w.Journal(tmp_path / "work.sqlite3")
    settings = MemorySettings()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0),
                                w.handler_factory(w.WorkService(journal), NONCE, settings))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_port

    def request(method, path, body=None, *, host=None, origin="default", nonce=NONCE, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        conn.putheader("Host", host or f"127.0.0.1:{port}")
        if origin == "default":
            origin = f"http://127.0.0.1:{port}"
        if origin is not None:
            conn.putheader("Origin", origin)
        if nonce is not None:
            conn.putheader("X-App-Nonce", nonce)
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        if method == "POST":
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", str(len(data)))
        conn.endheaders(data if method == "POST" else None)
        resp = conn.getresponse()
        payload = resp.read().decode("utf-8")
        headers = dict(resp.getheaders())
        conn.close()
        return resp.status, payload, headers

    request.port = port
    yield request, journal, settings
    httpd.shutdown()
    httpd.server_close()


def test_home_page_embeds_nonce_with_strict_csp(server):
    request, _, _ = server
    status, html, headers = request("GET", "/")
    assert status == 200
    assert f'const NONCE="{NONCE}"' in html and "__APP_NONCE__" not in html
    csp = headers["Content-Security-Policy"]
    assert f"script-src 'nonce-{NONCE}'" in csp and "frame-ancestors 'none'" in csp
    assert headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("host", ["localhost:{port}", "evil.example", "127.0.0.1:1", "127.0.0.1"])
def test_dns_rebinding_hosts_are_refused_for_every_get(server, host):
    request, _, _ = server
    for path in ("/", "/api/tasks", "/api/settings", "/api/definitions", "/static/gc.css"):
        status, _, _ = request("GET", path, host=host.format(port=request.port))
        assert status == 403, path


def test_get_api_requires_nonce_and_never_returns_secrets(server):
    request, _, _ = server
    assert request("GET", "/api/tasks", nonce=None)[0] == 403
    assert request("GET", "/api/settings", nonce="wrong")[0] == 403
    status, body, _ = request("GET", "/api/settings")
    assert status == 200 and SECRET not in body
    assert json.loads(body)["has_model_key"] is True
    assert request("GET", "/api/tasks")[0] == 200
    assert request("GET", "/static/gc.css")[0] == 200
    assert request("GET", "/nope")[0] == 404


@pytest.mark.parametrize("override", [
    {"nonce": None}, {"nonce": "wrong"}, {"origin": None}, {"origin": "http://evil.example"},
    {"origin": "http://localhost"}, {"host": "evil.example"},
])
def test_state_changing_posts_require_nonce_origin_and_host(server, override):
    request, journal, settings = server
    journal.finish(journal.create("review_issues", "o/r"), "failed", error="x")
    for path, body in (("/api/settings", {"repository": "attacker/repo"}),
                       ("/api/tasks/1/delete", {}), ("/api/tasks/1/review", {}),
                       ("/api/tasks", {"definition_id": "review_issues"})):
        status, _, _ = request("POST", path, body, **override)
        assert status == 403, (path, override)
    assert settings.saves == 0 and settings.data["repository"] == "o/r"
    assert [t["id"] for t in journal.list()] == [1]


def test_request_size_and_shape_limits(server):
    request, _, settings = server
    assert request("POST", "/api/settings", raw=b"{")[0] == 413
    assert request("POST", "/api/settings", raw=b"{" + b" " * w.MAX_REQUEST_BYTES + b"}")[0] == 413
    assert request("POST", "/api/settings", raw=b"[1, 2]")[0] == 400
    assert request("POST", "/api/unknown", {})[0] == 404
    assert settings.saves == 0


def test_invalid_task_is_rejected_without_record_or_echoing_input(server):
    request, journal, _ = server
    status, body, _ = request("POST", "/api/tasks", {
        "route": "work_type", "selection": SECRET, "definition_id": "promote_self"})
    assert status == 400
    assert SECRET not in body and "Invalid task selection" in body
    assert journal.list(include_archived=True) == []


def test_delete_and_review_only_apply_to_allowed_states(server):
    request, journal, _ = server
    failed = journal.create("review_issues", "o/r")
    journal.finish(failed, "failed", error="x")
    running = journal.create("review_issues", "o/r")
    drafted = journal.create("draft_issue", "o/r")
    journal.finish(drafted, "needs_attention", result={"posted": False})

    assert request("POST", f"/api/tasks/{running}/delete", {})[0] == 409
    assert request("POST", "/api/tasks/x/delete", {})[0] == 404
    status, body, _ = request("POST", f"/api/tasks/{failed}/delete", {})
    assert status == 200 and json.loads(body)["scope"] == "local_work_only"
    visible = [t["id"] for t in json.loads(request("GET", "/api/tasks")[1])["tasks"]]
    archived = json.loads(request("GET", "/api/tasks?include_archived=1")[1])["tasks"]
    assert failed not in visible and any(t["id"] == failed and t["deleted_utc"] for t in archived)

    assert request("POST", f"/api/tasks/{failed}/review", {})[0] == 409
    status, body, _ = request("POST", f"/api/tasks/{drafted}/review", {})
    assert status == 200 and json.loads(body) == {"id": drafted, "status": "finished", "posted": False}


def test_settings_save_goes_through_authorized_post_only(server):
    request, _, settings = server
    status, body, _ = request("POST", "/api/settings", {"repository": "owner/new"})
    assert status == 200 and settings.saves == 1
    assert json.loads(body)["repository"] == "owner/new" and SECRET not in body


@pytest.mark.skipif(sys.platform != "win32", reason="real DPAPI settings need Windows")
def test_real_dpapi_settings_never_leave_plaintext_on_disk_or_in_api(tmp_path):
    from github_community_agent.encrypted_settings import EncryptedSettings
    settings = EncryptedSettings(tmp_path)
    settings.save({"provider": "openai", "model": "gpt-4.1-mini", "repository": "o/r",
                   "model_key": SECRET, "read_token": ""})
    raw = (tmp_path / "settings.dpapi").read_bytes()
    assert SECRET.encode() not in raw and SECRET.encode("utf-16-le") not in raw
    assert SECRET not in json.dumps(settings.public())
    assert settings.load()["model_key"] == SECRET


def test_rejected_posts_reliably_return_their_status(server):
    # Rejected requests used to be answered without reading the body; Windows
    # then reset the connection (unread data -> RST), intermittently hiding
    # the 403/413 from the client. Repeat to make that race visible.
    request, _, settings = server
    body = {"repository": "x" * 9000}
    for _ in range(25):
        assert request("POST", "/api/settings", body, nonce="wrong")[0] == 403
        assert request("POST", "/api/settings", raw=b"{" + b" " * w.MAX_REQUEST_BYTES + b"}")[0] == 413
    assert settings.saves == 0


def test_lying_content_length_cannot_stall_a_rejected_request(server):
    import socket
    request, _, _ = server
    with socket.create_connection(("127.0.0.1", request.port), timeout=15) as s:
        host = f"127.0.0.1:{request.port}"
        s.sendall((f"POST /api/settings HTTP/1.1\r\nHost: {host}\r\nOrigin: http://{host}\r\n"
                   "X-App-Nonce: wrong\r\nContent-Length: 5000\r\n\r\n{}").encode())
        reply = s.recv(4096)
    assert reply.startswith(b"HTTP/1.0 403") or reply.startswith(b"HTTP/1.1 403")
