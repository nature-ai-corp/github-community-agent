"""Static safeguards for optimized frozen 26 native-binary version evidence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/windows-optimized-native-binary-versions.ps1"


def test_binary_version_audit_is_hash_anchored_and_create_only():
    s = SCRIPT.read_text(encoding="utf-8")
    assert "optimized-candidate-sbom-review\\native-binary-fileversion-evidence.json" in s
    assert "actual-frozen-files.json" in s
    assert "Get-FileHash" in s
    assert "if ($hash -ne $item.sha256)" in s
    assert "if (Test-Path -LiteralPath $report)" in s
    assert "$items.Count -ne 26" in s
    assert "VersionInfo" in s
    assert "file_version_metadata_is_provenance = $false" in s
    assert "license_text_verified = $false" in s


def test_binary_version_audit_never_modifies_frozen_files_or_credentials():
    s = SCRIPT.read_text(encoding="utf-8")
    for forbidden in (
        "Remove-Item", "Copy-Item", "Move-Item", "Start-Process",
        "Stop-Process", "Set-AuthenticodeSignature",
        "settings.dpapi", "work.sqlite3", "ReadAllBytes",
        "Invoke-WebRequest", "Invoke-RestMethod", "ISCC.exe",
    ):
        assert forbidden not in s
