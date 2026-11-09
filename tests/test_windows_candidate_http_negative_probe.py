"""Offline guardrail tests for the credential-free live candidate HTTP probe."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/windows_candidate_http_negative_probe.py"
SPEC = importlib.util.spec_from_file_location("gc_http_probe", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_probe_accepts_only_exact_loopback_candidate_url():
    assert mod.validate_url("http://127.0.0.1:49152/") == "http://127.0.0.1:49152"
    for bad in (
        "http://localhost:49152/", "https://127.0.0.1:49152/",
        "http://10.0.0.1:49152/", "http://127.0.0.1/",
        "http://127.0.0.1:49152@evil.invalid/", "http://127.0.0.1:49152/api/tasks",
        "http://127.0.0.1:49152/?key=secret", "http://[::1]:49152/",
        "file:///C:/windows/system32",
    ):
        with pytest.raises(ValueError):
            mod.validate_url(bad)


def test_probe_never_constructs_authorized_request_or_reads_secrets():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ProxyHandler({})" in source
    assert 'method="POST"' in source
    assert '"X-App-Nonce": "not-a-real-nonce"' in source
    assert "forged Host GET refused" in source
    assert "tasks GET without nonce refused" in source
    assert "settings POST foreign Origin refused" in source
    assert "GC Agent definitions discovery" in source
    for forbidden in (
        "settings.dpapi", "work.sqlite3", "model_key",
        "read_token", "Authorization", "token_urlsafe",
        "webbrowser.open", "subprocess", "startfile",
        "os.environ", "DELETE FROM", "INSERT INTO",
        "Set-MpPreference",
    ):
        assert forbidden not in source
