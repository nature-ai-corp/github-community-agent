"""Static contract for the PREPARED (not yet used) Windows code-signing path.

No signing, network, credentials or installation: these tests read scripts only.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_installer_signing_is_opt_in_and_signs_uninstaller():
    iss = _read("packaging/windows/gc-agent.iss")
    block = re.search(r"#ifdef SignToolName\s*(.*?)#endif", iss, re.S)
    assert block, "SignTool must only be enabled when SignToolName is defined"
    body = block.group(1)
    assert "SignTool={#SignToolName}" in body
    assert "SignedUninstaller=yes" in body
    outside = iss.replace(block.group(0), "")
    assert "SignTool=" not in outside, "default (unsigned) build must not sign"
    # The sign command (paths, account) is passed via ISCC /S, never stored here.
    for forbidden in ("signtool.exe", "codesigning.azure.net", "dlib", "metadata.json"):
        assert forbidden not in iss.lower()


def test_sign_script_defaults_to_plan_and_uses_sha256_with_timestamp():
    s = _read("scripts/windows-sign-release.ps1")
    assert "[switch]$Execute" in s
    assert "PLAN ONLY: nothing was signed" in s
    plan_exit = s.index("if (-not $Execute)")
    first_sign = s.index("& $SignTool @signArgs")
    assert plan_exit < first_sign, "plan mode must exit before any signing call"
    for token in ("'/fd', 'SHA256'", "'/td', 'SHA256'", "'/tr', $TimestampUrl", "'/dlib'", "'/dmdf'"):
        assert token in s
    assert "http://timestamp.acs.microsoft.com" in s
    # Never re-sign; never accept credentials in metadata; verify after signing.
    assert "Never re-sign" in s
    assert "must not contain credentials" in s
    assert "windows-verify-signatures.ps1" in s
    assert "--self-check" in s
    # Signs only our EXE, not the bundle's third-party binaries.
    assert "$target = Join-Path $bundle 'GitHubCommunityAgent.exe'" in s
    assert s.count("$target") >= 3 and "@signArgs" in s


def test_signed_installer_requires_signed_bundle_first_and_verifies_output():
    s = _read("scripts/windows-build-installer.ps1")
    i_guard = s.index("'-BundleDir', $BundleDir")
    i_compile = s.index("@signDefines $iss")
    assert i_guard < i_compile, "bundle signature must be verified before compiling a signed installer"
    assert "/fd SHA256 /tr http://timestamp.acs.microsoft.com /td SHA256" in s
    assert "Signed installer verification FAILED" in s
    assert "'/DSignToolName=artifact'" in s


def test_verifier_is_read_only_and_checks_policy():
    s = _read("scripts/windows-verify-signatures.ps1")
    assert "verify /pa /all /v" in s
    for check in ("sha256", "timestamped", "TimeStamperCertificate", "ExpectedSigner"):
        assert check in s
    # Third-party binaries must keep their ORIGINAL publisher signature.
    assert "CN=Python Software Foundation" in s
    assert "CN=Microsoft Windows Software Compatibility Publisher" in s
    lowered = s.lower()
    for forbidden in (" sign /", "set-authenticodesignature", "remove-item", "invoke-webrequest"):
        assert forbidden not in lowered


def test_ci_never_signs():
    ci = _read(".github/workflows/tests.yml").lower()
    for forbidden in ("artifact-signing-action", "signtool", "azure/login", "secrets."):
        assert forbidden not in ci
