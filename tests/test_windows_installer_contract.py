"""Static safety checks for the first internal Windows installer preparation.

These do not build or execute Windows installer tools on Linux.
"""
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_windows_launcher_and_optional_build_dependency():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "pyinstaller>=6,<7" in pyproject["project"]["optional-dependencies"]["build"]
    launcher = (ROOT / "scripts/gc_agent_launcher.py").read_text(encoding="utf-8")
    assert "freeze_support()" in launcher
    assert 'sys.argv[1:] == ["--self-check"]' in launcher
    assert 'from github_community_agent.work_center import main as serve' in launcher
    assert "GitHub Community Agent" not in launcher or "self-check" in launcher


def test_windows_bundle_script_preserves_data_and_independent_identity():
    build = (ROOT / "scripts/windows-build-exe.ps1").read_text(encoding="utf-8")
    assert "--onedir" in build
    assert "--collect-data" in build
    assert "github_community_agent" in build
    assert "GitHubCommunityAgent" in build
    assert "--self-check" in build
    assert "Existing product build found" in build
    assert "Remove-Item" not in build
    assert "github-community-agent-home" not in build  # frozen launcher, not venv entrypoint


def test_inno_setup_only_installs_program_files_and_preserves_user_history():
    iss = (ROOT / "packaging/windows/gc-agent.iss").read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in iss
    assert "DefaultDirName={localappdata}\\Programs\\GitHub Community Agent" in iss
    assert "AppId={{B728F255-29F8-438B-B2F7-E495DF0120E1}" in iss
    assert "Source: \"..\\..\\LICENSE\"" in iss
    assert "Source: \"..\\..\\NOTICE\"" in iss
    directives = [line.strip() for line in iss.splitlines() if not line.lstrip().startswith(";")]
    assert "[UninstallDelete]" not in directives
    assert "[Run]" not in directives
    assert "{app}" in iss
    assert "NATURE AI CORP" in iss
    # The installation recipe must not ship, read or erase user-specific GC data.
    assert "work.sqlite3" not in "\n".join(
        x for x in iss.splitlines() if x.startswith("Source: "))
    assert "settings.dpapi" not in "\n".join(
        x for x in iss.splitlines() if x.startswith("Source: "))


def test_installer_compilation_requires_explicit_external_compiler_and_self_check():
    script = (ROOT / "scripts/windows-build-installer.ps1").read_text(encoding="utf-8")
    assert "ISCC.exe" in script
    assert "Get-FileHash" in script
    assert "--self-check" in script
    assert "Existing test installer must not be overwritten" in script
    assert "No installer execution, signing, or publication" in script


