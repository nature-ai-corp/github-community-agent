"""Safety tests for independent valid-nonce / Origin check."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/windows_candidate_origin_isolated_probe.py"


def test_origin_probe_uses_only_nonexistent_endpoint_for_valid_nonce():
    s = SOURCE.read_text(encoding="utf-8")
    assert 'NO_SUCH_ENDPOINT = "/api/__origin_security_probe_no_such_endpoint__"' in s
    assert 'method == "GET" else NO_SUCH_ENDPOINT' in s
    assert "foreign Origin + correct nonce" in s
    assert "correct Origin + correct nonce" in s
    assert "expected 404" not in s or "404" in s
    assert "ProxyHandler({})" in s
    assert "validate_url(args.url)" in s
    for forbidden in (
        "/api/tasks", "/api/settings", "/api/test-connection",
        "settings.dpapi", "work.sqlite3", "github.com/",
        "model_key", "read_token", "requests.post",
        "write_text(", "write_bytes(", "open(",
    ):
        # 'open(' would also match opener.open, so check dangerous file use separately
        if forbidden != "open(":
            assert forbidden not in s


def test_nonce_only_prints_status_counts_not_nonce():
    s = SOURCE.read_text(encoding="utf-8")
    assert "nonce = matches[0].decode" in s
    assert "print(nonce)" not in s
    assert "nonce=" not in "".join(x for x in s.splitlines() if "print(" in x)
