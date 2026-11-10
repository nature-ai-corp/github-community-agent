"""Offline safety contract for frozen license material inventory."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gc_license_presence", ROOT / "scripts/frozen_license_material_presence.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_installer_source_contains_first_party_notice_and_third_party_package():
    script = (ROOT / "packaging/windows/gc-agent.iss").read_text(encoding="utf-8")
    # SOURCE contract only. The built-installer payload is verified separately by
    # scripts/windows-verify-installer-license-payload.ps1 (see
    # tests/test_third_party_license_package.py).
    import re
    assert re.search(r'(?im)^Source:\s*"[^"]*\\LICENSE";', script)
    assert re.search(r'(?im)^Source:\s*"[^"]*\\NOTICE";', script)
    assert "recursesubdirs" in script
    assert "THIRD_PARTY_NOTICES.txt" in script
    # The same pattern the presence audit uses now detects the directory.
    assert re.search(r'(?im)^Source:.*(?:THIRD_PARTY|third.party)', script)


def test_report_never_auto_claims_license_approval():
    s = (ROOT / "scripts/frozen_license_material_presence.py").read_text(encoding="utf-8")
    assert '"full_redistribution_license_review_pass": False' in s
    assert '"all_frozen_versions_proven": False' in s
    assert '"optimized_installer_built_verified": False' in s
    assert '"release_approved": False' in s
    assert "source_version_verified_in_frozen" in s
    assert 'with args.output.open("x"' in s
    for forbidden in (
        "shutil.copy", "Remove-Item", "Copy-Item", "subprocess",
        "settings.dpapi", "work.sqlite3", "api_key", "read_token",
        "httpx.get", "requests.get", "urllib.request", "os.environ",
    ):
        assert forbidden not in s
