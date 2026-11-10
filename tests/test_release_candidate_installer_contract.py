"""Guard the isolated GC Agent V1 release-candidate installer source contract.

These source checks cannot certify licensing or the actual built installer.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RC = ROOT / "packaging/windows/gc-agent-release-candidate.iss"
EXISTING = ROOT / "packaging/windows/gc-agent.iss"


def test_rc_requires_independent_reviewed_legal_materials():
    source = RC.read_text(encoding="utf-8")
    assert "#ifndef ReviewedLegalDir" in source
    assert "#ifndef LegalReviewEvidence" in source
    assert "THIRD_PARTY_NOTICES.txt" in source
    assert "REVIEW_APPROVAL.json" in source
    assert "Missing reviewed THIRD_PARTY_NOTICES.txt" in source
    assert "Missing approved license review record" in source
    assert "Missing independent legal review evidence" in source
    assert "#ifndef AppVersion" in source
    assert 'AppVersion == "0.0.0-dev0"' in source
    assert source.count("#error") >= 6


def test_rc_points_only_at_optimized_candidate_and_adds_legal_tree():
    source = RC.read_text(encoding="utf-8")
    assert "build\\gc-agent-exclusion-candidate\\dist\\GitHubCommunityAgent\\*" in source
    assert 'Source: "{#ReviewedLegalDir}\\*"' in source
    assert 'DestDir: "{app}\\third-party-licenses"' in source
    assert "build\\gc-agent-release-candidate-installer" in source
    assert 'Source: "..\\..\\LICENSE"' in source
    assert 'Source: "..\\..\\NOTICE"' in source
    assert "PrivilegesRequired=lowest" in source
    assert "No [UninstallDelete]" in source
    assert "[UninstallDelete]\n" not in source


def test_legacy_internal_installer_remains_unchanged_separate():
    source = EXISTING.read_text(encoding="utf-8")
    assert 'OutputBaseFilename={#OutputName}' in source
    assert "GitHubCommunityAgent-InternalTest-Unsigned" in source
    # Default bundle unchanged; overridable so the build script can package a
    # bundle that the third-party license package has been checked against.
    assert '#define BundleDir "..\\..\\dist\\GitHubCommunityAgent"' in source
    assert 'Source: "{#BundleDir}\\*"' in source


def test_rc_never_forces_install_or_touches_work_data():
    source = RC.read_text(encoding="utf-8")
    for forbidden in (
        "runas", "CreateProcess", "DeleteFile", "DelTree",
        "UninstallRun", "UninstallDelete]\n", "Source: \"settings.dpapi\"",
        "Source: \"work.sqlite3\"", "Set-AuthenticodeSignature",
        "nature-ai-worker\\dist",
    ):
        assert forbidden not in source
