"""Security regression tests for extracted GitHub reading code.

Network is fully mocked. No real GitHub token, live post, or public API call.
"""
import base64
import json

import httpx
import pytest

from github_community_agent import github_readonly as gh
from github_community_agent.errors import ToolError

REPO = "example-org/community-project"
FAKE_TOKEN = "not_a_real_test_token_1234567890"


@pytest.fixture
def github(monkeypatch):
    requests = []
    responses = []

    def handle(request):
        requests.append(request)
        assert responses, "Unexpected GitHub request"
        return responses.pop(0)

    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(handle))
    return requests, responses


def test_issues_exclude_pull_requests_and_canonicalize_links(github):
    requests, responses = github
    responses.append(httpx.Response(200, json=[
        {"number": 7, "title": "Help", "state": "open",
         "html_url": "https://attacker.invalid/phishing", "labels": "bad-shape"},
        {"number": 8, "title": "PR", "pull_request": {"url": "something"}},
        {"number": -5, "title": "Invalid"},
    ]))
    result = json.loads(gh.github_issues(REPO, {"mode": "list"}))
    assert len(result["issues"]) == 1
    assert result["issues"][0]["url"] == "https://github.com/example-org/community-project/issues/7"
    assert result["issues"][0]["labels"] == []
    assert "untrusted" in result["note"].lower()
    assert len(requests) == 1
    assert requests[0].url.host == "api.github.com"
    assert requests[0].headers.get("authorization") is None


@pytest.mark.parametrize("args", [
    {"mode": "list", "repo": "attacker/repo"},
    {"mode": "list", "url": "https://evil.invalid"},
    {"mode": "list", "page": True},
    {"mode": "list", "page": 999},
    {"mode": "issue", "number": 0},
    {"mode": "issue", "number": True},
    {"mode": "issue", "number": "7"},
    {"mode": "comments", "number": 7, "state": "open"},
])
def test_invalid_issues_args_never_reach_network(github, args):
    requests, _ = github
    with pytest.raises(ToolError):
        gh.github_issues(REPO, args)
    assert not requests


def test_redirect_not_followed_and_no_auth_leak(github):
    requests, responses = github
    responses.append(httpx.Response(302, headers={"Location": "https://attacker.invalid/redirect"}))
    with pytest.raises(ToolError, match="HTTP 302"):
        gh.github_issues(REPO, {"mode": "list"})
    assert len(requests) == 1
    assert requests[0].url.host == "api.github.com"


def test_oversize_response_is_blocked(github):
    _, responses = github
    responses.append(httpx.Response(200, content=b"x" * (gh.MAX_BYTES + 1)))
    with pytest.raises(ToolError, match="exceeded"):
        gh.github_issues(REPO, {"mode": "list"})


@pytest.mark.parametrize("status,headers,expected", [
    (401, {}, "rejected the token"),
    (403, {}, "refused access"),
    (403, {"x-ratelimit-remaining": "0"}, "rate limit"),
    (429, {}, "rate limit"),
    (404, {}, "not found"),
])
def test_http_errors_are_mapped_without_raw_payload(github, status, headers, expected):
    _, responses = github
    responses.append(httpx.Response(status, headers=headers, text="PRIVATE_FAKE_KEY"))
    with pytest.raises(ToolError) as err:
        gh.github_issues(REPO, {"mode": "list"})
    assert expected in str(err.value)
    assert "PRIVATE_FAKE_KEY" not in str(err.value)


def test_bad_json_produces_safe_error(github):
    _, responses = github
    responses.append(httpx.Response(200, content=b"not json"))
    with pytest.raises(ToolError, match="Unexpected GitHub API response"):
        gh.github_issues(REPO, {"mode": "list"})


def test_discussions_require_token_before_network(github):
    requests, _ = github
    with pytest.raises(ToolError, match="read-only GitHub token"):
        gh.github_discussions(lambda: None, {"mode": "list"}, REPO)
    assert requests == []


@pytest.mark.parametrize("cursor", [
    "javascript:alert(1)", "%%%invalid%%%", base64.b64encode(b"other:abc").decode(),
])
def test_invalid_discussion_cursor_never_uses_token(github, cursor):
    requests, _ = github
    called = []
    with pytest.raises(ToolError, match="end_cursor"):
        gh.github_discussions(lambda: called.append(True) or FAKE_TOKEN,
                              {"mode": "list", "after": cursor}, REPO)
    assert not called
    assert not requests


def test_graphql_only_allows_read_documents(github):
    requests, _ = github
    with pytest.raises(ToolError, match="read-only GitHub queries"):
        gh._graphql("mutation { deleteRepository(input: {}) { clientMutationId } }",
                    {}, FAKE_TOKEN)
    assert requests == []


def test_graphql_rejects_overscoped_classic_token(github):
    requests, responses = github
    responses.append(httpx.Response(200, headers={"X-OAuth-Scopes": "repo, read:discussion"},
                                    json={"data": {"repository": {"isPrivate": False}}}))
    with pytest.raises(ToolError, match="more access"):
        gh.github_discussions(lambda: FAKE_TOKEN, {"mode": "list"}, REPO)
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].url.path == "/graphql"
    assert requests[0].url.host == "api.github.com"


def test_graphql_refuses_private_repo(github):
    _, responses = github
    responses.append(httpx.Response(200, json={"data": {"repository": {"isPrivate": True}}}))
    with pytest.raises(ToolError, match="not public"):
        gh.github_discussions(lambda: FAKE_TOKEN, {"mode": "list"}, REPO)


def test_graphql_success_redacts_token_from_untrusted_text(github):
    requests, responses = github
    responses.append(httpx.Response(200, json={"data": {"repository": {
        "isPrivate": False,
        "discussions": {"totalCount": 1, "nodes": [{
            "number": 2, "title": "leaked " + FAKE_TOKEN, "isAnswered": False,
            "locked": False, "category": {"name": "Q&A"}, "comments": {"totalCount": 0}
        }], "pageInfo": {"hasNextPage": False, "endCursor": None}}
    }}}))
    result = gh.github_discussions(lambda: FAKE_TOKEN, {"mode": "list"}, REPO)
    assert FAKE_TOKEN not in result
    parsed = json.loads(result)
    assert "[REDACTED]" in parsed["discussions"][0]["title"]
    assert "untrusted" in parsed["note"].lower()
    assert len(requests) == 1
    assert requests[0].url.host == "api.github.com"
    assert requests[0].headers["authorization"] == "Bearer " + FAKE_TOKEN


def test_discussion_result_never_claims_write_permission(github):
    _, responses = github
    responses.append(httpx.Response(200, json={"data": {"repository": {
        "isPrivate": False,
        "discussions": {"totalCount": 0, "nodes": [], "pageInfo": {}}
    }}}))
    result = json.loads(gh.github_discussions(lambda: FAKE_TOKEN, {}, REPO))
    assert "Posting is turned off" in result["scope"]
    assert "read-only" in result["source"]
