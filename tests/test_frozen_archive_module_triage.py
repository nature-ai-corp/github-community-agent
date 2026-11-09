"""Read-only PyInstaller module triage tests."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gc_archive_triage", ROOT / "scripts/frozen_archive_module_triage.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_archive_triage_categories_are_only_candidates():
    archive = """ 0, 'github_community_agent.work_center', 'PYMODULE'
 1, 'json', 'PYMODULE'
 2, 'httpx._client', 'PYMODULE'
 3, 'hypothetical_missing', 'PYMODULE'
garbled archive header without module
"""
    result = mod.analyze(archive, {"httpx": ["httpx"]})
    assert result["listing_lines"] == 5
    assert result["unmatched_listing_lines"] == 1
    assert result["unique_parsed_member_names"] == 4
    categories = {r["member"]: r["category"] for r in result["members"]}
    assert categories == {
        "github_community_agent.work_center": "first_party",
        "json": "stdlib_candidate",
        "httpx._client": "environment_distribution_candidate",
        "hypothetical_missing": "unresolved",
    }
    assert "not a complete or validated frozen SBOM" in result["scope"]


def test_archive_triage_never_invents_origin_for_unknown_modules():
    result = mod.analyze(" 0, 'unknown_bundle.somewhere', 'PYMODULE'\n", {})
    assert result["members"][0]["candidate_distributions"] == []
    assert result["members"][0]["category"] == "unresolved"
    assert any("manual" in warning.lower() for warning in result["review_required"])


def test_archive_triage_collapses_duplicate_names_but_preserves_occurrence_count():
    result = mod.analyze("0, 'httpx'\n1, 'httpx'\n", {"httpx": ["httpx"]})
    assert result["parsed_member_occurrences"] == 2
    assert result["unique_parsed_member_names"] == 1
    assert result["members"][0]["occurrences"] == 2


def test_archive_triage_script_is_offline_and_refuses_overwrite():
    source = (ROOT / "scripts/frozen_archive_module_triage.py").read_text(
        encoding="utf-8"
    )
    assert "packages_distributions()" in source
    assert "output.exists()" in source
    assert "read_text(encoding=" in source
    assert "NOT A FROZEN SBOM" in source
    for forbidden in ("subprocess", "requests.get(", "httpx.get(", "unlink(", "rmtree("):
        assert forbidden not in source


def test_real_pyinstaller_six_brief_recursive_unquoted_output():
    # User-supplied first 30 lines from the actual Windows frozen executable.
    archive = """Options in 'GitHubCommunityAgent.exe' (PKG/CArchive):
 pyi-contents-directory _internal
Contents of 'GitHubCommunityAgent.exe' (PKG/CArchive):
 struct
 pyimod01_archive
 pyimod02_importers
 pyimod03_ctypes
 pyimod04_pywin32
 pyiboot01_bootstrap
 pyi_rth_inspect
 pyi_rth_pkgutil
 pyi_rth__tkinter
 pyi_rth_multiprocessing
 gc_agent_launcher
 PYZ.pyz

Contents of 'PYZ.pyz' (PYZ):
 __future__
 _aix_support
 _colorize
 _compat_pickle
 _compression
 _opcode_metadata
 _py_abc
 _pydatetime
 _pydecimal
 _pytest
 _pytest._version
 _pytest.outcomes
 _strptime
"""
    result = mod.analyze(archive, {"_pytest": ["pytest"]})
    names = {x["member"] for x in result["members"]}
    assert "gc_agent_launcher" in names
    assert "_pytest" in names
    assert "_pytest._version" in names
    assert "_pytest.outcomes" in names
    assert "PYZ.pyz" not in names  # archive filename, not module
    assert "pyi-contents-directory" not in names
    assert result["parsed_member_occurrences"] >= 20
    assert result["unmatched_listing_lines"] <= 6
    assert set(result["development_module_candidates"]) >= {
        "_pytest", "_pytest._version", "_pytest.outcomes"
    }


def test_development_module_alert_does_not_claim_version_or_license():
    report = mod.analyze(" _pytest\n pytest\n _not_in_map\n", {"_pytest": ["pytest"]})
    assert "_pytest" in report["development_module_candidates"]
    assert "pytest" in report["development_module_candidates"]
    assert report["members"][0]["category"] in {
        "environment_distribution_candidate", "unresolved",
    }
    assert report["scope"].startswith("Archive member TRIAGE ONLY")
