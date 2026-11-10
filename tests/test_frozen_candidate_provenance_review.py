"""Frozen optimized component provenance report must not claim SBOM closure."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gc_frozen_provenance", ROOT / "scripts/frozen_candidate_provenance_review.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_report_counts_actual_files_and_marks_license_unverified():
    manifest = {
        "bundle_name": "GitHubCommunityAgent",
        "file_count": 2,
        "total_size_bytes": 30,
        "files": [
            {"path": "GitHubCommunityAgent.exe", "sha256": "A" * 64, "kind": "binary"},
            {"path": "_internal/certifi/cacert.pem", "sha256": "B" * 64,
             "kind": "public_ca_certificates"},
        ],
    }
    triage = {
        "unique_parsed_member_names": 2,
        "members": [
            {"member": "httpx._client", "category": "environment_distribution_candidate",
             "candidate_distributions": ["httpx"]},
            {"member": "pyiboot01_bootstrap", "category": "unresolved",
             "candidate_distributions": []},
        ],
    }
    report = mod.build(manifest, triage)
    assert report["candidate_bundle_file_count"] == 2
    assert report["candidate_embedded_module_count"] == 2
    assert report["candidate_distribution_count"] == 1
    assert len(report["compiled_binary_candidates"]) == 1
    assert report["unresolved_archive_members"] == ["pyiboot01_bootstrap"]
    assert report["actual_package_versions_verified"] is False
    assert report["complete_third_party_notices_verified"] is False
    assert report["approved_public_redistribution"] is False
    assert report["candidate_distributions"][0]["exact_frozen_component_version_verified"] is False


def test_reviewer_and_windows_wrapper_do_not_touch_installed_data():
    source = (ROOT / "scripts/windows-optimized-frozen-sbom-review.ps1").read_text(
        encoding="utf-8"
    )
    assert "build\\gc-agent-exclusion-candidate\\dist\\GitHubCommunityAgent" in source
    assert "optimized-candidate-sbom-review" in source
    assert "if (Test-Path -LiteralPath $parent)" in source
    assert "pyi-archive_viewer.exe" in source
    assert "frozen_bundle_inventory.py" in source
    assert "frozen_candidate_provenance_review.py" in source
    for forbidden in (
        "Remove-Item", "Copy-Item", "Move-Item", "Start-Process",
        "Stop-Process", "ISCC.exe", "settings.dpapi", "work.sqlite3",
        "Get-MpComputerStatus", "Set-AuthenticodeSignature", "Invoke-WebRequest",
    ):
        assert forbidden not in source
