"""Unified home contract: product definitions, alternate New Task routes, journal and auth."""
import json
from pathlib import Path

import pytest

from github_community_agent import work_center as w
from github_community_agent.errors import ToolError


def test_new_task_alternative_routes_use_product_defined_taxonomies():
    by_type = w.task_choices("work_type", "Review Issues")
    self_promotion = w.task_choices("domain", "Self-Promotion")
    product_promotion = w.task_choices("domain", "Product Promotion")
    assert w.BY_ID["review_issues"] in by_type
    assert w.BY_ID["review_issues"] not in self_promotion
    assert self_promotion == [w.BY_ID["promote_self"]]
    assert w.BY_ID["promote_worker"] in product_promotion
    assert w.BY_ID["promote_other"] in product_promotion
    domains = {d.domain for d in w.DEFINITIONS if d.domain}
    assert domains == {"Self-Promotion", "Product Promotion"}
    assert not w.task_choices("domain", "Issues")
    assert any(d.version == "V2" and not d.enabled for d in w.DEFINITIONS)
    with pytest.raises(ToolError, match="Work Type or Domain"):
        w.task_choices("both", "Issues")


def test_definitions_are_product_owned_and_v2_unavailable(tmp_path):
    service = w.WorkService(w.Journal(tmp_path / "work.sqlite"))
    with pytest.raises(ToolError, match="must match"):
        service.start({"route": "domain", "selection": "Self-Promotion",
                       "definition_id": "promote_self"})
    with pytest.raises(ToolError, match="must match"):
        service.start({"route": "domain", "selection": "Discussions",
                       "definition_id": "review_issues"})
    assert service.journal.list() == []


def test_work_journal_persists_definition_classifications_and_review(tmp_path):
    db = tmp_path / "work.sqlite"
    j = w.Journal(db)
    wid = j.create("draft_issue", "example/public")
    j.finish(wid, "needs_attention", {"read_only": True, "posted": False, "draft": "hello"})
    j2 = w.Journal(db)
    task = j2.list()[0]
    assert task["id"] == wid
    assert task["classifications"] == {"work_type": "Draft Issue Reply", "domain": ""}
    assert task["status"] == "needs_attention"
    assert task["result"]["draft"] == "hello"
    assert j2.review(wid)
    assert j2.list()[0]["status"] == "finished"
    assert not j2.review(wid)


def test_real_workflow_receives_secret_but_journal_never_does(monkeypatch, tmp_path):
    journal = w.Journal(tmp_path / "work.sqlite")
    service = w.WorkService(journal)
    secrets_seen = []
    def production_runtime(**kwargs):
        secrets_seen.append((kwargs["model_key"], kwargs["discussion_token"]))
        return {"read_only": True, "posted": False,
                "workflow": kwargs["workflow"], "analysis": "Source-backed example"}
    monkeypatch.setattr(w, "execute_workflow", production_runtime)
    class ImmediateThread:
        def __init__(self, target, args, daemon):
            self.target, self.args = target, args
        def start(self):
            self.target(*self.args)
    monkeypatch.setattr(w.threading, "Thread", ImmediateThread)
    secret_model = "not_a_real_model_key_123456"
    secret_gh = "not_a_real_github_key_123456"
    wid = service.start({
        "route": "work_type", "selection": "Review Issues",
        "definition_id": "review_issues", "repository": "example/public",
        "provider": "openai", "model_name": "gpt-4.1-mini",
        "model_key": secret_model, "discussion_token": secret_gh,
    })
    assert secrets_seen == [(secret_model, secret_gh)]
    task = journal.list()[0]
    assert task["id"] == wid and task["status"] == "finished"
    contents = (tmp_path / "work.sqlite").read_bytes()
    assert secret_model.encode() not in contents and secret_gh.encode() not in contents


def test_start_requires_selected_domain_or_work_type(tmp_path):
    s = w.WorkService(w.Journal(tmp_path / "db.sqlite"))
    payload = {"route": "domain", "selection": "Discussions",
               "definition_id": "draft_issue",
               "repository": "example/public", "provider": "openai",
               "model_name": "gpt-4.1-mini", "model_key": "fake"}
    with pytest.raises(ToolError, match="must match"):
        s.start(payload)


def test_unified_html_includes_exclusive_routes_and_standalone_navigation():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert 'name="route" value="work_type" checked' in html
    assert 'name="route" value="domain"' in html
    assert "New Task" in html and "My Work" in html
    assert "Needs My Attention" in html
    assert "Promotion is planned" in html
    assert "Settings" in html


