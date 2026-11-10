"""Build and verify GC Agent's third-party license distribution package.

The package (THIRD_PARTY_NOTICES.txt, verbatim license texts, a CycloneDX
SBOM and a SHA256 MANIFEST) is derived from an ACTUAL PyInstaller onedir
bundle, never from a hand-written dependency list:

* every Python module embedded in the frozen PYZ/CArchive must be
  code-object-identical to source in the current build venv, the CPython
  stdlib, the PyInstaller loader/run-time hooks or first-party ``src``;
* every native binary must be byte-identical to the build interpreter's
  CPython Windows runtime file (official PSF build, see PYTHON_VERSION);
* the EXE bootloader code sections must match PyInstaller's stock bootloader;
* every other bundle file must be byte-identical to a known source file.

Anything unrecognised, or any license metadata that differs from the pinned
expectation below, FAILS the build. A human must then review and update the
pins; nothing is guessed. Passing these checks establishes provenance and
packaging completeness. It is not a legal opinion, and it records no approval
status: there is no internal approval gate (release procedure, 2026-11-10).

Subcommands (all read-only towards user data; no network access):

  generate  --bundle B --output-dir NEW [--upstream-dir U]   create-only
  check     --bundle B --package P      regenerate in memory, compare bytes
  verify-installed --app-dir A --package P --bundle B [--report NEW.json]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import marshal
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "packaging" / "third-party-licenses"
EXE_NAME = "GitHubCommunityAgent.exe"
FIRST_PARTY = "github-community-agent"
PYTHON_VERSION = "3.13.17"
PYINSTALLER_VERSION = "6.22.3"

# Pinned expectations. A dependency/version change must fail until a human
# re-reviews the license text and updates this table deliberately.
PY_DISTRIBUTIONS = {
    "anyio": ("4.16.0", "MIT", "https://github.com/agronholm/anyio"),
    "certifi": ("2026.10.23", "MPL-2.0", "https://github.com/certifi/python-certifi"),
    "h11": ("0.16.0", "MIT", "https://github.com/python-hyper/h11"),
    "httpcore": ("1.0.9", "BSD-3-Clause", "https://github.com/encode/httpcore"),
    "httpx": ("0.28.1", "BSD-3-Clause", "https://github.com/encode/httpx"),
    "idna": ("3.20", "BSD-3-Clause", "https://github.com/kjd/idna"),
    "typing-extensions": ("4.16.0", "PSF-2.0", "https://github.com/python/typing_extensions"),
}

# certifi is MPL-2.0 and ships cacert.pem (Source Code Form). Exact upstream
# source archive published on PyPI for the bundled version.
CERTIFI_SDIST = (
    "https://files.pythonhosted.org/packages/fd/11/"
    "b524cbd9bbdaca58608e4cf4053fd463417549e1959fa8d3aa18319f9555/"
    "certifi-2026.10.23.tar.gz",
    "a9895e6e2758b371e0545e321a3a8fd1fcfd9829ada8824a936dfb16aaaf36cd",
)

CERTIFI_SDIST_REL = "certifi-2026.10.23/source/certifi-2026.10.23.tar.gz"

# Upstream files not present in the build environment. Fetched once from the
# pinned public URL and committed verbatim; their hashes must never drift.
# (The certifi sdist is the MPL-2.0 Source Code Form shipped with the program.)
UPSTREAM_TEXTS = {
    f"cpython-{PYTHON_VERSION}/license.rst": (
        f"https://raw.githubusercontent.com/python/cpython/v{PYTHON_VERSION}/Doc/license.rst",
        "952ac05720d7f1dcb63589b35eb0931b1442eb250230a4ad31198eddf0ad6abc",
    ),
    "certifi-2026.10.23/MPL-2.0.txt": (
        "https://www.mozilla.org/media/MPL/2.0/index.txt",
        "3f3d9e0024b1921b067d6f7f88deb4a60cbe7a78e76c64e3f1d7fc3b779b9d04",
    ),
    CERTIFI_SDIST_REL: CERTIFI_SDIST,
}
BINARY_UPSTREAM = {CERTIFI_SDIST_REL}
# Version evidence only (not shipped): the official CPython Windows build's
# third-party library list (PCbuild/get_externals.bat at the release tag).
EXTERNALS_EVIDENCE = (
    f"https://raw.githubusercontent.com/python/cpython/v{PYTHON_VERSION}/PCbuild/get_externals.bat",
    "4c2f8f42af137dd6861a96b24e4ec468a959ec2567b3ce5b63865be70026106c",
)
OPENSSL_VERSION = "3.5.9"  # OpenSSL 3.5 LTS line
VCRUNTIME_VERSION = "14.51.36247.0"

# Native runtime file -> component. Every .pyd not listed is CPython itself.
NATIVE_COMPONENTS = {
    "python313.dll": "cpython",
    "libcrypto-3.dll": "openssl",
    "libssl-3.dll": "openssl",
    "libffi-8.dll": "libffi",
    "sqlite3.dll": "sqlite",
    "tcl86t.dll": "tcl-tk",
    "tk86t.dll": "tcl-tk",
    "vcruntime140.dll": "msvc-runtime",
    "zlib1.dll": "zlib",
}
TCL_DATA_DIRS = {"_tcl_data": "tcl/tcl8.6", "_tk_data": "tcl/tk8.6", "tcl8": "tcl/tcl8"}

NOTICE_SECTIONS = f"cpython-{PYTHON_VERSION}/license.rst"
WIN_LICENSE = f"cpython-{PYTHON_VERSION}/LICENSE.txt"

# (key, name, version, SPDX expression or license name, where the text is).
NATIVE_SBOM = [
    ("cpython", "CPython runtime", PYTHON_VERSION, "PSF-2.0",
     [WIN_LICENSE, NOTICE_SECTIONS], f"pkg:generic/python@{PYTHON_VERSION}"),
    ("openssl", "OpenSSL", OPENSSL_VERSION, "Apache-2.0",
     [WIN_LICENSE + " (Apache License 2.0 section)", NOTICE_SECTIONS + " (OpenSSL)"],
     f"pkg:generic/openssl@{OPENSSL_VERSION}"),
    ("sqlite", "SQLite", "3.50.4", "blessing", ["THIRD_PARTY_NOTICES.txt (public domain)"],
     "pkg:generic/sqlite@3.50.4"),
    ("zlib", "zlib", "1.3.1", "Zlib", [NOTICE_SECTIONS + " (zlib)"], "pkg:generic/zlib@1.3.1"),
    ("libffi", "libffi", "3.4.4", "MIT",
     [WIN_LICENSE + " (libffi)", NOTICE_SECTIONS + " (libffi)"], "pkg:generic/libffi@3.4.4"),
    ("tcl-tk", "Tcl/Tk", "8.6.15", "TCL",
     ["tcl-tk-8.6.15/license.terms", WIN_LICENSE + " (Tcl, Tk)"], "pkg:generic/tcl-tk@8.6.15"),
    ("expat", "Expat (statically linked in pyexpat)", "2.8.1", "MIT",
     [NOTICE_SECTIONS + " (expat)"], "pkg:generic/expat@2.8.1"),
    ("libmpdec", "libmpdec (statically linked in _decimal)", "4.0.0", "BSD-2-Clause",
     [NOTICE_SECTIONS + " (libmpdec)"], "pkg:generic/mpdecimal@4.0.0"),
    ("bzip2", "bzip2 (statically linked in _bz2)", "1.0.8", "bzip2-1.0.6",
     [WIN_LICENSE + " (bzip2)"], "pkg:generic/bzip2@1.0.8"),
    ("xz", "liblzma from XZ Utils (statically linked in _lzma)", "5.2.5",
     "LicenseRef-public-domain", ["THIRD_PARTY_NOTICES.txt (public domain)"],
     "pkg:generic/xz@5.2.5"),
    ("msvc-runtime", "Microsoft Visual C++ runtime (VCRUNTIME140.dll)", VCRUNTIME_VERSION,
     "LicenseRef-Microsoft-Distributable-Code",
     [WIN_LICENSE + " (Additional Conditions for this Windows binary build)"],
     f"pkg:generic/microsoft/vcruntime140@{VCRUNTIME_VERSION}"),
    ("pyinstaller", "PyInstaller bootloader and loader", PYINSTALLER_VERSION,
     "GPL-2.0-or-later WITH Bootloader-exception",
     ["pyinstaller-6.22.3/COPYING.txt"], "pkg:pypi/pyinstaller@6.22.3"),
    ("pyinstaller-rthooks", "PyInstaller run-time hooks", PYINSTALLER_VERSION, "Apache-2.0",
     ["pyinstaller-6.22.3/COPYING.txt (Run-time Hooks)"], "pkg:pypi/pyinstaller@6.22.3"),
]


class BundleError(RuntimeError):
    """The bundle contains something this package cannot account for."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _same_code(source: Path, code) -> bool:
    if code is None or not source.is_file():
        return False
    return compile(source.read_bytes(), code.co_filename, "exec", dont_inherit=True) == code


