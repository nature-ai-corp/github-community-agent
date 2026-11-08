"""Desktop application's production workflow routing and evidence boundaries.

Offline tests call the same execute_workflow entrypoint as the UI. These do
not substitute for actual human-operated desktop E2E acceptance.
"""
import pytest

from github_community_agent import desktop
from github_community_agent.errors import ToolError

REPO = "example-org/public-repo"


def test_rejects_unknown_workflow_without_contacts():
    with pytest.raises(ToolError, match="Unsupported"):
        desktop.execute_workflow(REPO, "delete_repository", provider="openai",
                                 model_name="gpt-4.1-mini", model_key="fake_api_key_123456")


def test_missing_model_key_fails_closed():
    with pytest.raises(ToolError, match="API key"):
        desktop.execute_workflow(REPO, "review_issues", provider="openai",
                                 model_name="gpt-4.1-mini", model_key="")


def test_actual_runtime_route_issue(monkeypatch):
    observed = []
    def fake_issues(self, mode="list", number=None):
        observed.append(("github_issues", mode, number))
        if mode == "list":
            return {"issues": [{"number": 12, "url": f"https://github.com/{REPO}/issues/12"}]}
        return {"issues": [{"number": 12, "url": f"https://github.com/{REPO}/issues/12",
                            "body": "Real issue body in mocked contract", "title": "Important"}]}
    def fake_model(self, instruction, evidence):
        observed.append(("model", instruction, evidence))
        return "Evidence-grounded review."
    monkeypatch.setattr(desktop.CommunityRuntime, "_issues", fake_issues)
    monkeypatch.setattr(desktop.ChatCompletionsModel, "__call__", fake_model)
    result = desktop.execute_workflow(REPO, "review_issues",
                                      provider="openai", model_name="gpt-4.1-mini",
                                      model_key="fake_api_key_123456")
    assert result["read_only"] is True
    assert result["posted"] is False
    assert result["issues_analyzed"] == 1
    assert observed[0] == ("github_issues", "list", None)
    assert observed[1] == ("github_issues", "issue", 12)
    assert observed[2][0] == "model"


def test_actual_runtime_route_discussion(monkeypatch):
    def fake_discussions(self, mode="list", number=None):
        if mode == "list":
            return {"discussions": [{"number": 7, "url": f"https://github.com/{REPO}/discussions/7"}]}
        return {"discussion": {"number": number, "url": f"https://github.com/{REPO}/discussions/{number}",
                               "body": "Question details"},
                "comments": []}
    monkeypatch.setattr(desktop.CommunityRuntime, "_discussions", fake_discussions)
    monkeypatch.setattr(desktop.ChatCompletionsModel, "__call__",
                        lambda self, instruction, evidence: "Question needs answer.")
    result = desktop.execute_workflow(REPO, "review_discussions",
                                      provider="openai", model_name="gpt-4.1-mini",
                                      model_key="fake_api_key_123456",
                                      discussion_token="fake_read_token_1234567890")
    assert result["discussions_analyzed"] == 1
    assert result["read_only"] is True and result["posted"] is False


def test_actual_runtime_route_draft(monkeypatch):
    def fake_issues(self, mode="list", number=None):
        assert mode == "issue" and number == 22
        return {"issues": [{"number": 22, "url": f"https://github.com/{REPO}/issues/22",
                             "body": "Question about release"}]}
    monkeypatch.setattr(desktop.CommunityRuntime, "_issues", fake_issues)
    monkeypatch.setattr(desktop.ChatCompletionsModel, "__call__",
                        lambda self, instruction, evidence: "Draft only.")
    result = desktop.execute_workflow(REPO, "draft_replies",
                                      provider="openai", model_name="gpt-4.1-mini",
                                      model_key="fake_api_key_123456", target="issue", number=22)
    assert result["posted"] is False
    assert result["draft"] == "Draft only."


def test_evidence_export_contains_no_credentials():
    outcome = {"workflow": "review_issues", "repository": REPO,
               "read_only": True, "posted": False,
               "issues": [{"url": f"https://github.com/{REPO}/issues/12"}]}
    evidence = desktop.evidence_record(outcome, started_at="2026-11-08T01:00:00+00:00",
                                        completed_at="2026-11-08T01:00:01+00:00")
    assert evidence["application"] == "GitHub Community Agent"
    assert evidence["evidence_schema"] == 1
    assert evidence["result"]["issues"][0]["url"].endswith("/issues/12")
    assert "api_key" not in str(evidence).lower()
    assert "token" not in str(evidence).lower()


def test_rejects_unverified_write_or_unsafe_evidence():
    for result in ({"read_only": True, "posted": True},
                   {"read_only": False, "posted": False}, {}):
        with pytest.raises(ToolError, match="Cannot export"):
            desktop.evidence_record(result, started_at="start", completed_at="end")
