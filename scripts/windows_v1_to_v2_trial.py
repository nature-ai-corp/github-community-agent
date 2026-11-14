"""Isolated V1.0.0-rc1 -> V2 (2.0.0b1 candidate) Windows installation trial.

Usage (with the build venv that has PyInstaller):
  python scripts/windows_v1_to_v2_trial.py <repo root> <candidate onedir bundle> [v1.0.0-rc1]

Reuses scripts/windows_upgrade_continuity_trial.py helpers (random AppId installers built
from the real gc-agent.iss, per-user install into an isolated folder, LOCALAPPDATA pointed at
an isolated data folder). The real installation, real data folder and the real AppId
registry entry are only HASHED before and after.

LIMITATION: the trial AppId is random, never the product AppId, so it does not exercise the
production upgrade identity (the product AppId and default install folder). The OLD build is
frozen from the exact v1.0.0-rc1 tag source; it is not the published V1 installer binary,
because that installer carries the product AppId and would touch the real registration.
"""
from __future__ import annotations

import importlib.util
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()            # the V2 worktree (current src = candidate)
NEW_BUNDLE = Path(sys.argv[2]).resolve()      # candidate onedir bundle
OLD_COMMIT = sys.argv[3] if len(sys.argv) > 3 else "v1.0.0-rc1"

spec = importlib.util.spec_from_file_location("trial", ROOT / "scripts" / "windows_upgrade_continuity_trial.py")
T = importlib.util.module_from_spec(spec)
sys.modules["trial"] = T
spec.loader.exec_module(T)

VERIFIED = ["promote_repository", "promote_repository_optimization", "promote_bluesky", "promote_dev_community"]
V1_DEFS = ["review_issues", "review_discussions", "draft_issue", "draft_discussion", "community_report"]
REFUSED = ["promote_reddit", "promote_developer_forums", "promote_technical_articles", "promote_social_media"]


def real_fingerprints() -> dict:
    local = Path(os.environ["LOCALAPPDATA"])
    out = T.fingerprints()
    data = local / "GitHubCommunityAgent"
    out["real_data_files"] = {p.name: T.sha(p) for p in sorted(data.iterdir()) if p.is_file()} if data.is_dir() else {}
    inst = local / "Programs" / "GitHub Community Agent"
    out["real_install_file_count"] = sum(1 for _ in inst.rglob("*")) if inst.is_dir() else 0
    return out


def tables(db: Path) -> dict:
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as con:
        return {r[0]: [c[1] for c in con.execute(f"PRAGMA table_info({r[0]})")]
                for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}


def gate_checks(app, prefix: str) -> dict:
    defs = [d["id"] for d in app.get("/api/definitions")["definitions"]]
    titles = [d["title"] for d in app.get("/api/definitions")["definitions"] if d["id"].startswith("promote_")]
    c = {f"{prefix}definitions_v1_plus_four_verified": defs == V1_DEFS + VERIFIED,
         f"{prefix}promotion_titles": titles == ["GitHub Discussions", "Repository Optimization", "Bluesky",
                                                  "DEV Community"]}
    for d in REFUSED:
        try:
            app.post("/api/tasks", {"route": "domain", "selection": "Promotion", "definition_id": d})
            c[f"{prefix}refuses_{d}"] = False
        except Exception as exc:  # urllib raises HTTPError for 400
            c[f"{prefix}refuses_{d}"] = getattr(exc, "code", None) == 400
    c[f"{prefix}bluesky_available"] = app.get("/api/promotion/bluesky") == {"available": True, "connected": False}
    c[f"{prefix}devto_available"] = app.get("/api/promotion/devto") == {"available": True, "connected": False}
    return c