def analyze_bundle(bundle: Path) -> dict:
    """Account for every file and embedded module of a frozen onedir bundle."""
    import PyInstaller
    import pefile
    from PyInstaller.archive.readers import CArchiveReader

    bundle = bundle.resolve(strict=True)
    exe = bundle / EXE_NAME
    internal = bundle / "_internal"
    if not exe.is_file() or not internal.is_dir():
        raise BundleError(f"Not a GC Agent onedir bundle: {bundle}")
    if sys.version.split()[0] != PYTHON_VERSION:
        raise BundleError(f"Run with the build interpreter (CPython {PYTHON_VERSION})")
    if md.version("pyinstaller") != PYINSTALLER_VERSION:
        raise BundleError(f"Expected PyInstaller {PYINSTALLER_VERSION} in the build venv")
    runtime = Path(sys.base_prefix)
    stdlib = runtime / "Lib"
    src = ROOT / "src"
    pyi = Path(PyInstaller.__file__).parent
    errors: list[str] = []

    # 1. Embedded Python code.
    owners = md.packages_distributions()
    dist_modules: dict[str, int] = {}
    counts = {"stdlib": 0, "first_party": 0, "pyinstaller_loader": 0, "pyinstaller_rthooks": 0}
    archive = CArchiveReader(str(exe))
    for name, entry in archive.toc.items():
        typecode = entry[-1]
        if typecode == "z":
            continue
        code = marshal.loads(archive.extract(name))
        if name.startswith(("pyimod", "pyiboot")):
            ok, key = _same_code(pyi / "loader" / f"{name}.py", code), "pyinstaller_loader"
        elif name.startswith("pyi_rth_"):
            ok, key = _same_code(pyi / "hooks" / "rthooks" / f"{name}.py", code), "pyinstaller_rthooks"
        elif name == "gc_agent_launcher":
            ok, key = _same_code(ROOT / "scripts" / "gc_agent_launcher.py", code), "first_party"
        else:
            ok, key = _same_code(stdlib / code.co_filename, code), "stdlib"
        if not ok:
            errors.append(f"CArchive entry not identical to a known source: {name}")
        counts[key] += 1
    pyz = archive.open_embedded_archive("PYZ.pyz")
    for name in pyz.toc:
        code = pyz.extract(name)
        if code is None:
            errors.append(f"PYZ entry without code: {name}")
            continue
        top = name.split(".")[0]
        dists = owners.get(top, [])
        if dists and md.distribution(dists[0]).metadata["Name"] == FIRST_PARTY:
            ok, key = _same_code(src / code.co_filename, code), "first_party"
        elif dists:
            canonical = md.distribution(dists[0]).metadata["Name"].lower().replace("_", "-")
            base = Path(md.distribution(dists[0]).locate_file(""))
            ok, key = _same_code(base / code.co_filename, code), canonical
            if canonical not in PY_DISTRIBUTIONS:
                errors.append(f"Unreviewed third-party distribution bundled: {canonical} ({name})")
        else:
            ok, key = _same_code(stdlib / code.co_filename, code), "stdlib"
        if not ok:
            errors.append(f"PYZ module not identical to a known source: {name}")
        if key in counts:
            counts[key] += 1
        else:
            dist_modules[key] = dist_modules.get(key, 0) + 1

    distributions = []
    for canonical, (version, spdx, repo) in sorted(PY_DISTRIBUTIONS.items()):
        if canonical not in dist_modules:
            errors.append(f"Pinned distribution not found in bundle: {canonical}")
            continue
        dist = md.distribution(canonical)
        meta = dist.metadata
        declared = meta.get("License-Expression") or meta.get("License") or ""
        if dist.version != version or declared.strip() != spdx:
            errors.append(f"{canonical}: venv {dist.version}/{declared!r} != pinned {version}/{spdx}")
        license_files = [f for f in dist.files or () if "/licenses/" in f.as_posix()]
        if not license_files:
            errors.append(f"{canonical}: no license file in dist-info")
        distributions.append({
            "name": canonical, "version": version, "license": spdx, "repository": repo,
            "frozen_modules_code_identical": dist_modules[canonical],
            "license_files": {
                f"python-packages/{canonical}-{version}/{Path(f.as_posix()).name}":
                    Path(dist.locate_file(f)) for f in license_files},
        })

    # 2. Files on disk.
    files: list[dict] = []
    certifi_dir = Path(md.distribution("certifi").locate_file("certifi"))
    for path in sorted(p for p in bundle.rglob("*") if p.is_file()):
        rel = path.relative_to(bundle).as_posix()
        digest = sha256_file(path)
        parts = rel.split("/")
        component, origin = None, None
        if rel == EXE_NAME:
            component = "pyinstaller"
            origin = _bootloader_matches(pefile, path, pyi)
            if origin is None:
                errors.append("EXE bootloader sections differ from PyInstaller's stock run.exe")
        elif parts[0] == "_internal" and len(parts) == 2 and path.suffix.lower() in (".dll", ".pyd"):
            name = parts[1].lower()
            source = runtime / name if name.endswith(".dll") and (runtime / name).is_file() \
                else runtime / "DLLs" / parts[1]
            component = NATIVE_COMPONENTS.get(name, "cpython" if name.endswith(".pyd") else None)
            origin = str(source.relative_to(runtime)).replace("\\", "/")
            if component is None or not source.is_file() or sha256_file(source) != digest:
                errors.append(f"Native file not byte-identical to CPython runtime: {rel}")
        elif parts[0] == "_internal" and len(parts) > 2 and parts[1] in TCL_DATA_DIRS:
            component = "tcl-tk"
            source = runtime / TCL_DATA_DIRS[parts[1]] / "/".join(parts[2:])
            if not source.is_file() or sha256_file(source) != digest:
                errors.append(f"Tcl/Tk data not identical to CPython runtime: {rel}")
        elif rel == "_internal/base_library.zip":
            component = "cpython"
            errors += _check_base_library(path, stdlib)
        elif parts[:2] == ["_internal", "certifi"]:
            component = "certifi"
            if sha256_file(certifi_dir / parts[-1]) != digest:
                errors.append(f"certifi data differs from the installed distribution: {rel}")
        elif parts[:2] == ["_internal", "github_community_agent"]:
            component = "first-party"
            if sha256_file(src / "github_community_agent" / parts[-1]) != digest:
                errors.append(f"First-party data differs from src: {rel}")
        else:
            errors.append(f"Unclassified bundle file: {rel}")
        files.append({"path": rel, "sha256": digest, "component": component, "origin": origin})

    if errors:
        raise BundleError("Bundle cannot be fully accounted for:\n  " + "\n  ".join(errors))
    exe_sha = next(f["sha256"] for f in files if f["path"] == EXE_NAME)
    return {
        "exe_sha256": exe_sha,
        "file_count": len(files),
        "files": files,
        "python_distributions": distributions,
        "embedded_counts": counts,
        "runtime_license": runtime / "LICENSE.txt",
        "tk_license_terms": internal / "_tk_data" / "license.terms",
        "pyinstaller_copying": next(
            Path(md.distribution("pyinstaller").locate_file(f))
            for f in md.distribution("pyinstaller").files if f.name == "COPYING.txt"),
    }


