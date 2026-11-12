"""DEV Community (dev.to, Forem API v1): one technical article per approved Task action.

Verified by real-world acceptance (Task #23, 2026-11-12) and released through the Work Type gate.

Scope is deliberately small: the Agent creates ONE article in the connected project account
as a PRIVATE DRAFT, reads that draft back and compares it with the approved version, and
only after a separate confirmation publishes that same article (one ``PUT published=true``).
No comments, reactions, follows, edits of other articles, organizations or series.

Security
* The API key lives in its OWN Windows DPAPI file (``devto.dpapi``), never with GitHub tokens,
  Bluesky credentials or AI provider keys, never in the work database, never sent to the AI
  model, never logged or returned by the API. ``users/me`` is used only to bind the key to an
  account (numeric id + username); the e-mail it also returns is discarded.
* One fixed host (``https://dev.to``), a fixed set of API paths, no redirects followed.
* A DEV API key has no scopes; the key is used only for the calls in this module.
* No idempotency key exists on DEV: before creating, the account's own articles are searched
  for the exact title (a duplicate is refused); an uncertain outcome is reconciled by reading
  the account's own articles, never retried blindly.

Article rules (Forem source: Article/Tag models; DEV Terms §11; DEV guidelines for
AI-assisted articles): title at most 128 characters; at most 4 tags, each alphanumeric and at
most 30 characters; body Markdown without front matter (it would override the approved title,
tags or publish state) and without Liquid tags (embeds of content outside the approved text);
substantive, educational content, not designed primarily for promotion; truthful author
affiliation and AI-assistance disclosure.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import threading
from pathlib import Path

import httpx

from .encrypted_settings import SettingsError
from .errors import ToolError
from .windows_dpapi import protect_for_current_user, unprotect_for_current_user

PLATFORM = "dev.to"
HOST = "https://dev.to"
ACCEPT = "application/vnd.forem.api-v1+json"
USER_AGENT = "GitHubCommunityAgent-Promotion"
MAX_TITLE = 128            # Forem Article#title_length_based_on_type_of (full_post)
MAX_TAGS = 4               # Forem Article::MAX_TAG_LIST_SIZE
MAX_TAG_LENGTH = 30        # Forem Tag#validate_name
MAX_DESCRIPTION = 170
MIN_WORDS = 500
MAX_ARTICLE_CHARS = 20000
AI_DISCLOSURE_LEVEL = "some_ai"   # Forem AiDisclosable: not_disclosed | no_ai | some_ai | fully_autonomous
# Fixed publishing settings, part of every approval: personal account, no organization,
# no series, no canonical URL, no cover image, AI assistance disclosed.
PUBLISH_SETTINGS = {"platform": PLATFORM, "organization": None, "series": None, "canonical_url": None,
                    "main_image": None, "ai_disclosure_level": AI_DISCLOSURE_LEVEL}
_transport: httpx.BaseTransport | None = None  # replaced in tests only

API_KEY = re.compile(r"[A-Za-z0-9]{16,64}")
USERNAME = re.compile(r"[A-Za-z0-9_]{1,40}")
TAG = re.compile(r"[a-z0-9]{1,%d}" % MAX_TAG_LENGTH)
SECTIONS = ("DESCRIPTION:", "TAGS:", "ARTICLE:")

_AFFILIATION = re.compile(
    r"\b(i|we)\s+(maintain|built|build|develop|created|create|work on)\b|\bi'?m\s+(a|the|one of the)\s+"
    r"maintainers?\b|\bi am\s+(a|the|one of the)\s+maintainers?\b|\bdisclosure:", re.I)
_AI_DISCLOSURE = re.compile(
    r"\b(ai[- ]assisted|ai assistance|with the help of (an? )?ai|assisted by (an? )?ai|"
    r"(written|drafted|created|generated|prepared) with (the help of |the assistance of )?(an? )?ai)\b|#abotwrotethis",
    re.I)
_ADVERT = re.compile(
    r"\b(buy (it )?now|sign up (now|today)|limited[- ]time|discount|coupon|free trial|download (it )?(now|today)|"
    r"try it (now|today)|subscribe (now|today)|act now|best[- ]in[- ]class|game[- ]chang\w*|revolutionary|"
    r"must[- ]have|world[- ]class)\b", re.I)
_UNSAFE_HTML = re.compile(r"<\s*(script|iframe|style|object|embed|form|input)\b", re.I)
_FENCED = re.compile(r"```.*?```", re.S)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_MENTION = re.compile(r"(?<![\w/@.])@[A-Za-z0-9_]{2,30}\b")


class DevError(ToolError):
    """A definite refusal or failure with a fixed code (safe for Activity History)."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class DevUncertain(DevError):
    """The write may have reached DEV; reconcile before any new attempt."""