def test_work_center_handler_rejects_cross_origin_and_bad_nonce(tmp_path):
    journal = w.Journal(tmp_path / "db.sqlite")
    service = w.WorkService(journal)
    handler = w.handler_factory(service, "random_nonce")
    assert handler.__name__ == "Handler"
    assert journal.list() == []


def test_worker_style_settings_modal_and_real_connection_control():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert 'id="settings-overlay"' in html
    assert 'role="dialog"' in html
    assert 'id="provider"' in html
    assert 'id="model"' in html
    assert 'id="model-key"' in html
    assert 'id="settings-advanced"' in html
    assert 'id="settings-repo"' in html
    assert 'id="read-key"' in html
    assert 'id="test-connection"' in html
    assert 'id="settings-cancel"' in html
    assert 'id="settings-save"' in html
    assert "/api/test-connection" in html
    assert 'id="page-settings"' not in html
    assert 'Leave empty to keep current key' in html


def test_actual_worker_v011_css_is_packaged_separately_from_product_ui():
    root = Path(w.__file__).parent
    base = (root / "worker_v011.css").read_text(encoding="utf-8")
    custom = (root / "gc.css").read_text(encoding="utf-8")
    html = (root / "home.html").read_text(encoding="utf-8")
    assert "SPDX-License-Identifier: Apache-2.0" in base
    assert "--nav-bg: #13161e" in base
    assert ".sidebar-footer" in base
    assert "dialog::backdrop" in base
    assert "/static/worker_v011.css" in html
    assert "/static/gc.css" in html
    assert 'id="sidebar"' in html
    assert 'id="work-center"' in html
    assert 'id="settings-dialog"' in html
    assert 'id="settings-form"' in html
    assert "#choices" in custom and ".taskchoice" in custom
    assert "GitHub Community Agent" in html


def test_ui_routes_select_five_concrete_work_types_and_promotion_domains():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert 'state.route==="work_type"&&items.length===1' in html
    assert 'if(state.route==="work_type"){' in html
    assert 'vals.sort((a,b)=>a==="Self-Promotion"?-1' in html
    assert '$("selection").value=state.route==="domain"&&vals.includes("Self-Promotion")?"Self-Promotion":(vals[0]||"")' in html
    assert 'choose(items[0].id)' in html
    assert {d.domain for d in w.DEFINITIONS if d.domain} == {"Self-Promotion", "Product Promotion"}


def test_concrete_work_types_and_separate_promotion_domains(tmp_path):
    definitions = w.WorkService(w.Journal(tmp_path / "work.sqlite")).definitions()
    work_types = {d["work_type"] for d in definitions if d["work_type"]}
    domains = {d["domain"] for d in definitions if d["domain"]}
    assert work_types == {
        "Review Issues", "Review Discussions", "Draft Issue Reply",
        "Draft Discussion Reply", "Community Report",
    }
    assert domains == {"Self-Promotion", "Product Promotion"}
    assert all(not d["work_type"] for d in definitions if d["id"].startswith("promote_"))
    assert all(not d["domain"] for d in definitions if d["version"] == "V1")
    assert len(w.task_choices("work_type", "Review Issues")) == 1
    assert len(w.task_choices("work_type", "Community Management")) == 0
    assert len(w.task_choices("work_type", "Product Promotion")) == 0
    assert len(w.task_choices("domain", "Product Promotion")) == 2


def test_task_details_available_for_every_definition(tmp_path):
    definitions = w.WorkService(w.Journal(tmp_path / "work.sqlite")).definitions()
    for definition in definitions:
        details = definition["details"]
        assert set(details) == {"goal", "steps", "output", "requires", "review", "limitations"}
        assert details["goal"] and len(details["steps"]) >= 2
        assert details["output"] and details["review"]
        if not definition["enabled"]:
            assert "not implemented" in details["limitations"]


def test_task_details_are_shown_after_selection():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    for marker in ("id=\"task-details\"", "What this Task does", "Expected result",
                   "Review and approval", "Scope / availability", "V2 planned — view details"):
        assert marker in html


def test_new_task_entry_labels_are_community_management_and_promotion():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert 'value="work_type" checked>Community Management</label>' in html
    assert 'value="domain">Promotion</label>' in html
    assert '"Community Management — Work Type":"Promotion — Domain"' in html
    assert 'Select Community Management or Promotion to choose a Task.' in html
    # UI label changes must not mutate the mutually exclusive backend routes.
    assert w.task_choices("work_type", "Review Issues") == [w.BY_ID["review_issues"]]
    assert w.task_choices("domain", "Self-Promotion") == [w.BY_ID["promote_self"]]