def _bootloader_matches(pefile, exe: Path, pyi: Path) -> str | None:
    def sections(path):
        pe = pefile.PE(str(path), fast_load=True)
        return {s.Name.rstrip(b"\0").decode(): sha256_bytes(s.get_data()) for s in pe.sections}
    built = sections(exe)
    for variant in ("run.exe", "runw.exe"):
        stock = sections(pyi / "bootloader" / "Windows-64bit-intel" / variant)
        # Code and initialised data must match; .rdata/.rsrc carry build-time
        # resources (icon/manifest) that PyInstaller rewrites per application.
        if all(built.get(k) == stock.get(k) for k in (".text", ".data", ".pdata")):
            return f"PyInstaller/bootloader/Windows-64bit-intel/{variant}"
    return None


def _check_base_library(path: Path, stdlib: Path) -> list[str]:
    import zipfile
    errors = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            rel = name[:-1] if name.endswith(".pyc") else name
            if not ((stdlib / rel).is_file() or (stdlib / rel.removesuffix(".py") / "__init__.py").is_file()):
                errors.append(f"base_library.zip entry is not stdlib: {name}")
    return errors


# ---------------------------------------------------------------- rendering

def _text(data: bytes) -> str:
    return data.decode("utf-8").replace("\r\n", "\n").rstrip("\n") + "\n"


