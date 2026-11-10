"""Source packaging contract for a separate Windows-first GC Agent.

No network calls, no credentials, no machine installation required.
"""
from pathlib import Path
import tomllib

from github_community_agent import work_center


ROOT = Path(__file__).resolve().parents[1]


def test_distribution_entrypoints_and_ui_assets():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = project["project"]["scripts"]
    assert scripts["github-community-agent-home"] == "github_community_agent.work_center:main"
    assert scripts["github-community-agent-desktop"] == "github_community_agent.desktop:main"
    data = project["tool"]["setuptools"]["package-data"]["github_community_agent"]
    for required in ("home.html", "gc.css", "worker_v011.css"):
        assert required in data
        assert (ROOT / "src" / "github_community_agent" / required).is_file()


def test_windows_ci_matrix_and_isolated_wheel_smoke_script():
    ci = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    script = (ROOT / "scripts" / "windows-v1-preflight.ps1").read_text(encoding="utf-8")
    assert "windows-latest" in ci
    assert "ubuntu-latest" in ci
    assert 'python-version: ["3.11", "3.12", "3.13"]' in ci
    assert "scripts/windows-v1-preflight.ps1" in ci
    # Node 24 action majors (v4 checkout / v5 setup-python run on deprecated Node 20).
    assert "actions/checkout@v4" not in ci and "actions/setup-python@v5" not in ci
    assert ci.count("actions/checkout@v7") == 2 and ci.count("actions/setup-python@v7") == 2
    assert "python -m pip" not in ci or "python -m pytest -q" in ci
    assert "pip wheel . --no-deps" in script
    assert "--target $install" in script
    # Declared runtime deps go into the isolated target, and the smoke runs with
    # -I -S so the host interpreter's site-packages cannot mask a missing one.
    assert "--no-deps --no-index --target" not in script
    assert "$smoke | & $python -I -S -" in script
    assert "github-community-agent-home" in script
    assert "Remove-Item -LiteralPath $temp" in script
    assert "RELEASE BLOCKER" in script


def test_readonly_product_has_no_github_write_capability_in_work_center():
    source = (ROOT / "src" / "github_community_agent" / "work_center.py").read_text(encoding="utf-8")
    assert 'ThreadingHTTPServer(("127.0.0.1", 0)' in source
    assert 'origin == f"http://127.0.0.1:{self.server.server_port}"' in source
    assert 'self.headers.get("X-App-Nonce") == nonce' in source
    assert 'path.endswith("/restore")' not in source
    assert not hasattr(work_center.Journal, "restore")
