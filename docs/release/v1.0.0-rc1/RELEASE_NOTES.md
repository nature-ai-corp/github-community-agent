# GitHub Community Agent 1.0.0-rc1 — Windows pre-release (unsigned)

> **DRAFT release text.** Not published. Prepared 2026-11-10 for the owner's
> review. No tag or GitHub Release exists. Items marked ⚠ must be resolved or
> consciously accepted by the owner before publication; see
> `RELEASE_READINESS.md` in this folder.

**Proposed tag:** `v1.0.0-rc1` (not created) · **Mark as pre-release:** yes
**Asset:** `GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe`
**SHA256:** `cafeaf6c8ba9322500e5ddb1397d08aedcf230d12fe0741e3a0ca139a18a8e16`
(also in `SHA256SUMS.txt`)

---

## What it is

GitHub Community Agent is an independent Windows desktop application from
NATURE AI CORP that helps maintainers review community activity in a public
GitHub repository with an AI model of their choice. It is **read-only toward
GitHub**: it never posts, comments, labels, closes or edits anything. Every AI
output stays in the app until a person reviews it.

Five Work Types:
- **Review Issues:** prioritized findings from a bounded page of recent Issues,
  with source links.
- **Review Discussions:** follow-up candidates from recent Discussions (needs a
  GitHub token with Discussions **read** access).
- **Draft Issue Reply / Draft Discussion Reply:** an unposted reply draft for
  one Issue or Discussion, held for your review.
- **Community Report:** a summary of observed activity, with stated coverage
  limits.

GitHub Community Agent is an independent product of NATURE AI CORP. It is not
affiliated with, sponsored by, or endorsed by GitHub, Inc. or Microsoft
Corporation. "GitHub" is a trademark of GitHub, Inc. and is used only to
identify the service this software works with.

## Windows requirements

- Windows 10 or Windows 11, 64-bit (x64). Tested on Windows 11 x64; Windows 10
  and ARM64 devices were not tested for this pre-release.
- About 35 MB of disk space. A per-user installation that needs no
  administrator rights.
- A default web browser: the app's interface opens at a local
  `http://127.0.0.1` address that only this PC can reach.
- An internet connection, plus:
  - an **OpenAI** or **DeepSeek** API key (you pay your provider for model use);
  - optional: a GitHub token with Discussions read access, for the Discussion
    Work Types.

## ⚠ This installer is not code-signed

This pre-release is **unsigned**. Windows will show "Unknown publisher", and
Microsoft Defender SmartScreen will probably warn before it runs. That is
expected for a new unsigned program. It is not a malware detection. The exact
file below was scanned with Microsoft Defender Antivirus (security intelligence
1.463.226.0) with no threats found. Verify the file yourself before running it.

### 1. Verify the download (recommended)

In PowerShell, in the folder where you saved the file:

```powershell
Get-FileHash .\GitHubCommunityAgent-1.0.0-rc1-Setup-x64-unsigned.exe -Algorithm SHA256
```

The hash must be exactly:
`CAFEAF6C8BA9322500E5DDB1397D08AEDCF230D12FE0741E3A0CA139A18A8E16`.
If it differs, **do not run the file**. Delete it and download it again from
the official GitHub Release page.

### 2. SmartScreen

If "Windows protected your PC" appears, select **More info**. Check that the
file name is the one you verified, then select **Run anyway**. Do not turn
SmartScreen or Defender off to install this app. If Defender reports a threat,
do not run the file; please report it instead.

## Installation

1. Run the verified installer.
2. **Read the End-User Terms and Third-Party Notice.** Installation continues
   only after you select **I accept the agreement**.
3. Finish the wizard. The app installs to
   `%LOCALAPPDATA%\Programs\GitHub Community Agent`. A Start-menu entry is
   created; a desktop shortcut is optional.
4. Start **GitHub Community Agent**. Your browser opens the Work Center.
5. Open **Settings**: choose OpenAI or DeepSeek, choose a model, enter your API
   key and repository (`owner/name`), then use **Test connection**.

**Where your data lives:**
- Task history: `%LOCALAPPDATA%\GitHubCommunityAgent\work.sqlite3`.
- Settings: `settings.dpapi` in the same folder. API keys are encrypted with
  Windows DPAPI for your Windows account only.

**Upgrading** from an earlier internal build keeps your settings, keys and task
history. The database is upgraded in place.

**Uninstalling** (Settings → Apps, or the Start-menu uninstaller) removes the
program but **keeps** your data folder. Delete
`%LOCALAPPDATA%\GitHubCommunityAgent` yourself if you want to remove your task
history and saved keys.

## Known limitations

- **Pre-release, unsigned:** expect SmartScreen prompts (see above).
- **Windows only:** there is no Linux or macOS release.
- **Read-only toward GitHub:** the app never posts. You copy any reply you
  approve.
- **Bounded coverage:** the analyses cover a bounded page of recent items, not
  a full audit; reports state their coverage.
- **Public repositories:** the Work Types are designed for public repositories.
  Discussions need a read token.
- **AI output can be wrong:** human review is required before acting on it.
- **Key protection:** API keys are protected per Windows user with DPAPI. That
  does not protect them from malware running under your own Windows account.
- **Promotion Work Types:** these are listed as V2 plans and cannot run in V1.
- ⚠ **Draft terms:** the End-User Terms text shown by the installer is marked
  DRAFT pending legal review.

## Changelog — 1.0.0-rc1 (first public pre-release)

Built on the independent product foundation and read-only GitHub integration
already on `main` (#1, #3, #5).

- **AI provider adapter** (#6): explicit OpenAI/DeepSeek chat-completions
  adapter. Provider hosts are validated, with DNS preflight that blocks private
  or non-public destinations. API keys are redacted from model output.
- **AI Issue reviews and Community Report** (#7): evidence-grounded Issue
  review that reads the actual Issue bodies; partial Community Report with
  stated coverage limits.
- **Discussions review** (#8): bounded AI review of real Discussion bodies and
  comments, with a separate read-only token.
- **Windows desktop** (#9): Windows launcher that runs the real workflows.
- **Unified Work Center** (#11):
  - **Work Center:** a browser-based local interface; New Task by Work Type;
    Needs My Attention; Archived Work; task soft-delete with an activity
    record.
  - **Settings:** saved with DPAPI and verified in isolation across Windows
    accounts.
  - **Local server security:** loopback only, with host, origin and per-session
    token checks; rejected requests reliably return 403/413.
  - **Installer:** per-user Inno Setup installer, upgrade-safe (settings, keys
    and history are kept), with an End-User Terms page that must be accepted.
  - **Runtime:** CPython 3.13.17 with OpenSSL 3.5.
  - **License package:** a full third-party license package with a CycloneDX
    SBOM and the exact certifi source; a GitHub/Microsoft independence
    disclaimer; EXE version metadata.

## Licenses

GitHub Community Agent is licensed under the **Apache License 2.0** (`LICENSE`,
`NOTICE`). The installer also contains third-party components under their own
licenses. All texts, a CycloneDX SBOM and the certifi source archive are
installed in `third-party-licenses\`; start with `THIRD_PARTY_NOTICES.txt`.