def render(analysis: dict, upstream: dict[str, bytes]) -> dict[str, bytes]:
    """Return {relative path: bytes} for the complete distribution package."""
    out: dict[str, bytes] = {}
    for dist in analysis["python_distributions"]:
        for rel, source in dist["license_files"].items():
            out[rel] = source.read_bytes()
    out[WIN_LICENSE] = analysis["runtime_license"].read_bytes()
    out["tcl-tk-8.6.15/license.terms"] = analysis["tk_license_terms"].read_bytes()
    out["pyinstaller-6.22.3/COPYING.txt"] = analysis["pyinstaller_copying"].read_bytes()
    for rel, (_url, pinned) in UPSTREAM_TEXTS.items():
        if sha256_bytes(upstream[rel]) != pinned:
            raise BundleError(f"Upstream text hash mismatch: {rel}")
        out[rel] = upstream[rel]
    _check_certifi_source(upstream[CERTIFI_SDIST_REL], analysis)
    out["THIRD_PARTY_NOTICES.txt"] = _notices(analysis, out).encode("utf-8")
    out["sbom.cdx.json"] = _json(_sbom(analysis))
    manifest = {
        "schema": "gc-agent-third-party-licenses/1",
        "generator": "scripts/third_party_notices.py",
        "bundle": {"exe_sha256": analysis["exe_sha256"], "file_count": analysis["file_count"],
                   "embedded_module_counts": analysis["embedded_counts"]},
        "upstream_sources": {rel: {"url": u, "sha256": s} for rel, (u, s) in UPSTREAM_TEXTS.items()},
        "version_evidence": {"url": EXTERNALS_EVIDENCE[0], "sha256": EXTERNALS_EVIDENCE[1]},
        "files": {rel: sha256_bytes(data) for rel, data in sorted(out.items())},
        "provenance_verified": True,
        "evidence_note": "Automated provenance and packaging checks of the bundled third-party "
                         "components. Not legal advice.",
    }
    out["MANIFEST.json"] = _json(manifest)
    return out


