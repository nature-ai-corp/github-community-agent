"""Keep every declared application version in agreement.

The release version itself is an owner decision; these tests only make sure
that when it changes, pyproject, the package and the installer change together.
"""
import re
import tomllib
from pathlib import Path

import github_community_agent

ROOT = Path(__file__).resolve().parents[1]


def inno_spelling(pep440: str) -> str:
    """PEP 440 '1.0.0rc1' / '0.0.0.dev0' -> installer '1.0.0-rc1' / '0.0.0-dev0'."""
    return re.sub(r"\.?(dev|rc|a|b)(\d+)$", r"-\1\2", pep440)


def test_pyproject_and_package_versions_match():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert github_community_agent.__version__ == project["version"]


def test_internal_installer_default_matches_package_version():
    iss = (ROOT / "packaging/windows/gc-agent.iss").read_text(encoding="utf-8")
    default = re.search(r'#ifndef AppVersion\s+#define AppVersion "([^"]+)"', iss).group(1)
    assert default == inno_spelling(github_community_agent.__version__)


def test_inno_spelling_examples():
    assert inno_spelling("0.0.0.dev0") == "0.0.0-dev0"
    assert inno_spelling("1.0.0rc1") == "1.0.0-rc1"
    assert inno_spelling("1.0.0") == "1.0.0"


def test_release_candidate_spec_refuses_the_development_version():
    rc = (ROOT / "packaging/windows/gc-agent-release-candidate.iss").read_text(encoding="utf-8")
    assert f'#if AppVersion == "{inno_spelling(github_community_agent.__version__)}"' in rc \
        or "dev" not in github_community_agent.__version__


def test_sbom_and_exe_metadata_follow_the_package_version():
    import json
    sbom = json.loads((ROOT / "packaging/third-party-licenses/sbom.cdx.json").read_text(encoding="utf-8"))
    assert sbom["metadata"]["component"]["version"] == github_community_agent.__version__
    builder = (ROOT / "scripts/windows-build-release-bundle.ps1").read_text(encoding="utf-8")
    assert "windows_version_info.py') write --output $versionFile" in builder
    assert "'--version-file', $versionFile" in builder
