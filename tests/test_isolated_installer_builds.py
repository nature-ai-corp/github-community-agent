"""Isolated (verification/trial/probe) installer builds can never target the real
GitHub Community Agent installation or user-data folder. Static contract only.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ISS = (ROOT / "packaging" / "windows" / "gc-agent.iss").read_text(encoding="utf-8")


def _isolated_setup_block() -> str:
    m = re.search(r"\[Setup\]\s*#ifdef PayloadVerificationAppId.*?#else(.*?)#endif.*?"
                  r"#ifdef PayloadVerificationAppId(.*?)#else(.*?)#endif", ISS, re.S)
    assert m, "isolated [Setup] directives not found"
    return m.group(2)


def test_isolated_build_requires_its_own_install_folder():
    head = ISS.split("[Setup]")[0]
    assert re.search(r"#ifdef PayloadVerificationAppId.*#ifndef IsolatedInstallDir\s*#error", head, re.S)
    iso = _isolated_setup_block()
    assert "DefaultDirName={#IsolatedInstallDir}" in iso
    assert "UsePreviousAppDir=no" in iso
    assert "DisableDirPage=yes" in iso
    assert "Programs\\GitHub Community Agent" not in iso


def test_real_build_keeps_real_folder_and_previous_dir():
    m = re.search(r"#else\s*DefaultDirName=\{localappdata\}\\Programs\\GitHub Community Agent\s*"
                  r"UsePreviousAppDir=yes\s*#endif", ISS)
    assert m, "the real (non-isolated) installer must keep its install folder behaviour"


def test_isolated_build_refuses_real_install_and_data_folders_before_copying():
    code = ISS.split("[Code]", 1)[1]
    assert ISS.index("#ifdef PayloadVerificationAppId\n[Code]") >= 0
    assert "function PrepareToInstall(" in code
    assert "{localappdata}\\Programs\\GitHub Community Agent" in code
    assert "{localappdata}\\GitHubCommunityAgent" in code
    assert "refuses to install into a protected GitHub Community Agent folder" in code
    # Never deletes anything on uninstall.
    assert "[UninstallDelete]" not in ISS.replace("No [UninstallDelete]", "")


def test_every_isolated_compile_passes_an_isolated_install_dir():
    payload = (ROOT / "scripts" / "windows-verify-installer-license-payload.ps1").read_text(encoding="utf-8")
    trial = (ROOT / "scripts" / "windows_upgrade_continuity_trial.py").read_text(encoding="utf-8")
    assert '"/DIsolatedInstallDir=$installDir"' in payload
    assert "f\"/DIsolatedInstallDir={run / 'install'}\"" in trial
    for src in (payload, trial):
        assert "PayloadVerificationAppId" in src
