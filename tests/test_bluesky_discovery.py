"""Offline tests of the read-only Bluesky discovery boundary."""
from datetime import datetime, timezone

import httpx
import pytest

from github_community_agent.bluesky_discovery import (
    DiscoveryError, SEARCH_API, search_opportunities,
)


def _post(rkey="3n23dccbqbt3h", text="Helpful AI agent discussion", likes=4):
    did = "did:plc:c3nlceuqshyilc3zeps4vwlq"
    return {"uri": f"at://{did}/app.bsky.feed.post/{rkey}",
            "record": {"$type": "app.bsky.feed.post", "text": text,
                       "createdAt": "2026-11-12T01:34:37Z"},
            "author": {"did": did, "handle": "natureai.bsky.social"},
            "likeCount": likes, "replyCount": 2, "repostCount": 1}


def test_search_and_cross_query_deduplication():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"posts": [_post()]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        out = search_opportunities(["AI agent", "open source"], pages=1, client=c)
    assert out["count"] == 1 and out["scored"] is False
    assert out["posts"][0]["matched_queries"] == ["AI agent", "open source"]
    assert out["posts"][0]["url"].endswith("/post/3n23dccbqbt3h")
    assert all(str(x.url).startswith(SEARCH_API) and x.method == "GET" for x in calls)


def test_missing_metrics_are_not_zero():
    p = _post()
    del p["likeCount"]
    with httpx.Client(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"posts": [p]}))) as c:
        result = search_opportunities(["agent"], pages=1, client=c)
    assert result["posts"][0]["metrics"]["likeCount"] is None


def test_cutoff_enforced_locally():
    with httpx.Client(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"posts": [_post()]}))) as c:
        assert search_opportunities(["agent"], pages=1,
               since="2026-11-13T00:00:00Z", client=c)["count"] == 0


def test_invalid_posts_discarded():
    p = _post()
    p["uri"] = "https://malicious.invalid/"
    with httpx.Client(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"posts": [p]}))) as c:
        assert search_opportunities(["agent"], pages=1, client=c)["count"] == 0


def test_fail_closed_on_server_error():
    with httpx.Client(transport=httpx.MockTransport(
            lambda req: httpx.Response(429, json={"secret": "never show"}))) as c:
        with pytest.raises(DiscoveryError, match="search request failed"):
            search_opportunities(["agent"], client=c)


@pytest.mark.parametrize("queries", [[], ["x"] * 9, [""]])
def test_bad_queries(queries):
    with pytest.raises(DiscoveryError):
        search_opportunities(queries)


def test_time_paging_uses_until_not_cursor():
    urls = []
    def handler(req):
        urls.append(str(req.url))
        return httpx.Response(200, json={"posts": [_post()] if len(urls) == 1 else []})
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        result = search_opportunities(["agent"], pages=3, client=c)
    assert result["requests"] == 2
    assert "until=" in urls[1] and "cursor=" not in urls[1]
