"""Regression tests for malformed remote GraphQL payloads.

GitHub responses are untrusted. Shape errors must become safe ToolError
messages rather than uncaught Python exceptions or leaked response bodies.
"""
import httpx
import pytest

from github_community_agent import github_readonly as gh
from github_community_agent.errors import ToolError

REPO = "example-org/public-repo"
TOKEN = "test_not_a_real_token_123456789"


@pytest.mark.parametrize("payload", [
    {"data": ["not-an-object"]},
    {"data": "not-an-object"},
    {"errors": {"message": "sensitive payload"}},
    {"data": {"repository": {"isPrivate": False, "discussions": []}}},
    {"data": {"repository": {"isPrivate": False, "discussions": {"nodes": "not-a-list"}}}},
    {"data": {"repository": {"isPrivate": False, "discussions": {"nodes": [], "pageInfo": "not-an-object"}}}},
])
def test_malformed_discussions_listing_is_safe(monkeypatch, payload):
    monkeypatch.setattr(
        gh, "_transport", httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
    )
    with pytest.raises(ToolError) as err:
        gh.github_discussions(lambda: TOKEN, {"mode": "list"}, REPO)
    assert "sensitive payload" not in str(err.value)


@pytest.mark.parametrize("comments", [
    [],
    {"nodes": "wrong"},
    {"nodes": [], "pageInfo": "wrong"},
])
def test_malformed_discussion_comments_are_safe(monkeypatch, comments):
    payload = {"data": {"repository": {"isPrivate": False, "discussion": {
        "number": 5, "title": "Test", "comments": comments
    }}}}
    monkeypatch.setattr(
        gh, "_transport", httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
    )
    with pytest.raises(ToolError):
        gh.github_discussions(lambda: TOKEN, {"mode": "discussion", "number": 5}, REPO)


def test_extremely_large_rate_reset_timestamp_does_not_crash(monkeypatch):
    def handler(request):
        return httpx.Response(429, headers={"x-ratelimit-reset": "9" * 300})
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(handler))
    with pytest.raises(ToolError, match="rate limit"):
        gh.github_issues(REPO, {"mode": "list"})
