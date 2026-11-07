"""No-network verification of the independent, read-only CLI."""
import json

import httpx
import pytest

from github_community_agent import github_readonly as gh
from github_community_agent import read_cli


def test_cli_issues_list_is_read_only_and_scoped(monkeypatch, capsys):
    requests = []
    def fake(request):
        requests.append(request)
        return httpx.Response(200, json=[{
            "number": 7, "title": "Bug", "state": "open", "labels": []
        }])
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(fake))
    code = read_cli.main(["--repo", "example-org/project", "--resource", "issues"])
    output = json.loads(capsys.readouterr().out)
    assert code == 0
    assert output["repository"] == "example-org/project"
    assert output["issues"][0]["number"] == 7
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].url.host == "api.github.com"
    assert requests[0].headers.get("authorization") is None


def test_cli_discussions_requires_dedicated_token_not_gh_token(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_COMMUNITY_AGENT_READ_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "token_that_must_never_be_used_123456")
    called = []
    def fake(request):
        called.append(request)
        raise AssertionError("No network request permitted")
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(fake))
    code = read_cli.main(["--repo", "example-org/project", "--resource", "discussions"])
    captured = capsys.readouterr()
    assert code == 2
    assert "read-only GitHub token" in captured.err
    assert "token_that_must_never_be_used" not in captured.err
    assert not called


def test_cli_discussions_with_explicit_token_and_readonly_graphql(monkeypatch, capsys):
    token = "not_a_real_scoped_token_for_tests_123"
    monkeypatch.setenv("GITHUB_COMMUNITY_AGENT_READ_TOKEN", token)
    requests = []
    def fake(request):
        requests.append(request)
        return httpx.Response(200, json={"data": {"repository": {
            "isPrivate": False,
            "discussions": {"totalCount": 0, "nodes": [], "pageInfo": {}}
        }}})
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(fake))
    code = read_cli.main(["--repo", "example-org/project", "--resource", "discussions"])
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["repository"] == "example-org/project"
    assert token not in captured.out and token not in captured.err
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].url.host == "api.github.com"
    assert requests[0].url.path == "/graphql"
    assert json.loads(requests[0].content)["query"] == gh.DISCUSSIONS_QUERY


@pytest.mark.parametrize("argv", [
    ["--repo", "https://github.com/owner/repo", "--resource", "issues"],
    ["--repo", "example/repo", "--resource", "issues", "--mode", "discussion"],
    ["--repo", "example/repo", "--resource", "discussions", "--mode", "comments"],
    ["--repo", "example/repo", "--resource", "issues", "--after", "anything"],
    ["--repo", "example/repo", "--resource", "discussions", "--state", "open"],
])
def test_cli_invalid_invocation_is_refused_before_network(monkeypatch, argv):
    requests = []
    def fake(request):
        requests.append(request)
        raise AssertionError("No network permitted")
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(fake))
    with pytest.raises(SystemExit) as err:
        read_cli.main(argv)
    assert err.value.code == 2
    assert not requests


def test_cli_reports_http_error_without_raw_payload(monkeypatch, capsys):
    def fake(request):
        return httpx.Response(404, text="private-sensitive-test-value")
    monkeypatch.setattr(gh, "_transport", httpx.MockTransport(fake))
    code = read_cli.main(["--repo", "example-org/project", "--resource", "issues"])
    out = capsys.readouterr()
    assert code == 2
    assert "not found" in out.err
    assert "private-sensitive-test-value" not in out.err
