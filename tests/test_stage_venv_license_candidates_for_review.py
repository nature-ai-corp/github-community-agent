"""Guard license candidate staging from accidental installer or release use."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gc_license_stage", ROOT / "scripts/stage_venv_license_candidates_for_review.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_review_staging_requires_create_only_and_no_license_signoff():
    src = (ROOT / "scripts/stage_venv_license_candidates_for_review.py").read_text(
        encoding="utf-8"
    )
    assert '"frozen_versions_verified": False' in src
    assert '"third_party_license_clearance": False' in src
    assert '"installed_package_contains_these_files": False' in src
    assert '"public_release_approved": False' in src
    assert "target.mkdir(parents=True, exist_ok=False)" in src
    assert 'out.open("xb")' in src
    assert "target.exists() or target.is_symlink()" in src
    assert "legal_candidates" in src
    assert "dist-info" in src


def test_review_staging_does_not_modify_build_user_data_or_installation():
    src = (ROOT / "scripts/stage_venv_license_candidates_for_review.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "settings.dpapi", "work.sqlite3", "LOCALAPPDATA", "api_key",
        "github_token", "subprocess", "shutil", "requests.",
        "urllib.request", "PyInstaller", "ISCC.exe",
        "unlink(", ".remove(", "os.environ",
    ):
        assert forbidden not in src


def test_license_filename_match_is_explicit():
    assert mod.LEGAL_BASENAME.fullmatch("LICENSE")
    assert mod.LEGAL_BASENAME.fullmatch("LICENSE.txt")
    assert mod.LEGAL_BASENAME.fullmatch("NOTICE.md")
    assert not mod.LEGAL_BASENAME.fullmatch("credentials.json")
    assert not mod.LEGAL_BASENAME.fullmatch("setup.cfg")
