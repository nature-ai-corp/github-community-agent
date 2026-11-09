"""Guardrails for real but isolated frozen-candidate UI acceptance."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/windows-run-exclusion-candidate-isolated.ps1"


def test_candidate_live_runner_requires_isolated_new_root_and_restores_env():
    s = RUNNER.read_text(encoding="utf-8")
    assert "build\\gc-agent-exclusion-candidate\\dist" in s
    assert "build\\gc-agent-e2e-trials" in s
    assert "[guid]::NewGuid()" in s
    assert "$env:LOCALAPPDATA = $trial" in s
    assert "$env:LOCALAPPDATA = $originalLocalAppData" in s
    assert "finally {" in s
    assert "LOCALAPPDATA restored" in s
    assert "--self-check" in s
    assert "& $candidate" in s


def test_candidate_live_runner_has_no_real_data_copy_or_auto_credentials():
    s = RUNNER.read_text(encoding="utf-8")
    for forbidden in (
        "Remove-Item", "Move-Item", "Copy-Item", "robocopy", "xcopy",
        "work.sqlite3", "settings.dpapi", "api_key =", "ghp_", "sk-",
        "ISCC.exe", "Start-Process", "Set-AuthenticodeSignature",
        "Invoke-RestMethod", "Invoke-WebRequest",
    ):
        assert forbidden not in s
    assert "test-authorized model/GitHub read credentials" in s
    assert "Mark reviewed must NOT post anything" in s
