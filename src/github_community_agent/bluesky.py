"""Bluesky: the first Social Media platform of the V2 Promotion Agent (development only).

Scope is deliberately small: ONE post (``app.bsky.feed.post``) in the connected project
account, created by ONE ``com.atproto.repo.createRecord`` call after the owner approved the
exact action. No likes, follows, replies, reposts, deletes or other collections.

Security
* Credentials (handle, DID, PDS host, app password) live in their OWN Windows DPAPI file
  (``bluesky.dpapi``), never with GitHub tokens or AI provider keys, never in the work
  database, never sent to the AI model, never logged or returned by the API.
* Only app passwords (xxxx-xxxx-xxxx-xxxx) are accepted, never an account password.
* Fixed hosts: the bsky.social entryway (login), the account's Bluesky-hosted PDS
  (``*.bsky.network`` or ``bsky.social``, taken from the DID document) and the public
  AppView ``public.api.bsky.app`` (unauthenticated read-back). No redirects followed.
* Durable outbox: the record key (a TID) is chosen and stored BEFORE the request, so an
  uncertain outcome is reconciled by reading exactly that record, never retried blindly.

Text rules follow the ``app.bsky.feed.post`` Lexicon: text at most 300 graphemes and
3000 UTF-8 bytes; links are ``app.bsky.richtext.facet#link`` facets with UTF-8 byte offsets.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sys
import tempfile
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .encrypted_settings import SettingsError
from .errors import ToolError
from .windows_dpapi import protect_for_current_user, unprotect_for_current_user

PLATFORM = "bluesky"
ENTRYWAY = "https://bsky.social"
APPVIEW = "https://public.api.bsky.app"
COLLECTION = "app.bsky.feed.post"
MAX_GRAPHEMES = 300   # Lexicon app.bsky.feed.post#text maxGraphemes
MAX_BYTES = 3000      # Lexicon app.bsky.feed.post#text maxLength (UTF-8 bytes)
USER_AGENT = "GitHubCommunityAgent-Promotion"
_transport: httpx.BaseTransport | None = None  # replaced in tests only

HANDLE = re.compile(r"(?=.{3,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]([a-z0-9-]{0,61}[a-z0-9])?")
APP_PASSWORD = re.compile(r"[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}")
DID = re.compile(r"did:plc:[a-z2-7]{24}|did:web:[a-z0-9.-]{3,253}")
RKEY = re.compile(r"[234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12}")
CID = re.compile(r"[a-z2-7]{20,100}")


class BlueskyError(ToolError):
    """A definite refusal or failure with a fixed code (safe for Activity History)."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class BlueskyUncertain(BlueskyError):
    """The create request may have reached Bluesky; reconcile before any new attempt."""


# -- Lexicon text rules -----------------------------------------------------------------------
#
# Extended grapheme clusters (Unicode UAX #29): CR LF, controls, Extend (Mn, Me, ZWJ, ZWNJ,
# variation selectors, emoji modifiers, tag characters), SpacingMark (Mc), Hangul syllable
# sequences, regional-indicator pairs and emoji ZWJ sequences. Two rules are intentionally
# not applied (GB9b Prepend, GB9c Indic conjunct linking); without them the count can only be
# HIGHER than Bluesky's, so the check never accepts a text Bluesky would reject. Bluesky's PDS
# validates the record again (validate=true) and a rejection there is a definite failure.

def _ext_pict(cp: int) -> bool:
    return (cp in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139, 0x24C2, 0x3030, 0x303D, 0x3297, 0x3299)
            or 0x2194 <= cp <= 0x21AA or 0x231A <= cp <= 0x23FF or 0x25AA <= cp <= 0x25FE
            or 0x2600 <= cp <= 0x27BF or 0x2934 <= cp <= 0x2935 or 0x2B05 <= cp <= 0x2B55
            or 0x1F000 <= cp <= 0x1FAFF or 0x1FC00 <= cp <= 0x1FFFD)


