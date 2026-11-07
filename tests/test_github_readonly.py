"""Offline boundary tests for the extracted read-only GitHub tools."""

import json
import httpx
import pytest

from github_community_agent import github_readonly as gh
from github_community_agent.errors import ToolError

REPO = "nature-ai-corp/github-community-agent"


def test_repository_validation_rejects_url_and_traversal():
    assert gh.valid_repository(REPO)
    for value in ("https://github.com/a/b", "../test", "a/..", "a/b/c", "a/."):
        assert not gh.valid_repository(value)


def test_invalid_repo_cannot_generate_api_root():
    with pytest.raises(ToolError):
        gh.api_root("https://attacker.example/repo")


def test_readonly_issues_only_requests_fixed_github_host(monkeypatch):
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=[])
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(handle))
    result = json.loads(gh.github_issues(REPO, {"mode": "list"}))
    assert requests and all(r.method == "GET" for r in requests)
    assert all(r.url.host == "api.github.com" and r.url.scheme == "https" for r in requests)
    assert isinstance(result, dict)


def test_unsupported_issue_mode_does_not_make_network_request(monkeypatch):
    def unreachable(request):
        raise AssertionError("Unexpected network request")
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(unreachable))
    with pytest.raises(ToolError):
        gh.github_issues(REPO, {"mode": "delete"})


def test_no_implicit_repository_default():
    # A newly installed independent product must not silently point at the
    # maintainer's repository, including one that is currently private.
    assert gh.DEFAULT_REPOSITORY == ""
    with pytest.raises(ToolError):
        gh.api_root(gh.DEFAULT_REPOSITORY)
