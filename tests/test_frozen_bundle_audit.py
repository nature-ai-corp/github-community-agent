"""Frozen build file/hash audit tests. No build or network required."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "frozen_bundle_audit", ROOT / "scripts" / "frozen_bundle_inventory.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_frozen_bundle_audit_records_actual_files_and_hashes(tmp_path):
    bundle = tmp_path / "GitHubCommunityAgent"
    bundle.mkdir()
    app = bundle / "GitHubCommunityAgent.exe"
    app.write_bytes(b"test-executable")
    internal = bundle / "_internal"
    internal.mkdir()
    binary = internal / "python313.dll"
    binary.write_bytes(b"test-runtime")
    ui = internal / "home.html"
    ui.write_text("<!doctype html>", encoding="utf-8")

    manifest = mod.inventory(bundle)
    assert manifest["file_count"] == 3
    assert manifest["category_counts"]["binary"] == 2
    assert manifest["category_counts"]["ui_asset"] == 1
    assert "not a complete license/SBOM" in manifest["scope"]
    files = {f["path"]: f for f in manifest["files"]}
    assert files["GitHubCommunityAgent.exe"]["sha256"] == hashlib.sha256(
        b"test-executable"
    ).hexdigest().upper()
    assert files["_internal/python313.dll"]["size_bytes"] == len(b"test-runtime")
    assert manifest["review_required"]


@pytest.mark.parametrize("secret_name", ["settings.dpapi", "work.sqlite3", ".env", "credentials.json"])
def test_frozen_bundle_audit_refuses_secret_data_files(tmp_path, secret_name):
    bundle = tmp_path / "GitHubCommunityAgent"
    bundle.mkdir()
    (bundle / "GitHubCommunityAgent.exe").write_bytes(b"safe")
    (bundle / secret_name).write_text("secret", encoding="utf-8")
    with pytest.raises(ValueError, match="Forbidden"):
        mod.inventory(bundle)


def test_frozen_bundle_audit_refuses_non_gc_root(tmp_path):
    bundle = tmp_path / "DifferentProduct"
    bundle.mkdir()
    (bundle / "GitHubCommunityAgent.exe").write_bytes(b"safe")
    with pytest.raises(ValueError, match="GC Agent"):
        mod.inventory(bundle)


def test_frozen_audit_windows_script_uses_official_archive_viewer_without_writes():
    script = (ROOT / "scripts" / "windows-frozen-payload-audit.ps1").read_text(
        encoding="utf-8"
    )
    assert "pyi-archive_viewer.exe" in script
    assert "--brief --recursive" in script
    assert "frozen_bundle_inventory.py" in script
    assert "frozen-bundle-files.json" in script
    assert "frozen-embedded-archive.txt" in script
    assert "Existing audit output must be preserved" in script
    for prohibited in ("Remove-Item", "Stop-Process", "Start-Process",
                       "Set-MpPreference", "Set-AuthenticodeSignature"):
        assert prohibited not in script
