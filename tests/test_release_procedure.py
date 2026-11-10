"""Release procedure contract (owner decision 2026-11-10).

The release follows the practical Nature AI Worker process: no internal
signed-attestation or approval-record gate in packaging or automation, while
license notices, Microsoft redistribution conditions and security checks stay.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DOCS = ROOT / "docs" / "release" / "v1.0.0-rc1"


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_single_release_installer_spec_without_approval_record_gates():
    specs = sorted(p.name for p in (ROOT / "packaging" / "windows").glob("*.iss"))
    assert "gc-agent.iss" in specs
    assert "gc-agent-release-candidate.iss" not in specs
    for spec in (ROOT / "packaging" / "windows").glob("*.iss"):
        source = spec.read_text(encoding="utf-8")
        for gate in ("REVIEW_APPROVAL.json", "LegalReviewEvidence", "ReviewedLegalDir"):
            assert gate not in source, (spec.name, gate)


def test_checklist_has_no_signature_or_attestation_requirement():
    checklist = (RELEASE_DOCS / "FINAL_APPROVAL_CHECKLIST.md").read_text(encoding="utf-8").lower()
    # No phrase that *imposes* a signature/attestation step may remain.
    for phrase in ("signed and dated", "must sign", "attestation required",
                   "sign the attestation", "owner signs", "- [ ] **owner (nature ai corp), signed"):
        assert phrase not in checklist, phrase
    assert "no document or signature is required" in checklist
    assert "signed owner attestation | **removed**" in checklist
    # The withdrawn statement text must not be reproduced.
    assert "is not malicious, deceptive or unlawful software" not in checklist


def test_genuine_obligations_are_still_shipped_and_checked():
    iss = _text("packaging/windows/gc-agent.iss")
    assert "LicenseFile=END_USER_TERMS.txt" in iss                      # Microsoft condition (e)
    assert 'Source: "..\\..\\LICENSE"' in iss and 'Source: "..\\..\\NOTICE"' in iss  # Apache 4(a),(d)
    assert "third-party-licenses" in iss                                # MIT/BSD/MPL/... notices
    terms = _text("packaging/windows/END_USER_TERMS.txt")
    assert "Microsoft Distributable Code" in terms
    assert "not affiliated with, sponsored by, or endorsed by GitHub, Inc." in " ".join(terms.split())
    assert "Copyright 2026 The Nature AI Worker Authors" in _text("NOTICE")