def _gcb(ch: str) -> str:
    cp = ord(ch)
    if ch == "\r":
        return "CR"
    if ch == "\n":
        return "LF"
    if ch == "‍":
        return "ZWJ"
    if (0x1F1E6 <= cp <= 0x1F1FF):
        return "RI"
    if (0x1F3FB <= cp <= 0x1F3FF or 0xFE00 <= cp <= 0xFE0F or 0xE0020 <= cp <= 0xE007F or cp == 0x200C
            or 0xFF9E <= cp <= 0xFF9F or 0xE0100 <= cp <= 0xE01EF):
        return "Extend"
    if 0x1100 <= cp <= 0x115F or 0xA960 <= cp <= 0xA97C:
        return "L"
    if 0x1160 <= cp <= 0x11A7 or 0xD7B0 <= cp <= 0xD7C6:
        return "V"
    if 0x11A8 <= cp <= 0x11FF or 0xD7CB <= cp <= 0xD7FB:
        return "T"
    if 0xAC00 <= cp <= 0xD7A3:
        return "LV" if (cp - 0xAC00) % 28 == 0 else "LVT"
    cat = unicodedata.category(ch)
    if cat in ("Mn", "Me"):
        return "Extend"
    if cat == "Mc":
        return "SpacingMark"
    if cat in ("Cc", "Zl", "Zp") or (cat == "Cf" and cp not in (0x200C, 0x200D)):
        return "Control"
    return "ExtPict" if _ext_pict(cp) else "Other"


def grapheme_count(text: str) -> int:
    count, prev, ri_run, pict_zwj = 0, None, 0, False
    in_pict = False  # inside ExtPict Extend* (for GB11)
    for ch in text:
        cur = _gcb(ch)
        if prev is None:
            brk = True
        elif prev == "CR" and cur == "LF":
            brk = False
        elif prev in ("CR", "LF", "Control") or cur in ("CR", "LF", "Control"):
            brk = True
        elif prev == "L" and cur in ("L", "V", "LV", "LVT"):
            brk = False
        elif prev in ("LV", "V") and cur in ("V", "T"):
            brk = False
        elif prev in ("LVT", "T") and cur == "T":
            brk = False
        elif cur in ("Extend", "ZWJ", "SpacingMark"):
            brk = False
        elif prev == "ZWJ" and cur == "ExtPict" and pict_zwj:
            brk = False
        elif prev == "RI" and cur == "RI" and ri_run % 2 == 1:
            brk = False
        else:
            brk = True
        if brk:
            count += 1
        # state for GB11 (ExtPict Extend* ZWJ x ExtPict) and GB12/13 (RI pairs)
        if cur == "ExtPict":
            in_pict = True
        elif cur != "Extend" and cur != "ZWJ":
            in_pict = False
        pict_zwj = cur == "ZWJ" and in_pict
        ri_run = ri_run + 1 if cur == "RI" else 0
        prev = cur
    return count


_URL = re.compile(r"https://[^\s<>\"'`]+")
_TRAILING = ".,;:!?)]}'\""


