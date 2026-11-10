"""Negative HTTP controls for an ALREADY RUNNING, isolated GC Agent candidate.

No credentials, no extraction of the real nonce, no authorized POST actions.
Loopback requests only; checks host, CSRF nonce and foreign Origin rejection.
The target Work Center must be confirmed by the operator as optimized candidate.
"""
from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler


def validate_url(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or not parsed.port or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ValueError("Use exact current candidate URL: http://127.0.0.1:<port>/")
    return f"http://127.0.0.1:{parsed.port}"


def probe(base: str, path: str, *, method: str = "GET",
          headers: dict[str, str] | None = None,
          payload: bytes | None = None) -> tuple[int, bytes]:
    # Ignore configured system proxies for strictly loopback localhost probes.
    opener = build_opener(ProxyHandler({}))
    request = Request(base + path, data=payload, method=method,
                      headers=headers or {})
    try:
        with opener.open(request, timeout=5) as response:
            return response.status, response.read(20000)
    except HTTPError as exc:
        return exc.code, exc.read(20000)


def run(base: str) -> list[tuple[str, int, int]]:
    checks: list[tuple[str, int, int]] = []

    def check(label: str, expected: int, observed: int) -> None:
        checks.append((label, expected, observed))
        print(f"{'PASS' if expected == observed else 'FAIL'} {label}: "
              f"expected {expected}, got {observed}")

    status, body = probe(base, "/api/definitions")
    if status == 200:
        try:
            definitions = json.loads(body)["definitions"]
            identities = {item["id"] for item in definitions}
            required = {"review_issues", "review_discussions",
                        "draft_issue", "draft_discussion", "community_report"}
            if not required.issubset(identities):
                raise ValueError("Unexpected Work Center definition set")
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Endpoint is not a valid GC Agent Work Center") from exc
    check("GC Agent definitions discovery", 200, status)
    if status != 200:
        raise ValueError("Not a confirmed GC Agent Work Center; stopping probes")

    forged_host = {"Host": "host-attacker.invalid"}
    check("forged Host GET refused", 403,
          probe(base, "/api/definitions", headers=forged_host)[0])
    check("tasks GET without nonce refused", 403,
          probe(base, "/api/tasks")[0])
    check("settings GET without nonce refused", 403,
          probe(base, "/api/settings")[0])
    wrong_nonce = {"X-App-Nonce": "not-a-real-nonce",
                   "Origin": base,
                   "Content-Type": "application/json"}
    check("tasks POST invalid nonce refused", 403,
          probe(base, "/api/tasks", method="POST",
                headers=wrong_nonce, payload=b"{}")[0])
    check("test connection POST invalid nonce refused", 403,
          probe(base, "/api/test-connection", method="POST",
                headers=wrong_nonce, payload=b"{}")[0])
    wrong_origin = {"Origin": "https://foreign.invalid",
                    "X-App-Nonce": "not-a-real-nonce",
                    "Content-Type": "application/json"}
    check("settings POST foreign Origin plus invalid nonce refused", 403,
          probe(base, "/api/settings", method="POST",
                headers=wrong_origin, payload=b"{}")[0])
    check("tasks POST forged Host refused", 403,
          probe(base, "/api/tasks", method="POST",
                headers={**wrong_nonce, **forged_host}, payload=b"{}")[0])
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True,
                        help="Already-running optimized GC Agent Work Center URL")
    args = parser.parse_args()
    try:
        base = validate_url(args.url)
        checks = run(base)
    except (ValueError, URLError, OSError) as exc:
        print("FAIL: cannot verify selected local Work Center:", str(exc))
        return 1
    failures = sum(expected != actual for _, expected, actual in checks)
    print(f"Local HTTP negative checks: {len(checks) - failures} / {len(checks)} PASS")
    print("No valid nonce, authorized POST, model key or GitHub token was used.")
    print("Foreign-Origin check also has an invalid nonce; origin enforcement is not independently isolated.")
    print("No independent GitHub API side-effect audit was performed.")
    return int(failures != 0)


if __name__ == "__main__":
    raise SystemExit(main())
