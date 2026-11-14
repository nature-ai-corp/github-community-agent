"""Read-only Bluesky opportunity discovery, before valuation.

Independent of the existing Bluesky publisher: this module makes only unauthenticated
GET calls to the fixed Bluesky AppView endpoint. No account credentials, session,
database write, engagement action or general engine is involved.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

SEARCH_API = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"
_AT_URI = re.compile(r"^at://(did:plc:[a-z2-7]{24}|did:web:[a-z0-9.-]+)/app\\.bsky\\.feed\\.post/([a-zA-Z0-9._~-]{1,128})$")
# Bluesky's public search currently may reject cursor requests from anonymous clients.
# Use 'until' date paging in latest-first results instead.
MAX_QUERIES = 8
MAX_PAGES = 5
MAX_CANDIDATES = 200


class DiscoveryError(ValueError):
    """A bounded, safe error that does not expose provider response bodies."""


def _utc_stamp(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise DiscoveryError("Invalid timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DiscoveryError("Invalid timestamp") from exc
    if result.tzinfo is None:
        raise DiscoveryError("Timezone is required")
    return result.astimezone(timezone.utc)


def _parse_post(post: dict) -> dict | None:
    if not isinstance(post, dict):
        return None
    uri = post.get("uri")
    match = _AT_URI.fullmatch(uri) if isinstance(uri, str) else None
    record = post.get("record")
    author = post.get("author")
    if not match or not isinstance(record, dict) or not isinstance(author, dict):
        return None
    if record.get("$type", "app.bsky.feed.post") != "app.bsky.feed.post":
        return None
    text = record.get("text")
    created = record.get("createdAt")
    if not isinstance(text, str) or not text.strip() or len(text) > 5000:
        return None
    try:
        created_at = _utc_stamp(created)
    except DiscoveryError:
        return None
    handle = author.get("handle")
    if not isinstance(handle, str) or len(handle) > 253:
        handle = None
    counts = {}
    for key in ("likeCount", "replyCount", "repostCount", "quoteCount"):
        value = post.get(key)
        counts[key] = value if type(value) is int and value >= 0 else None
    return {
        "uri": uri,
        "url": "https://bsky.app/profile/" + quote(match.group(1), safe=":") + "/post/" + quote(match.group(2), safe=""),
        "author_did": match.group(1),
        "author_handle": handle,
        "text": text,
        "created_at": created_at.isoformat(),
        "metrics": counts,
        "facts_source": "Bluesky public search API",
    }


def search_opportunities(queries: list[str], *, pages: int = 2,
                         page_size: int = 50, max_candidates: int = 100,
                         since: str | None = None, client: httpx.Client | None = None) -> dict:
    """Search and deduplicate public Bluesky posts; return *unscored* evidence.

    Fail closed on API errors. Returned metrics may be absent; missing != zero.
    The time-window 'since' is enforced locally even when the API ignores it.
    Requests use latest ordering and the oldest observed post timestamp for
    subsequent 'until' pages (no anonymous cursor assumption).
    """
    if not isinstance(queries, list) or not 1 <= len(queries) <= MAX_QUERIES:
        raise DiscoveryError("Provide 1-8 search queries")
    if any(not isinstance(q, str) or not q.strip() or len(q) > 120 for q in queries):
        raise DiscoveryError("Invalid search query")
    if type(pages) is not int or not 1 <= pages <= MAX_PAGES:
        raise DiscoveryError("Pages must be 1-5")
    if type(page_size) is not int or not 1 <= page_size <= 100:
        raise DiscoveryError("Page size must be 1-100")
    if type(max_candidates) is not int or not 1 <= max_candidates <= MAX_CANDIDATES:
        raise DiscoveryError("Maximum candidates must be 1-200")
    cutoff = _utc_stamp(since) if since is not None else None
    seen = {}
    request_count = 0
    own_client = client is None
    session = client if client is not None else httpx.Client(timeout=15.0, follow_redirects=False,
                                                             trust_env=False)
    try:
        for raw in queries:
            query = raw.strip()
            until = None
            for _ in range(pages):
                params = {"q": query, "sort": "latest", "limit": page_size}
                if until is not None:
                    params["until"] = until
                if cutoff is not None:
                    params["since"] = cutoff.isoformat().replace("+00:00", "Z")
                try:
                    response = session.get(SEARCH_API, params=params, headers={"Accept": "application/json"})
                    request_count += 1
                    response.raise_for_status()
                    payload = response.json()
                except (httpx.HTTPError, ValueError) as exc:
                    raise DiscoveryError("Bluesky search request failed") from exc
                if not isinstance(payload, dict) or not isinstance(payload.get("posts"), list):
                    raise DiscoveryError("Unexpected Bluesky search response")
                oldest = None
                new_uris = 0
                for raw_post in payload["posts"][:page_size]:
                    post = _parse_post(raw_post)
                    if post is None:
                        continue
                    stamp = _utc_stamp(post["created_at"])
                    if oldest is None or stamp < oldest:
                        oldest = stamp
                    if cutoff is not None and stamp < cutoff:
                        continue
                    if post["uri"] not in seen:
                        post["matched_queries"] = [query]
                        seen[post["uri"]] = post
                        new_uris += 1
                    elif query not in seen[post["uri"]]["matched_queries"]:
                        seen[post["uri"]]["matched_queries"].append(query)
                    if len(seen) >= max_candidates:
                        break
                if len(seen) >= max_candidates or not payload["posts"] or oldest is None:
                    break
                next_until = oldest.isoformat(timespec="microseconds").replace("+00:00", "Z")
                if until is not None and next_until >= until:
                    break
                if cutoff is not None and oldest <= cutoff:
                    break
                if new_uris == 0:
                    break
                until = next_until
            if len(seen) >= max_candidates:
                break
    finally:
        if own_client:
            session.close()
    posts = sorted(seen.values(), key=lambda p: (p["created_at"], p["uri"]), reverse=True)
    return {"posts": posts, "count": len(posts), "requests": request_count,
            "scored": False, "source": SEARCH_API}
