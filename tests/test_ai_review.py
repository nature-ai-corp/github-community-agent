"""Offline contract checks for real evidence-grounded AI community reviews."""
import json

import pytest

from github_community_agent import ai_review as ar
from github_community_agent import runtime as rt
from github_community_agent.errors import ToolError

REPO = "example-org/public-community"


def _mock_issues(monkeypatch, *, include_two=True):
    calls = []

    def fake(repo, args):
        assert repo == REPO
        calls.append(dict(args))
        if args["mode"] == "list":
            return json.dumps({"issues": [
                {"number": 7, "url": f"https://github.com/{REPO}/issues/7",
                 "title": "Bug when using tool", "state": "open"},
                *([{"number": 8, "url": f"https://github.com/{REPO}/issues/8",
                    "title": "Feature request"}] if include_two else []),
            ]})
        assert args["mode"] == "issue"
        number = args["number"]
        return json.dumps({"issues": [{
            "number": number, "title": f"Issue {number}",
            "url": f"https://github.com/{REPO}/issues/{number}",
            "body": "Steps to reproduce: run application, then get an error"
                    if number == 7 else "Please add a new capability",
        }]})

    monkeypatch.setattr(rt, "github_issues", fake)
    return calls


def test_ai_issue_review_uses_real_details_and_sources(monkeypatch):
    calls = _mock_issues(monkeypatch)
    seen = []

    def model(instruction, evidence):
        data = json.loads(evidence)
        seen.append((instruction, data))
        return "Issue #7: possible bug, verify steps. Source: https://github.com/" + REPO + "/issues/7"

    runtime = rt.CommunityRuntime(rt.CommunitySettings(REPO))
    result = ar.CommunityAnalyst(runtime, model).run("review_issues")
    assert [c["mode"] for c in calls] == ["list", "issue", "issue"]
    assert len(seen) == 1
    assert seen[0][1]["issues"][0]["body_excerpt"].startswith("Steps to reproduce")
    assert seen[0][1]["issues"][1]["body_excerpt"] == "Please add a new capability"
    assert len(result["issues"]) == 2
    assert result["detail_reads"] == 2
    assert result["requires_human_review"] is True
    assert result["read_only"] is True
    assert result["posted"] is False


def test_ai_community_report_without_discussion_access_is_explicitly_partial(monkeypatch):
    calls = _mock_issues(monkeypatch, include_two=False)
    observed = []

    def model(instruction, evidence):
        observed.append(json.loads(evidence))
        return "Partial report. Discussions were NOT checked."

    runtime = rt.CommunityRuntime(rt.CommunitySettings(REPO),
                                  discussion_token=lambda: None)
    result = ar.CommunityAnalyst(runtime, model).run("community_report")
    assert [c["mode"] for c in calls] == ["list", "issue"]
    assert observed[0]["discussions_checked"] is False
    assert result["incomplete"] is True
    assert result["discussions_checked"] is False
    assert result["posted"] is False


def test_issue_mismatch_fails_closed(monkeypatch):
    def fake(repo, args):
        items = [{"number": 7, "title": "Issue"}] if args["mode"] == "list" else [{"number": 77, "body": "unrelated"}]
        return json.dumps({"issues": items})
    monkeypatch.setattr(rt, "github_issues", fake)
    runtime = rt.CommunityRuntime(rt.CommunitySettings(REPO))
    with pytest.raises(ToolError, match="did not match"):
        ar.CommunityAnalyst(runtime, lambda *_: "Unsafe").run("review_issues")


def test_model_failure_is_not_hidden(monkeypatch):
    _mock_issues(monkeypatch, include_two=False)
    runtime = rt.CommunityRuntime(rt.CommunitySettings(REPO))
    with pytest.raises(ToolError, match="usable"):
        ar.CommunityAnalyst(runtime, lambda *_: "").run("review_issues")


def test_unsupported_ai_workflow_no_network(monkeypatch):
    calls = []
    monkeypatch.setattr(rt, "github_issues", lambda *_: calls.append(True))
    runtime = rt.CommunityRuntime(rt.CommunitySettings(REPO))
    with pytest.raises(ToolError, match="currently supports"):
        ar.CommunityAnalyst(runtime, lambda *_: "text").run("draft_replies")
    assert not calls


def test_report_input_disambiguates_issue_count_and_unverified_release(monkeypatch):
    _mock_issues(monkeypatch, include_two=True)
    observed = []
    def model(instruction, evidence):
        observed.append((instruction, json.loads(evidence)))
        return "Two issue records inspected; release signing status not independently verified."
    runtime = rt.CommunityRuntime(rt.CommunitySettings(REPO))
    result = ar.CommunityAnalyst(runtime, model).run("community_report")
    instruction, evidence = observed[0]
    assert "not the number of pages" in instruction.lower()
    assert "never call an installer signed" in instruction.lower()
    assert evidence["issue_page_count"] == 2
    assert evidence["total_pages_known"] is False
    assert "NOT number of pages" in evidence["issue_page_count_meaning"]
    assert result["total_pages_known"] is False
    assert result["issue_page_count"] == 2
