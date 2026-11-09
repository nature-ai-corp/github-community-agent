"""Read-only candidate classification of PyInstaller archive member names.

The PyInstaller -r listing is NOT a full SBOM. The candidate map uses the
current Python environment, not proof of the frozen module origin/version.
No network calls, imports of frozen app, credential reads or file mutation.
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import re
import sys
from collections import Counter
from pathlib import Path

# PyInstaller --brief listing uses module/member names in quoted strings.
# Preserve raw unmatched lines in aggregate counts, not as guessed packages.
QUOTED = re.compile(r"""['"]([A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_0-9]+)*)['"]""")
FIRST_PARTY = "github_community_agent"
STDLIB = frozenset(sys.stdlib_module_names)


# Real PyInstaller 6 --brief --recursive output uses unquoted, indented
# module names under section headers such as Contents of 'PYZ.pyz' (PYZ).
# Keep legacy quoted-line support for fixtures and future output variations.
BARE_MEMBER = re.compile(r"^\\s+([A-Za-z_][A-Za-z_0-9]*(?:\\.[A-Za-z_0-9]+)*)\\s*$")
DEV_MODULES = frozenset({"_pytest", "pytest", "pluggy", "iniconfig", "pygments"})


def extract_names(lines: list[str]) -> tuple[list[str], int]:
    names = []
    unmatched = 0
    for line in lines:
        bare = BARE_MEMBER.fullmatch(line)
        if bare:
            item = bare.group(1)
            # PYZ.pyz is the embedded archive filename, not a module.
            if item.lower().endswith((".pyz", ".zip", ".dll", ".pyd", ".exe")):
                unmatched += 1
                continue
            names.append(item)
            continue
        # Preserve old fixture support; never interpret quoted archive
        # metadata labels (PYMODULE, BINARY etc.) as actual dependencies.
        candidates = QUOTED.findall(line)
        if re.match(r"^\\s*\\d+\\s*,", line) and candidates:
            item = candidates[0]
            if item not in {"PYMODULE", "PYPACKAGE", "PYZ", "BINARY",
                            "DATA", "EXTENSION", "SPLASH"}:
                names.append(item)
                continue
        unmatched += 1
    return names, unmatched


def classify(names: list[str], distribution_map: dict[str, list[str]]) -> dict:
    by_name: dict[str, dict] = {}
    for name in names:
        if name in by_name:
            by_name[name]["occurrences"] += 1
            continue
        root = name.partition(".")[0]
        if root == FIRST_PARTY:
            category, candidates = "first_party", []
        elif root in STDLIB:
            category, candidates = "stdlib_candidate", []
        else:
            candidates = sorted(set(distribution_map.get(root, [])))
            category = "environment_distribution_candidate" if candidates else "unresolved"
        by_name[name] = {
            "member": name,
            "category": category,
            "candidate_distributions": candidates,
            "occurrences": 1,
        }
    entries = sorted(by_name.values(), key=lambda x: x["member"])
    counts = Counter(x["category"] for x in entries)
    return {"members": entries, "category_counts": dict(sorted(counts.items()))}


def analyze(archive_text: str, mapping: dict[str, list[str]] | None = None) -> dict:
    if mapping is None:
        mapping = md.packages_distributions()
    lines = archive_text.splitlines()
    names, unmatched = extract_names(lines)
    result = classify(names, mapping)
    unexpected_development_modules = [
        x["member"] for x in result["members"]
        if x["member"].partition(".")[0] in DEV_MODULES
    ]
    return {
        "scope": "Archive member TRIAGE ONLY; not a complete or validated frozen SBOM",
        "listing_lines": len(lines),
        "unmatched_listing_lines": unmatched,
        "parsed_member_occurrences": len(names),
        "unique_parsed_member_names": len(result["members"]),
        "category_counts": result["category_counts"],
        "members": result["members"],
        "development_module_candidates": unexpected_development_modules,
        "review_required": [
            "Quoted names in PyInstaller listing are candidates; verify parse against source listing",
            "Candidate distribution mapping is from current Python environment, NOT guaranteed frozen app version",
            "Ambiguous and unresolved names require manual provenance, license and version review",
            "Native binaries, embedded stdlib, bootloader, Tcl/Tk files and required NOTICE text need separate review",
            "Investigate pytest/dev-only modules present in a frozen release candidate",
            "No release decision, software signing or legal license clearance is implied",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-list", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Existing output will not be overwritten")
    # Only read the already-generated PyInstaller listing, never the EXE.
    archive = args.archive_list.read_text(encoding="utf-8-sig")
    report = analyze(archive)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Archive module candidate report:", output)
    print("Original listing lines:", report["listing_lines"])
    print("Matched module occurrences:", report["parsed_member_occurrences"])
    print("Unique parsed names:", report["unique_parsed_member_names"])
    print("Unmatched listing lines:", report["unmatched_listing_lines"])
    print("Development module candidates:", len(report["development_module_candidates"]))
    for member in report["development_module_candidates"][:20]:
        print("  DEV CANDIDATE:", member)
    for category, count in report["category_counts"].items():
        print(category + ":", count)
    print("NOT A FROZEN SBOM: candidate classifications need manual validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