def test_frozen_diagnostics_is_read_only_and_does_not_expose_secrets(tmp_path, monkeypatch, capsys):
    import importlib.util
    from github_community_agent import work_center
    launch_path = ROOT / "scripts" / "gc_agent_launcher.py"
    spec = importlib.util.spec_from_file_location("gc_agent_launcher_test", launch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert module.diagnostics() == 0
    assert not (tmp_path / "GitHubCommunityAgent").exists()
    output = capsys.readouterr().out
    assert "Existing work database: False" in output
    assert "Existing protected settings: False" in output
    assert "key" not in output.lower()
    assert "--diagnostics" in launch_path.read_text(encoding="utf-8")


def test_msix_store_python_migration_is_opt_in_and_non_destructive():
    script = (ROOT / "scripts/windows-store-data-migration.ps1").read_text(encoding="utf-8")
    assert "param([switch]$Apply)" in script
    # MSIX path redirection happens below os.path.realpath: only actual file
    # fingerprints may identify the corresponding LocalCache backing files.
    assert "os.path.realpath(root)" not in script
    assert "PythonSoftwareFoundation.Python.3.13_*" in script
    assert "settings_sha256" in script
    assert "db_sha256" in script
    assert "$matches.Count -ne 1" in script
    assert "mode=ro" in script
    assert "LocalCache\\Local" in script
    assert "Source has no Tasks; refusing migration." in script
    assert "Cannot prove target database is empty." in script
    assert "Target already has encrypted settings" in script
    assert "Source SQLite WAL/SHM/rollback journal exists" in script
    assert "Target SQLite WAL/SHM/rollback journal exists" in script
    assert "ReparsePoint" in script
    assert "DRY RUN PASS. No files changed." in script
    assert "if (-not $Apply)" in script
    assert "migration-backup-" in script
    assert "migration-stage-" in script
    assert "Get-FileHash" in script
    assert "Move-Item -LiteralPath $stageDb" in script
    assert "Move-Item -LiteralPath $stageSettings" in script
    assert "Remove-Item" not in script
    assert "Copy-Item -LiteralPath $sourceDb" in script
    assert "Copy-Item -LiteralPath $sourceSettings" in script



def test_installed_windows_acceptance_is_read_only_and_preserves_data():
    script = (ROOT / "scripts/windows-installed-acceptance.ps1").read_text(
        encoding="utf-8"
    )
    assert "Programs\\GitHub Community Agent\\GitHubCommunityAgent.exe" in script
    assert "GC-Agent-PreInstall-Backup" in script
    assert "work.sqlite3" in script
    assert "settings.dpapi" in script
    assert "Get-FileHash" in script
    assert "Get-AuthenticodeSignature" in script
    assert "--self-check" in script
    assert "--diagnostics" in script
    assert "No files were modified." in script
    assert "Remove-Item" not in script
    assert "Copy-Item" not in script
    assert "Move-Item" not in script
    assert "Start-Process" not in script
    assert "Test Connection checks are still REQUIRED" in script
    assert "Work database SHA256 INCOMPLETE" in script
    assert "Get-FileHash -LiteralPath $current -Algorithm SHA256 -ErrorAction Stop" in script
    assert "if ($hashIncomplete)" in script
    assert "exit 2" in script
    assert "Stop the app and rerun" in script



def test_upgrade_trial_version_is_distinct_and_reuses_gc_app_id():
    original = (ROOT / "packaging/windows/gc-agent.iss").read_text(encoding="utf-8")
    trial = (ROOT / "packaging/windows/gc-agent-upgrade-trial.iss").read_text(
        encoding="utf-8"
    )
    builder = (ROOT / "scripts/windows-build-installer.ps1").read_text(encoding="utf-8")
    assert '#define AppVersion "0.0.1-devtrial"' in trial
    assert '#define OutputName "GitHubCommunityAgent-UpgradeTrial-Unsigned"' in trial
    assert '#include "gc-agent.iss"' in trial
    assert "#ifndef OutputName" in original
    assert "OutputBaseFilename={#OutputName}" in original
    assert "AppId={{B728F255-29F8-438B-B2F7-E495DF0120E1}" in original
    assert "param([switch]$UpgradeTrial)" in builder
    assert "same bundled application" in builder
    assert "not an application feature/code upgrade" in builder
    assert "Existing test installer must not be overwritten" in builder


def test_upgrade_uninstall_verifier_does_not_uninstall_or_modify_work_files():
    script = (ROOT / "scripts/windows-upgrade-uninstall-verify.ps1").read_text(
        encoding="utf-8"
    )
    assert "Baseline','AfterUpgrade','AfterUninstall','AfterReinstall" in script
    assert "Get-Process -Name 'GitHubCommunityAgent'" in script
    assert "Get-FileHash -LiteralPath $db" in script
    assert "Get-FileHash -LiteralPath $settings" in script
    assert "Baseline already exists; refusing to overwrite" in script
    assert "User data differs from baseline" in script or "user data differs from baseline" in script
    assert "AfterUninstall" in script
    assert "Installed EXE still exists" in script
    assert "READ-ONLY VERIFICATION COMPLETE" in script
    for dangerous in ("Remove-Item", "Copy-Item", "Move-Item", "Start-Process", "Stop-Process"):
        assert dangerous not in script



def test_release_security_preflight_does_not_bypass_security_or_sign_release():
    path = ROOT / "scripts/windows-release-security-preflight.ps1"
    script = path.read_text(encoding="utf-8")
    assert "Get-AuthenticodeSignature" in script
    assert "Get-MpComputerStatus" in script
    assert "Get-FileHash" in script
    assert "PrivilegesRequired=lowest" in script
    assert "release_dependency_inventory.py" in script
    assert "RELEASE PREFLIGHT INCOMPLETE" in script
    assert "No scan results claimed" in script
    for forbidden in (
        "Set-MpPreference", "Add-MpPreference", "Start-MpScan", "Remove-Item",
        "Stop-Process", "Copy-Item", "Move-Item", "Start-Process",
        "Set-AuthenticodeSignature",
    ):
        assert forbidden not in script


def test_license_inventory_is_not_misrepresented_as_frozen_exe_sbom(tmp_path):
    import importlib.util
    import json
    path = ROOT / "scripts/release_dependency_inventory.py"
    script = path.read_text(encoding="utf-8")
    assert "NOT a final frozen-binary SBOM" in script
    assert "License-Expression" in script
    assert "License" in script
    assert "metadata" in script
    assert "destination.exists()" in script
    spec = importlib.util.spec_from_file_location("release_inventory_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    inventory = mod.build_inventory()
    assert inventory["scope"].endswith("NOT a final frozen-binary SBOM")
    assert inventory["dependencies"]
    assert isinstance(inventory["missing_license_metadata"], list)
    assert any("unsigned" in x for x in inventory["release_blockers"])
    # Inventory must not collect user data or local secrets.
    assert "api_key" not in json.dumps(inventory)