def _check_certifi_source(sdist: bytes, analysis: dict) -> None:
    """The shipped sdist must be the exact Source Code Form of the frozen certifi."""
    import io
    import tarfile
    version = PY_DISTRIBUTIONS["certifi"][0]
    with tarfile.open(fileobj=io.BytesIO(sdist), mode="r:gz") as tf:
        members = {m.name: m for m in tf.getmembers() if m.isfile()}
        shipped = [f for f in analysis["files"] if f["component"] == "certifi"]
        if not shipped:
            raise BundleError("certifi data not found in bundle")
        for f in shipped:
            member = members.get(f"certifi-{version}/certifi/" + f["path"].rsplit("/", 1)[-1])
            if member is None or sha256_bytes(tf.extractfile(member).read()) != f["sha256"]:
                raise BundleError(f"certifi sdist does not contain bundled file: {f['path']}")
        dist = md.distribution("certifi")
        for f in dist.files or ():
            posix = f.as_posix()
            if posix.startswith("certifi/") and posix.endswith(".py"):
                member = members.get(f"certifi-{version}/" + posix)
                if member is None or tf.extractfile(member).read() != Path(dist.locate_file(f)).read_bytes():
                    raise BundleError(f"certifi sdist differs from frozen source: {posix}")


def _json(obj) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _notices(analysis: dict, texts: dict[str, bytes]) -> str:
    rows = [(d["name"], d["version"], d["license"], ", ".join(d["license_files"]))
            for d in analysis["python_distributions"]]
    rows += [(name, version, lic, "; ".join(where)) for _k, name, version, lic, where, _p in NATIVE_SBOM]
    lines = [
        "GitHub Community Agent - Third-Party Notices",
        "=" * 44,
        "",
        "GitHub Community Agent is licensed under the Apache License, Version 2.0",
        "(see LICENSE and NOTICE in the installation directory). The Windows",
        "distribution also contains the third-party software listed below, each",
        "under its own license. The full license texts follow this list and are",
        "also provided as separate files in this third-party-licenses directory.",
        "",
        f"Frozen application: {EXE_NAME}",
        f"SHA256: {analysis['exe_sha256']}",
        f"Bundle files: {analysis['file_count']}. Machine-readable SBOM: sbom.cdx.json",
        "",
        "Components",
        "----------",
    ]
    for name, version, lic, where in rows:
        lines += [f"* {name} {version}", f"    License: {lic}", f"    Text: {where}"]
    lines += [
        "",
        "The CPython runtime incorporates further software whose notices are",
        f"reproduced in {NOTICE_SECTIONS} (section \"Licenses and",
        "Acknowledgements for Incorporated Software\").",
        "",
        "Modifications",
        "-------------",
        f"Summary of changes made to Python {PYTHON_VERSION} (PSF License Agreement,",
        "clause 3): none. The bundled CPython runtime files are unmodified copies",
        "of the Python Software Foundation's Windows release. All other",
        "third-party components listed above are likewise included unmodified.",
        "",
        "Source Code Form availability (Mozilla Public License 2.0)",
        "----------------------------------------------------------",
        "certifi 2026.10.23 is distributed under the Mozilla Public License 2.0.",
        "Its file _internal/certifi/cacert.pem is included unmodified, in Source",
        "Code Form. The bundled Python code of certifi is unmodified. The complete",
        "Source Code Form of this exact version is included in this directory:",
        f"  {CERTIFI_SDIST_REL}",
        f"  (SHA256 {CERTIFI_SDIST[1]}). The bundled cacert.pem and",
        "  certifi Python sources were verified identical to this archive.",
        "It is also published upstream at:",
        f"  {CERTIFI_SDIST[0]}",
        "  https://github.com/certifi/python-certifi",
        "A copy of the MPL 2.0 is in certifi-2026.10.23/MPL-2.0.txt.",
        "",
        "Public-domain components",
        "------------------------",
        "SQLite 3.50.4 (sqlite3.dll): the SQLite authors have dedicated the code",
        "to the public domain; see https://www.sqlite.org/copyright.html.",
        "liblzma from XZ Utils 5.2.5 (statically linked in _lzma.pyd): liblzma",
        "5.2.x is in the public domain; see https://tukaani.org/xz/.",
        "",
        "Microsoft Visual C++ runtime",
        "----------------------------",
        "VCRUNTIME140.dll is Microsoft Distributable Code redistributed as part of",
        "the CPython Windows binary build. The conditions that apply are stated in",
        f"{WIN_LICENSE} under \"Additional Conditions for this Windows binary build\".",
        "",
        "Independence from GitHub",
        "------------------------",
        "GitHub Community Agent is an independent product of NATURE AI CORP. It is",
        "not affiliated with, sponsored by, or endorsed by GitHub, Inc. or",
        "Microsoft Corporation. \"GitHub\" is a trademark of GitHub, Inc. and is",
        "used only to identify the service this software works with. All other",
        "trademarks are the property of their respective owners.",
        "",
        "Full license texts",
        "------------------",
    ]
    order = sorted(k for k in texts if k != "THIRD_PARTY_NOTICES.txt" and k not in BINARY_UPSTREAM)
    for rel in order:
        lines += ["", "=" * 76, rel, "=" * 76, "", _text(texts[rel]).rstrip("\n")]
    return "\n".join(lines) + "\n"


