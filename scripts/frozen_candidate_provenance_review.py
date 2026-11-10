"""Candidate frozen-component provenance review (not a final SBOM).

Uses hashes/relative paths from the *real candidate*, PyInstaller archive
triage and metadata of the CURRENT venv. Explicitly distinguishes proven
files from candidate distribution mappings; no network/credentials.
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROVENANCE_REQUIRED = [
    "Python runtime executable and stdlib redistribution license",
    "Tcl/Tk 8.6 binaries and data license/copyright",
    "Windows C runtime, OpenSSL, SQLite, libffi, zlib binary origins/licenses",
    "PyInstaller executable bootloader and bundled runtime helpers",
    "certifi public CA trust store provenance and notices",
    "Each actual Python distribution: exact frozen build version and license text",
    "Distribution package LICENSE/NOTICE included in installer as required",
]


def build(manifest: dict, triage: dict) -> dict:
    if manifest.get("bundle_name") != "GitHubCommunityAgent":
        raise ValueError("Unexpected frozen bundle")
    files = manifest.get("files")
    members = triage.get("members")
    if not isinstance(files, list) or not isinstance(members, list):
        raise ValueError("Manifest and triage must have actual file/module arrays")
    if len(files) != manifest.get("file_count") or len(members) != triage.get("unique_parsed_member_names"):
        raise ValueError("Inconsistent frozen evidence counts")
    seen = set()
    for item in files:
        path = item.get("path", "")
        if not isinstance(path, str) or not path or path in seen or ".." in Path(path).parts:
            raise ValueError("Invalid/duplicate frozen file path")
        seen.add(path)
        digest = item.get("sha256", "")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("Missing file digest")
    candidates: dict[str, set[str]] = defaultdict(set)
    unresolved = []
    for item in members:
        category = item.get("category")
        if category == "environment_distribution_candidate":
            for name in item.get("candidate_distributions", []):
                candidates[name.lower().replace("_", "-")].add(item["member"])
        elif category == "unresolved":
            unresolved.append(item["member"])
    metadata = {}
    for dist in md.distributions():
        name = dist.metadata.get("Name", "").lower().replace("_", "-")
        if name in candidates:
            metadata.setdefault(name, []).append({
                "version_in_current_build_environment_ONLY": dist.version,
                "license_expression_or_legacy": (dist.metadata.get("License-Expression")
                                                 or dist.metadata.get("License") or "")[:240],
            })
    components = [
        {
            "distribution_candidate": name,
            "frozen_module_name_count": len(names),
            "sample_module_names": sorted(names)[:6],
            "venv_metadata_candidates": metadata.get(name, []),
            "exact_frozen_component_version_verified": False,
            "license_text_in_installer_verified": False,
        }
        for name, names in sorted(candidates.items())
    ]
    binary = [
        {"path": f["path"], "sha256": f["sha256"],
         "component_origin_verified": False, "license_text_verified": False}
        for f in files if f.get("kind") == "binary"
    ]
    return {
        "scope": "Actual frozen file hashes + module candidate provenance. NOT a complete SBOM/license clearance.",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_bundle_file_count": len(files),
        "candidate_bundle_total_size_bytes": manifest.get("total_size_bytes"),
        "candidate_embedded_module_count": len(members),
        "candidate_distribution_count": len(components),
        "candidate_distributions": components,
        "compiled_binary_candidates": binary,
        "unresolved_archive_members": sorted(unresolved),
        "review_required": PROVENANCE_REQUIRED,
        "actual_package_versions_verified": False,
        "complete_third_party_notices_verified": False,
        "approved_public_redistribution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--triage", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("Existing report must be preserved; choose a different filename")
    result = build(json.loads(args.manifest.read_text(encoding="utf-8")),
                   json.loads(args.triage.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print("Frozen candidate component review:", args.output)
    print("Actual files:", result["candidate_bundle_file_count"])
    print("Embedded modules:", result["candidate_embedded_module_count"])
    print("Distribution candidates:", result["candidate_distribution_count"])
    print("Native binary files:", len(result["compiled_binary_candidates"]))
    print("Unresolved PyInstaller member names:", len(result["unresolved_archive_members"]))
    print("RELEASE BLOCKED: exact frozen versions/redistribution NOTICE not fully verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
