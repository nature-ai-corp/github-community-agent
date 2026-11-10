"""Static contract for the MANUAL installer license-page test kit.

The kit must stay isolated (temporary AppId and folder, real data fingerprinted)
and must never generate UI input: the person operates the wizard.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = (ROOT / "scripts" / "windows-manual-license-page-test.ps1").read_text(encoding="utf-8")


def test_kit_never_sends_ui_input():
    lowered = KIT.lower()
    for forbidden in ("sendmessage", "postmessage", "sendkeys", "sendinput", "keybd_event",
                      "mouse_event", "uiautomation", "invokepattern", "selectionitempattern",
                      "wscript.shell", "appactivate", "/verysilent\", \"/dir", "/silent"):
        assert forbidden not in lowered, forbidden
    assert "automated_ui_input_used = $false" in KIT


def test_kit_uses_isolated_identity_and_folder_and_fingerprints_real_data():
    assert '"/DPayloadVerificationAppId={{$guid}"' in KIT
    assert '"/DIsolatedInstallDir=$installDir"' in KIT
    assert "build\\manual-license-test\\run-" in KIT
    assert "{B728F255-29F8-438B-B2F7-E495DF0120E1}" in KIT  # real AppId only READ for fingerprinting
    assert "B728F255" not in KIT.split("$realAppKey =")[0]
    for real in ("Programs\\GitHub Community Agent\\GitHubCommunityAgent.exe", "work.sqlite3", "settings.dpapi"):
        assert real in KIT
    assert "real_installation_and_user_data_unchanged" in KIT


def test_kit_expectations_per_scenario():
    assert "ValidateSet('Decline', 'Accept')" in KIT
    # Inno Setup exit code 2 = cancelled before the installation started.
    assert "($exit -eq 2) -and -not $installed -and -not $registered -and $untouched" in KIT
    assert "($exit -eq 0) -and $installed -and $payloadOk -and $uninstalled -and $untouched" in KIT
    assert "verify-installed" in KIT
    assert "[switch]$PrepareOnly" in KIT
