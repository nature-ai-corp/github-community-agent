"""Inventory ACTUAL frozen onedir files for human SBOM/license review.

Safe offline inspection. No imports from the frozen program and no reads of
Windows user data, SQLite, DPAPI files or environment credentials. This is a
hash/file manifest, not a complete SBOM: embedded PYZ modules, OS libraries,
license obligations and package identity need further review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

MAX_BUNDLE_FILES = 10000
CHUNK_BYTES = 1024 * 1024
FORBIDDEN_SUFFIXES = {".dpapi", ".sqlite", ".sqlite3", ".db", ".key", ".pem", ".pfx", ".p12"}
FORBIDDEN_NAMES = {"settings.json", ".env", ".env.local", "credentials.json", "token.txt"}
BINARY_SUFFIXES = {".exe", ".dll", ".pyd", ".so", ".dylib"}
ARCHIVE_SUFFIXES = {".zip", ".pyz", ".whl"}
LICENSE_WORDS = ("license", "notice", "copying", "copyright")
# Certifi distributes a PUBLIC CA trust bundle as cacert.pem. This single
# well-known relative path is not a credential; all other .pem remain blocked.
PUBLIC_CA_BUNDLE_PATH = "_internal/certifi/cacert.pem"


def is_public_certifi_bundle(path: Path, relative: Path) -> bool:
    if relative.as_posix().lower() != PUBLIC_CA_BUNDLE_PATH:
        return False
    # A public trust store must contain certificates ONLY, not any PEM key.
    # Limit inspection to a small static vendor bundle, not arbitrary secrets.
    if path.stat().st_size > 3_000_000:
        return False
    contents = path.read_bytes()
    headers = re.findall(rb"-----BEGIN ([A-Z0-9 ]+)-----", contents)
    if not headers or any(header != b"CERTIFICATE" for header in headers):
        return False
    ends = re.findall(rb"-----END ([A-Z0-9 ]+)-----", contents)
    return len(headers) == len(ends) and all(
        item == b"CERTIFICATE" for item in ends
    )


def kind(path: Path) -> str:
    name = path.name.lower()
    if any(word in name for word in LICENSE_WORDS):
        return "license_or_notice_candidate"
    if path.suffix.lower() in BINARY_SUFFIXES:
        return "binary"
    if path.suffix.lower() in ARCHIVE_SUFFIXES:
        return "archive"
    if path.suffix.lower() in {".html", ".css", ".js"}:
        return "ui_asset"
    return "other"


def inventory(bundle: Path) -> dict:
    root = bundle.resolve(strict=True)
    if not root.is_dir() or bundle.is_symlink() or getattr(bundle, "is_junction", lambda: False)():
        raise ValueError("Bundle must be a normal existing directory")
    if root.name != "GitHubCommunityAgent":
        raise ValueError("Only the GC Agent onedir folder may be inventoried")
    if not (root / "GitHubCommunityAgent.exe").is_file():
        raise ValueError("GC Agent EXE missing from bundle")

    files = []
    for path in root.rglob("*"):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise ValueError("Bundle contains a symlink or junction-like entry")
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if len(files) >= MAX_BUNDLE_FILES:
            raise ValueError("Bundle file count exceeds inventory safety limit")
        low = path.name.lower()
        secret_like = path.suffix.lower() in FORBIDDEN_SUFFIXES or low in FORBIDDEN_NAMES
        known_public_ca = (
            path.suffix.lower() == ".pem" and is_public_certifi_bundle(path, rel)
        )
        if secret_like and not known_public_ca:
            # Path is safe to show: never read or expose the suspect contents.
            raise ValueError(
                f"Forbidden user-data or secret-like file in frozen bundle: {rel.as_posix()}"
            )
        sha = hashlib.sha256()
        with path.open("rb") as inp:
            while chunk := inp.read(CHUNK_BYTES):
                sha.update(chunk)
        files.append({
            "path": rel.as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha.hexdigest().upper(),
            "kind": "public_ca_certificates" if known_public_ca else kind(path),
        })
    files.sort(key=lambda x: x["path"].lower())
    if not files:
        raise ValueError("Empty application bundle")
    counts = Counter(x["kind"] for x in files)
    total = sum(x["size_bytes"] for x in files)
    return {
        "scope": "Actual GC Agent onedir FILE manifest; not a complete license/SBOM analysis",
        "bundle_name": root.name,
        "file_count": len(files),
        "total_size_bytes": total,
        "category_counts": dict(sorted(counts.items())),
        "files": files,
        "review_required": [
            "Review embedded PYZ/PyInstaller archive modules separately",
            "Resolve file origins, exact dependency versions and third-party license notices",
            "Verify bundled Python runtime and compiled binaries redistribution terms",
            "Review installer-specific LICENSE and NOTICE separately",
            "Code signing, Windows AV and multi-user security checks are separate gates",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists():
        p.error("Refusing to overwrite an existing audit manifest")
    report = inventory(args.bundle)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("GC Agent frozen file manifest created:", out)
    print("Actual bundle files:", report["file_count"])
    print("Total bytes:", report["total_size_bytes"])
    for category, count in report["category_counts"].items():
        print(category + ":", count)
    print("INCOMPLETE SBOM: embedded archives, provenance and licenses need review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
