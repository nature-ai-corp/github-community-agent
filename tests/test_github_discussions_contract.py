"""More complete contract tests for the extracted GitHub Discussions reader.

All requests use httpx.MockTransport, with no real token or network access.
"""
import base64
import json

import httpx
import pytest

from github_community_agent import github_readonly as gh
from github_community_agent.errors import ToolError

REPO = "example-org/example-repo"
TOKEN = "test_read_only_token_not_real_12345678"


@pytest.fixture
def api(monkeypatch):
    requests = []
    queued = []

    def handle(request):
        requests.append(request)
        assert queued, "unexpected network request"
        return queued.pop(0)

    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(handle))
    return requests, queued


def test_discussion_detail_and_comment_links(api):
    requests, queued = api
    queued.append(httpx.Response(200, headers={"X-OAuth-Scopes": "read:discussion"}, json={
        "data": {"repository": {"isPrivate": False, "discussion": {
            "number": 15, "title": "Question", "body": "Hello", "author": {"login": "alice"},
            "category": {"name": "Q&A"}, "comments": {
                "totalCount": 1, "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [{"databaseId": 72, "body": "Answer", "author": {"login": "bob"},
                           "replies": {"totalCount": 0}, "isAnswer": True}]
            }
        }}}
    }))
    data = json.loads(gh.github_discussions(lambda: TOKEN, {"mode": "discussion", "number": 15}, REPO))
    assert data["discussion"]["url"] == "https://github.com/example-org/example-repo/discussions/15"
    assert data["comments"][0]["url"].endswith("/discussions/15#discussioncomment-72")
    assert data["comments"][0]["is_answer"] is True
    payload = json.loads(requests[0].content)
    assert payload["query"] == gh.DISCUSSION_QUERY
    assert payload["variables"]["owner"] == "example-org"
    assert payload["variables"]["name"] == "example-repo"
    assert payload["variables"]["number"] == 15


def test_graphql_pagination_cursor_is_forwarded_only_as_variable(api):
    requests, queued = api
    cursor = base64.b64encode(b"cursor:next").decode()
    queued.append(httpx.Response(200, json={"data": {"repository": {"isPrivate": False,
        "discussions": {"totalCount": 0, "nodes": [],
                        "pageInfo": {"hasNextPage": False, "endCursor": None}}
    }}}))
    gh.github_discussions(lambda: TOKEN, {"mode": "list", "after": cursor}, REPO)
    payload = json.loads(requests[0].content)
    assert payload["query"] == gh.DISCUSSIONS_QUERY
    assert payload["variables"]["after"] == cursor
    assert cursor not in payload["query"]


@pytest.mark.parametrize("payload,expected", [
    ({"errors": [{"type": "RATE_LIMITED", "message": "secret raw"}]}, "rate limit"),
    ({"errors": [{"type": "NOT_FOUND", "message": "secret raw"}]}, "not found"),
    ({"errors": [{"message": "secret raw"}]}, "could not answer"),
    ({"data": {"repository": None}}, "repository not found"),
])
def test_graphql_errors_do_not_expose_raw_responses(api, payload, expected):
    _, queued = api
    queued.append(httpx.Response(200, json=payload))
    with pytest.raises(ToolError) as exc:
        gh.github_discussions(lambda: TOKEN, {"mode": "list"}, REPO)
    assert expected in str(exc.value)
    assert "secret raw" not in str(exc.value)


def test_private_discussion_repository_is_refused(api):
    _, queued = api
    queued.append(httpx.Response(200, json={"data": {"repository": {
        "isPrivate": True, "discussions": {"nodes": [], "pageInfo": {}}
    }}}))
    with pytest.raises(ToolError, match="not public"):
        gh.github_discussions(lambda: TOKEN, {"mode": "list"}, REPO)


def test_rejected_discussion_number_never_sends_token(api):
    requests, _ = api
    with pytest.raises(ToolError):
        gh.github_discussions(lambda: TOKEN, {"mode": "discussion", "number": True}, REPO)
    assert not requests


def test_token_never_printed_in_success_output(api):
    _, queued = api
    queued.append(httpx.Response(200, json={"data": {"repository": {"isPrivate": False,
        "discussions": {"totalCount": 1, "nodes": [{
            "number": 13, "title": "question", "category": {"name": TOKEN},
            "comments": {"totalCount": 0}
        }], "pageInfo": {}}
    }}}))
    result = gh.github_discussions(lambda: TOKEN, {"mode": "list"}, REPO)
    assert TOKEN not in result
    assert "[REDACTED]" in result


def test_github_api_does_not_follow_redirect_for_discussions(api):
    requests, queued = api
    queued.append(httpx.Response(302, headers={"location": "https://invalid.example/steal"}))
    with pytest.raises(ToolError, match="HTTP 302"):
        gh.github_discussions(lambda: TOKEN, {"mode": "list"}, REPO)
    assert len(requests) == 1
    assert requests[0].url.host == "api.github.com"


def test_discussions_never_use_private_default():
    assert gh.DEFAULT_REPOSITORY == ""
    assert not gh.valid_repository(gh.DEFAULT_REPOSITORY)


def test_transient_graphql_detail_timeout_retries_once_without_any_write(monkeypatch):
    requests = []
    def handle(request):
        requests.append(request)
        if len(requests) == 1:
            raise httpx.ReadTimeout("simulated network timeout", request=request)
        return httpx.Response(200, json={"data": {"repository": {
            "isPrivate": False,
            "discussion": {
                "number": 32, "title": "Welcome", "body": "Community welcome",
                "category": {"name": "Announcements"},
                "comments": {"totalCount": 0, "pageInfo": {"hasNextPage": False},
                             "nodes": []},
            },
        }}})
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(handle))
    data = json.loads(gh.github_discussions(lambda: TOKEN, {"mode": "discussion", "number": 32}, REPO))
    assert data["discussion"]["number"] == 32
    assert len(requests) == 2
    for request in requests:
        assert request.method == "POST" and request.url.host == "api.github.com"
        query = json.loads(request.content)["query"]
        assert query == gh.DISCUSSION_QUERY
        assert "mutation" not in query.lower()
        assert b"number" in request.content


def test_repeated_discussion_timeout_has_specific_safe_error(monkeypatch):
    requests = []
    def handle(request):
        requests.append(request)
        raise httpx.ReadTimeout("secret from transport", request=request)
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(handle))
    with pytest.raises(ToolError, match="timed out") as exc:
        gh.github_discussions(lambda: TOKEN, {"mode": "discussion", "number": 32}, REPO)
    assert len(requests) == 2
    assert TOKEN not in str(exc.value)
    assert "secret" not in str(exc.value)


def test_non_timeout_http_error_is_not_retried(monkeypatch):
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(403)
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(handle))
    with pytest.raises(ToolError, match="HTTP 403"):
        gh.github_discussions(lambda: TOKEN, {"mode": "discussion", "number": 32}, REPO)
    assert len(requests) == 1


def test_github_readonly_rest_get_does_not_retry_timeout(monkeypatch):
    requests = []
    def handle(request):
        requests.append(request)
        raise httpx.ConnectTimeout("no connection", request=request)
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(handle))
    with pytest.raises(ToolError, match="timed out"):
        gh.github_issues(REPO, {"mode": "list"})
    assert len(requests) == 1
