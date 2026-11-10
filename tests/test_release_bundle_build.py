"""Contracts for the clean release bundle build and Windows EXE version metadata."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

import github_community_agent

ROOT = Path(__file__).resolve().parents[1]
REQS = ROOT / "packaging" / "windows" / "build-requirements.txt"
BUILD = ROOT / "scripts" / "windows-build-release-bundle.ps1"
INSTALLER = ROOT / "scripts" / "windows-build-installer.ps1"


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tp = _load("gc_tp_rb", "third_party_notices.py")
vi = _load("gc_vi_rb", "windows_version_info.py")


def _requirements() -> dict[str, tuple[str, list[str]]]:
    text = REQS.read_text(encoding="utf-8").replace("\\\n", " ")
    out = {}
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        name, version = line.split()[0].split("==")
        out[name.lower().replace("_", "-")] = (version, re.findall(r"--hash=sha256:([0-9a-f]{64})", line))
    return out


def test_build_requirements_are_hash_locked_and_match_reviewed_pins():
    reqs = _requirements()
    for name, (version, hashes) in reqs.items():
        assert hashes, f"{name} has no sha256 hash"
    for name, (version, _spdx, _repo) in tp.PY_DISTRIBUTIONS.items():
        assert reqs[name][0] == version, name
    assert reqs["pyinstaller"][0] == tp.PYINSTALLER_VERSION


def test_build_requirements_contain_no_test_or_dev_tooling():
    for forbidden in ("pytest", "pygments", "colorama", "iniconfig", "pluggy", "coverage"):
        assert forbidden not in _requirements(), forbidden


def test_release_build_script_verifies_runtime_and_fails_closed():
    script = BUILD.read_text(encoding="utf-8")
    for token in ("Get-AuthenticodeSignature", "CN=Python Software Foundation",
                  "libssl-3.dll", "libcrypto-3.dll", r"^OpenSSL 3\.5\.\d+ ",
                  f"$expectedPython = '{tp.PYTHON_VERSION}'",
                  "--require-hashes", "--only-binary", "--version-file",
                  "windows_version_info.py') check", "--self-check",
                  "Test-only distributions present", "Test-only modules frozen",
                  "nothing is overwritten"):
        assert token in script, token
    for forbidden in ("Set-AuthenticodeSignature", "signtool", "gh release", "git push",
                      "Remove-Item", "settings.dpapi", "work.sqlite3"):
        assert forbidden not in script, forbidden


def test_installer_build_defaults_to_clean_bundle_and_stamps_version():
    script = INSTALLER.read_text(encoding="utf-8")
    assert "build\\release-bundle\\dist\\GitHubCommunityAgent" in script
    assert "build\\release-bundle\\venv\\Scripts\\python.exe" in script
    assert "'.venv\\Scripts\\python.exe'" not in script
    assert '"/DAppVersion=$appVersion"' in script
    assert script.index("windows_version_info.py') check --exe") < script.index("& $compiler")


@pytest.mark.parametrize("version,nums,inno", [
    ("0.0.0.dev0", (0, 0, 0, 0), "0.0.0-dev0"),
    ("1.0.0rc1", (1, 0, 0, 0), "1.0.0-rc1"),
    ("1.0.0", (1, 0, 0, 0), "1.0.0"),
    ("1.2.3b4", (1, 2, 3, 0), "1.2.3-b4"),
])
def test_version_mapping(version, nums, inno):
    assert vi.numeric(version) == nums
    assert vi.inno(version) == inno


@pytest.mark.parametrize("bad", ["1.0", "v1.0.0", "1.0.0-rc1", "1.0.0.post1", ""])
def test_unsupported_versions_are_rejected(bad):
    with pytest.raises(ValueError):
        vi.numeric(bad)


def test_version_file_carries_exact_package_version():
    assert vi.package_version() == github_community_agent.__version__
    text = vi.render(github_community_agent.__version__)
    assert f"StringStruct('FileVersion', '{github_community_agent.__version__}')" in text
    assert f"StringStruct('ProductVersion', '{github_community_agent.__version__}')" in text
    assert f"filevers={vi.numeric(github_community_agent.__version__)}" in text
    assert "not affiliated with GitHub, Inc." in text
    # Must be a valid PyInstaller VSVersionInfo expression when PyInstaller exists.
    versioninfo = pytest.importorskip("PyInstaller.utils.win32.versioninfo")
    namespace = {k: getattr(versioninfo, k) for k in dir(versioninfo) if not k.startswith("_")}
    info = eval(text.split("\n", 2)[2], namespace)  # noqa: S307 - our own generated text
    n = vi.numeric(github_community_agent.__version__)
    assert info.ffi.fileVersionMS == (n[0] << 16) | n[1]
