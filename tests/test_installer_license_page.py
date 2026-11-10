"""Installer end-user terms page (DRAFT pending legal review): static contract.

Reads files only. It checks that the terms are shown and installed, carry the
draft marker, and reproduce the CPython Microsoft Distributable Code
conditions verbatim, without adding new Microsoft permissions.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TERMS = ROOT / "packaging" / "windows" / "END_USER_TERMS.txt"
CPYTHON_LICENSE = ROOT / "packaging" / "third-party-licenses" / "cpython-3.13.17" / "LICENSE.txt"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def test_release_installer_shows_and_installs_the_terms():
    iss = (ROOT / "packaging" / "windows" / "gc-agent.iss").read_text(encoding="utf-8")
    assert re.search(r"^LicenseFile=END_USER_TERMS\.txt$", iss, re.M)
    assert 'Source: "END_USER_TERMS.txt"; DestDir: "{app}"' in iss


def test_terms_are_ascii_draft_and_name_the_product_and_publisher():
    raw = TERMS.read_bytes()
    raw.decode("ascii")  # Inno license memo: plain ASCII renders everywhere
    text = raw.decode("ascii")
    assert "DRAFT FOR LEGAL REVIEW" in text
    assert "has not been approved" in text
    assert text.startswith("GitHub Community Agent - End-User Terms")
    assert "Publisher: NATURE AI CORP" in text
    assert "Apache License, Version 2.0" in text
    assert "THIRD_PARTY_NOTICES.txt" in text


def test_microsoft_conditions_are_reproduced_verbatim_from_cpython():
    terms = _norm(TERMS.read_text(encoding="ascii"))
    lic = _norm(CPYTHON_LICENSE.read_text(encoding="utf-8"))
    for clause in (
        "you must comply with the restrictions on distribution specified by Microsoft",
        "require distributors and external end users to agree to terms that protect the "
        "Microsoft Distributable Code at least as much as Microsoft's own requirements for "
        "the Distributable Code",
        "alter any copyright, trademark or patent notice in Microsoft's Distributable Code",
        "use Microsoft's trademarks in your programs' names or in a way that suggests your "
        "programs come from or are endorsed by Microsoft",
        "distribute Microsoft's Distributable Code to run on a platform other than Microsoft "
        "operating systems, run-time technologies or application platforms",
        "include Microsoft Distributable Code in malicious, deceptive or unlawful programs",
    ):
        assert clause in lic, clause
        assert clause in terms, clause
    # No invented Microsoft permissions or extra Microsoft restrictions.
    for invented in ("Microsoft grants", "Microsoft permits", "reverse engineer", "Visual Studio"):
        assert invented not in terms


def test_terms_preserve_every_apache_section_2_right_including_modification():
    terms = _norm(TERMS.read_text(encoding="ascii"))
    for right in ("reproduce", "prepare derivative works of", "(modify)", "publicly display",
                  "publicly perform", "sublicense", "distribute"):
        assert right in terms, right
    assert "Nothing in these terms limits the rights that the Apache License grants" in terms


def test_terms_identify_vcruntime_as_microsoft_distributable_code():
    terms = _norm(TERMS.read_text(encoding="ascii"))
    assert "VCRUNTIME140.dll is itself Microsoft Distributable Code" in terms
    assert "including VCRUNTIME140.dll" not in terms


def test_pending_review_markers_stay_until_owner_approves_final_wording():
    # Removing these is a release decision (legal review + owner wording), not automation.
    assert "DRAFT FOR LEGAL REVIEW" in TERMS.read_text(encoding="ascii")
    notice = _norm((ROOT / "NOTICE").read_text(encoding="utf-8"))
    assert "This independent repository is not yet released." in notice


def test_notice_reproduces_upstream_nature_ai_worker_attribution():
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "  Nature AI Worker\n  Copyright 2026 The Nature AI Worker Authors\n" in notice.replace("\r\n", "\n")
    adapted = [p for p in (ROOT / "src" / "github_community_agent").glob("*.py")
               if "SPDX-FileCopyrightText: 2026 The Nature AI Worker Authors" in p.read_text(encoding="utf-8")]
    assert adapted, "attribution is only required while adapted files exist"


def test_installer_embedded_texts_have_pinned_line_endings():
    # Reproducible installer bytes from any checkout: these files are copied
    # into the installer verbatim, so their line endings must not depend on
    # core.autocrlf.
    attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    for path in ("LICENSE", "NOTICE", "packaging/windows/END_USER_TERMS.txt"):
        # Root-anchored: an unanchored "LICENSE" would also match (and convert)
        # the verbatim third-party LICENSE files.
        assert f"/{path} text eol=crlf" in attrs, path
    assert not any(a.split()[:1] in (["LICENSE"], ["NOTICE"]) for a in attrs)
    assert "packaging/third-party-licenses/** -text" in attrs
    for path in ("LICENSE", "NOTICE", "packaging/windows/END_USER_TERMS.txt"):
        data = (ROOT / path).read_bytes()
        assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b""), path


def test_independence_disclaimer_matches_notice():
    notice = _norm((ROOT / "NOTICE").read_text(encoding="utf-8"))
    terms = _norm(TERMS.read_text(encoding="ascii"))
    disclaimer = ("GitHub Community Agent is an independent product of NATURE AI CORP. It is not "
                  "affiliated with, sponsored by, or endorsed by GitHub, Inc. or Microsoft "
                  "Corporation.")
    assert disclaimer in notice and disclaimer in terms
