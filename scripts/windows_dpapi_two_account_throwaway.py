"""Cross-Windows-user DPAPI verification using ONLY a disposable random blob.

Never read or copy any saved GC Agent production settings file. An authorized operator must
run 'create' as Windows account A, then 'verify --expect denied' as a REAL
different Windows account B against a mutually readable disposable file.
No automatic account creation, privilege elevation or cleanup.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from github_community_agent.windows_dpapi import (
    WindowsProtectionError,
    protect_for_current_user,
    unprotect_for_current_user,
)


def safe_path(path: Path) -> Path:
    resolved = path.absolute()
    if resolved.name.lower() != "gc-agent-dpapi-throwaway.bin":
        raise ValueError("Only gc-agent-dpapi-throwaway.bin is permitted")
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Linked path refused")
    return resolved


def create(path: Path) -> None:
    if sys.platform != "win32":
        raise ValueError("Windows is required")
    target = safe_path(path)
    if not target.parent.is_dir():
        raise ValueError("Use an existing operator-authorized common test folder")
    ciphertext = protect_for_current_user(os.urandom(32))
    with target.open("xb") as out:
        out.write(ciphertext)
    print("THROWAWAY DPAPI blob created (never a real API Key).")
    print("Windows account:", getpass.getuser())
    print("Blob:", target)
    print("Run verify as a DIFFERENT Windows user; do not upload this blob.")


def verify(path: Path, expectation: str) -> bool:
    if sys.platform != "win32":
        raise ValueError("Windows is required")
    source = safe_path(path)
    if not source.is_file():
        raise ValueError("Disposable blob not available to this Windows account")
    blob = source.read_bytes()
    if not 20 <= len(blob) <= 10_000:
        raise ValueError("Unexpected disposable blob size")
    try:
        result = unprotect_for_current_user(blob)
        decrypted = len(result) == 32
    except WindowsProtectionError:
        decrypted = False
    if expectation == "denied":
        success = not decrypted
    else:
        success = decrypted
    print("Windows account:", getpass.getuser())
    print("DPAPI outcome:", "decrypted" if decrypted else "denied")
    print("Expected:", expectation)
    print("PASS" if success else "FAIL")
    print("Only disposable random bytes were used; real GC settings not accessed.")
    return success


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("create", "verify"))
    p.add_argument("--file", required=True, type=Path)
    p.add_argument("--expect", choices=("allowed", "denied"))
    args = p.parse_args()
    try:
        if args.action == "create":
            if args.expect is not None:
                p.error("--expect applies to verify only")
            create(args.file)
        else:
            if not args.expect:
                p.error("--expect required for verify")
            if not verify(args.file, args.expect):
                return 1
        return 0
    except (ValueError, OSError, WindowsProtectionError) as exc:
        print("FAIL: DPAPI throwaway test incomplete:", type(exc).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