# -- the approved article ----------------------------------------------------------------------


def _section(body: str, label: str) -> str | None:
    start = body.find(label)
    if start < 0:
        return None
    start += len(label)
    ends = [body.find(o, start) for o in SECTIONS if o != label and body.find(o, start) >= 0]
    if label == "ARTICLE:":  # the article runs to the end; labels inside it are content
        ends = []
    return body[start:min(ends) if ends else len(body)].strip()


def normalize_tags(raw) -> list[str]:
    if not isinstance(raw, str):
        return []
    tags = []
    for part in raw.split(","):
        tag = part.strip().lstrip("#").lower()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def parse_article(body: str) -> dict:
    """Split a DEV draft body (DESCRIPTION / TAGS / ARTICLE sections) into its fields."""
    body = (body or "").replace("\r\n", "\n")
    head = body[:body.find("ARTICLE:")] if "ARTICLE:" in body else body
    return {"description": (_section(head, "DESCRIPTION:") or "").strip(),
            "tags": normalize_tags(_section(head, "TAGS:")),
            "markdown": (_section(body, "ARTICLE:") or "").strip()}


def _prose(markdown: str) -> str:
    return _INLINE_CODE.sub(" ", _FENCED.sub(" ", markdown))


def article_issues(title: str, article: dict) -> list[str]:
    """DEV's limits and content rules for the exact article that would be sent."""
    issues = []
    title = title or ""
    if not title.strip():
        issues.append("The DEV article needs a title.")
    elif len(re.sub(r"\s+", "", title)) > MAX_TITLE:
        issues.append(f"The title is longer than DEV's limit of {MAX_TITLE} characters.")
    desc, tags, md = article["description"], article["tags"], article["markdown"]
    if not desc:
        issues.append("Missing 'DESCRIPTION:' (one sentence for previews).")
    elif len(desc) > MAX_DESCRIPTION or "\n" in desc:
        issues.append(f"The description must be one line of at most {MAX_DESCRIPTION} characters.")
    if not tags:
        issues.append("Missing 'TAGS:' (1 to 4 tags).")
    elif len(tags) > MAX_TAGS:
        issues.append(f"DEV allows at most {MAX_TAGS} tags.")
    bad = [t for t in tags if not TAG.fullmatch(t)]
    if bad:
        issues.append(f"Tags must be lowercase letters and digits only, at most {MAX_TAG_LENGTH} characters: "
                      + ", ".join(bad[:4]) + ".")
    if not md:
        return issues + ["Missing 'ARTICLE:' (the Markdown article)."]
    if md.startswith("---"):
        issues.append("The article must not start with front matter ('---'); it would override the approved fields.")
    if "{%" in md or "{{" in md:
        issues.append("The article must not contain Liquid tags ({% %} / {{ }}).")
    if _UNSAFE_HTML.search(md):
        issues.append("The article must not contain script, iframe, style, object, embed or form HTML.")
    if re.search(r"\]\(\s*http://|<http://", md):
        issues.append("Links must use https://.")
    if len(md) > MAX_ARTICLE_CHARS:
        issues.append(f"The article is {len(md)} characters; the limit is {MAX_ARTICLE_CHARS}.")
    if md.count("```") % 2:
        issues.append("The article has an unclosed code block.")
    prose = _prose(md)
    words = len(re.findall(r"\b\w+\b", prose))
    if words < MIN_WORDS:
        issues.append(f"The article has {words} words of prose; a substantive DEV article needs at least {MIN_WORDS}.")
    if len(re.findall(r"(?m)^##\s+\S", md)) < 2:
        issues.append("The article needs at least two '## ' sections.")
    if not _AFFILIATION.search(md[:1500]):
        issues.append("Author affiliation ('I maintain …') is missing near the start of the article.")
    if not _AI_DISCLOSURE.search(md):
        issues.append("AI-assistance disclosure is missing (e.g. 'This article was written with the help of AI').")
    if _ADVERT.search(prose) or _ADVERT.search(title):
        issues.append("Advertising language: DEV articles must be educational, not promotional.")
    if _MENTION.search(prose):
        issues.append("The article must not @mention people or organizations.")
    return issues


