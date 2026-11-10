# VCRUNTIME140.dll: redistribution basis (for counsel; NOT approved)

**Prepared 2026-11-10. Not legal advice. This records facts and open questions;
it does not conclude that redistribution is permitted. DECISION 3 in
`V1_LICENSE_REVIEW_REPORT.md` remains open until a named person decides it.**

## 1. What is shipped (verified)

| Fact | Evidence |
|---|---|
| One Microsoft runtime file: `_internal/VCRUNTIME140.dll` (x64) | Bundle listing; no `vcruntime140_1.dll`, `msvcp140.dll` or UCRT files are bundled |
| Version 14.51.36247.0 | PE version resource |
| SHA256 `d1f4225d…c9ce7` | Byte-identical to `vcruntime140.dll` in the official CPython 3.13.17 x64 build (`core.msi`, administrative extract) and in the PSF NuGet `python` 3.13.17 package |
| Authenticode: Valid, signer "Microsoft Windows Software Compatibility Publisher" | `Get-AuthenticodeSignature` |
| Unmodified | `scripts/third_party_notices.py` fails the build unless it is byte-identical to the CPython runtime copy |
| Reached the bundle via PyInstaller's dependency collection from the CPython runtime, not from Visual Studio | Bundle analysis (`origin: vcruntime140.dll` of `sys.base_prefix`) |

NATURE AI CORP does not obtain the file from Visual Studio or from Microsoft's
download pages. It redistributes the PSF's copy as part of the CPython runtime
that the frozen application embeds.

## 2. The terms that travel with the file (verbatim, CPython 3.13.17 `LICENSE.txt`)

> If you further distribute programs that include the Microsoft
> Distributable Code, you must comply with the restrictions on
> distribution specified by Microsoft. In particular, you must require
> distributors and external end users to agree to terms that protect the
> Microsoft Distributable Code at least as much as Microsoft's own
> requirements for the Distributable Code.
>
> Redistribution of the Windows binary build of the Python interpreter
> complies with this agreement, provided that you do not:
> - alter any copyright, trademark or patent notice in Microsoft's Distributable Code;
> - use Microsoft's trademarks in your programs' names or in a way that suggests your programs come from or are endorsed by Microsoft;
> - distribute Microsoft's Distributable Code to run on a platform other than Microsoft operating systems, run-time technologies or application platforms; or
> - include Microsoft Distributable Code in malicious, deceptive or unlawful programs.

The full text ships at `third-party-licenses/cpython-3.13.17/LICENSE.txt` and is
referenced from `THIRD_PARTY_NOTICES.txt`.

## 3. Microsoft's own statement (Microsoft Learn, "Visual Studio 2022 Redistribution", checked 2026-11-10)

- Under "Visual C++ Runtime Files": *"Subject to the License Terms for the
  software, you may copy and distribute with your program any of the files
  within the following folder and its subfolders except as noted below. You may
  not modify these files. — [VisualStudioFolder]\VC\redist"*.
- The same section: *"Distribution of the Visual C++ Runtime Redistributable
  package, merge modules, and individual binaries obtained from those pages is
  limited to licensed Visual Studio users and is subject to its license terms."*

