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


def test_both_installer_specs_show_and_install_the_terms():
    for name in ("gc-agent.iss", "gc-agent-release-candidate.iss"):
        iss = (ROOT / "packaging" / "windows" / name).read_text(encoding="utf-8")
        assert re.search(r"^LicenseFile=END_USER_TERMS\.txt$", iss, re.M), name
        assert 'Source: "END_USER_TERMS.txt"; DestDir: "{app}"' in iss, name


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


def test_independence_disclaimer_matches_notice():
    notice = _norm((ROOT / "NOTICE").read_text(encoding="utf-8"))
    terms = _norm(TERMS.read_text(encoding="ascii"))
    disclaimer = ("GitHub Community Agent is an independent product of NATURE AI CORP. It is not "
                  "affiliated with, sponsored by, or endorsed by GitHub, Inc. or Microsoft "
                  "Corporation.")
    assert disclaimer in notice and disclaimer in terms
