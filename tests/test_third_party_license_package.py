"""Guard the third-party LICENSE/NOTICE/SBOM distribution package.

Static tests run everywhere (CI included). Tests marked as needing the frozen
bundle run only on a Windows build machine with the optimized onedir and the
build venv; they prove the committed package still matches that bundle, so a
future rebuild that changes dependencies cannot silently ship stale notices.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "packaging" / "third-party-licenses"
ISS = ROOT / "packaging" / "windows" / "gc-agent.iss"
BUILD = ROOT / "scripts" / "windows-build-installer.ps1"
VERIFY = ROOT / "scripts" / "windows-verify-installer-license-payload.ps1"
# Override to check another clean build (e.g. a provisional release-candidate output).
BUNDLE = Path(os.environ.get("GC_AGENT_BUNDLE") or
              ROOT / "build" / "release-bundle" / "dist" / "GitHubCommunityAgent")

SPEC = importlib.util.spec_from_file_location("gc_third_party", ROOT / "scripts" / "third_party_notices.py")
tp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tp)


def _manifest() -> dict:
    return json.loads((PACKAGE / "MANIFEST.json").read_text(encoding="utf-8"))


def _sbom() -> dict:
    return json.loads((PACKAGE / "sbom.cdx.json").read_text(encoding="utf-8"))


# ------------------------------------------------------- committed package

def test_committed_package_is_complete_and_unaltered():
    assert tp.validate_package(PACKAGE) == []
    assert {"THIRD_PARTY_NOTICES.txt", "sbom.cdx.json"} <= set(_manifest()["files"])


def test_every_pinned_distribution_and_runtime_component_has_license_text():
    files = set(_manifest()["files"])
    for name, (version, _spdx, _repo) in tp.PY_DISTRIBUTIONS.items():
        assert any(f.startswith(f"python-packages/{name}-{version}/") for f in files), name
    for key, _name, _version, _lic, where, _purl in tp.NATIVE_SBOM:
        for ref in where:
            target = ref.split(" (")[0]
            assert target in files or target == "THIRD_PARTY_NOTICES.txt", (key, ref)


def test_sbom_is_cyclonedx_and_describes_the_packaged_bundle():
    sbom = _sbom()
    assert sbom["bomFormat"] == "CycloneDX" and sbom["specVersion"] == "1.5"
    assert sbom["serialNumber"].startswith("urn:uuid:")
    app = sbom["metadata"]["component"]
    assert app["name"] == "github-community-agent"
    assert app["licenses"] == [{"expression": "Apache-2.0"}]
    assert app["hashes"][0]["content"] == _manifest()["bundle"]["exe_sha256"]
    refs = [c["bom-ref"] for c in sbom["components"]]
    assert len(refs) == len(set(refs))
    names = {c["name"] for c in sbom["components"]}
    assert set(tp.PY_DISTRIBUTIONS) <= names
    for component in sbom["components"]:
        assert component["licenses"], component["name"]
        assert component["version"], component["name"]
        for f in component.get("components", []):
            assert f["hashes"][0]["alg"] == "SHA-256" and len(f["hashes"][0]["content"]) == 64
    # All 25 runtime binaries plus the bootloader EXE are hashed individually.
    hashed = [f for c in sbom["components"] for f in c.get("components", [])]
    assert len(hashed) == 26
    assert sbom["dependencies"][0]["dependsOn"] == sorted(refs)


def test_notices_reproduce_every_license_text_in_full():
    notices = (PACKAGE / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    for rel in _manifest()["files"]:
        if rel in ("THIRD_PARTY_NOTICES.txt", "sbom.cdx.json") or rel in tp.BINARY_UPSTREAM:
            continue  # the certifi source archive is referenced by path, not inlined
        body = tp._text((PACKAGE / rel).read_bytes()).strip()
        assert body in notices, rel
    for name, (version, spdx, _repo) in tp.PY_DISTRIBUTIONS.items():
        assert f"* {name} {version}\n    License: {spdx}" in notices


def test_mpl_source_availability_and_special_conditions_are_stated():
    notices = (PACKAGE / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    url, digest = tp.CERTIFI_SDIST
    assert url in notices and digest in notices
    assert "Source Code Form" in notices and "certifi-2026.10.23/MPL-2.0.txt" in notices
    # MPL-2.0 s3.2: the exact Source Code Form ships inside the package itself.
    assert tp.CERTIFI_SDIST_REL in notices
    assert _manifest()["files"][tp.CERTIFI_SDIST_REL] == digest
    assert hashlib.sha256((PACKAGE / tp.CERTIFI_SDIST_REL).read_bytes()).hexdigest() == digest
    assert "Mozilla Public License Version 2.0" in (PACKAGE / "certifi-2026.10.23/MPL-2.0.txt").read_text()
    assert "Additional Conditions for this Windows binary build" in notices
    # PSF License clause 3 requires a summary of changes made to Python.
    assert (f"Summary of changes made to Python {tp.PYTHON_VERSION} (PSF License Agreement,\n"
            "clause 3): none.") in notices
    assert "Microsoft Distributable Code" in (PACKAGE / tp.WIN_LICENSE).read_text()
    assert "Bootloader Exception" in (PACKAGE / "pyinstaller-6.22.3/COPYING.txt").read_text()
    for section in ("OpenSSL", "expat", "libffi", "zlib", "libmpdec"):
        assert f"\n{section}\n" in (PACKAGE / tp.NOTICE_SECTIONS).read_text(encoding="utf-8")


def test_github_independence_disclaimer_is_shipped_everywhere():
    phrase = "not affiliated with, sponsored by, or endorsed by GitHub, Inc."
    notices = (PACKAGE / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    assert "Independence from GitHub" in notices
    assert phrase in " ".join(notices.split())
    assert phrase in " ".join((ROOT / "NOTICE").read_text(encoding="utf-8").split())
    assert phrase in (ROOT / "README.md").read_text(encoding="utf-8")


def test_runtime_pins_use_supported_openssl_line():
    sbom = {c["bom-ref"]: c for c in _sbom()["components"]}
    assert tp.OPENSSL_VERSION.startswith("3.5.")
    assert sbom["openssl"]["version"] == tp.OPENSSL_VERSION
    assert sbom["cpython"]["version"] == tp.PYTHON_VERSION
    assert not any(f.startswith("cpython-3.13.14/") for f in _manifest()["files"])
    for component in sbom.values():
        assert "3.0.21" not in json.dumps(component)


def test_package_never_claims_legal_approval_or_release():
    manifest = _manifest()
    # No internal approval flag (release procedure 2026-11-10); provenance evidence stays.
    assert "legal_review_approved" not in manifest and "legal_review_note" not in manifest
    assert manifest["provenance_verified"] is True
    assert "Not legal advice" in manifest["evidence_note"]
    generated = (PACKAGE / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8").split("Full license texts")[0]
    for claim in ("compliance complete", "fully compliant", "legally approved", "release approved"):
        assert claim not in generated.lower()


def test_verbatim_texts_are_protected_from_line_ending_conversion():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "packaging/third-party-licenses/** -text" in attributes
    if shutil.which("git"):
        out = subprocess.run(
            ["git", "check-attr", "text", "--", "packaging/third-party-licenses/MANIFEST.json"],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout
        assert out.strip().endswith("unset")


# ---------------------------------------------------- tamper and payload logic

def _fake_package(tmp_path: Path, exe: bytes) -> Path:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    files = {"THIRD_PARTY_NOTICES.txt": b"notice\n", "python-packages/x-1/LICENSE": b"MIT\n"}
    for rel, data in files.items():
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        (pkg / rel).write_bytes(data)
    manifest = {"files": {k: hashlib.sha256(v).hexdigest() for k, v in files.items()},
                "bundle": {"exe_sha256": hashlib.sha256(exe).hexdigest()}}
    (pkg / "MANIFEST.json").write_text(json.dumps(manifest))
    return pkg


def test_validate_package_detects_tampering(tmp_path):
    pkg = _fake_package(tmp_path, b"exe")
    assert tp.validate_package(pkg) == []
    (pkg / "python-packages/x-1/LICENSE").write_bytes(b"changed\n")
    (pkg / "extra.txt").write_bytes(b"x")
    (pkg / "THIRD_PARTY_NOTICES.txt").unlink()
    errors = tp.validate_package(pkg)
    assert "hash mismatch: python-packages/x-1/LICENSE" in errors
    assert "unlisted file: extra.txt" in errors
    assert "missing file: THIRD_PARTY_NOTICES.txt" in errors
    manifest = json.loads((pkg / "MANIFEST.json").read_text())
    manifest["legal_review_approved"] = False   # obsolete internal approval flag
    (pkg / "MANIFEST.json").write_text(json.dumps(manifest))
    assert "obsolete internal approval field present: legal_review_approved" in tp.validate_package(pkg)


def _install(app: Path, bundle: Path, pkg: Path, repo: Path) -> None:
    shutil.copytree(bundle, app)
    shutil.copytree(pkg, app / "third-party-licenses")
    for name, source in tp.INSTALLED_REPO_FILES.items():
        shutil.copy(repo / source, app / name)
    (app / "unins000.exe").write_bytes(b"uninstaller")


def test_verify_installed_passes_only_for_exact_payload(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "_internal").mkdir(parents=True)
    (bundle / tp.EXE_NAME).write_bytes(b"exe")
    (bundle / "_internal" / "lib.dll").write_bytes(b"dll")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "LICENSE").write_bytes(b"Apache\n")
    (repo / "NOTICE").write_bytes(b"Notice\n")
    (repo / "packaging" / "windows").mkdir(parents=True)
    (repo / "packaging" / "windows" / "END_USER_TERMS.txt").write_bytes(b"Terms\n")
    pkg = _fake_package(tmp_path, b"exe")

    app = tmp_path / "app-ok"
    _install(app, bundle, pkg, repo)
    report = tp.verify_installed(app, pkg, bundle, repo)
    assert report["pass"] and report["errors"] == []
    assert "legal_review_approved" not in report

    app = tmp_path / "app-missing-notice"
    _install(app, bundle, pkg, repo)
    (app / "third-party-licenses" / "THIRD_PARTY_NOTICES.txt").unlink()
    assert "not installed: third-party-licenses/THIRD_PARTY_NOTICES.txt" in \
        tp.verify_installed(app, pkg, bundle, repo)["errors"]

    app = tmp_path / "app-altered"
    _install(app, bundle, pkg, repo)
    (app / "third-party-licenses" / "python-packages/x-1/LICENSE").write_bytes(b"edited\n")
    (app / "NOTICE").write_bytes(b"other\n")
    (app / "stray.txt").write_bytes(b"?")
    errors = tp.verify_installed(app, pkg, bundle, repo)["errors"]
    assert "installed copy differs: third-party-licenses/python-packages/x-1/LICENSE" in errors
    assert "NOTICE missing or different after install" in errors
    assert "unexpected installed file: stray.txt" in errors

    app = tmp_path / "app-missing-terms"
    _install(app, bundle, pkg, repo)
    (app / "END_USER_TERMS.txt").unlink()
    assert "END_USER_TERMS.txt missing or different after install" in \
        tp.verify_installed(app, pkg, bundle, repo)["errors"]

    app = tmp_path / "app-wrong-exe"
    _install(app, bundle, pkg, repo)
    (app / tp.EXE_NAME).write_bytes(b"different build")
    assert "installed EXE is not the bundle described by MANIFEST.json" in \
        tp.verify_installed(app, pkg, bundle, repo)["errors"]


# ------------------------------------------------- installer/build contracts

def test_internal_installer_ships_the_package_and_fails_closed_without_it():
    iss = ISS.read_text(encoding="utf-8")
    assert '#define ThirdPartyDir AddBackslash(SourcePath) + "..\\third-party-licenses"' in iss
    assert ('Source: "{#ThirdPartyDir}\\*"; DestDir: "{app}\\third-party-licenses"; '
            "Flags: recursesubdirs createallsubdirs ignoreversion") in iss
    assert '#if !FileExists(ThirdPartyDir + "\\THIRD_PARTY_NOTICES.txt")' in iss
    assert '#if !FileExists(ThirdPartyDir + "\\MANIFEST.json")' in iss
    assert iss.count("#error") >= 2
    assert (ISS.parent / ".." / "third-party-licenses" / "THIRD_PARTY_NOTICES.txt").resolve().is_file()
    # The real product identity is the default; verification uses its own.
    assert "AppId={{B728F255-29F8-438B-B2F7-E495DF0120E1}" in iss
    assert "AppId={#PayloadVerificationAppId}" in iss
    # Default input is the clean release bundle, never the dev dist/ build.
    assert '#define BundleDir "..\\..\\build\\release-bundle\\dist\\GitHubCommunityAgent"' in iss
    assert "dist\\GitHubCommunityAgent\"" not in iss.replace("release-bundle\\dist", "")


def test_upgrade_trial_inherits_the_third_party_package():
    trial = (ISS.parent / "gc-agent-upgrade-trial.iss").read_text(encoding="utf-8")
    assert '#include "gc-agent.iss"' in trial


def test_installer_build_refuses_package_that_does_not_match_bundle():
    script = BUILD.read_text(encoding="utf-8")
    gate = script.index("third_party_notices.py') check --bundle $BundleDir")
    assert gate < script.index("& $compiler")
    assert "installer not built" in script[gate:script.index("& $compiler")]
    assert '"/DBundleDir=$BundleDir"' in script


def test_payload_verifier_installs_only_an_isolated_identity_and_guards_user_data():
    script = VERIFY.read_text(encoding="utf-8")
    assert "[guid]::NewGuid()" in script and "/DPayloadVerificationAppId={{$guid}" in script
    assert "B728F255" not in script  # never targets the real installation
    for token in ("/CURRENTUSER", "/VERYSILENT", "/DIR=", "unins000.exe", "verify-installed",
                  "work.sqlite3", "settings.dpapi", "refusing to overwrite",
                  "third-party-licenses\\$relative", "real_installation_and_user_data_unchanged"):
        assert token in script, token
    assert "legal_review_approved" not in script
    for forbidden in ("Remove-Item", "Set-AuthenticodeSignature", "gh release", "git push",
                      "GitHubCommunityAgent.exe --", "Invoke-WebRequest"):
        assert forbidden not in script, forbidden


# -------------------------------------- bound to the actual frozen bundle

def _bundle_ready() -> bool:
    try:
        import pefile  # noqa: F401
        import PyInstaller  # noqa: F401
    except ImportError:
        return False
    return BUNDLE.joinpath(tp.EXE_NAME).is_file() and sys.version.split()[0] == tp.PYTHON_VERSION


needs_bundle = pytest.mark.skipif(not _bundle_ready(),
                                  reason="optimized frozen bundle / build venv not present")


@needs_bundle
def test_committed_package_matches_actual_frozen_bundle():
    assert tp.check(BUNDLE, PACKAGE) == []


@needs_bundle
def test_unreviewed_or_relicensed_dependency_fails_closed(monkeypatch):
    pins = dict(tp.PY_DISTRIBUTIONS)
    del pins["idna"]
    monkeypatch.setattr(tp, "PY_DISTRIBUTIONS", pins)
    with pytest.raises(tp.BundleError, match="Unreviewed third-party distribution bundled: idna"):
        tp.analyze_bundle(BUNDLE)
    pins = dict(tp.PY_DISTRIBUTIONS, idna=("3.20", "BSD-3-Clause", "x"),
                httpx=("0.28.1", "MIT", "x"))
    monkeypatch.setattr(tp, "PY_DISTRIBUTIONS", pins)
    with pytest.raises(tp.BundleError, match="httpx: venv 0.28.1/'BSD-3-Clause' != pinned 0.28.1/MIT"):
        tp.analyze_bundle(BUNDLE)


@pytest.mark.skipif(os.environ.get("GC_AGENT_VERIFY_INSTALLER") != "1" or os.name != "nt",
                    reason="opt-in: builds, installs into build/ and uninstalls an isolated installer")
def test_built_installer_actually_installs_license_package():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(VERIFY)],
        cwd=ROOT, capture_output=True, text=True, timeout=900)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "INSTALLER LICENSE PAYLOAD VERIFICATION PASS" in result.stdout
