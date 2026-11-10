"""Read-only GitHub issue-comment snapshot for before/after V1 no-write review.

Public GitHub REST GET only, fixed api.github.com host, no tokens,
no proxies/redirects, no contents or user handles retained. A matching
before/after result is limited evidence, NOT proof of zero writes.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}")
USER_AGENT = "GC-Agent-ReadOnly-Release-Audit"
API = "https://api.github.com"
MAX_ITEMS = 100
MAX_PAGES = 3


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected REST redirect")


def get_json(path: str):
    if not path.startswith("/repos/") or "?" in path and not path.startswith("/repos/"):
        raise ValueError("Unexpected GitHub API URL")
    req = urllib.request.Request(
        API + path,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": USER_AGENT,
                 "X-GitHub-Api-Version": "2022-11-28"},
        method="GET",
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect()
    )
    with opener.open(req, timeout=12) as resp:
        if resp.status != 200:
            raise ValueError("GitHub REST query did not succeed")
        size = resp.headers.get("Content-Length")
        if size and int(size) > 600_000:
            raise ValueError("GitHub response exceeds audit limit")
        blob = resp.read(600_001)
        if len(blob) > 600_000:
            raise ValueError("GitHub response exceeds audit limit")
        return json.loads(blob), resp.headers


def snapshot(repository: str, issue: int) -> dict:
    if not NAME.fullmatch(repository) or ".." in repository:
        raise ValueError("Choose a valid public GitHub owner/repository")
    if not 1 <= issue <= 10_000_000:
        raise ValueError("Invalid issue number")
    metadata, _ = get_json(f"/repos/{repository}")
    if not isinstance(metadata, dict) or metadata.get("private") is not False:
        raise ValueError("Expected an accessible PUBLIC repository")
    item, _ = get_json(f"/repos/{repository}/issues/{issue}")
    if not isinstance(item, dict) or "pull_request" in item or item.get("number") != issue:
        raise ValueError("Expected a public Issue, not a PR")
    comments = []
    for page in range(1, MAX_PAGES + 1):
        rows, _ = get_json(
            f"/repos/{repository}/issues/{issue}/comments?per_page={MAX_ITEMS}&page={page}"
        )
        if not isinstance(rows, list):
            raise ValueError("Unexpected public GitHub comment response")
        for row in rows:
            if not isinstance(row, dict) or type(row.get("id")) is not int:
                raise ValueError("Unexpected comment metadata")
            comments.append({"id": row["id"], "created_at": row.get("created_at"),
                             "updated_at": row.get("updated_at")})
        if len(rows) < MAX_ITEMS:
            break
    else:
        raise ValueError("Comment pagination over limit; no complete snapshot")
    return {
        "scope": "Public Issue metadata and comments; no Discussions, other Issues, deletions between snapshots, or GitHub audit log",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "repository": repository, "issue": issue, "issue_updated_at": item.get("updated_at"),
        "issue_state": item.get("state"),
        "comments": sorted(comments, key=lambda x: x["id"]),
        "gitHub_write_proof": False,
    }


def compare(before: dict, after: dict) -> dict:
    if ((before.get("repository"), before.get("issue")) !=
            (after.get("repository"), after.get("issue"))):
        raise ValueError("Snapshots address different GitHub objects")
    if before.get("checked_utc", "") >= after.get("checked_utc", ""):
        raise ValueError("Before snapshot must precede after snapshot")
    changes = []
    for key in ("issue_state", "issue_updated_at", "comments"):
        if before.get(key) != after.get(key):
            changes.append(key)
    return {
        "scope": "Bounded before/after public Issue state comparison ONLY",
        "repository": before["repository"], "issue": before["issue"],
        "before_checked_utc": before["checked_utc"],
        "after_checked_utc": after["checked_utc"],
        "observed_changes": changes,
        "matching_snapshots": not changes,
        "proves_zero_github_writes": False,
        "limitations": [
            "Does not capture Discussions, other Issues or all repository activity",
            "Does not exclude transient writes later deleted or hidden events",
            "Needs a before snapshot genuinely taken BEFORE the candidate trial",
            "Read-only API permissions and frozen app network behavior require separate evidence",
        ],
    }


def write_new(path: Path, report: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--repository", required=True)
    snap.add_argument("--issue", type=int, required=True)
    snap.add_argument("--output", type=Path, required=True)
    diff = sub.add_parser("compare")
    diff.add_argument("--before", type=Path, required=True)
    diff.add_argument("--after", type=Path, required=True)
    diff.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite existing evidence")
    try:
        if args.action == "snapshot":
            report = snapshot(args.repository, args.issue)
            print("GitHub public Issue comment metadata REST GET snapshot acquired.")
            print("Comment records:", len(report["comments"]))
        else:
            before = json.loads(args.before.read_text(encoding="utf-8"))
            after = json.loads(args.after.read_text(encoding="utf-8"))
            report = compare(before, after)
            print("Observed change categories:", report["observed_changes"])
            print("Matching snapshots:", report["matching_snapshots"])
        write_new(args.output, report)
        print("Report:", args.output)
        print("LIMITED evidence only; NOT independent proof of all GitHub no-write actions.")
        return 0
    except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print("FAIL: bounded GitHub evidence check:", type(exc).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