def _sbom(analysis: dict) -> dict:
    components = []
    for d in analysis["python_distributions"]:
        components.append({
            "type": "library", "bom-ref": f"pypi:{d['name']}", "name": d["name"],
            "version": d["version"], "purl": f"pkg:pypi/{d['name']}@{d['version']}",
            "licenses": [{"expression": d["license"]}],
            "externalReferences": [{"type": "vcs", "url": d["repository"]}],
            "properties": [{"name": "gc-agent:frozen-modules-code-identical",
                            "value": str(d["frozen_modules_code_identical"])}],
        })
    by_component: dict[str, list[dict]] = {}
    for f in analysis["files"]:
        if f["component"] not in (None, "first-party"):
            by_component.setdefault(f["component"], []).append(f)
    for key, name, version, lic, _where, purl in NATIVE_SBOM:
        lic_entry = ({"expression": lic} if not lic.startswith("LicenseRef") and lic != "blessing"
                     else {"license": {"name": lic}})
        comp = {"type": "library", "bom-ref": key, "name": name, "version": version,
                "purl": purl, "licenses": [lic_entry]}
        binaries = [f for f in by_component.get(key, []) if f["path"].endswith((".dll", ".pyd", ".exe"))]
        if binaries:
            comp["components"] = [{
                "type": "file", "bom-ref": f"file:{f['path']}", "name": f["path"],
                "hashes": [{"alg": "SHA-256", "content": f["sha256"]}],
                **({"properties": [{"name": "gc-agent:identical-to", "value": f["origin"]}]}
                   if f["origin"] else {}),
            } for f in binaries]
        components.append(comp)
    serial = uuid.uuid5(uuid.NAMESPACE_URL, "gc-agent-sbom:" + analysis["exe_sha256"])
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "serialNumber": f"urn:uuid:{serial}",
        "metadata": {
            "component": {
                "type": "application", "bom-ref": FIRST_PARTY, "name": FIRST_PARTY,
                "version": md.version(FIRST_PARTY), "licenses": [{"expression": "Apache-2.0"}],
                "hashes": [{"alg": "SHA-256", "content": analysis["exe_sha256"]}],
            },
            "tools": {"components": [{"type": "application", "name": "scripts/third_party_notices.py"}]},
        },
        "components": components,
        "dependencies": [{"ref": FIRST_PARTY,
                          "dependsOn": sorted(c["bom-ref"] for c in components)}],
    }