def test_my_work_result_copy_and_json_export_controls():
    root = Path(w.__file__).parent
    html = (root / "home.html").read_text(encoding="utf-8")
    css = (root / "gc.css").read_text(encoding="utf-8")
    assert 'id="copy-result"' in html
    assert 'id="export-result"' in html
    assert 'id="task-result-json"' in html
    assert 'navigator.clipboard.writeText(resultText(t))' in html
    assert 'JSON.stringify(exportRecord(t),null,2)' in html
    assert 'type:"application/json;charset=utf-8"' in html
    assert 'link.download="gc-agent-task-"+t.id+"-result.json"' in html
    assert 'exported_at_utc:new Date().toISOString()' in html
    assert "task_id:t.id" in html and "created_at_utc:t.created_utc" in html
    assert "result:t.result" in html and "status:t.status" in html
    assert 'const hasResult=t.result!==null&&t.result!==undefined;' in html
    assert ".result-toolbar" in css
    assert ".result-action-buttons" in css


def test_no_work_result_does_not_offer_copy_or_export():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert 'const resultActions=hasResult?' in html
    assert "No result yet." in html


def test_my_work_displays_human_readable_report_before_raw_json():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    css = (Path(w.__file__).parent / "gc.css").read_text(encoding="utf-8")
    assert 'function taskReport(t)' in html
    assert 'function reportSections(analysis)' in html
    assert 'Community Review Report' in html
    for heading in ("Summary", "Findings", "Recommended Actions",
                    "Next Step", "Sources", "Technical Details"):
        assert heading in html
    assert '<details class="technical-details"><summary>Technical Details</summary>' in html
    assert 'taskReport(t)+' in html
    assert 'escapeHTML(summaryText' in html
    assert 'escapeHTML(suggestions.trim())' in html
    assert 'r.total_pages_known===false' in html
    assert 'No GitHub action has been performed.' in html
    assert 'id="copy-result"' in html and 'id="export-result"' in html
    assert '.user-report' in css and '.report-section' in css


def test_report_is_presentational_and_technical_result_is_preserved():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert 'function resultText(t)' in html
    assert 'return JSON.stringify(t.result,null,2);' in html
    assert 'result:t.result' in html
    assert 'Copy JSON' in html and 'Export JSON' in html
    assert 'r.requires_human_review?' in html


def test_polling_does_not_reset_expanded_technical_details():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    # Finished tasks do not change on each poll. Rendering them every two
    # seconds destroyed the expanded <details> node and caused flashing.
    assert "const signature=JSON.stringify(obj.tasks);" in html
    assert "if(signature===state.tasksSignature)return;" in html
    assert "state.tasksSignature=signature;" in html
    # If data legitimately changes, keep the user's open/closed preference
    # and JSON scrolling position when rendering the new Work record.
    assert 'const wasOpen=Boolean(opened?.open);' in html
    assert 'next.open=wasOpen;' in html
    assert 'if(result&&wasOpen)result.scrollTop=priorScroll;' in html


def test_issue_report_breaks_ai_analysis_into_source_linked_findings_and_actions():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    css = (Path(w.__file__).parent / "gc.css").read_text(encoding="utf-8")
    assert 'function issueReviewItems(analysis, issues)' in html
    assert 't.definition_id==="review_issues"?issueReviewItems(r.analysis,r.issues):[]' in html
    assert 'Issue records fetched in page:' in html
    assert 'Issues analyzed:' in html
    assert 'Limited sample — not a full repository review' in html
    assert "Priority (AI assessment):" in html
    assert 'issue.finding' in html and 'issue.action' in html
    assert 'class="issue-finding"' in html
    assert 'class="issue-actions"' in html
    assert '.issue-finding' in css
    # Original raw evidence remains accessible for full provenance and export.
    assert '<summary>Technical Details</summary>' in html
    assert 'result:t.result' in html


def test_draft_reply_is_visible_and_never_claims_publication():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    css = (Path(w.__file__).parent / "gc.css").read_text(encoding="utf-8")
    assert 'typeof r.draft==="string"' in html
    assert "Draft Reply — Not Published" in html
    assert 'escapeHTML(r.draft)' in html
    assert "Needs your review. No GitHub reply has been posted." in html
    assert "Marked reviewed locally. No GitHub reply has been posted." in html
    assert "To publish, use GitHub manually" in html
    assert '.draft-reply-text' in css


