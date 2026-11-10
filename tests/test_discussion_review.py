"""Offline contract verification for read-only Discussions AI workflow."""
import json

import pytest

from github_community_agent import runtime as rt
from github_community_agent import discussion_review as dr
from github_community_agent.errors import ToolError

REPO = "example-org/public-community"
TOKEN = "fake_read_token_1234567890"


def setup_discussions(monkeypatch, count=2):
    called = []
    def fake(token, args, repo):
        assert repo == REPO
        assert token() == TOKEN
        called.append(dict(args))
        if args["mode"] == "list":
            return json.dumps({
                "discussions": [
                    {"number": n, "url": f"https://github.com/{REPO}/discussions/{n}",
                     "title": f"Question {n}", "category": "Q&A", "answered": n == 1}
                    for n in range(1, count + 1)
                ],
                "has_next_page": False,
            })
        number = args["number"]
        return json.dumps({
            "discussion": {"number": number,
                           "url": f"https://github.com/{REPO}/discussions/{number}",
                           "title": f"Question {number}", "body": "How does this work?",
                           "category": "Q&A", "answered": number == 1},
            "comments": [{"url": f"https://github.com/{REPO}/discussions/{number}#discussioncomment-12",
                          "body": "Please check the documentation", "is_answer": True}],
            "has_next_page": False,
        })
    monkeypatch.setattr(rt, "github_discussions", fake)
    return called


def test_real_detail_content_passed_to_ai_without_token(monkeypatch):
    calls = setup_discussions(monkeypatch)
    seen = []
    def model(instruction, evidence):
        seen.append((instruction, json.loads(evidence)))
        return "Discussion #1 needs human review."
    app = rt.CommunityRuntime(rt.CommunitySettings(REPO),
                              discussion_token=lambda: TOKEN)
    result = dr.review_discussions(app, model)
    assert [x["mode"] for x in calls] == ["list", "discussion", "discussion"]
    assert len(seen) == 1
    assert seen[0][1]["discussions"][0]["body_excerpt"] == "How does this work?"
    assert seen[0][1]["discussions"][0]["comments_in_sample"][0]["body_excerpt"] == "Please check the documentation"
    assert TOKEN not in json.dumps(seen)
    assert result["discussions_analyzed"] == 2
    assert result["read_only"] and not result["posted"]
    assert result["requires_human_review"]


def test_token_missing_no_github_request(monkeypatch):
    monkeypatch.setattr(rt, "github_discussions",
                        lambda *_: (_ for _ in ()).throw(AssertionError("network not allowed")))
    app = rt.CommunityRuntime(rt.CommunitySettings(REPO))
    with pytest.raises(ToolError, match="read-only GitHub token"):
        dr.review_discussions(app, lambda *_: "text")


def test_details_must_match_list(monkeypatch):
    def bad(token, args, repo):
        if args["mode"] == "list":
            return json.dumps({"discussions": [{
                "number": 7, "url": f"https://github.com/{REPO}/discussions/7"}]})
        return json.dumps({"discussion": {"number": 77, "body": "unrelated"}, "comments": []})
    monkeypatch.setattr(rt, "github_discussions", bad)
    app = rt.CommunityRuntime(rt.CommunitySettings(REPO), discussion_token=lambda: TOKEN)
    with pytest.raises(ToolError, match="did not match"):
        dr.review_discussions(app, lambda *_: "text")


def test_bounded_detail_requests(monkeypatch):
    calls = setup_discussions(monkeypatch, count=9)
    app = rt.CommunityRuntime(rt.CommunitySettings(REPO), discussion_token=lambda: TOKEN)
    output = dr.review_discussions(app, lambda *_: "Limited review.")
    assert len([x for x in calls if x["mode"] == "discussion"]) == dr.MAX_DISCUSSIONS
    assert output["discussions_in_fetched_page"] == 9
    assert output["discussions_analyzed"] == dr.MAX_DISCUSSIONS
    assert output["sample_limited"] is True
    assert output["total_pages_known"] is False


def test_empty_model_fails_closed(monkeypatch):
    setup_discussions(monkeypatch, count=1)
    app = rt.CommunityRuntime(rt.CommunitySettings(REPO), discussion_token=lambda: TOKEN)
    with pytest.raises(ToolError, match="usable"):
        dr.review_discussions(app, lambda *_: "")


def test_empty_discussions_does_not_invent_items(monkeypatch):
    setup_discussions(monkeypatch, count=0)
    app = rt.CommunityRuntime(rt.CommunitySettings(REPO), discussion_token=lambda: TOKEN)
    result = dr.review_discussions(app, lambda *_: "No discussions observed in this page.")
    assert result["discussions"] == []
    assert result["discussions_analyzed"] == 0