# ---------------------------------------------------------- package checks

def read_tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def validate_package(package: Path) -> list[str]:
    """Self-consistency of a committed or installed package (no bundle needed)."""
    errors = []
    tree = read_tree(package)
    if "MANIFEST.json" not in tree:
        return ["MANIFEST.json missing"]
    manifest = json.loads(tree["MANIFEST.json"])
    listed = manifest.get("files", {})
    actual = {k for k in tree if k != "MANIFEST.json"}
    for missing in sorted(set(listed) - actual):
        errors.append(f"missing file: {missing}")
    for extra in sorted(actual - set(listed)):
        errors.append(f"unlisted file: {extra}")
    for rel in sorted(set(listed) & actual):
        if sha256_bytes(tree[rel]) != listed[rel]:
            errors.append(f"hash mismatch: {rel}")
    for rel, (_u, pinned) in UPSTREAM_TEXTS.items():
        if rel in tree and sha256_bytes(tree[rel]) != pinned:
            errors.append(f"upstream text altered: {rel}")
    for obsolete in ("legal_review_approved", "legal_review_note"):
        if obsolete in manifest:
            errors.append(f"obsolete internal approval field present: {obsolete}")
    return errors


def check(bundle: Path, package: Path) -> list[str]:
    errors = validate_package(package)
    committed = read_tree(package)
    expected = render(analyze_bundle(bundle), committed)
    for rel in sorted(set(expected) | set(committed)):
        if rel not in committed:
            errors.append(f"package lacks file required by bundle: {rel}")
        elif rel not in expected:
            errors.append(f"package has file not derived from bundle: {rel}")
        elif expected[rel] != committed[rel]:
            errors.append(f"package content is stale for bundle: {rel}")
    return errors