def approval_sha256(repository: str, user_id: int, username: str, title: str, article: dict) -> str:
    """One exact action: account, title, complete body, description, tags and publishing settings."""
    data = {"platform": PLATFORM, "repository": repository.lower(), "user_id": user_id,
            "username": (username or "").lower(), "title": title, "description": article["description"],
            "tags": article["tags"], "body_markdown": article["markdown"], "settings": PUBLISH_SETTINGS}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _norm_body(text) -> str:
    return (text or "").replace("\r\n", "\n").strip() if isinstance(text, str) else ""


def _tags_of(article: dict) -> list[str]:
    for key in ("tags", "tag_list"):
        value = article.get(key)
        if isinstance(value, list):
            return sorted(str(t).lower() for t in value)
        if isinstance(value, str) and value.strip():
            return sorted(normalize_tags(value))
    return []


def compare(found: dict | None, expected: dict, *, published: bool) -> dict:
    """Field-by-field comparison of a DEV article with the approved action."""
    checks = {"found": found is not None}
    if found is None:
        return checks
    user = found.get("user") if isinstance(found.get("user"), dict) else {}
    checks.update({
        "id": found.get("id") == expected["id"],
        "account": user.get("user_id") == expected["user_id"] and str(user.get("username", "")).lower()
        == expected["username"].lower(),
        "title": found.get("title") == expected["title"],
        "description": (found.get("description") or "") == expected["description"],
        "tags": _tags_of(found) == sorted(expected["tags"]),
        "body": _norm_body(found.get("body_markdown")) == _norm_body(expected["markdown"]),
        "no_organization": not found.get("organization"),
        "state": (found.get("published_at") is not None if published else found.get("published") is False),
    })
    if published:
        checks["url"] = isinstance(found.get("url"), str) and found["url"].startswith(
            f"{HOST}/{expected['username']}/")
    return checks


# -- HTTP ----------------------------------------------------------------------------------------

_PATHS = re.compile(r"/api/(users/me|articles|articles/me/(all|unpublished|published)|articles/\d{1,12})")


def _request(method: str, path: str, *, api_key=None, body=None, params=None, write=False):
    if not _PATHS.fullmatch(path):
        raise DevError("Only the fixed DEV API calls of this application can be sent.", "path")
    headers = {"User-Agent": USER_AGENT, "Accept": ACCEPT}
    if api_key:
        headers["api-key"] = api_key
    try:
        with httpx.Client(timeout=httpx.Timeout(30, connect=10), follow_redirects=False, trust_env=False,
                          transport=_transport) as client:
            r = client.request(method, HOST + path, params=params, json=body, headers=headers)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise DevError("DEV could not be reached; nothing was sent.", "network") from None
    except httpx.TransportError:
        if write:
            raise DevUncertain("The connection ended before DEV answered; the outcome is uncertain.",
                               "uncertain") from None
        raise DevError("DEV could not be read (network).", "network") from None
    try:
        data = r.json()
    except ValueError:
        data = None
    if r.status_code >= 500 and write:
        raise DevUncertain(f"DEV answered HTTP {r.status_code}; the outcome is uncertain.", "uncertain")
    if r.status_code == 404 and not write:
        return None
    if r.status_code == 401:
        raise DevError("DEV refused the API key (HTTP 401).", "unauthorized")
    if r.status_code == 429:
        raise DevError("DEV's rate limit was reached; nothing was created. Try again later.", "rate_limited")
    if r.status_code not in (200, 201):
        err = data.get("error") if isinstance(data, dict) and isinstance(data.get("error"), str) else ""
        raise DevError(f"DEV refused the request (HTTP {r.status_code}{': ' + err[:120] if err else ''}).",
                       f"http_{r.status_code}")
    if not isinstance(data, (dict, list)):
        if write:
            raise DevUncertain("DEV returned an unreadable answer; the outcome is uncertain.", "uncertain")
        raise DevError("DEV returned an unexpected response.", "format")
    return data


def users_me(api_key: str) -> dict:
    """Bind a key to its account: numeric id and username only (the e-mail is discarded)."""
    data = _request("GET", "/api/users/me", api_key=api_key)
    uid, name = (data or {}).get("id"), (data or {}).get("username")
    if type(uid) is not int or not isinstance(name, str) or not USERNAME.fullmatch(name):
        raise DevError("DEV returned an unexpected account response.", "format")
    return {"user_id": uid, "username": name}