The Visual Studio license terms themselves (the "Distributable Code" section,
including any permission for a licensee's distributors to redistribute) were not
retrievable as text on 2026-11-10 and are **not quoted here**; counsel should
read them from the Visual Studio license that applies.

## 4. How each condition is currently addressed (status, not a conclusion)

| Condition (CPython `LICENSE.txt`) | Current state | Status |
|---|---|---|
| Do not alter Microsoft notices | DLL byte-identical and validly signed | Met (verified) |
| No Microsoft trademarks in program names / no implied endorsement | Product name contains "GitHub" (a GitHub, Inc. trademark; GitHub is a Microsoft subsidiary). An explicit independence disclaimer now ships in `NOTICE`, `THIRD_PARTY_NOTICES.txt`, `README.md` and the EXE `FileDescription` | **Open — counsel** |
| Windows-only | Windows x64 installer only | Met |
| Not malicious/deceptive/unlawful | Read-only V1 functions; no GitHub writes | Met by the product (no attestation document required; owner decision 2026-11-10) |
| "Require distributors and external end users to agree to terms that protect the Microsoft Distributable Code" | The installer shows no end-user terms page; the terms are only installed as files | **Open — counsel** |

## 5. Options for the owner/counsel

1. **Keep app-local VCRUNTIME140.dll (current), add an end-user terms page.**
   Add an Inno Setup `LicenseFile` page that users must accept, containing the
   GC Agent license and a clause protecting Microsoft Distributable Code. Small
   packaging change; text must be drafted by counsel.
2. **Have NATURE AI CORP redistribute as its own Visual Studio licensee.**
   If the company holds a Visual Studio license whose Distributable Code terms
   cover it, the file could be sourced from `VC\redist` under that license
   instead of the PSF chain. It would have to be the same or a newer compatible
   version, and the provenance checks would need a new pin.
3. **Do not bundle; require the Microsoft Visual C++ Redistributable.** The
   installer would check for or chain Microsoft's own redistributable package.
   This removes app-local redistribution, but it is a packaging change with
   compatibility and UX impact; the installer and upgrade trials must be
   repeated.

## 5a. Narrowed analysis (2026-11-10): what actually applies to NATURE AI CORP

No new purchase is assumed. NATURE AI CORP is a **downstream redistributor of
the PSF's unmodified Windows build**. Its permission is the conditional grant in
CPython's `LICENSE.txt`, quoted in §2: redistribution "complies with this
agreement, provided that you do not …". That route does **not** depend on
NATURE AI CORP holding its own Visual Studio license, so **option 2 is not
needed**. Counsel only has to confirm that the PSF route is sufficient.

**Scope of the conditions** (CPython `LICENSE.txt`, lines 284–287 of the
shipped copy): "The Microsoft Distributable Code is embedded in each .exe,
.dll and .pyd file as a result of running the code through a linker." The
conditions therefore cover the whole CPython runtime in the bundle, not only
`VCRUNTIME140.dll`. **Consequence:** option 3 (not bundling `VCRUNTIME140.dll`)
would **not** remove the end-user-terms condition; it would only add packaging
risk. It is no longer recommended.

The applicable obligations, and only these:

| # | Condition | State in the shipped RC1 | Action |
|---|---|---|---|
| a | Do not alter Microsoft notices | DLL byte-identical and Microsoft-signed; signing scripts refuse to re-sign third-party binaries | None (verified) |
| b | No Microsoft trademarks in program names, and no suggestion of origin or endorsement by Microsoft | Name contains "GitHub" (a GitHub, Inc. mark; GitHub is a Microsoft subsidiary); independence disclaimer shipped | **Counsel decision** (shared with the product-name issue) |
| c | Microsoft platforms only | Windows x64 only | None |
| d | Not malicious, deceptive or unlawful | Read-only V1 | Met by the product; no attestation document required |
| e | "require distributors and external end users to agree to terms that protect the Microsoft Distributable Code at least as much as Microsoft's own requirements" | Installer shows **no** terms; `LICENSE`/`NOTICE` are only installed as files | **Open.** The smallest fix is option 1: an end-user license page in the installer (Inno `LicenseFile`, accepted before install), with a counsel-approved clause protecting the Microsoft Distributable Code |

**Recommended path for counsel to confirm:**
- **Condition (e):** option 1 (installer terms page). Counsel drafts or
  approves the text; then it is a small packaging change plus re-verification.
- **Condition (b):** decided together with the product name.
- **Upstream licenses:** nothing else is reopened. All other upstream license
  items stay as already verified.

## 6. Required human decisions

- Whether the product name "GitHub Community Agent" is acceptable under the
  Microsoft condition **and** GitHub's own trademark/logo policy (renaming is
  the conservative alternative).
- Which option in section 5 to adopt, and the text of any end-user terms.
- Record the decision, reviewer and date with DECISION 3 of the license review.
