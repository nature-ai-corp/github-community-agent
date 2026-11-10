"""Guardrails on throwaway Windows two-account DPAPI test."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/windows_dpapi_two_account_throwaway.py"


def test_dpapi_trial_uses_only_throwaway_random_data_and_no_real_user_paths():
    src = SCRIPT.read_text(encoding="utf-8")
    assert "os.urandom(32)" in src
    assert 'with target.open("xb")' in src
    assert 'unprotect_for_current_user(blob)' in src
    assert 'choices=("allowed", "denied")' in src
    assert '"gc-agent-dpapi-throwaway.bin"' in src
    for token in (
        "settings.dpapi", "work.sqlite3", "AppData", "Remove-Item",
        "DeleteFile", "CryptProtectMemory", "runas", "net user",
        "subprocess", "shutil.copy", "api_key", "read_token",
    ):
        assert token not in src
    assert 'Only disposable random bytes were used' in src


def test_powershell_verifier_matches_app_dpapi_call_and_never_false_passes():
    ps = (ROOT / "scripts/windows-dpapi-verify-throwaway.ps1").read_text(encoding="utf-8")
    # Same call as windows_dpapi.unprotect_for_current_user: no entropy, user scope.
    assert "ProtectedData]::Unprotect($blob, $null, $scope)" in ps
    assert "DataProtectionScope]::CurrentUser" in ps
    assert "'gc-agent-dpapi-throwaway.bin'" in ps
    assert "ReparsePoint" in ps and "$ExpectSha256" in ps
    # Unreadable file or wrong blob is INCOMPLETE (exit 2), never PASS.
    assert ps.count("exit 2") >= 4
    assert "cannot read the blob file" in ps
    for token in ("settings.dpapi", "work.sqlite3", "Remove-Item", "Set-Content",
                  "Out-File", "WriteAllBytes", "Write-Host $plain", "ToBase64String($plain)"):
        assert token not in ps, token
