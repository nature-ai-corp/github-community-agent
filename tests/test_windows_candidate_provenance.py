"""Read-only GC candidate provenance script safeguards."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/windows-check-exclusion-candidate-provenance.ps1"


def test_provenance_does_not_touch_user_appdata_or_secrets():
    s = SCRIPT.read_text(encoding="utf-8")
    assert "Get-CimInstance" in s
    assert "Win32_Process" in s
    assert "Get-FileHash" in s
    assert "build\\gc-agent-e2e-trials" in s
    assert 'db.resolve().as_uri() + "?mode=ro"' in s
    assert "SELECT definition_id, status, count(*)" in s
    assert "SELECT event, count(*)" in s
    for forbidden in (
        "Remove-Item", "Move-Item", "Copy-Item", "Start-Process",
        "Stop-Process", "Set-AuthenticodeSignature", "settings.dpapi",
        "result_json", "model_key", "read_token", "protect_for_current_user",
        "INSERT INTO", "UPDATE work", "DELETE FROM",
        "Invoke-RestMethod", "Invoke-WebRequest",
    ):
        assert forbidden not in s


def test_provenance_warns_if_unattributable():
    s = SCRIPT.read_text(encoding="utf-8")
    assert "cannot be attributed" in s
    assert "cannot prove historical Task-to-process linkage" in s
    assert "No dedicated isolated-trial root found." in s
    assert "EXCLUSION_CANDIDATE" in s
    assert "ACCEPTED_BASELINE" in s
