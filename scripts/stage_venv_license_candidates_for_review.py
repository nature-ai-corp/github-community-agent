"""Stage exact current-venv third-party LICENSE bytes for HUMAN review only.

This does not install, modify a frozen EXE, or create legal clearance.
Candidate versions/bytes from current venv cannot prove frozen provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import re
from datetime import datetime, timezone
from pathlib import Path

PACKAGES = ("anyio", "certifi", "h11", "httpcore", "httpx", "idna", "typing-extensions")
MAX_LICENSE_FILE = 2_000_000
MAX_LICENSES_PER_DIST = 12
LEGAL_BASENAME = re.compile(r"(?i)^(?:license|licence|copying|notice|copyright)(?:[._-].*)?$")


def legal_candidates(dist: md.Distribution) -> list[tuple[Path, Path]]:
    selected = []
    for entry in dist.files or ():
        rel = Path(entry.as_posix())
        parts = rel.parts
        # Restrict to dist's metadata directory, never arbitrary package data.
        if not parts or not parts[0].endswith(".dist-info"):
            continue
        if any(part in ("", ".", "..") for part in parts):
            continue
        if not LEGAL_BASENAME.fullmatch(rel.name):
            continue
        path = Path(dist.locate_file(entry))
        if not path.is_file() or path.is_symlink():
            continue
        if path.stat().st_size > MAX_LICENSE_FILE:
            raise ValueError(f"Oversized legal candidate for {dist.metadata['Name']}")
        selected.append((rel, path))
        if len(selected) > MAX_LICENSES_PER_DIST:
            raise ValueError("Too many license files; review manually")
    return selected


def collect() -> tuple[list[dict], list[tuple[str, bytes]]]:
    manifest = []
    payloads = []
    for name in PACKAGES:
        dist = md.distribution(name)
        files = legal_candidates(dist)
        entries = []
        for i, (rel, path) in enumerate(files):
            raw = path.read_bytes()
            filename = f"{name}/{i:02d}-{rel.name}"
            entries.append({
                "candidate_venv_relative_path": rel.as_posix(),
                "staged_path": filename,
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest().upper(),
            })
            payloads.append((filename, raw))
        manifest.append({
            "package_candidate": name,
            "current_venv_version_only": dist.version,
            "license_metadata_only": (dist.metadata.get("License-Expression")
                                      or dist.metadata.get("License") or "")[:240],
            "license_material_candidates": entries,
            "frozen_origin_verified": False,
            "redistribution_requirements_reviewed": False,
        })
    return manifest, payloads


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    target = args.output_dir
    if target.exists() or target.is_symlink():
        p.error("Refusing to overwrite earlier license review material")
    manifest, payloads = collect()
    if any(not item["license_material_candidates"] for item in manifest):
        p.error("Missing at least one requested VENV license file; no partial output")
    target.mkdir(parents=True, exist_ok=False)
    for relative, raw in payloads:
        out = target / relative
        out.parent.mkdir(parents=True, exist_ok=False) if not out.parent.exists() else None
        with out.open("xb") as file:
            file.write(raw)
    result = {
        "scope": "VERBATIM current build-venv license candidates for HUMAN review, NOT a release third-party notices package",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_distributions": manifest,
        "frozen_versions_verified": False,
        "third_party_license_clearance": False,
        "installed_package_contains_these_files": False,
        "public_release_approved": False,
    }
    with (target / "REVIEW_MANIFEST.json").open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2)
        file.write("\n")
    print("Staged seven current-venv license sets for HUMAN review:", target)
    print("Candidate text files:", len(payloads))
    print("NEITHER installer package NOR copyright clearance; frozen origin and obligations OPEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
