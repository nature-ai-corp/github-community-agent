"""Read-only legal-material presence inventory for the GC Agent frozen candidate.

Lists discovered license/notice files in build VENV and existing frozen
bundle, and checks current Inno installer source declarations. Does NOT
copy text, infer frozen exact versions, or certify redistribution compliance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import re
from datetime import datetime, timezone
from pathlib import Path

TARGETS = ("anyio", "certifi", "h11", "httpcore", "httpx", "idna", "typing-extensions")
LICENSE_NAME = re.compile(r"(?i)(?:^|/)(?:license|licence|copying|notice|copyright)(?:[._-]|$)")
MAX_TEXT_SIZE = 2_000_000


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1_048_576), b""):
            sha.update(chunk)
    return sha.hexdigest().upper()


def build(bundle: Path, installer: Path) -> dict:
    root = bundle.resolve(strict=True)
    if root.name != "GitHubCommunityAgent" or bundle.is_symlink():
        raise ValueError("Only the existing GC Agent onedir may be inspected")
    if not (root / "GitHubCommunityAgent.exe").is_file():
        raise ValueError("Missing frozen EXE")
    if not installer.is_file():
        raise ValueError("Missing Inno Setup input")
    iss = installer.read_text(encoding="utf-8")
    # Installer is a SOURCE CONTRACT, not proof of actual installed output.
    contract = {
        "includes_first_party_LICENSE": bool(re.search(r'(?im)^Source:\s*"[^"]*\\LICENSE";', iss)),
        "includes_first_party_NOTICE": bool(re.search(r'(?im)^Source:\s*"[^"]*\\NOTICE";', iss)),
        "copies_frozen_bundle_recursive": "recursesubdirs" in iss and "GitHubCommunityAgent\\*" in iss,
        "explicit_third_party_license_directory": bool(re.search(r'(?im)^Source:.*(?:THIRD_PARTY|third.party)', iss)),
    }
    distributions = []
    for canonical in TARGETS:
        normalized = canonical.replace("-", "_")
        try:
            dist = md.distribution(canonical)
        except md.PackageNotFoundError:
            distributions.append({"name": canonical, "available_in_current_venv": False,
                                  "license_files": [], "source_version_verified_in_frozen": False})
            continue
        files = []
        for file in dist.files or ():
            rel = file.as_posix()
            if not LICENSE_NAME.search(rel):
                continue
            loc = Path(dist.locate_file(file))
            if (not loc.is_file() or loc.is_symlink()
                    or loc.stat().st_size > MAX_TEXT_SIZE):
                continue
            files.append({"venv_relative_path": rel, "sha256": digest(loc),
                          "size_bytes": loc.stat().st_size})
        distributions.append({
            "name": canonical,
            "current_venv_version_candidate": dist.version,
            "current_venv_license_metadata": dist.metadata.get("License-Expression")
                                             or dist.metadata.get("License") or "",
            "license_files": sorted(files, key=lambda x: x["venv_relative_path"]),
            "source_version_verified_in_frozen": False,
            "license_in_final_installer_verified": False,
        })
    frozen_license_files = []
    for relative in ("_internal/_tk_data/license.terms", "LICENSE", "NOTICE",
                     "THIRD_PARTY_NOTICES.txt"):
        p = root / relative
        if p.is_file() and not p.is_symlink() and p.stat().st_size <= MAX_TEXT_SIZE:
            frozen_license_files.append({"frozen_relative_path": relative,
                                         "sha256": digest(p),
                                         "size_bytes": p.stat().st_size})
    return {
        "scope": "Actual frozen candidate + CURRENT build venv + Inno script license-file PRESENCE only",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "installer_source_contract": contract,
        "venv_license_material_candidates": distributions,
        "existing_frozen_license_materials": frozen_license_files,
        "full_redistribution_license_review_pass": False,
        "all_frozen_versions_proven": False,
        "optimized_installer_built_verified": False,
        "release_approved": False,
        "blockers": [
            "Venv license files do not automatically enter PyInstaller onedir or Inno installer",
            "Confirm actual exact frozen versions and bundle provenance",
            "Review CPython bundled licenses (including incorporated software)",
            "Review Tcl/Tk licensing and whether notice covers all Tcl/Tk binary/data files",
            "Review certifi MPL-2.0 source availability and executable distribution notices",
            "Review OpenSSL 3 Apache-2.0 and component notices",
            "Review libffi/zlib and Visual C++ redistributable licensing with actual origins",
            "Verify installed optimized installer payload before any release signoff",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", required=True, type=Path)
    p.add_argument("--installer-script", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    if args.output.exists():
        p.error("Existing audit output must be preserved")
    data = build(args.bundle, args.installer_script)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(data, out, indent=2)
        out.write("\n")
    print("Installer LICENSE/NOTICE source declarations:", data["installer_source_contract"])
    for item in data["venv_license_material_candidates"]:
        print("VENV license candidates:", item["name"], len(item["license_files"]))
    print("Frozen license material files:", len(data["existing_frozen_license_materials"]))
    print("Audit report:", args.output)
    print("RELEASE BLOCKED: not verified versioned frozen licenses, source availability or actual installer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
