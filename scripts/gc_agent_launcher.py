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


def diagnostics() -> int:
    """Read-only local diagnostics: no creation, no credentials, no network."""
    import os
    import sqlite3
    from github_community_agent.work_center import data_directory

    root = data_directory()
    db = root / "work.sqlite3"
    settings = root / "settings.dpapi"
    print("Windows user:", os.environ.get("USERNAME", "(not set)"))
    print("LOCALAPPDATA:", os.environ.get("LOCALAPPDATA", "(not set)"))
    print("GC Agent data directory:", root)
    print("Existing work database:", db.is_file())
    print("Existing protected settings:", settings.is_file())
    if db.is_file():
        try:
            # URI mode=ro prevents accidentally making a fresh empty db.
            with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as con:
                count = con.execute("SELECT COUNT(*) FROM work").fetchone()[0]
                print("Stored Task count (including archived):", count)
        except (sqlite3.Error, OSError) as exc:
            print("Work database cannot be read:", type(exc).__name__)
            return 1
    return 0


def main() -> int:
    freeze_support()
    if sys.argv[1:] == ["--self-check"]:
        return self_check()
    if sys.argv[1:] == ["--diagnostics"]:
        return diagnostics()
    if len(sys.argv) > 1:
        print("Unsupported argument.", file=sys.stderr)
        return 2
    from github_community_agent.work_center import main as serve
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