def test_both_draft_definitions_require_human_attention(tmp_path, monkeypatch):
    journal = w.Journal(tmp_path / "work.sqlite")
    service = w.WorkService(journal)
    produced = []
    def fake_production_runtime(**kwargs):
        produced.append(kwargs)
        return {"workflow": "draft_replies", "read_only": True,
                "posted": False, "requires_human_review": True,
                "source_url": "https://github.com/example/public/issues/33",
                "draft": "This is a proposed reply, not posted."}
    monkeypatch.setattr(w, "execute_workflow", fake_production_runtime)
    class ImmediateThread:
        def __init__(self, target, args, daemon):
            self.target, self.args = target, args
        def start(self):
            self.target(*self.args)
    monkeypatch.setattr(w.threading, "Thread", ImmediateThread)
    for definition_id, work_type, target in (
        ("draft_issue", "Draft Issue Reply", "issue"),
        ("draft_discussion", "Draft Discussion Reply", "discussion"),
    ):
        task_id = service.start({
            "route": "work_type", "selection": work_type,
            "definition_id": definition_id, "repository": "example/public",
            "provider": "openai", "model_name": "gpt-4.1-mini",
            "model_key": "test-only-credential", "number": 33,
        })
        record = next(t for t in journal.list() if t["id"] == task_id)
        assert record["status"] == "needs_attention"
        assert record["result"]["posted"] is False
        assert record["result"]["draft"].startswith("This is a proposed")
        assert produced[-1]["target"] == target
        assert journal.review(task_id)
        updated = next(t for t in journal.list() if t["id"] == task_id)
        assert updated["status"] == "finished"
        assert updated["result"]["posted"] is False
        assert updated["result"]["requires_human_review"] is True
        assert not journal.review(task_id)


def test_community_report_renders_sections_not_raw_ai_text_as_summary():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    css = (Path(w.__file__).parent / "gc.css").read_text(encoding="utf-8")
    assert "function communityReportSections(analysis)" in html
    assert 't.definition_id==="community_report"' in html
    assert 'elements.push(communityReportBody(t));' in html
    assert "Issue Activity Summary" in html
    assert "Discussion Activity Summary" in html
    assert "Key Observations and Themes" in html
    assert "Recommendations (with uncertainty)" in html
    assert "Recommended Actions — AI Assessment" in html
    assert "GitHub Issue descriptions may represent earlier plans" in html
    assert "Coverage incomplete" in html
    assert "Limited sample — not a full repository audit" in html
    assert "Total pages unverified" in html
    assert "Discussions not checked" in html
    assert 'escapeHTML(text||"No observed data in this section.")' in html
    assert "function reportLines(text)" in html
    assert ".report-prose" in css
    assert "<summary>Technical Details</summary>" in html


def test_community_report_does_not_fabricate_missing_discussion_coverage():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert 'if(r.discussions_checked===false)caveats.push("Discussions not checked")' in html
    assert 'if(r.incomplete===true)caveats.push("Coverage incomplete")' in html
    assert 'if(parsed.recommendations)' in html
    assert 'if(parsed.discussions)' in html
    assert 'if(parsed.issues)' in html


def test_delete_task_soft_delete_terminal_only_and_preserve_audit(tmp_path):
    import sqlite3
    database = tmp_path / "work.sqlite"
    journal = w.Journal(database)
    running = journal.create("review_issues", "owner/repo")
    pending = journal.create("draft_issue", "owner/repo")
    finished = journal.create("review_issues", "owner/repo")
    failed = journal.create("review_issues", "owner/repo")
    journal.finish(pending, "needs_attention", {"posted": False, "draft": "test"})
    journal.finish(finished, "finished", {"read_only": True, "posted": False})
    journal.finish(failed, "failed", error="test failure")

    assert not journal.delete(running)
    assert not journal.delete(pending)
    assert not journal.delete(0)
    assert not journal.delete(True)
    assert journal.delete(finished)
    assert journal.delete(failed)
    assert not journal.delete(finished)
    assert {task["id"] for task in journal.list()} == {running, pending}

    with sqlite3.connect(database) as con:
        records = con.execute(
            "SELECT id, status, deleted_utc, result_json, error FROM work "
            "WHERE id IN (?,?) ORDER BY id", (finished, failed)
        ).fetchall()
    assert len(records) == 2
    assert all(row[2] for row in records)
    assert records[0][3] is not None
    assert records[1][4] == "test failure"
    # A clean application restart keeps deleted Tasks out of user-facing lists.
    assert {task["id"] for task in w.Journal(database).list()} == {running, pending}


