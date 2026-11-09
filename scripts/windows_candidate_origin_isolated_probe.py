"""Independent Origin enforcement test against a live isolated GC Agent.

This reads a LOCAL session nonce from the locally served HTML, never prints or
stores it, and sends only requests to a nonexistent endpoint. It does not
create/update Tasks, settings, credentials, or any GitHub content.
"""
from __future__ import annotations

import argparse
import re
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from windows_candidate_http_negative_probe import validate_url

NO_SUCH_ENDPOINT = "/api/__origin_security_probe_no_such_endpoint__"
OPENER = build_opener(ProxyHandler({}))


def request(base: str, *, method: str = "GET",
            origin: str | None = None, nonce: str | None = None) -> tuple[int, bytes]:
    headers = {}
    if origin is not None:
        headers["Origin"] = origin
    if nonce is not None:
        headers["X-App-Nonce"] = nonce
    data = b"{}" if method == "POST" else None
    url = base + ("/" if method == "GET" else NO_SUCH_ENDPOINT)
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=5) as response:
            return response.status, response.read(200000)
    except HTTPError as exc:
        return exc.code, exc.read(200000)


def run(base: str) -> bool:
    status, page = request(base)
    if status != 200:
        raise ValueError("Local app root not available.")
    matches = re.findall(rb'const NONCE="([A-Za-z0-9_-]{16,128})";', page)
    if len(matches) != 1:
        raise ValueError("Cannot safely extract exactly one local UI nonce.")
    # Keep real session nonce only in volatile local Python memory; never log.
    nonce = matches[0].decode("ascii")
    checks = [
        ("correct Origin + correct nonce (unknown endpoint)", base, 404),
        ("foreign Origin + correct nonce", "https://foreign.invalid", 403),
        ("missing Origin + correct nonce", None, 403),
        ("correct Origin + invalid nonce", base, 403),
    ]
    failed = 0
    for label, origin, expected in checks:
        actual, _ = request(base, method="POST", origin=origin,
                            nonce="not-the-session-nonce" if "invalid nonce" in label else nonce)
        passed = actual == expected
        failed += not passed
        print(f"{'PASS' if passed else 'FAIL'} {label}: expected {expected}, got {actual}")
    print(f"Independent Origin/nonce negative checks: {len(checks) - failed} / {len(checks)} PASS")
    print("Valid nonce was never printed, saved or sent to a real action endpoint.")
    print("No authorized Task or Settings action; no model or GitHub request.")
    return failed == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    try:
        return 0 if run(validate_url(args.url)) else 1
    except (URLError, ValueError, OSError) as exc:
        print("FAIL: isolated Origin verification unavailable:", type(exc).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
