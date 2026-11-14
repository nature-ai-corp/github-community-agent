"""Shared test configuration.

Technical review (M1): approving a Promotion draft requires a recorded technical review of
exactly that draft. Behaviour tests that are not about the review gate approve drafts a person
has reviewed: before such an approval this helper records the review of the CURRENT draft
through the real ``mark_reviewed`` path. Tests of the gate itself use the marker
``real_review_gate`` and run without the helper (see tests/test_promotion_review_gate.py).
"""
from __future__ import annotations

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "real_review_gate: run without the automatic technical-review helper")


@pytest.fixture(autouse=True)
def _technical_review_done(request, monkeypatch):
    if request.node.get_closest_marker("real_review_gate"):
        return
    from github_community_agent import promotion as pr
    from github_community_agent.errors import ToolError

    def wrap(name):
        original = getattr(pr.PromotionService, name)

        def approve(self, task_id, action_id, *args, **kwargs):
            try:
                a = self.store.get(action_id)
                if (a and a["task_id"] == task_id and a["status"] in pr.REVIEWABLE_STATUSES
                        and a["status"] != "incomplete"  # an incomplete draft is not presented for approval
                        and self._review_view(a)["state"] != "current"):
                    self.mark_reviewed(task_id, action_id,
                                       pr.draft_sha256(a["repository"], a["title"], a["body"], a["channel"]))
            except ToolError:
                pass  # the approval itself reports the real refusal
            return original(self, task_id, action_id, *args, **kwargs)
        monkeypatch.setattr(pr.PromotionService, name, approve)

    for name in ("approve", "bluesky_approve", "devto_approve"):
        wrap(name)
