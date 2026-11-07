"""Narrow, read-only verification CLI for the independent Community Agent.

This is a development/acceptance interface, not the future agent UI.
No GitHub mutation, token argument, token persistence, or implicit repository.
"""
from __future__ import annotations

import argparse
import os
import sys

from .errors import ToolError
from .github_readonly import github_discussions, github_issues, valid_repository

_TOKEN_ENV = "GITHUB_COMMUNITY_AGENT_READ_TOKEN"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="github-community-agent-read",
        description="Read public GitHub Issues or Discussions from one explicitly selected repository.",
    )
    parser.add_argument("--repo", required=True, help="GitHub owner/repository (public repository)")
    parser.add_argument("--resource", required=True, choices=("issues", "discussions"))
    parser.add_argument("--mode", choices=("list", "issue", "comments", "discussion"), default="list")
    parser.add_argument("--number", type=int)
    parser.add_argument("--page", type=int)
    parser.add_argument("--state", choices=("open", "closed", "all"))
    parser.add_argument("--after", help="Opaque GitHub Discussions page cursor")
    options = parser.parse_args(argv)

    if not valid_repository(options.repo):
        parser.error("--repo must be a valid owner/repository, not a URL or file path")
    if options.resource == "issues":
        if options.mode not in ("list", "issue", "comments") or options.after is not None:
            parser.error("Issues allow list, issue or comments modes, not Discussions cursors")
        args = {"mode": options.mode}
        for key in ("number", "page", "state"):
            value = getattr(options, key)
            if value is not None:
                args[key] = value
        action = lambda: github_issues(options.repo, args)
    else:
        if options.mode not in ("list", "discussion") or options.page is not None or options.state is not None:
            parser.error("Discussions allow only list or discussion modes and an optional cursor")
        args = {"mode": options.mode}
        if options.number is not None:
            args["number"] = options.number
        if options.after is not None:
            args["after"] = options.after
        # Only this dedicated environment variable is consulted. Never accept a token
        # on the command line or silently inherit GITHUB_TOKEN / GH_TOKEN.
        action = lambda: github_discussions(lambda: os.environ.get(_TOKEN_ENV), args, options.repo)

    try:
        print(action())
        return 0
    except ToolError as exc:
        # Error types are safe for display and do not expose secrets or HTTP bodies.
        print(f"GitHub read failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