def main() -> int:
    os.environ["GCA_PROMOTION_DEV_WORK_TYPES"] = "1"   # must be ignored by the frozen build
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = ROOT / "build" / "v1-to-v2-trial" / f"run-{stamp}"
    run.mkdir(parents=True)
    guid, guid_clean = str(uuid.uuid4()).upper(), str(uuid.uuid4()).upper()
    repo = f"gc-agent-upgrade-trial/nonexistent-{secrets.token_hex(4)}"
    ev = {"run": str(run), "trial_app_id": "{" + guid + "}", "clean_trial_app_id": "{" + guid_clean + "}",
          "old_source": OLD_COMMIT, "new_bundle": str(NEW_BUNDLE), "signed": False,
          "limitation": "random trial AppId; not the production AppId upgrade path"}
    before = real_fingerprints()
    ev["real_before"] = before
    checks: dict = {}
    installed = []
    app = None
    try:
        print("1/8 freeze OLD from", OLD_COMMIT, flush=True)
        old_bundle = T.build_old(OLD_COMMIT, run)
        if not T.matches_source(NEW_BUNDLE / T.EXE, ROOT / "src"):
            raise T.TrialError("candidate bundle is not identical to current src")
        ev["old_exe_sha256"], ev["new_exe_sha256"] = T.sha(old_bundle / T.EXE), T.sha(NEW_BUNDLE / T.EXE)
        new_ver = T.vi.inno(T.vi.package_version())
        ev["new_version"] = new_ver

        print("2/8 compile installers (random AppIds)", flush=True)
        old_setup = T.compile_installer(run, guid, old_bundle, "1.0.0-rc1", "Trial-V1")
        new_setup = T.compile_installer(run, guid, NEW_BUNDLE, new_ver, "Trial-V2")
        clean_run = run / "clean"
        clean_run.mkdir()
        clean_setup = T.compile_installer(clean_run, guid_clean, NEW_BUNDLE, new_ver, "Trial-V2-clean")

        print("3/8 CLEAN install of V2 + first run", flush=True)
        cdir, cdata = clean_run / "install", clean_run / "appdata"
        T.install(clean_setup, cdir, clean_run / "install.log")
        installed.append((cdir, guid_clean, clean_run))
        checks["clean_payload_matches_bundle"] = not T.tp.verify_installed(cdir, T.tp.DEFAULT_PACKAGE, NEW_BUNDLE)["errors"]
        checks["clean_registry_version"] = (T.registry_entry(guid_clean) or {}).get("DisplayVersion") == new_ver
        app = T.App(cdir / T.EXE, cdata, clean_run / "app.log")
        st = app.get("/api/settings")
        checks["clean_first_run_no_saved_settings"] = not (st.get("has_model_key") or st.get("hasModelKey"))
        checks["clean_tasks_empty"] = app.get("/api/tasks")["tasks"] == []
        checks.update(gate_checks(app, "clean_"))
        checks["clean_no_task_created"] = app.get("/api/tasks?include_archived=1")["tasks"] == []
        app.stop(); app = None
        T.uninstall(cdir, guid_clean, clean_run / "uninstall.log")
        installed.pop()
        checks["clean_uninstall_removed_program_and_registry"] = not (cdir / T.EXE).exists() and T.registry_entry(guid_clean) is None
        checks["clean_uninstall_kept_data_folder"] = (cdata / "GitHubCommunityAgent" / "work.sqlite3").is_file()

        print("4/8 install V1, create settings, Tasks and an archived Task", flush=True)
        idir, adata = run / "install", run / "appdata"
        data = adata / "GitHubCommunityAgent"
        T.install(old_setup, idir, run / "install-v1.log")
        installed.append((idir, guid, run))
        app = T.App(idir / T.EXE, adata, run / "app-v1.log")
        app.post("/api/settings", {"provider": "openai", "model": "gpt-4.1-mini", "repository": repo,
                                    "model_key": "gc-trial-" + secrets.token_hex(16), "read_token": ""})
        for selection, definition in T.TASKS:
            app.post("/api/tasks", {"route": "work_type", "selection": selection, "definition_id": definition})
        v1_tasks = app.wait_idle(len(T.TASKS))
        archived_id = v1_tasks[-1]["id"]
        app.post(f"/api/tasks/{archived_id}/delete", {})
        v1_all = sorted(app.get("/api/tasks?include_archived=1")["tasks"], key=lambda t: t["id"])
        v1_settings = app.get("/api/settings")
        app.stop(); app = None
        v1_db = T.db_snapshot(data / "work.sqlite3")
        v1_tables = tables(data / "work.sqlite3")
        v1_dpapi = T.sha(data / "settings.dpapi")
        ev["v1_tables"] = sorted(v1_tables)

        print("5/8 install V2 OVER V1 (upgrade) and verify data", flush=True)
        T.install(new_setup, idir, run / "install-v2.log")
        checks["upgrade_payload_matches_bundle"] = not T.tp.verify_installed(idir, T.tp.DEFAULT_PACKAGE, NEW_BUNDLE)["errors"]
        checks["upgrade_registry_version"] = (T.registry_entry(guid) or {}).get("DisplayVersion") == new_ver
        app = T.App(idir / T.EXE, adata, run / "app-v2.log")
        v2_all = sorted(app.get("/api/tasks?include_archived=1")["tasks"], key=lambda t: t["id"])
        checks["upgrade_settings_identical"] = app.get("/api/settings") == v1_settings
        checks["upgrade_task_core_fields_identical"] = (
            [{k: t.get(k) for k in ("id", "definition_id", "repository", "status", "error", "created_utc")} for t in v2_all]
            == [{k: t.get(k) for k in ("id", "definition_id", "repository", "status", "error", "created_utc")} for t in v1_all])
        checks["upgrade_activity_history_identical"] = [t.get("activity") for t in v2_all] == [t.get("activity") for t in v1_all]
        checks["upgrade_archived_task_still_archived"] = any(t["id"] == archived_id and t.get("deleted_utc") for t in v2_all) \
            and archived_id not in [t["id"] for t in app.get("/api/tasks")["tasks"]]
        checks.update(gate_checks(app, "upgrade_"))
        promo = app.post("/api/promotion/settings", {"repository": "nature-ai-corp/github-community-agent", "token": ""})
        checks["upgrade_promotion_settings_saved_separately"] = promo.get("selected") == "nature-ai-corp/github-community-agent" \
            and (data / "promotion.dpapi").is_file()
        app.stop(); app = None
        v2_tables = tables(data / "work.sqlite3")
        ev["v2_new_tables"] = sorted(set(v2_tables) - set(v1_tables))
        checks["upgrade_migration_additive_only"] = all(set(v1_tables[t]) <= set(v2_tables.get(t, [])) for t in v1_tables)
        checks["upgrade_v1_rows_unchanged"] = [{k: r[k] for k in T.CORE} for r in T.db_snapshot(data / "work.sqlite3")["rows"]] \
            == [{k: r[k] for k in T.CORE} for r in v1_db["rows"]]
        checks["upgrade_settings_dpapi_bytes_unchanged"] = T.sha(data / "settings.dpapi") == v1_dpapi
        no_secret = True
        for p in data.iterdir():
            if p.is_file() and p.suffix != ".dpapi":
                no_secret &= b"gc-trial-" not in p.read_bytes()
        checks["upgrade_model_key_not_in_plain_files"] = no_secret

        print("6/8 ROLLBACK: reinstall V1 over V2 and read the upgraded data", flush=True)
        T.install(old_setup, idir, run / "install-rollback-v1.log")
        app = T.App(idir / T.EXE, adata, run / "app-rollback-v1.log")
        rb = sorted(app.get("/api/tasks?include_archived=1")["tasks"], key=lambda t: t["id"])
        checks["rollback_v1_reads_tasks"] = [t["id"] for t in rb] == [t["id"] for t in v1_all]
        checks["rollback_v1_reads_settings"] = app.get("/api/settings") == v1_settings
        app.stop(); app = None
        T.install(new_setup, idir, run / "install-v2-again.log")
        app = T.App(idir / T.EXE, adata, run / "app-v2-again.log")
        checks["reupgrade_v2_reads_tasks"] = [t["id"] for t in sorted(app.get("/api/tasks?include_archived=1")["tasks"],
                                                                    key=lambda t: t["id"])] == [t["id"] for t in v1_all]
        checks["reupgrade_promotion_settings_kept"] = app.get("/api/promotion/settings").get("selected") == \
            "nature-ai-corp/github-community-agent"
        app.stop(); app = None
        after_v2 = {p.name: T.sha(p) for p in data.iterdir() if p.is_file()}

        print("7/8 uninstall (data must remain), reinstall, diagnostics", flush=True)
        T.uninstall(idir, guid, run / "uninstall-1.log")
        installed.pop()
        checks["uninstall_kept_all_data_files"] = {p.name: T.sha(p) for p in data.iterdir() if p.is_file()} == after_v2
        T.install(new_setup, idir, run / "install-reinstall.log")
        installed.append((idir, guid, run))
        diag = subprocess.run([str(idir / T.EXE), "--diagnostics"], capture_output=True, text=True,
                              env=dict(os.environ, LOCALAPPDATA=str(adata)))
        checks["reinstall_diagnostics_reads_all_tasks"] = f"Stored Task count (including archived): {len(v1_all)}" in diag.stdout
        T.uninstall(idir, guid, run / "uninstall-2.log")
        installed.pop()
    finally:
        if app is not None:
            app.stop()
        for d, g, r in installed:
            if (d / "unins000.exe").exists():
                T.uninstall(d, g, r / "uninstall-cleanup.log")
        print("8/8 real installation / data / AppId registry unchanged?", flush=True)
        ev["real_after"] = real_fingerprints()
        checks["real_v1_installation_data_registry_unchanged"] = ev["real_after"] == before
        checks["trial_registry_entries_removed"] = T.registry_entry(guid) is None and T.registry_entry(guid_clean) is None
        ev["checks"] = checks
        ev["pass"] = bool(checks) and all(checks.values())
        (run / "v1-to-v2-trial-evidence.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
        for name in ("old-work", "old-spec"):
            shutil.rmtree(run / name, ignore_errors=True)
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    print(f"{sum(checks.values())}/{len(checks)} PASS", "| evidence:", run / "v1-to-v2-trial-evidence.json")
    return 0 if ev["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