def test_existing_database_migrates_safely_and_keeps_original_work(tmp_path):
    import sqlite3
    database = tmp_path / "work.sqlite"
    with sqlite3.connect(database) as con:
        con.execute(
            "CREATE TABLE work (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "definition_id TEXT NOT NULL, repository TEXT NOT NULL, "
            "status TEXT NOT NULL, created_utc TEXT NOT NULL, "
            "updated_utc TEXT NOT NULL, result_json TEXT, error TEXT)"
        )
        con.execute(
            "INSERT INTO work (definition_id,repository,status,created_utc,updated_utc) "
            "VALUES ('review_issues','owner/repo','finished','2026-11-08','2026-11-08')"
        )
    journal = w.Journal(database)
    assert len(journal.list()) == 1
    assert journal.delete(1)
    assert journal.list() == []
    with sqlite3.connect(database) as con:
        assert con.execute("SELECT count(*) FROM work").fetchone()[0] == 1


def test_delete_button_is_confirmed_and_limited_to_terminal_tasks():
    root = Path(w.__file__).parent
    html = (root / "home.html").read_text(encoding="utf-8")
    css = (root / "gc.css").read_text(encoding="utf-8")
    assert 'id="delete-task"' in html
    assert 'window.confirm("Archive Task #"' in html
    assert '["finished","failed"].includes(t.status)' in html
    assert 'postJSON("/api/tasks/"+t.id+"/delete",{})' in html
    assert "GitHub content is unchanged." in html
    assert "state.tasksSignature=null;" in html
    assert ".task-management" in css and ".task-delete" in css


def test_archived_work_is_read_only_and_keeps_activity(tmp_path):
    db = tmp_path / "db.sqlite"
    journal = w.Journal(db)
    task_id = journal.create("draft_issue", "example/repository")
    journal.finish(task_id, "needs_attention", {"draft": "sample", "posted": False})
    assert journal.review(task_id)
    assert journal.delete(task_id)
    assert journal.list() == []
    archived = journal.list(include_archived=True)
    assert len(archived) == 1
    assert archived[0]["archived"] is True
    assert archived[0]["result"]["draft"] == "sample"
    assert [e["event"] for e in archived[0]["activity"]] == [
        "created", "needs_attention", "marked_reviewed_locally", "archived"
    ]
    assert not hasattr(journal, "restore")
    assert not journal.delete(task_id)
    assert w.Journal(db).list() == []
    assert w.Journal(db).list(include_archived=True)[0]["result"]["draft"] == "sample"


def test_archived_existing_database_has_no_fake_historical_events(tmp_path):
    import sqlite3
    db = tmp_path / "db.sqlite"
    with sqlite3.connect(db) as con:
        con.execute(
            "CREATE TABLE work (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "definition_id TEXT NOT NULL, repository TEXT NOT NULL, "
            "status TEXT NOT NULL, created_utc TEXT NOT NULL, "
            "updated_utc TEXT NOT NULL, result_json TEXT, error TEXT)"
        )
        con.execute(
            "INSERT INTO work (definition_id,repository,status,created_utc,updated_utc) "
            "VALUES ('review_issues','example/repository','finished','2026-11-08','2026-11-08')"
        )
    journal = w.Journal(db)
    assert journal.list()[0]["activity"] == []
    assert journal.delete(1)
    archived = journal.list(include_archived=True)[0]
    assert [e["event"] for e in archived["activity"]] == ["archived"]


def test_archive_ui_exposes_read_only_retained_records():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert 'data-page="archived">Archived Work' in html
    assert 'getJSON("/api/tasks?include_archived=1")' in html
    assert 'state.page==="archived"?t.archived:!t.archived' in html
    assert 'id="restore-task"' not in html
    assert 'function restoreTask(' not in html
    assert 'Archived record — view only.' in html
    assert 'path.endswith("/restore")' not in (Path(w.__file__).read_text(encoding="utf-8"))
    assert 'Activity History (' in html
    assert 'This record predates activity tracking.' in html
    assert 'Marked reviewed locally (not posted)' in html
    assert 'Archive Task' in html
