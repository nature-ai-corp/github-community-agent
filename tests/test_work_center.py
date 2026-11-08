"""Unified home contract: product definitions, alternate New Task routes, journal and auth."""
import json
from pathlib import Path

import pytest

from github_community_agent import work_center as w
from github_community_agent.errors import ToolError


def test_new_task_alternative_routes_use_product_defined_taxonomies():
    by_type = w.task_choices("work_type", "Community Management")
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
    assert task["classifications"] == {"work_type": "Community Management", "domain": ""}
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
        "route": "work_type", "selection": "Community Management",
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


def test_domain_selector_defaults_to_self_promotion():
    html = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")
    assert 'vals.includes("Self-Promotion")' in html
    assert '$("selection").value="Self-Promotion"' in html
    assert 'a==="Self-Promotion"?-1' in html
    assert {d.domain for d in w.DEFINITIONS if d.domain} == {"Self-Promotion", "Product Promotion"}
