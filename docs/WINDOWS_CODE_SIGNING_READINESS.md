# Windows code signing readiness — Azure Artifact Signing (`1.0.0rc1`)

**Prepared 2026-11-10. Preparation only.** No Azure account, subscription,
identity validation or certificate profile exists. Nothing has been purchased
and nothing has been signed; every artifact is still `NotSigned`.

Microsoft facts below come from Microsoft Learn, checked on 2026-11-10:
[Quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart),
[Signing integrations](https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations),
[Resources and roles](https://learn.microsoft.com/en-us/azure/artifact-signing/concept-resources-roles),
[FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq), and the
[Azure/artifact-signing-action](https://github.com/Azure/artifact-signing-action)
repository (v2.0.0). Re-check them when you start; the service changes.

## 1. What has to be signed (and what must NOT be)

Read-only inventory of the committed `1.0.0rc1` build
(`scripts/windows-verify-signatures.ps1`):

| File | Today | Action |
|---|---|---|
| `GitHubCommunityAgent.exe` (bundle) | NotSigned | **Sign** (NATURE AI CORP) |
| Setup EXE (Inno Setup) | NotSigned | **Sign** (NATURE AI CORP) |
| `unins000.exe` (written at install time from the setup) | NotSigned | **Sign** (Inno `SignedUninstaller`) |
| 24 CPython DLL/PYD files (`python313.dll`, OpenSSL, `_ssl.pyd` …) | Valid, Python Software Foundation, SHA-256, timestamped | **Do not touch** |
| `VCRUNTIME140.dll` | Valid, Microsoft Windows Software Compatibility Publisher, timestamped | **Do not touch** (re-signing would alter Microsoft's Distributable Code) |

`python313.dll` is itself signed through Artifact Signing (chain:
`Microsoft ID Verified CS EOC CA 03` → `Microsoft ID Verified Code Signing PCA 2021`
→ `Microsoft Identity Verification Root Certificate Authority 2020`, with a
Microsoft Public RSA timestamp). That is the same chain NATURE AI CORP's
signatures will have, and the verifier was tested against it (§5).

## 2. Signing order (mandatory)

Signing changes the EXE bytes, and the license `MANIFEST.json`/SBOM pin the
EXE's SHA256. The installer build refuses a bundle whose package does not
match. So the order is fixed:

1. Build the release bundle (`scripts/windows-build-release-bundle.ps1`).
2. **Sign the app EXE:** `scripts/windows-sign-release.ps1 -Metadata … -Dlib … -Execute`.
   It refuses an already-signed file, signs only `GitHubCommunityAgent.exe`,
   re-runs `--self-check` on the signed EXE, and verifies the whole bundle.
3. **Regenerate the license package** against the signed bundle
   (`third_party_notices.py generate` → copy → `check`). This is a new commit;
   only the EXE hash and the SBOM serial change.
4. **Build and sign the installer:**
   `scripts/windows-build-installer.ps1 -SignMetadata … -Dlib …`. It first
   verifies the bundle signature (and that third-party files are untouched).
   Inno Setup then signs the setup EXE **and** the uninstaller, and the result
   is verified.
5. Run the verification procedure (§5), the payload, upgrade and security
   checks, and the Defender/SmartScreen tests (§6) on the **signed** files.

Prepared and dry-run tested (no signing performed):
- **Plan mode** prints the exact command and exits 0.
- **Refusals:** a metadata file containing a secret, a non-Azure endpoint, and
  an already-signed target are all refused.
- **Signed-installer guard:** refuses an unsigned bundle before compiling.
- **Inno sign-tool wiring:** checked with an argument recorder in place of
  SignTool. The arguments arrived exactly: `sign /v /fd SHA256 /tr
  http://timestamp.acs.microsoft.com /td SHA256 /dlib … /dmdf … <uninstaller>`.
  Inno then aborted with "the file does not have a digital signature", so an
  unsigned uninstaller cannot slip into a "signed" build.

## 3. Azure Artifact Signing: requirements for NATURE AI CORP

**Eligibility.** Public Trust certificates are available to organizations in
the US, Canada, the EU, the UK, Australia, New Zealand, Japan, South Korea,
Singapore, Switzerland, Norway and Israel. Free, trial and sponsored Azure
subscriptions are not supported; a **paid** subscription is required.

**Organization identity validation** (Azure portal only; 1–20 business days, or longer):
- **Legal name.** The organization name must be the **legal business entity**.
  The certificate CN/O is that validated name and cannot be customized. Confirm
  the exact registered spelling of "NATURE AI CORP", including any period or
  suffix.
- **Website and email.** A website belonging to the entity, plus a monitored
  **primary email on a domain the entity owns**. The verification link expires
  in **7 days**, and the mailbox must accept external links. A **secondary
  email** on the same domain is also needed.
- **Business identifier and address.** Provide the business identifier and the
  registered business address.
- **Named representative.** The representative completes **individual identity
  verification** with a government ID through Microsoft Verified ID / AU10TIX,
  using Microsoft Authenticator. The name must match the ID exactly.
- **Documents.** Supporting documents must be issued within the last 12 months
  and remain valid for at least 2 more months. There are 3 upload attempts. If
  validation fails, the request cannot be retried; start a new one.
- **Renewal.** Validation expires and must be renewed (reminders start 60 days
  before). If it lapses, signing stops.

**Resources:** a subscription with the `Microsoft.CodeSigning` resource provider
registered → an Artifact Signing account (choose a region and its endpoint, for
example East US `https://eus.codesigning.azure.net`, and a Basic or Premium SKU;
billed at the full monthly amount, not prorated) → identity validation → a
**Public Trust** certificate profile.
- **Public Trust Test:** not publicly trusted, and its lifetime EKU makes
  signatures expire with the certificate. Use it only for a dry run.
- **No EV:** Artifact Signing does not issue EV certificates.

**Roles (least privilege):**

| Who | Role | Scope |
|---|---|---|
| Owner/admin who sets up | Owner or Contributor (account, profiles); User Access Admin (assign roles) | Resource group |
| Person completing validation | **Artifact Signing Identity Verifier** | Account |
| Identity that signs | **Artifact Signing Certificate Profile Signer** only | **Certificate profile** |

**Certificates and timestamps.** Signing certificates are valid for **3 days**
and the private key never leaves the service (FIPS 140-3 Level 3). A trusted
**RFC 3161 SHA-256 timestamp** (`http://timestamp.acs.microsoft.com`) is
therefore mandatory: without it, a signature stops validating after 3 days.
The scripts always use `/fd SHA256 /tr … /td SHA256`.

**Tooling** (on the signing PC):
- Install Artifact Signing Client Tools:
  `winget install -e --id Microsoft.Azure.ArtifactSigningClientTools`. It
  includes the dlib, a compatible SignTool and .NET 8.
- Do not use the Windows SDK 20348 SignTool.
- The x64 SignTool must be paired with the x64 `Azure.CodeSigning.Dlib.dll`.
  This PC already has SignTool from SDK 10.0.26100 (x64).
- Create `metadata.json`, which holds no secrets:
  ```json
  { "Endpoint": "https://<region>.codesigning.azure.net",
    "CodeSigningAccountName": "<account>",
    "CertificateProfileName": "<profile>",
    "ExcludeCredentials": ["ManagedIdentityCredential","WorkloadIdentityCredential","EnvironmentCredential","SharedTokenCacheCredential","VisualStudioCredential","VisualStudioCodeCredential","AzurePowerShellCredential","AzureDeveloperCliCredential","InteractiveBrowserCredential"] }
  ```
  These exclusions leave only `AzureCliCredential`.
- The endpoint must match the account's region; a mismatch causes 403 /
  `SignerSign()` errors.

## 4. Credentials, and local versus GitHub Actions signing

**Recommendation for `1.0.0rc1`: sign locally on this PC, run by the owner.**
- **No stored credentials.** Authentication is interactive `az login` as a
  named person who holds only the Signer role (MFA enforced by Entra). There is
  no client secret, nothing is stored in the repo or in GitHub, and
  `metadata.json` contains no credentials (the script refuses one that does).
- **Matches the build.** The release bundle is built on this PC from the
  verified CPython 3.13.17 runtime extract, so signing where it is built avoids
  shipping unsigned binaries anywhere.
- **Fits the current GitHub plan.** The repository is **private on GitHub's Free
  plan**: branch protection and environment required-reviewer rules are not
  available, so CI cannot hold signing behind an approval gate.
- **Sign out afterwards:** run `az logout` when finished.

**GitHub Actions (later, optional)** with `Azure/artifact-signing-action@v2`:
- **Authentication:** OIDC through `azure/login`, using an Entra app or
  user-assigned managed identity with a **federated credential** restricted to
  one specific branch, tag or environment. No client secrets.
- **Least privilege:** grant only the Signer role, on the certificate profile.
- **Triggers:** run only on `workflow_dispatch` or release tags, never on
  `pull_request`, and only after a plan that supports required reviewers on a
  `signing` environment.
- **Runner:** the action is a composite `pwsh` action, so it needs a Windows
  runner.
- **Other Actions-only requirements:** the CI build must reproduce the release
  bundle, and the license package must be regenerated after signing.

The current `tests.yml` is verified by a test never to sign or use secrets.

## 5. Read-only signature verification procedure

```powershell
cd C:\Users\aiuser\projects\github-community-agent
# Bundle: our EXE signed by NATURE AI CORP; every third-party PE file keeps its ORIGINAL PSF/Microsoft signature
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-verify-signatures.ps1 `
  -BundleDir .\build\release-bundle\dist\GitHubCommunityAgent `
  -File .\dist\installer\GitHubCommunityAgent-Setup-1.0.0-rc1.exe `
  -ExpectedSigner 'CN=<exact validated legal name>' -Report .\build\signature-report.json
# Installed copy (after installing the signed setup): app EXE and uninstaller
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows-verify-signatures.ps1 `
  -File "$env:LOCALAPPDATA\Programs\GitHub Community Agent\GitHubCommunityAgent.exe","$env:LOCALAPPDATA\Programs\GitHub Community Agent\unins000.exe" `
  -ExpectedSigner 'CN=<exact validated legal name>'
```

For each file it requires all of the following:
- `Get-AuthenticodeSignature` status `Valid`;
- the signer subject contains `-ExpectedSigner`;
- `signtool verify /pa /all /v` succeeds;
- every file digest is **SHA-256**;
- a trusted **timestamp** is present.

It exits 0 only if every file passes. It never signs, changes, runs or uploads
anything.

Manual cross-check (also read-only):
```powershell
& "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe" verify /pa /all /v <file>
Get-AuthenticodeSignature <file> | Format-List Status,StatusMessage,SignerCertificate,TimeStamperCertificate
```
Expect: "Hash of file (sha256)", the chain ending in `Microsoft Identity
Verification Root Certificate Authority 2020`, "The signature is timestamped",
and "Successfully verified". In Explorer, Properties → Digital Signatures shows
the signer and a timestamp.

Tested on 2026-11-10 (read-only):
- `python313.dll` with `-ExpectedSigner 'CN=Python Software Foundation'`: **PASS**.
- The same file with the NATURE signer: **FAIL** (wrong signer).
- The current unsigned bundle plus installer: **25/27 PASS**. Only
  `GitHubCommunityAgent.exe` and the setup EXE FAIL, as `NotSigned`, which is
  correct today.

## 6. Windows Defender and SmartScreen validation (signed build)

**A. Defender scan (this PC, then the clean PC):**
1. Update signatures: `"%ProgramFiles%\Windows Defender\MpCmdRun.exe" -SignatureUpdate`.
2. Scan the setup EXE and the bundle:
   `MpCmdRun.exe -Scan -ScanType 3 -File "<setup.exe>" -DisableRemediation`,
   then the same for `<bundle folder>`. Expect "found no threats".
3. Check the history: `Get-MpThreatDetection` shows nothing new.
   `Get-MpComputerStatus | Select AMProductVersion,AntivirusSignatureVersion`
   records the engine and signature versions.
4. For a false positive, submit the **signed** file at
   https://www.microsoft.com/wdsi/filesubmission as a software developer. Do
   not add exclusions.

**B. Clean Windows 11 installation test** (a fresh VM, for example Hyper-V
"Quick Create" or a Windows 11 evaluation, fully updated; standard user;
Defender and SmartScreen at their defaults; no Python, no developer tools, no
prior GC Agent):
1. Deliver the signed setup the way users will get it: **download it in Edge
   over HTTPS** (for example a private test link), so the file gets
   Mark-of-the-Web. Copying from a share does not exercise SmartScreen.
2. Run it and record exactly what appears:
   - no prompt;
   - "Windows protected your PC" (SmartScreen);
   - an Edge download warning.

   Under **More info**, the publisher must read the validated NATURE AI CORP
   name, not "Unknown publisher".
3. The UAC prompt should **not** appear (per-user install, `PrivilegesRequired=lowest`).
4. After install, check that:
   - the app starts;
   - Settings saves a dummy key (DPAPI);
   - one read-only task runs;
   - uninstall works, and `unins000.exe` shows the same signer;
   - the user data folder `%LOCALAPPDATA%\GitHubCommunityAgent` is kept after
     uninstall, as designed.
5. Run the §5 verifier against the installed files.
6. Record: Windows build (`winver`), Defender versions, the SmartScreen outcome
   (screenshot), and the setup SHA256.

**SmartScreen expectations.** Signing removes "Unknown publisher", but a new
publisher or file may still get a SmartScreen prompt. Microsoft states that
reputation "builds up automatically" as the file accumulates download history
(FAQ). Artifact Signing issues no EV certificates, and nothing buys instant
reputation. A first-run prompt is **expected and not a blocker** on its own;
a **Defender detection is a blocker**.

## 7. Owner actions (Azure Artifact Signing), in order

1. **Choose a subscription and confirm eligibility.** Confirm the legal
   entity's exact registered name, country, business identifier, website and
   an owned-domain mailbox. Choose or create a **paid** Azure subscription in
   the company's Entra tenant (decision and purchase are the owner's).
2. **Register the provider.** Register `Microsoft.CodeSigning` on the
   subscription.
3. **Create the account.** Create a resource group and an Artifact Signing
   account. Pick the region/endpoint and the SKU; this starts billing.
4. **Validate identity.** Assign yourself **Artifact Signing Identity
   Verifier**. In the portal, submit **Organization → Public** identity
   validation. Click the email link within 7 days, then complete the
   representative's Verified ID check. Wait for **Completed**.
5. **Create the certificate profile.** Create a **Public Trust** certificate
   profile bound to that validation, and note the exact certificate subject
   shown.
6. **Grant signing rights.** Assign **Artifact Signing Certificate Profile
   Signer** at **certificate-profile scope** to the named signing person only.
7. **Set up the signing PC.**
   - Install Client Tools: `winget install -e --id Microsoft.Azure.ArtifactSigningClientTools`.
   - Install Azure CLI: `winget install -e --id Microsoft.AzureCLI`.
   - Run `az login` as the signer.
   - Create `metadata.json` (§3) **outside the repo**.
   - Check the timestamp service: `curl http://timestamp.acs.microsoft.com`
     should return 200.
8. **Plan run.** Run `scripts/windows-sign-release.ps1 -Metadata <json> -Dlib "<…\x64\Azure.CodeSigning.Dlib.dll>"`
   **without** `-Execute`, and check the printed plan.
9. **Authorize the signing run explicitly**, then follow §2 steps 2–5. A
   **Public Trust Test** profile can be used first for a dry run; those
   signatures are not publicly trusted.
10. **Record the result.** Keep the signer subject, the signed hashes, the
    signing-transaction history (Azure) and the §5/§6 results with the release
    record.
