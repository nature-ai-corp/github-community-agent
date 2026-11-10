"""Offline no-network tests of bounded public GitHub snapshot integrity."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gc_public_issue_audit", ROOT / "scripts/github_public_issue_before_after_audit.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_compare_matching_snapshot_is_limited_not_conclusive():
    before = {
        "repository": "example/public", "issue": 33,
        "checked_utc": "2026-11-09T12:00:00+00:00",
        "issue_state": "open", "issue_updated_at": "x",
        "comments": [{"id": 1, "updated_at": "x"}],
    }
    after = {**before, "checked_utc": "2026-11-09T12:02:00+00:00"}
    result = mod.compare(before, after)
    assert result["matching_snapshots"] is True
    assert result["proves_zero_github_writes"] is False
    assert "Discussions" in result["limitations"][0]


def test_different_or_reversed_snapshots_rejected():
    a = {"repository": "a/b", "issue": 33, "checked_utc": "2026-11-09T01:00:00Z"}
    with pytest.raises(ValueError):
        mod.compare(a, {**a, "repository": "a/c", "checked_utc": "2026-11-09T02:00:00Z"})
    with pytest.raises(ValueError):
        mod.compare(a, {**a, "checked_utc": "2026-11-09T01:00:00Z"})


def test_no_credentials_and_no_github_write_calls():
    s = (ROOT / "scripts/github_public_issue_before_after_audit.py").read_text(encoding="utf-8")
    assert 'method="GET"' in s
    assert "ProxyHandler({})" in s
    assert "NoRedirect()" in s
    assert 'with path.open("x"' in s
    assert '"proves_zero_github_writes": False' in s
    for token in ("api_key", "read_token", "Authorization", "mutation {",
                  'method="POST"', "settings.dpapi", "work.sqlite3",
                  "subprocess", "os.environ"):
        assert token not in s