def create_draft(api_key: str, title: str, article: dict) -> dict:
    """WRITE 1: create the article as an unpublished (private) draft."""
    payload = {"article": {"title": title, "body_markdown": article["markdown"], "published": False,
                           "description": article["description"], "tags": list(article["tags"]),
                           "ai_disclosure_level": AI_DISCLOSURE_LEVEL}}
    data = _request("POST", "/api/articles", api_key=api_key, body=payload, write=True)
    if not isinstance(data, dict) or type(data.get("id")) is not int:
        raise DevUncertain("DEV's answer did not identify the created article; the outcome is uncertain.",
                           "uncertain")
    return data


def publish(api_key: str, article_id: int) -> dict:
    """WRITE 2: publish exactly that draft (after its read-back matched and the owner confirmed)."""
    data = _request("PUT", f"/api/articles/{int(article_id)}", api_key=api_key,
                    body={"article": {"published": True}}, write=True)
    if not isinstance(data, dict) or data.get("id") != article_id:
        raise DevUncertain("DEV's answer did not identify the published article; the outcome is uncertain.",
                           "uncertain")
    return data


def my_articles(api_key: str, which: str = "all", pages: int = 5) -> list[dict]:
    """The account's own articles (published and unpublished), newest first, with body_markdown."""
    found = []
    for page in range(1, pages + 1):
        data = _request("GET", f"/api/articles/me/{which}", api_key=api_key, params={"page": page, "per_page": 100})
        if not isinstance(data, list):
            raise DevError("DEV returned an unexpected article list.", "format")
        found.extend(a for a in data if isinstance(a, dict))
        if len(data) < 100:
            break
    return found


def public_article(article_id: int) -> dict | None:
    """Independent read-back: the public article API, without any API key."""
    data = _request("GET", f"/api/articles/{int(article_id)}")
    if data is not None and not isinstance(data, dict):
        raise DevError("DEV returned an unexpected article.", "format")
    return data


# -- the ONE connected project account ------------------------------------------------------------


class DevCredentials:
    """The connected DEV project account, in its own DPAPI file (devto.dpapi)."""

    def __init__(self, root: Path):
        self.root = root
        self.path = root / "devto.dpapi"
        self._lock = threading.RLock()

    def _verify(self):
        if sys.platform != "win32":
            raise SettingsError("DEV credentials require Windows user DPAPI.")
        if self.root.is_symlink() or self.path.is_symlink():
            raise SettingsError("Unsafe credential storage path.")

    def _load(self) -> dict | None:
        self._verify()
        try:
            ciphertext = self.path.read_bytes()
        except FileNotFoundError:
            return None
        try:
            data = json.loads(unprotect_for_current_user(ciphertext))
        except Exception as exc:
            raise SettingsError("DEV credentials cannot be decrypted.") from exc
        if (not isinstance(data, dict) or not API_KEY.fullmatch(str(data.get("api_key", "")))
                or type(data.get("user_id")) is not int or not USERNAME.fullmatch(str(data.get("username", "")))):
            raise SettingsError("Stored DEV credentials are invalid.")
        return data

    def _store(self, data: dict | None) -> None:
        self._verify()
        if data is None:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            return
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        encrypted = protect_for_current_user(json.dumps(data).encode("utf-8"))
        fd, temporary = tempfile.mkstemp(prefix=".gc-devto-", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(encrypted)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def public(self) -> dict:
        with self._lock:
            data = self._load()
        if not data:
            return {"connected": False}
        return {"connected": True, "username": data["username"], "user_id": data["user_id"]}

    def account(self) -> dict | None:
        """Internal: api_key, user_id and username. Never returned by the API."""
        with self._lock:
            return self._load()

    def connect(self, api_key) -> dict:
        """Check the key with one users/me read, then store key, id and username only."""
        api_key = api_key.strip() if isinstance(api_key, str) else ""
        if not API_KEY.fullmatch(api_key):
            raise SettingsError("Enter a DEV API key (DEV → Settings → Extensions → DEV Community API Keys).")
        me = users_me(api_key)
        with self._lock:
            self._store({"api_key": api_key, "user_id": me["user_id"], "username": me["username"]})
        return self.public()

    def remove(self) -> dict:
        with self._lock:
            self._store(None)
        return self.public()

    def checked(self) -> dict:
        """The stored key, re-checked now: it must still belong to the stored account."""
        data = self.account()
        if not data:
            raise DevError("No DEV account is connected. Connect it in Settings → Promotion.", "no_account")
        me = users_me(data["api_key"])
        if me["user_id"] != data["user_id"]:
            raise DevError("The DEV API key now belongs to a different account; nothing was sent.",
                           "account_mismatch")
        return data
