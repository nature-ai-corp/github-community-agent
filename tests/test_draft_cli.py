"""One-shot Draft CLI must not use implicit credentials or post anything."""
import json

import pytest

from github_community_agent import draft_cli
from github_community_agent import runtime as rt
from github_community_agent import model_provider as mp

REPO = "example-org/public-project"
KEY = "fake_dedicated_api_key_123456789"


def test_draft_cli_rejects_missing_dedicated_key(monkeypatch, capsys):
    monkeypatch.delenv(draft_cli.KEY_ENV, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "MUST_NOT_BE_USED")
    monkeypatch.setenv("GITHUB_TOKEN", "MUST_NOT_BE_USED")
    status = draft_cli.main(["--repo", REPO, "--target", "issue", "--number", "7",
                             "--provider", "deepseek", "--model", "deepseek-chat"])
    assert status == 2
    err = capsys.readouterr().err
    assert draft_cli.KEY_ENV in err
    assert "MUST_NOT_BE_USED" not in err


def test_cli_mocked_ai_draft_and_read_only_result(monkeypatch, capsys):
    monkeypatch.setenv(draft_cli.KEY_ENV, KEY)
    calls = []

    def issues(repo, args):
        calls.append(("github_read", repo, args))
        return json.dumps({"issues": [{
            "number": 7, "body": "What can I do?",
            "title": "Help", "url": f"https://github.com/{REPO}/issues/7"}]})

    def fake_model_call(self, instruction, evidence):
        calls.append(("model", instruction, json.loads(evidence)))
        return "Could you please provide a minimal example?"

    monkeypatch.setattr(rt, "github_issues", issues)
    monkeypatch.setattr(mp.ChatCompletionsModel, "__call__", fake_model_call)
    status = draft_cli.main(["--repo", REPO, "--target", "issue", "--number", "7",
                             "--provider", "deepseek", "--model", "deepseek-chat"])
    result = json.loads(capsys.readouterr().out)
    assert status == 0
    assert result["read_only"] and result["posted"] is False
    assert result["requires_human_review"]
    assert result["draft"] == "Could you please provide a minimal example?"
    assert len(calls) == 2
    assert calls[0][0] == "github_read"
    assert calls[1][0] == "model"
    assert KEY not in json.dumps(result)


@pytest.mark.parametrize("args", [
    ["--repo", "example-org/public-project", "--target", "issue", "--number", "7",
     "--provider", "compatible", "--model", "model"],
    ["--repo", "invalid/url/extra", "--target", "issue", "--number", "7",
     "--provider", "deepseek", "--model", "deepseek-chat"],
])
def test_invalid_config_does_not_attempt_gitHub_read(monkeypatch, capsys, args):
    monkeypatch.setenv(draft_cli.KEY_ENV, KEY)
    def forbidden(*args, **kwargs):
        raise AssertionError("No GitHub call should occur")
    monkeypatch.setattr(rt, "github_issues", forbidden)
    assert draft_cli.main(args) == 2
