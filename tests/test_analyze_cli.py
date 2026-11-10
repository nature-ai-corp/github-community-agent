"""Read-only AI analysis command checks; fake model and GitHub only."""
import json

from github_community_agent import ai_review, analyze_cli


def test_missing_key_blocks_analysis(monkeypatch, capsys):
    monkeypatch.delenv(analyze_cli.MODEL_KEY_ENV, raising=False)
    assert analyze_cli.main(["--repo", "a/b", "--workflow", "review_issues",
                             "--provider", "openai", "--model", "gpt-4.1-mini"]) == 2
    assert "dedicated" in capsys.readouterr().err


def test_opted_in_ai_cli_output_remains_read_only(monkeypatch, capsys):
    monkeypatch.setenv(analyze_cli.MODEL_KEY_ENV, "test_fake_key_123456789")
    calls = []
    def fake_run(self, workflow):
        calls.append(workflow)
        return {"workflow": workflow, "read_only": True, "posted": False,
                "analysis": "Grounded preview only.", "requires_human_review": True}
    monkeypatch.setattr(ai_review.CommunityAnalyst, "run", fake_run)
    rc = analyze_cli.main(["--repo", "example/public",
                           "--workflow", "review_issues",
                           "--provider", "openai", "--model", "gpt-4.1-mini"])
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert calls == ["review_issues"]
    assert result["read_only"] is True and result["posted"] is False
    assert "test_fake_key" not in json.dumps(result)