INSTALLER_OWN = {"unins000.exe", "unins000.dat"}
# First-party files the installer copies from the repository: installed name -> repo path.
INSTALLED_REPO_FILES = {
    "LICENSE": "LICENSE",
    "NOTICE": "NOTICE",
    "END_USER_TERMS.txt": "packaging/windows/END_USER_TERMS.txt",
}


def verify_installed(app_dir: Path, package: Path, bundle: Path, repo: Path = ROOT) -> dict:
    """Compare an INSTALLED directory with the package, bundle and repo notices."""
    errors: list[str] = []
    installed = read_tree(app_dir)
    pkg = read_tree(package)
    bun = read_tree(bundle)
    for rel, data in pkg.items():
        got = installed.get(f"third-party-licenses/{rel}")
        if got is None:
            errors.append(f"not installed: third-party-licenses/{rel}")
        elif got != data:
            errors.append(f"installed copy differs: third-party-licenses/{rel}")
    for rel, data in bun.items():
        if installed.get(rel) != data:
            errors.append(f"bundle file missing or different after install: {rel}")
    for name, source in INSTALLED_REPO_FILES.items():
        if installed.get(name) != (repo / source).read_bytes():
            errors.append(f"{name} missing or different after install")
    expected = set(bun) | set(INSTALLED_REPO_FILES) | {f"third-party-licenses/{r}" for r in pkg}
    for extra in sorted(set(installed) - expected - INSTALLER_OWN):
        errors.append(f"unexpected installed file: {extra}")
    errors += [f"installed package: {e}" for e in validate_package(app_dir / "third-party-licenses")]
    manifest = json.loads(pkg.get("MANIFEST.json", b"{}"))
    exe = installed.get(EXE_NAME)
    if exe is None or sha256_bytes(exe) != manifest.get("bundle", {}).get("exe_sha256"):
        errors.append("installed EXE is not the bundle described by MANIFEST.json")
    return {
        "installed_files": len(installed),
        "third_party_files_verified": len(pkg),
        "bundle_files_verified": len(bun),
        "errors": errors,
        "pass": not errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--bundle", type=Path, required=True)
    g.add_argument("--output-dir", type=Path, required=True)
    g.add_argument("--upstream-dir", type=Path, default=DEFAULT_PACKAGE)
    c = sub.add_parser("check")
    c.add_argument("--bundle", type=Path, required=True)
    c.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    v = sub.add_parser("verify-installed")
    v.add_argument("--app-dir", type=Path, required=True)
    v.add_argument("--bundle", type=Path, required=True)
    v.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    v.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    if args.command == "generate":
        if args.output_dir.exists():
            print(f"Refusing to overwrite existing {args.output_dir}", file=sys.stderr)
            return 2
        upstream = {rel: (args.upstream_dir / rel).read_bytes() for rel in UPSTREAM_TEXTS}
        tree = render(analyze_bundle(args.bundle), upstream)
        for rel, data in tree.items():
            target = args.output_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as fh:
                fh.write(data)
        print(f"Wrote {len(tree)} files to {args.output_dir}.")
        return 0
    if args.command == "check":
        errors = check(args.bundle, args.package)
        for e in errors:
            print("FAIL:", e)
        print("THIRD-PARTY PACKAGE MATCHES BUNDLE" if not errors else "THIRD-PARTY PACKAGE CHECK FAILED")
        return 0 if not errors else 1
    report = verify_installed(args.app_dir, args.package, args.bundle)
    if args.report:
        with args.report.open("x", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
    for e in report["errors"]:
        print("FAIL:", e)
    print(f"Installed files: {report['installed_files']}; third-party files verified: "
          f"{report['third_party_files_verified']}; bundle files verified: {report['bundle_files_verified']}")
    print("INSTALLED LICENSE PAYLOAD PASS" if report["pass"] else "INSTALLED LICENSE PAYLOAD FAILED")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