def link_facets(text: str) -> list[dict]:
    """``app.bsky.richtext.facet#link`` facets for every https URL, with UTF-8 byte offsets."""
    facets = []
    for m in _URL.finditer(text):
        url = m.group(0)
        while url and url[-1] in _TRAILING:
            if url[-1] == ")" and url.count("(") >= url.count(")"):
                break
            url = url[:-1]
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or "." not in parts.hostname:
            continue
        start = len(text[:m.start()].encode("utf-8"))
        facets.append({"index": {"byteStart": start, "byteEnd": start + len(url.encode("utf-8"))},
                       "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]})
    return facets


def text_issues(text: str) -> list[str]:
    issues = []
    if not isinstance(text, str) or not text.strip():
        return ["The post text is empty."]
    graphemes, size = grapheme_count(text), len(text.encode("utf-8"))
    if graphemes > MAX_GRAPHEMES:
        issues.append(f"The post is {graphemes} characters (graphemes); Bluesky allows {MAX_GRAPHEMES}.")
    if size > MAX_BYTES:
        issues.append(f"The post is {size} bytes (UTF-8); Bluesky allows {MAX_BYTES}.")
    if "\x00" in text:
        issues.append("The post contains a NUL character.")
    return issues


def approval_sha256(repository: str, did: str, text: str, facets: list) -> str:
    """Exact action: destination platform + account DID + collection + exact text + link facets."""
    payload = json.dumps([PLATFORM, repository, did, COLLECTION, text, facets], ensure_ascii=False,
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# AT Protocol TID: 64 bits, top bit 0, then 53 bits of microseconds since the UNIX epoch and a
# 10-bit clock identifier, written as 13 base32-sortable characters. Keys from this process are
# unique and strictly increasing even when the clock is coarse (Windows), frozen or goes back:
# each new key uses at least the previous microsecond + 1.
_TID_ALPHABET = "234567abcdefghijklmnopqrstuvwxyz"
_TID_LOCK = threading.Lock()
_TID_CLOCK_ID = secrets.randbelow(1024)
_tid_last_us = 0


def new_rkey() -> str:
    """A new, unique, monotonically increasing record key in TID format."""
    global _tid_last_us
    with _TID_LOCK:
        micros = max(time.time_ns() // 1000, _tid_last_us + 1)
        if micros >= 1 << 53:
            raise BlueskyError("The system clock is out of range for a Bluesky record key.", "clock")
        _tid_last_us = micros
    value = micros << 10 | _TID_CLOCK_ID
    return "".join(_TID_ALPHABET[(value >> (5 * i)) & 31] for i in range(12, -1, -1))


def post_url(did: str, rkey: str) -> str:
    return f"https://bsky.app/profile/{did}/post/{rkey}"


def post_uri(did: str, rkey: str) -> str:
    return f"at://{did}/{COLLECTION}/{rkey}"


def _utc_ms() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# -- HTTP (fixed endpoints only) ---------------------------------------------------------------


def _allowed_pds(url) -> bool:
    if not isinstance(url, str):
        return False
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    return (p.scheme == "https" and not p.username and not p.password and p.port in (None, 443)
            and p.path in ("", "/") and (host == "bsky.social" or host.endswith(".bsky.network")))


def _request(method: str, base: str, nsid: str, *, params=None, body=None, token=None, write=False):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = base.rstrip("/") + "/xrpc/" + nsid
    try:
        with httpx.Client(timeout=httpx.Timeout(20, connect=10), follow_redirects=False, trust_env=False,
                          transport=_transport) as client:
            r = client.request(method, url, params=params, json=body, headers=headers)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise BlueskyError("Bluesky could not be reached; nothing was sent.", "network") from None
    except httpx.TransportError:
        if write:
            raise BlueskyUncertain("The connection ended before Bluesky answered; the outcome is uncertain.",
                                   "uncertain") from None
        raise BlueskyError("Bluesky could not be read (network).", "network") from None
    try:
        data = r.json()
    except ValueError:
        data = None
    if r.status_code >= 500 and write:
        raise BlueskyUncertain(f"Bluesky answered HTTP {r.status_code}; the outcome is uncertain.", "uncertain")
    if r.status_code != 200:
        err = data.get("error") if isinstance(data, dict) and isinstance(data.get("error"), str) else ""
        code = re.sub(r"[^a-z0-9_]", "", err.lower())[:30] or f"http_{r.status_code}"
        raise BlueskyError(f"Bluesky refused the request (HTTP {r.status_code}{', ' + err[:40] if err else ''}).",
                           code)
    if not isinstance(data, dict):
        if write:
            raise BlueskyUncertain("Bluesky returned an unreadable answer; the outcome is uncertain.", "uncertain")
        raise BlueskyError("Bluesky returned an unexpected response.", "format")
    return data


def create_session(handle: str, app_password: str) -> dict:
    """Log in with an app password. Returns did, handle, pds and the in-memory access token."""
    data = _request("POST", ENTRYWAY, "com.atproto.server.createSession",
                    body={"identifier": handle, "password": app_password})
    did, token = data.get("did"), data.get("accessJwt")
    if not isinstance(did, str) or not DID.fullmatch(did) or not isinstance(token, str) or not token:
        raise BlueskyError("Bluesky returned an unexpected login response.", "login_format")
    pds = None
    for s in ((data.get("didDoc") or {}).get("service") or []):
        if isinstance(s, dict) and s.get("id") in ("#atproto_pds", f"{did}#atproto_pds"):
            pds = s.get("serviceEndpoint")
    if not _allowed_pds(pds):
        raise BlueskyError("Only accounts hosted by Bluesky (bsky.social) are supported.", "pds_not_allowed")
    if data.get("active") is False:
        raise BlueskyError("This Bluesky account is not active.", "account_inactive")
    return {"did": did, "handle": str(data.get("handle") or handle).lower(), "pds": pds.rstrip("/"),
            "token": token}


def create_post(session: dict, rkey: str, text: str, facets: list) -> dict:
    """The ONE authorized write: createRecord of one app.bsky.feed.post in the session's own repo."""
    record = {"$type": COLLECTION, "text": text, "createdAt": _utc_ms(), "langs": ["en"]}
    if facets:
        record["facets"] = facets
    data = _request("POST", session["pds"], "com.atproto.repo.createRecord", token=session["token"], write=True,
                    body={"repo": session["did"], "collection": COLLECTION, "rkey": rkey, "validate": True,
                          "record": record})
    uri, cid = data.get("uri"), data.get("cid")
    if uri != post_uri(session["did"], rkey) or not isinstance(cid, str) or not CID.fullmatch(cid):
        raise BlueskyUncertain("Bluesky's answer did not identify the expected record; the outcome is uncertain.",
                               "uncertain")
    return {"uri": uri, "cid": cid}


def get_record(pds: str, did: str, rkey: str) -> dict | None:
    """Public read of exactly the outbox record from the account's PDS; None if it does not exist."""
    if not _allowed_pds(pds):
        raise BlueskyError("Only Bluesky-hosted accounts are supported.", "pds_not_allowed")
    try:
        data = _request("GET", pds, "com.atproto.repo.getRecord",
                        params={"repo": did, "collection": COLLECTION, "rkey": rkey})
    except BlueskyError as exc:
        if exc.code in ("recordnotfound", "http_404"):
            return None
        raise
    if data.get("uri") != post_uri(did, rkey) or not isinstance(data.get("cid"), str):
        raise BlueskyError("Bluesky returned an unexpected record.", "format")
    return data


def get_public_post(uri: str) -> dict | None:
    """Independent read-back through the public AppView (no authentication)."""
    data = _request("GET", APPVIEW, "app.bsky.feed.getPosts", params={"uris": uri})
    posts = data.get("posts")
    if not isinstance(posts, list):
        raise BlueskyError("Bluesky returned an unexpected response.", "format")
    return next((p for p in posts if isinstance(p, dict) and p.get("uri") == uri), None)


# -- isolated credentials ----------------------------------------------------------------------


class BlueskyCredentials:
    """The ONE connected Bluesky project account, in its own DPAPI file (bluesky.dpapi)."""

    def __init__(self, root: Path):
        self.root = root
        self.path = root / "bluesky.dpapi"
        self._lock = threading.RLock()

    def _verify(self):
        if sys.platform != "win32":
            raise SettingsError("Bluesky credentials require Windows user DPAPI.")
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
            raise SettingsError("Bluesky credentials cannot be decrypted.") from exc
        if (not isinstance(data, dict) or not HANDLE.fullmatch(str(data.get("handle", "")))
                or not DID.fullmatch(str(data.get("did", ""))) or not _allowed_pds(data.get("pds"))
                or not APP_PASSWORD.fullmatch(str(data.get("app_password", "")))):
            raise SettingsError("Stored Bluesky credentials are invalid.")
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
        fd, temporary = tempfile.mkstemp(prefix=".gc-bluesky-", dir=self.root)
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
        return {"connected": True, "handle": data["handle"], "did": data["did"]}

    def account(self) -> dict | None:
        """Internal: handle, did, pds and app password. Never returned by the API."""
        with self._lock:
            return self._load()

    def connect(self, handle, app_password) -> dict:
        """Verify with one login, then store. Only app passwords are accepted."""
        handle = handle.strip().lstrip("@").lower() if isinstance(handle, str) else ""
        app_password = app_password.strip().lower() if isinstance(app_password, str) else ""
        if not HANDLE.fullmatch(handle):
            raise SettingsError("Enter the project account's Bluesky handle, e.g. project.bsky.social.")
        if not APP_PASSWORD.fullmatch(app_password):
            raise SettingsError("Enter a Bluesky APP password (xxxx-xxxx-xxxx-xxxx), never the account password.")
        session = create_session(handle, app_password)
        with self._lock:
            self._store({"handle": session["handle"], "did": session["did"], "pds": session["pds"],
                         "app_password": app_password})
        return self.public()

    def remove(self) -> dict:
        with self._lock:
            self._store(None)
        return self.public()

    def session(self) -> dict:
        """A fresh login for one publish; the access token is kept in memory only."""
        data = self.account()
        if not data:
            raise BlueskyError("No Bluesky account is connected. Connect it in Settings → Promotion.", "no_account")
        session = create_session(data["handle"], data["app_password"])
        if session["did"] != data["did"]:
            raise BlueskyError("The Bluesky login belongs to a different account; nothing was sent.",
                               "account_mismatch")
        return session

