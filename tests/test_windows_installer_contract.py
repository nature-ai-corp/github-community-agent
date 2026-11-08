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
