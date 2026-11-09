"""Conservative pre-release dependency/license inventory for GC Agent.

This examines the CURRENT BUILD PYTHON ENVIRONMENT, not the final frozen EXE.
Do not interpret its output as a complete software bill of materials (SBOM).
No network calls, application startup or credential reads occur.
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
from datetime import datetime, timezone
from pathlib import Path


def _license_metadata(dist: md.Distribution) -> tuple[str, list[str]]:
    license_expr = dist.metadata.get("License-Expression", "").strip()
    legacy = dist.metadata.get("License", "").strip()
    classifiers = [v.removeprefix("License :: ").strip()
                   for v in dist.metadata.get_all("Classifier", [])
                   if v.startswith("License :: ")]
    return license_expr or legacy, classifiers


def build_inventory() -> dict:
    records = []
    for dist in md.distributions():
        name = dist.metadata.get("Name", "").strip()
        if not name:
            continue
        license_text, classifiers = _license_metadata(dist)
        records.append({
            "name": name,
            "version": dist.version,
            "license_metadata": license_text[:350],
            "license_classifiers": classifiers,
            "license_metadata_missing": not (license_text or classifiers),
        })
    records.sort(key=lambda x: x["name"].lower())
    return {
        "scope": "Python environment inventory; NOT a final frozen-binary SBOM",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dependencies": records,
        "missing_license_metadata": [
            x["name"] for x in records if x["license_metadata_missing"]
        ],
        "release_blockers": [
            "Inventory includes dev/build packages, not exact PyInstaller bundled set",
            "Manually review included binary/runtime third-party notices and redistribution licenses",
            "Validate frozen EXE manifest, hashes, dependency lock and source attribution",
            "Product version 0.0.0.dev0 and unsigned installer are not public release candidates",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.exists():
        parser.error("Output already exists; do not overwrite existing audit evidence")
    destination.parent.mkdir(parents=True, exist_ok=True)
    inventory = build_inventory()
    destination.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print("GC Agent environment license inventory created:", destination)
    print("Distributions:", len(inventory["dependencies"]))
    print("Missing license metadata:", len(inventory["missing_license_metadata"]))
    print("NOT A COMPLETE FROZEN-BINARY SBOM; manual redistribution review required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
