"""Developer acceptance entry for the independent V1 workflow runtime.

Read-only; intentionally no model/token configuration or write actions exposed
through this command. This is not the final user-facing product.
"""
from __future__ import annotations

import argparse
import json
import sys

from .errors import ToolError
from .runtime import CommunityRuntime, CommunitySettings, Workflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="github-community-agent-workflow")
    parser.add_argument("--repo", required=True, help="Explicit public GitHub owner/repository")
    parser.add_argument("--workflow", required=True,
                        choices=(Workflow.REVIEW_ISSUES.value, Workflow.REVIEW_DISCUSSIONS.value,
                                 Workflow.COMMUNITY_REPORT.value))
    args = parser.parse_args(argv)
    try:
        runtime = CommunityRuntime(CommunitySettings(args.repo))
        result = runtime.run(args.workflow)
    except ToolError as exc:
        print(f"Community workflow failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
