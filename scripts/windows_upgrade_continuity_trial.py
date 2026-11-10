"""Isolated Windows upgrade-continuity trial between two DIFFERENT GC Agent builds.

OLD build: application source from an earlier commit (default ``a2bc626``,
before the soft-delete SQLite migration and Task activity table), frozen with
the same PyInstaller options as the optimized candidate. Its embedded code is
verified to equal that commit and to differ from current ``src``.
NEW build: by default the clean release bundle (build/release-bundle, CPython
3.13.17 / OpenSSL 3.5), verified to equal current ``src``.

Both are packaged with the real ``packaging/windows/gc-agent.iss`` recipe
under a fresh random AppId (never the product AppId), installed per-user into
``build/upgrade-continuity/run-*/install`` and run with LOCALAPPDATA pointed at
``run-*/appdata``. The OLD app saves throwaway DPAPI settings and creates Task
records through its own HTTP API; the NEW build is installed OVER it; the NEW
app must read the same Tasks and encrypted settings, migrate the schema, and
operate on migrated records; uninstall and reinstall must keep the data.

Network: Task creation makes the app read Issues of a NONEXISTENT public
repository name (unauthenticated GET, 404). The model is never called. No
GitHub token is stored, nothing is posted. The real installation, real
work.sqlite3/settings.dpapi and real AppId are only hashed, before and after.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid
import winreg
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ISS = ROOT / "packaging" / "windows" / "gc-agent.iss"
LAUNCHER = ROOT / "scripts" / "gc_agent_launcher.py"
NEW_BUNDLE = ROOT / "build" / "release-bundle" / "dist" / "GitHubCommunityAgent"
EXE = "GitHubCommunityAgent.exe"
REAL_APP_ID = "{B728F255-29F8-438B-B2F7-E495DF0120E1}"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
TASKS = [("Review Issues", "review_issues"), ("Community Report", "community_report"),
         ("Review Issues", "review_issues")]

def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tp = _load("gc_tp", "third_party_notices.py")
vi = _load("gc_vi", "windows_version_info.py")


def runtime_facts(bundle: Path) -> dict:
    """Versions read from the bundled PE resources (no execution)."""
    internal = bundle / "_internal"
    return {name: vi.read_exe(internal / name).get("FileVersion")
            for name in ("python313.dll", "libssl-3.dll", "libcrypto-3.dll")}


class TrialError(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------ builds

def first_party_code(exe: Path) -> dict:
    from PyInstaller.archive.readers import CArchiveReader
    pyz = CArchiveReader(str(exe)).open_embedded_archive("PYZ.pyz")
    return {n: pyz.extract(n) for n in pyz.toc if n.startswith("github_community_agent")}


def matches_source(exe: Path, src: Path) -> bool:
    code = first_party_code(exe)
    return bool(code) and all(tp._same_code(src / c.co_filename, c) for c in code.values())


def build_old(commit: str, run: Path) -> Path:
    archive = subprocess.run(["git", "archive", "--format=zip", commit, "src"],
                             cwd=ROOT, capture_output=True, check=True).stdout
    old_src = run / "old-src"
    zipfile.ZipFile(io.BytesIO(archive)).extractall(old_src)
    # --collect-data would resolve the package through the venv's editable
    # install (current src), so add the OLD commit's data files explicitly.
    package = old_src / "src" / "github_community_agent"
    data = [x for p in sorted(package.iterdir()) if p.is_file() and p.suffix != ".py"
            for x in ("--add-data", f"{p};github_community_agent")]
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--console",
            "--name", "GitHubCommunityAgent", "--paths", str(old_src / "src"), *data,
            "--exclude-module", "pytest", "--exclude-module", "_pytest", "--exclude-module", "pygments",
            "--distpath", str(run / "old-dist"), "--workpath", str(run / "old-work"),
            "--specpath", str(run / "old-spec"), str(LAUNCHER)]
    with (run / "old-pyinstaller.log").open("w", encoding="utf-8") as fh:
        subprocess.run(args, cwd=run, stdout=fh, stderr=subprocess.STDOUT, check=True)
    bundle = run / "old-dist" / "GitHubCommunityAgent"
    if not matches_source(bundle / EXE, old_src / "src"):
        raise TrialError(f"Old build code is not identical to commit {commit}")
    for name in ("home.html", "gc.css", "worker_v011.css"):
        if sha(bundle / "_internal" / "github_community_agent" / name) != \
                sha(old_src / "src" / "github_community_agent" / name):
            raise TrialError(f"Old build UI asset differs from commit {commit}: {name}")
    return bundle


def compile_installer(run: Path, guid: str, bundle: Path, version: str, name: str) -> Path:
    iscc = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Inno Setup 6" / "ISCC.exe"
    out = run / "installers"
    args = [str(iscc), f"/DPayloadVerificationAppId={{{{{guid}}}",
            "/DIsolatedAppName=GitHub Community Agent Upgrade Trial",
            f"/DIsolatedInstallDir={run / 'install'}",
            f"/DBundleDir={bundle}", f"/DAppVersion={version}", f"/DOutputName={name}",
            f"/O{out}", str(ISS)]
    with (run / f"iscc-{name}.log").open("w", encoding="utf-8") as fh:
        subprocess.run(args, stdout=fh, stderr=subprocess.STDOUT, check=True)
    return out / f"{name}.exe"


# ------------------------------------------------------- install/registry

def registry_entry(guid: str) -> dict | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY + "\\{" + guid + "}_is1") as key:
            return {n: winreg.QueryValueEx(key, n)[0]
                    for n in ("DisplayName", "DisplayVersion", "InstallLocation")}
    except FileNotFoundError:
        return None


def install(setup: Path, install_dir: Path, logfile: Path) -> None:
    result = subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                             "/CURRENTUSER", f"/DIR={install_dir}", f"/LOG={logfile}"])
    if result.returncode != 0:
        raise TrialError(f"Installer {setup.name} exited {result.returncode}")


def uninstall(install_dir: Path, guid: str, logfile: Path) -> None:
    subprocess.run([str(install_dir / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES",
                    "/NORESTART", f"/LOG={logfile}"])
    deadline = time.time() + 90
    while ((install_dir / EXE).exists() or registry_entry(guid)) and time.time() < deadline:
        time.sleep(0.5)
    if (install_dir / EXE).exists() or registry_entry(guid):
        raise TrialError("Uninstall did not remove the trial installation")


# -------------------------------------------------------------- app driver

class App:
    """Run an INSTALLED GC Agent with an isolated LOCALAPPDATA and use its API."""

    def __init__(self, exe: Path, appdata: Path, logfile: Path):
        env = dict(os.environ, LOCALAPPDATA=str(appdata), BROWSER="cmd /c rem %s")
        self.log = logfile.open("w", encoding="utf-8")
        self.proc = subprocess.Popen([str(exe)], env=env, stdout=self.log, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
        self.port = self._port()
        html = self._request("GET", "/", raw=True)
        self.nonce = re.search(r'const NONCE="([^"]+)"', html).group(1)

    def _port(self) -> int:
        deadline = time.time() + 60
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise TrialError("Application exited during startup")
            out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) == 5 and parts[3] == "LISTENING" and parts[4] == str(self.proc.pid) \
                        and parts[1].startswith("127.0.0.1:"):
                    return int(parts[1].rsplit(":", 1)[1])
            time.sleep(0.5)
        raise TrialError("Application did not open a loopback port")

    def _request(self, method: str, path: str, body: dict | None = None, raw: bool = False):
        base = f"http://127.0.0.1:{self.port}"
        headers = {"X-App-Nonce": getattr(self, "nonce", "")}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers.update({"Content-Type": "application/json", "Origin": base})
        req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
        return text if raw else json.loads(text)

    def get(self, path: str):
        return self._request("GET", path)

    def post(self, path: str, body: dict):
        return self._request("POST", path, body)

    def wait_idle(self, expected: int) -> list[dict]:
        deadline = time.time() + 120
        while time.time() < deadline:
            tasks = self.get("/api/tasks")["tasks"]
            if len(tasks) >= expected and all(t["status"] != "running" for t in tasks):
                return tasks
            time.sleep(1)
        raise TrialError("Tasks did not reach a terminal state")

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(30)
        self.log.close()


def db_snapshot(db: Path) -> dict:
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as con:
        con.row_factory = sqlite3.Row
        columns = [r[1] for r in con.execute("PRAGMA table_info(work)")]
        tables = sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'"))
        rows = [dict(r) for r in con.execute("SELECT * FROM work ORDER BY id")]
    return {"columns": columns, "tables": tables, "rows": rows}


CORE = ("id", "definition_id", "repository", "status", "created_utc", "updated_utc",
        "result_json", "error")


def fingerprints() -> dict:
    local = Path(os.environ["LOCALAPPDATA"])
    out = {}
    for p in (local / "Programs" / "GitHub Community Agent" / EXE,
              local / "GitHubCommunityAgent" / "work.sqlite3",
              local / "GitHubCommunityAgent" / "settings.dpapi"):
        out[str(p)] = sha(p) if p.is_file() else "absent"
    out["real_app_id_registry"] = registry_entry(REAL_APP_ID.strip("{}"))
    return out


# --------------------------------------------------------------------- run

def run_trial(commit: str, new_bundle: Path = NEW_BUNDLE, new_label: str | None = None) -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = ROOT / "build" / "upgrade-continuity" / f"run-{stamp}"
    run.mkdir(parents=True, exist_ok=False)
    install_dir, appdata = run / "install", run / "appdata"
    data = appdata / "GitHubCommunityAgent"
    guid = str(uuid.uuid4()).upper()
    repo = f"gc-agent-upgrade-trial/nonexistent-{secrets.token_hex(4)}"
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout.strip()
    ev: dict = {"run": str(run), "trial_app_id": "{" + guid + "}", "old_commit": commit,
                "new_commit": head, "legal_review_approved": False, "signed": False}
    new_label = new_label or vi.inno(vi.package_version())
    before = fingerprints()
    installed = False
    app = None
    try:
        log("1/9 Building OLD application from commit " + commit)
        old_bundle = build_old(commit, run)
        if matches_source(old_bundle / EXE, ROOT / "src"):
            raise TrialError("Old build is identical to current src; not a real upgrade")
        if not matches_source(new_bundle / EXE, ROOT / "src"):
            raise TrialError("New bundle is not identical to current src")
        ev["old_exe_sha256"], ev["new_exe_sha256"] = sha(old_bundle / EXE), sha(new_bundle / EXE)
        old_code, new_code = first_party_code(old_bundle / EXE), first_party_code(new_bundle / EXE)
        ev["first_party_modules_changed"] = sorted(n for n in new_code if old_code.get(n) != new_code[n])
        ev["old_runtime"], ev["new_runtime"] = runtime_facts(old_bundle), runtime_facts(new_bundle)

        log("2/9 Compiling OLD and NEW installers with isolated AppId")
        old_ver, new_ver = f"0.0.0-dev0+{commit}", f"{new_label}+{head}"
        old_setup = compile_installer(run, guid, old_bundle, old_ver, "UpgradeTrial-OLD")
        new_setup = compile_installer(run, guid, new_bundle, new_ver, "UpgradeTrial-NEW")

        log("3/9 Installing OLD build")
        install(old_setup, install_dir, run / "install-old.log")
        installed = True
        if sha(install_dir / EXE) != ev["old_exe_sha256"]:
            raise TrialError("Installed EXE is not the OLD build")
        ev["registry_after_old_install"] = registry_entry(guid)

        log("4/9 OLD app: saving throwaway DPAPI settings and creating Tasks")
        app = App(install_dir / EXE, appdata, run / "app-old.log")
        app.post("/api/settings", {"provider": "openai", "model": "gpt-4.1-mini", "repository": repo,
                                    "model_key": "gc-upgrade-trial-" + secrets.token_hex(16),
                                    "read_token": ""})
        for selection, definition in TASKS:
            app.post("/api/tasks", {"route": "work_type", "selection": selection,
                                    "definition_id": definition})
        old_tasks = app.wait_idle(len(TASKS))
        old_settings = app.get("/api/settings")
        app.stop()
        app = None
        ev["old_task_errors"] = sorted({t["error"] for t in old_tasks})
        old_db = db_snapshot(data / "work.sqlite3")
        old_dpapi = sha(data / "settings.dpapi")
        ev["old_schema"] = {"columns": old_db["columns"], "tables": old_db["tables"]}
        if "deleted_utc" in old_db["columns"] or "work_events" in old_db["tables"]:
            raise TrialError("OLD build already has the new schema")

        log("5/9 Installing NEW build OVER the OLD installation (upgrade)")
        install(new_setup, install_dir, run / "install-new.log")
        payload = tp.verify_installed(install_dir, tp.DEFAULT_PACKAGE, new_bundle)
        ev["upgraded_payload_errors"] = payload["errors"]
        ev["registry_after_upgrade"] = registry_entry(guid)
        if payload["errors"] or ev["registry_after_upgrade"]["DisplayVersion"] != new_ver:
            raise TrialError("Upgraded installation is not exactly the NEW build")

        log("6/9 NEW app: reading migrated Tasks and DPAPI settings")
        app = App(install_dir / EXE, appdata, run / "app-new.log")
        new_tasks = app.get("/api/tasks?include_archived=1")["tasks"]
        new_settings = app.get("/api/settings")
        checks = {
            "settings_identical_via_api": new_settings == old_settings,
            "model_key_still_decryptable": new_settings.get("has_model_key") is True,
            "tasks_identical_core_fields":
                sorted(({k: t[k] for k in CORE} for t in new_tasks), key=lambda r: r["id"]) ==
                sorted(({k: t[k] for k in CORE} for t in old_tasks), key=lambda r: r["id"]),
        }
        target = old_tasks[-1]["id"]
        app.post(f"/api/tasks/{target}/delete", {})
        visible = [t["id"] for t in app.get("/api/tasks")["tasks"]]
        archived = app.get("/api/tasks?include_archived=1")["tasks"]
        checks["new_feature_soft_delete_on_migrated_task"] = (
            target not in visible and any(t["id"] == target and t.get("deleted_utc") for t in archived))
        app.stop()
        app = None
        new_db = db_snapshot(data / "work.sqlite3")
        checks["schema_migrated"] = ("deleted_utc" in new_db["columns"]
                                     and "work_events" in new_db["tables"])
        checks["old_rows_unchanged_except_tombstone"] = all(
            {k: n[k] for k in CORE} == {k: o[k] for k in CORE}
            for o, n in zip(old_db["rows"], new_db["rows"])) and len(new_db["rows"]) == len(old_db["rows"])
        checks["settings_dpapi_bytes_unchanged"] = sha(data / "settings.dpapi") == old_dpapi
        ev["checks_after_upgrade"] = checks
        after_new = {p.name: sha(p) for p in data.iterdir() if p.is_file()}

        log("7/9 Uninstalling; user data must remain")
        uninstall(install_dir, guid, run / "uninstall-1.log")
        installed = False
        ev["data_unchanged_by_uninstall"] = {p.name: sha(p) for p in data.iterdir() if p.is_file()} == after_new

        log("8/9 Reinstalling NEW build and reading data with --diagnostics")
        install(new_setup, install_dir, run / "install-reinstall.log")
        installed = True
        diag = subprocess.run([str(install_dir / EXE), "--diagnostics"], capture_output=True, text=True,
                              env=dict(os.environ, LOCALAPPDATA=str(appdata)))
        ev["reinstall_diagnostics_task_count"] = re.search(
            r"Stored Task count \(including archived\): (\d+)", diag.stdout).group(1)
        uninstall(install_dir, guid, run / "uninstall-2.log")
        installed = False
    finally:
        if app is not None:
            app.stop()
        if installed and (install_dir / "unins000.exe").exists():
            uninstall(install_dir, guid, run / "uninstall-cleanup.log")
        log("9/9 Checking real installation and real user data were untouched")
        ev["real_installation_and_user_data_unchanged"] = fingerprints() == before
        ev["trial_registry_entry_removed"] = registry_entry(guid) is None
    ev["pass"] = (all(ev["checks_after_upgrade"].values()) and ev["data_unchanged_by_uninstall"]
                  and ev["reinstall_diagnostics_task_count"] == str(len(TASKS))
                  and ev["real_installation_and_user_data_unchanged"] and ev["trial_registry_entry_removed"]
                  and bool(ev["first_party_modules_changed"]))
    with (run / "upgrade-continuity-evidence.json").open("x", encoding="utf-8") as fh:
        json.dump(ev, fh, indent=2)
    for name in ("old-work", "old-spec"):          # bulky intermediates only
        shutil.rmtree(run / name, ignore_errors=True)
    return ev


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--old-commit", default="a2bc626")
    parser.add_argument("--new-bundle", type=Path, default=NEW_BUNDLE)
    args = parser.parse_args(argv)
    ev = run_trial(args.old_commit, args.new_bundle.resolve(strict=True))
    print(json.dumps({k: v for k, v in ev.items() if k not in ("old_schema",)}, indent=2))
    print("UPGRADE CONTINUITY TRIAL PASS" if ev["pass"] else "UPGRADE CONTINUITY TRIAL FAILED")
    return 0 if ev["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
