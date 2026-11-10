"""Static guardrails for the separate Windows exclusion experiment."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_candidate_never_reuses_accepted_output_or_installer():
    s = (ROOT / "scripts/windows-build-exclusion-candidate.ps1").read_text(
        encoding="utf-8"
    )
    assert "build\\gc-agent-exclusion-candidate" in s
    assert "dist\\GitHubCommunityAgent\\GitHubCommunityAgent.exe" in s
    assert "Candidate directory exists:" in s
    assert "Baseline SHA256 unchanged:" in s
    assert "--self-check" in s
    for module in ("pytest", "_pytest", "pygments"):
        assert "'--exclude-module', '" + module + "'" in s
    for forbidden in (
        "Remove-Item", "Move-Item", "Copy-Item", "Stop-Process",
        "Start-Process", "Set-AuthenticodeSignature",
        "Set-MpPreference", "ISCC.exe", "unins000.exe",
    ):
        assert forbidden not in s


def test_candidate_requires_actual_embedded_archive_verification():
    s = (ROOT / "scripts/windows-build-exclusion-candidate.ps1").read_text(
        encoding="utf-8"
    )
    assert "pyi-archive_viewer.exe" in s
    assert "--brief --recursive" in s
    assert "frozen_archive_module_triage.py" in s
    assert "candidate-embedded-archive.txt" in s
    assert "candidate-module-triage.json" in s
    assert "exclude-module verification FAILED" in s
    assert "Candidate self-check FAILED" in s
    assert "Not accepted as official release" in s
