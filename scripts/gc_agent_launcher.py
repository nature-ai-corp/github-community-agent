"""Frozen Windows executable launcher for the independent GC Agent Work Center.

Use --self-check as a no-browser/no-server packaging smoke test. It does not
load saved settings or work records, perform network operations, or start AI.
"""
from __future__ import annotations

import sys
from importlib.resources import files
from multiprocessing import freeze_support


def self_check() -> int:
    import github_community_agent
    from github_community_agent import work_center
    assert callable(work_center.main)
    pkg = files("github_community_agent")
    for filename in ("home.html", "worker_v011.css", "gc.css"):
        if not (pkg / filename).read_bytes():
            raise RuntimeError(f"Required UI resource missing: {filename}")
    print("GC Agent frozen executable self-check PASS", flush=True)
    return 0


def main() -> int:
    freeze_support()
    if sys.argv[1:] == ["--self-check"]:
        return self_check()
    if len(sys.argv) > 1:
        print("Unsupported argument.", file=sys.stderr)
        return 2
    from github_community_agent.work_center import main as serve
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
