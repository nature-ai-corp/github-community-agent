"""Additional runtime review regressions: preserve valid evidence and safe errors."""
import json

import pytest

from github_community_agent import runtime as rt
from github_community_agent.errors import ToolError

REPO = "example-org/community"


def test_model_receives_complete_json_even_when_source_body_is_oversize(monkeypatch):
    seen = []

    def fake_issues(repo, args):
        return json.dumps({"issues": [{
            "number": 7, "title": "help", "url": f"https://github.com/{REPO}/issues/7",
            "body": "large" * 3000,
        }]})

    def model(instruction, evidence):
        data = json.loads(evidence)
        seen.append(data)
        return "Could you provide a reproduction?"

    monkeypatch.setattr(rt, "github_issues", fake_issues)
    app = rt.CommunityRuntime(rt.CommunitySettings(REPO), model=model)
    result = app.run("draft_replies", target="issue", number=7)
    assert len(seen) == 1
    assert seen[0]["repository"] == REPO
    assert seen[0]["number"] == 7
    assert "untrusted" in seen[0]["warning"].lower()
    assert len(seen[0]["source"]["body"]) == 8000
    assert result["posted"] is False


@pytest.mark.parametrize("bad", [None, 27, [], {}])
def test_invalid_workflow_returns_safe_error_not_python_exception(bad):
    app = rt.CommunityRuntime(rt.CommunitySettings(REPO))
    with pytest.raises(ToolError, match="Unsupported community workflow"):
        app.run(bad)


def test_empty_discussion_token_does_not_claim_report_coverage(monkeypatch):
    calls = []

    def issues(repo, args):
        calls.append("issues")
        return json.dumps({"issues": []})

    def discussions(token, args, repo):
        calls.append("discussions")
        raise AssertionError("Must not try Discussions without a usable token")

    monkeypatch.setattr(rt, "github_issues", issues)
    monkeypatch.setattr(rt, "github_discussions", discussions)
    app = rt.CommunityRuntime(rt.CommunitySettings(REPO), discussion_token=lambda: "")
    result = app.run("community_report")
    assert result["incomplete"] is True
    assert result["discussions_checked"] is False
    assert calls == ["issues"]
