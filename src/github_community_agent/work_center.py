"""Independent, loopback-only Work Center with dynamic product Task definitions.

Task entry selects ONE taxonomy route (Work Type OR Domain) before choosing
a definition. This app is not a NATURE AI Platform Task engine. Credential
material stays in the request/worker memory, never the SQLite work journal.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import threading
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .desktop import execute_workflow
from .model_provider import ChatCompletionsModel, ModelSettings
from .errors import ToolError
from .encrypted_settings import EncryptedSettings, SettingsError

MAX_REQUEST_BYTES = 12000
MAX_DISCARD_BYTES = 64 * 1024  # largest rejected body drained before replying


@dataclass(frozen=True)
class TaskDefinition:
    id: str
    title: str
    work_type: str
    domain: str
    workflow: str | None
    version: str
    enabled: bool


# Product-specific, mutually exclusive Task definition routes. V1 concrete
# operations ARE the Work Types; V2 promotion targets are Domains. Blank
# classification means the Task belongs solely to the other route.
DEFINITIONS = (
    TaskDefinition("review_issues", "Review Issues", "Review Issues", "", "review_issues", "V1", True),
    TaskDefinition("review_discussions", "Review Discussions", "Review Discussions", "", "review_discussions", "V1", True),
    TaskDefinition("draft_issue", "Draft Issue Reply", "Draft Issue Reply", "", "draft_replies", "V1", True),
    TaskDefinition("draft_discussion", "Draft Discussion Reply", "Draft Discussion Reply", "", "draft_replies", "V1", True),
    TaskDefinition("community_report", "Community Report", "Community Report", "", "community_report", "V1", True),
    # V2: ONE Promotion Agent / engine with independently selectable Promotion Work
    # Types (one Task definition each; each social platform is its own Work Type).
    # The target repository and its token are configuration. promote_repository keeps
    # its id (existing Tasks/evidence). promote_social_media is legacy: existing Tasks
    # keep it, New Task never offers it (promotion.LEGACY_WORK_TYPES).
    TaskDefinition("promote_repository", "GitHub Discussions", "", "Promotion", "promotion", "V2", True),
    TaskDefinition("promote_repository_optimization", "Repository Optimization", "", "Promotion", "promotion", "V2", True),
    TaskDefinition("promote_reddit", "Reddit Promotion", "", "Promotion", "promotion", "V2", True),
    TaskDefinition("promote_developer_forums", "Developer Forums", "", "Promotion", "promotion", "V2", True),
    TaskDefinition("promote_technical_articles", "Technical Articles", "", "Promotion", "promotion", "V2", True),
    TaskDefinition("promote_bluesky", "Bluesky", "", "Promotion", "promotion", "V2", True),
    TaskDefinition("promote_social_media", "Social Media (legacy)", "", "Promotion", "promotion", "V2", True),
)
BY_ID = {d.id: d for d in DEFINITIONS}


def available_definitions() -> tuple:
    """Definitions New Task offers. Promotion Work Types pass the release gate and are not
    legacy (promotion.startable_work_types); every V1 definition is always available."""
    from .promotion import startable_work_types
    enabled = startable_work_types()
    return tuple(d for d in DEFINITIONS if d.workflow != "promotion" or d.id in enabled)

# Each Task owns its own user-facing definition. The Work Center only renders
# these records; another product can supply different classification/fields.
TASK_DETAILS = {
    "review_issues": {
        "goal": "Review recent public GitHub Issues and identify items that may need maintainer attention.",
        "steps": ["Read a bounded page of Issues from the configured repository.",
                  "Analyze the retrieved issues with the configured AI model.",
                  "Return prioritized findings grounded in actual GitHub evidence."],
        "output": "Issue analysis with evidence and source references; no GitHub changes.",
        "requires": "Public repository, configured AI model and API key.",
        "review": "Human review recommended before acting on findings.",
        "limitations": "Only fetched issues are covered; not a complete audit of every Issue."
    },
    "review_discussions": {
        "goal": "Review recent GitHub Discussions and identify questions or conversations needing follow-up.",
        "steps": ["Read a bounded page of Discussions and selected available details/comments.",
                  "Analyze topics and unanswered or pending conversations.",
                  "Produce a source-backed review for a maintainer."],
        "output": "Discussion analysis with actual links; no replies are published.",
        "requires": "Public repository, AI model, and GitHub Discussions READ token.",
        "review": "Human review required before any community reply.",
        "limitations": "Only fetched discussions and comments are covered."
    },
    "draft_issue": {
        "goal": "Prepare a suggested maintainer reply to one specific GitHub Issue.",
        "steps": ["Read the selected Issue and its existing context.",
                  "Generate a relevant reply draft using the AI model.",
                  "Place the draft in Needs My Attention for human review."],
        "output": "Unposted reply draft and associated GitHub source evidence.",
        "requires": "Public repository, Issue number, AI model and API key.",
        "review": "Must be reviewed by a person; Mark reviewed never posts to GitHub.",
        "limitations": "Read-only: no comments or replies are sent."
    },
    "draft_discussion": {
        "goal": "Prepare a suggested maintainer reply to one specific GitHub Discussion.",
        "steps": ["Read the selected Discussion and available context.",
                  "Generate a context-specific reply draft.",
                  "Place the draft in Needs My Attention for human review."],
        "output": "Unposted discussion reply draft and source evidence.",
        "requires": "Public repository, Discussion number, Discussions READ token, AI model and API key.",
        "review": "Must be reviewed by a person; Mark reviewed never posts to GitHub.",
        "limitations": "Read-only: no discussion replies are sent."
    },
    "community_report": {
        "goal": "Summarize observed community activity and follow-up opportunities.",
        "steps": ["Retrieve bounded available Issue and Discussion evidence.",
                  "Analyze observed activity with the configured AI model.",
                  "Report findings with coverage limitations and source evidence."],
        "output": "Community activity report, based only on retrieved data.",
        "requires": "Public repository, AI model; Discussions READ token needed for Discussion coverage.",
        "review": "Human review recommended; no changes are published.",
        "limitations": "A missing Discussions token or limited fetched data makes coverage incomplete."
    },
    "promote_repository": {
        "goal": "Announce the selected product repository (default: GitHub Community Agent) in its own GitHub Discussions.",
        "steps": ["Research the repository's real README, releases and public facts, with source links.",
                  "Plan audience, value proposition, channels, schedule and measurable objectives.",
                  "Draft one factual announcement for a GitHub Discussion in that repository.",
                  "You review, edit and approve the exact text; nothing is posted before that.",
                  "Publish only the approved action, after a fresh permission check.",
                  "Monitor engagement and get improvement suggestions."],
        "output": "Evidence, plan, an editable draft, the published Discussion link and engagement metrics.",
        "requires": "Public repository selected in Settings → Promotion, AI model and API key; publishing "
                    "needs that repository's own GitHub token (WRITE access, Discussions enabled).",
        "review": "Explicit approval of the exact repository, category, title and body before publication.",
        "limitations": "Automated publishing: only a Discussion in the selected repository itself, never "
                       "to other repositories or third-party sites."
    },
    "promote_repository_optimization": {
        "goal": "Propose improvements to how the product repository presents itself (description, topics, README, releases, templates).",
        "steps": ["Research the repository's real README, releases and public facts, with source links.",
                  "Plan this Work Type only (audience, value, approach, schedule, objectives).",
                  "Draft concrete proposals, each with the exact proposed text, its evidence and rationale.",
                  "You review, edit and approve the exact text.",
                  "Publish it yourself, by hand, following the community-rules checklist."],
        "output": "Reviewable list of proposed repository changes; nothing is changed in the repository.",
        "requires": "Public repository selected in Settings → Promotion, AI model and API key. No GitHub "
                    "token or channel account is used.",
        "review": "Explicit approval of the exact text. Approval only marks it ready; you publish it yourself.",
        "limitations": "Proposals only. This application never writes to the repository; you apply approved changes yourself."
    },
    "promote_reddit": {
        "goal": "Prepare one honest, disclosed Reddit post about the product for a subreddit that allows project posts.",
        "steps": ["Research the repository's real README, releases and public facts, with source links.",
                  "Plan this Work Type only (audience, value, approach, schedule, objectives).",
                  "Draft one post with an affiliation disclosure.",
                  "You review, edit and approve the exact text.",
                  "Publish it yourself, by hand, following the community-rules checklist."],
        "output": "An editable Reddit post draft and a community-rules checklist.",
        "requires": "Public repository selected in Settings → Promotion, AI model and API key. No GitHub "
                    "token or channel account is used.",
        "review": "Explicit approval of the exact text. Approval only marks it ready; you publish it yourself.",
        "limitations": "Draft / manual publication only: no Reddit integration; nothing is posted to Reddit."
    },
    "promote_developer_forums": {
        "goal": "Prepare one disclosed project announcement for a developer forum section that allows it.",
        "steps": ["Research the repository's real README, releases and public facts, with source links.",
                  "Plan this Work Type only (audience, value, approach, schedule, objectives).",
                  "Draft one technical announcement with an affiliation disclosure.",
                  "You review, edit and approve the exact text.",
                  "Publish it yourself, by hand, following the community-rules checklist."],
        "output": "An editable forum post draft and a community-rules checklist.",
        "requires": "Public repository selected in Settings → Promotion, AI model and API key. No GitHub "
                    "token or channel account is used.",
        "review": "Explicit approval of the exact text. Approval only marks it ready; you publish it yourself.",
        "limitations": "Draft / manual publication only: no forum integration; nothing is posted to any forum."
    },
    "promote_technical_articles": {
        "goal": "Prepare a technical article (tutorial or deep dive) about the product.",
        "steps": ["Research the repository's real README, releases and public facts, with source links.",
                  "Plan this Work Type only (audience, value, approach, schedule, objectives).",
                  "Draft one article grounded in the documented steps, with source links.",
                  "You review, edit and approve the exact text.",
                  "Publish it yourself, by hand, following the community-rules checklist."],
        "output": "An editable article draft and a publication checklist.",
        "requires": "Public repository selected in Settings → Promotion, AI model and API key. No GitHub "
                    "token or channel account is used.",
        "review": "Explicit approval of the exact text. Approval only marks it ready; you publish it yourself.",
        "limitations": "Draft / manual publication only: nothing is published to any blog or publication."
    },
    "promote_bluesky": {
        "goal": "Publish ONE short, factual, disclosed post about the product from the project's own "
                "Bluesky account, after you approve the exact post.",
        "steps": ["Research the repository's real README, releases and public facts, with source links.",
                  "Plan this Work Type only (audience, value, approach, schedule, objectives).",
                  "Draft one Bluesky post (within Bluesky's 300-character limit) with the repository link.",
                  "You review and edit it, then approve the exact post: account, text and links.",
                  "The Agent publishes it once from the connected project account and verifies it from the "
                  "public Bluesky index."],
        "output": "One Bluesky post published by the Agent, with its record URI, CID, public URL and "
                  "verification result in the Task.",
        "requires": "Public repository selected in Settings → Promotion, AI model and API key, and the "
                    "project's Bluesky account connected with an app password (Settings → Promotion → "
                    "Promotion Platform: Bluesky). No GitHub token is used.",
        "review": "Explicit approval of the exact post, bound to the account and links; publishing is a "
                  "separate confirmation. Any edit cancels the approval.",
        "limitations": "One post per approval, from the one connected project account; an uncertain outcome "
                       "is checked, never retried blindly. Bluesky-hosted accounts only."
    },
    "promote_social_media": {
        "goal": "Legacy: social media post drafts created before platform Work Types. Existing Tasks only.",
        "steps": ["Research the repository's real README, releases and public facts, with source links.",
                  "Plan this Work Type only (audience, value, approach, schedule, objectives).",
                  "Draft a short post (max 280 characters) and a longer post.",
                  "You review, edit and approve the exact text.",
                  "Publish it yourself, by hand, following the community-rules checklist."],
        "output": "Editable social media post drafts and a posting checklist.",
        "requires": "Public repository selected in Settings → Promotion, AI model and API key. No GitHub "
                    "token or channel account is used.",
        "review": "Explicit approval of the exact text. Approval only marks it ready; you publish it yourself.",
        "limitations": "Legacy draft only: no publisher, cannot be started. Use a platform Work Type "
                       "(Bluesky) instead."
    },
}




def task_choices(route: str, value: str) -> list[TaskDefinition]:
    """Choice route is mutually exclusive; Task definitions own both classifications."""
    if route not in ("work_type", "domain"):
        raise ToolError("Choose Work Type or Domain, not both.")
    return [d for d in available_definitions() if value and getattr(d, route) == value]


def data_directory() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return base / "GitHubCommunityAgent"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_SAFE_EVENT = re.compile(r"[a-z0-9_#:.-]{1,80}")


class Journal:
    def __init__(self, db: Path):
        self.db = db
        db.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS work (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                definition_id TEXT NOT NULL, repository TEXT NOT NULL,
                status TEXT NOT NULL, created_utc TEXT NOT NULL,
                updated_utc TEXT NOT NULL, result_json TEXT, error TEXT
            )""")
            # Backward-compatible in-place migration of existing local Work
            # history. A tombstone hides deleted items but preserves evidence.
            columns = {row[1] for row in con.execute("PRAGMA table_info(work)")}
            if "deleted_utc" not in columns:
                con.execute("ALTER TABLE work ADD COLUMN deleted_utc TEXT")
            # Append-only minimal Task activity. Older records cannot be
            # retroactively reconstructed as witnessed events.
            con.execute("""CREATE TABLE IF NOT EXISTS work_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                event TEXT NOT NULL,
                happened_utc TEXT NOT NULL,
                FOREIGN KEY(task_id) REFERENCES work(id)
            )""")

    def _connect(self):
        return sqlite3.connect(self.db, timeout=15)

    @staticmethod
    def _event(con, task_id: int, event: str, at: str):
        # Only internal event names/timestamps. Never API keys, tokens or the
        # source's arbitrary untrusted content.
        con.execute(
            "INSERT INTO work_events(task_id,event,happened_utc) VALUES (?,?,?)",
            (task_id, event, at))

    def create(self, definition_id: str, repository: str) -> int:
        now = _utc()
        with self._connect() as con:
            row = con.execute(
                "INSERT INTO work(definition_id,repository,status,created_utc,updated_utc) VALUES (?,?,?,?,?)",
                (definition_id, repository, "running", now, now))
            task_id = int(row.lastrowid)
            self._event(con, task_id, "created", now)
            return task_id

    def finish(self, task_id: int, status: str, result: dict | None = None, error: str | None = None):
        if status not in ("finished", "needs_attention", "failed"):
            raise ValueError("Invalid terminal work status.")
        with self._connect() as con:
            now = _utc()
            row = con.execute(
                "UPDATE work SET status=?, updated_utc=?, result_json=?, error=? WHERE id=? AND status='running' AND deleted_utc IS NULL",
                (status, now, json.dumps(result, ensure_ascii=False) if result is not None else None,
                 error, task_id))
            if row.rowcount == 1:
                self._event(con, task_id, "completed" if status == "finished" else status, now)

    def update_result(self, task_id: int, result: dict) -> bool:
        """Replace the stored result of a finished, non-archived Task (V2 draft regeneration)."""
        with self._connect() as con:
            row = con.execute(
                "UPDATE work SET result_json=?, updated_utc=? WHERE id=? AND status!='running' AND deleted_utc IS NULL",
                (json.dumps(result, ensure_ascii=False), _utc(), task_id))
            return row.rowcount == 1

    def record_event(self, task_id: int, event: str) -> bool:
        """Add one Activity History entry for an existing, non-archived Task.

        Only fixed internal event codes (e.g. "change#3:apply_refused:permission");
        never error text, tokens or other untrusted content."""
        if not isinstance(event, str) or not _SAFE_EVENT.fullmatch(event):
            raise ValueError("Invalid activity event name.")
        with self._connect() as con:
            if not con.execute("SELECT 1 FROM work WHERE id=? AND deleted_utc IS NULL", (task_id,)).fetchone():
                return False
            self._event(con, task_id, event, _utc())
            return True

    def review(self, task_id: int) -> bool:
        with self._connect() as con:
            now = _utc()
            result = con.execute("UPDATE work SET status='finished', updated_utc=? "
                                 "WHERE id=? AND status='needs_attention' AND deleted_utc IS NULL", (now, task_id))
            if result.rowcount == 1:
                self._event(con, task_id, "marked_reviewed_locally", now)
            return result.rowcount == 1

    def delete(self, task_id: int) -> bool:
        """Soft-delete an inactive record; never delete running or pending work.

        Retain a tombstone for history/audit; no GitHub API or filesystem action.
        """
        if type(task_id) is not int or task_id < 1:
            return False
        with self._connect() as con:
            now = _utc()
            row = con.execute(
                "UPDATE work SET deleted_utc=? WHERE id=? AND deleted_utc IS NULL "
                "AND status IN ('finished','failed')",
                (now, task_id))
            if row.rowcount == 1:
                self._event(con, task_id, "archived", now)
            return row.rowcount == 1

    def get(self, task_id: int) -> dict | None:
        """One Work record (including archived), with its parsed result."""
        if type(task_id) is not int or task_id < 1:
            return None
        with self._connect() as con:
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM work WHERE id=?", (task_id,)).fetchone()
        if not row:
            return None
        record = dict(row)
        record["result"] = json.loads(record.pop("result_json")) if record["result_json"] else None
        return record

    def list(self, include_archived: bool = False) -> list[dict]:
        with self._connect() as con:
            con.row_factory = sqlite3.Row
            where = "" if include_archived else "WHERE deleted_utc IS NULL"
            rows = con.execute(f"SELECT * FROM work {where} ORDER BY id DESC LIMIT 200").fetchall()
            ids = [row["id"] for row in rows]
            events = {}
            if ids:
                marks = ",".join("?" for _ in ids)
                for e in con.execute(
                    f"SELECT task_id,event,happened_utc FROM work_events WHERE task_id IN ({marks}) ORDER BY id",
                    ids):
                    events.setdefault(e["task_id"], []).append(
                        {"event": e["event"], "at_utc": e["happened_utc"]})
        output = []
        for row in rows:
            record = dict(row)
            definition = BY_ID.get(record["definition_id"])
            record["title"] = definition.title if definition else record["definition_id"]
            record["classifications"] = (
                {"work_type": definition.work_type, "domain": definition.domain}
                if definition else {})
            record["version"] = definition.version if definition else "unknown"
            record["result"] = json.loads(record.pop("result_json")) if record["result_json"] else None
            record["archived"] = record["deleted_utc"] is not None
            record["activity"] = events.get(record["id"], [])
            output.append(record)
        return output


class WorkService:
    def __init__(self, journal: Journal, promotion=None):
        self.journal = journal
        self.promotion = promotion  # the ONE V2 Promotion Agent (promotion.PromotionService)

    def definitions(self) -> list[dict]:
        return [{**asdict(d), "details": TASK_DETAILS[d.id]} for d in available_definitions()]

    def start(self, payload: dict) -> int:
        """Create a real Work record then launch one existing production workflow."""
        route = payload.get("route")
        selected = payload.get("selection")
        definition_id = payload.get("definition_id")
        definition = BY_ID.get(definition_id)
        if (not definition or not definition.enabled
                or definition not in task_choices(route, selected)):
            raise ToolError("Task must match the selected Work Type OR Domain.")
        if definition.workflow == "promotion":
            # V2: the repository comes from Settings → Promotion (bound at creation);
            # the AI model is the app's shared provider configuration.
            if self.promotion is None:
                raise ToolError("Promotion is not available in this session.")
            model_key = payload.get("model_key")
            if not isinstance(model_key, str) or not model_key:
                raise ToolError("Model API key must be provided for this run.")
            settings = ModelSettings(payload.get("provider"), payload.get("model_name"))
            return self.promotion.start(ChatCompletionsModel(settings, api_key=lambda: model_key), definition.id)
        repository = payload.get("repository", "")
        provider = payload.get("provider")
        model_name = payload.get("model_name")
        model_key = payload.get("model_key")
        discussion_token = payload.get("discussion_token") or ""
        target = "discussion" if definition_id == "draft_discussion" else "issue"
        number = payload.get("number")
        if definition.workflow == "draft_replies":
            if type(number) is not int or number <= 0:
                raise ToolError("A positive Issue/Discussion number is required.")
        if not isinstance(model_key, str) or not model_key:
            raise ToolError("Model API key must be provided for this run.")
        # Validate user-supplied settings BEFORE creating a work record.
        from .runtime import CommunitySettings
        CommunitySettings(repository)
        ModelSettings(provider, model_name)
        task_id = self.journal.create(definition_id, repository)
        args = dict(repository=repository, workflow=definition.workflow, provider=provider,
                    model_name=model_name, model_key=model_key, discussion_token=discussion_token,
                    target=target, number=number)
        threading.Thread(target=self._run, args=(task_id, definition_id, args), daemon=True).start()
        return task_id

    def _run(self, task_id: int, definition_id: str, args: dict):
        try:
            result = execute_workflow(**args)
            status = "needs_attention" if definition_id.startswith("draft_") else "finished"
            self.journal.finish(task_id, status, result=result)
        except ToolError as exc:
            self.journal.finish(task_id, "failed", error=str(exc)[:300])
        except Exception:
            self.journal.finish(task_id, "failed", error="Execution failed; inspect application settings.")


MAX_PROMOTION_REQUEST_BYTES = 200000  # an edited announcement or README (V2 promotion routes only)


def _change_route(path: str):
    """Parse /api/promotion/tasks/<id>/changes/<cid>/<verb>; None otherwise."""
    parts = path.strip("/").split("/")
    if (len(parts) == 7 and parts[:3] == ["api", "promotion", "tasks"] and parts[3].isdigit()
            and parts[4] == "changes" and parts[5].isdigit()):
        return int(parts[3]), int(parts[5]), parts[6]
    return None


def _promotion_route(path: str):
    """Parse /api/promotion/tasks/<id>[/actions/<aid>]/<verb>; None if not a promotion route."""
    parts = path.strip("/").split("/")
    if parts[:3] != ["api", "promotion", "tasks"] or len(parts) < 5 or not parts[3].isdigit():
        return None
    task_id = int(parts[3])
    if len(parts) == 5:
        return task_id, None, parts[4]
    if len(parts) == 7 and parts[4] == "actions" and parts[5].isdigit():
        return task_id, int(parts[5]), parts[6]
    return None


def handler_factory(service: WorkService, nonce: str, settings: EncryptedSettings | None = None,
                    promotion_credentials=None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "GitHubCommunityAgent/0.1"

        def log_message(self, format, *args):
            # Disable request logging (never log posted request content or credentials).
            return

        def _send(self, status: int, obj: dict | list):
            raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _authorized(self) -> bool:
            # Browsers from foreign origins cannot trigger even loopback actions.
            origin = self.headers.get("Origin")
            return (self.headers.get("X-App-Nonce") == nonce and
                    origin == f"http://127.0.0.1:{self.server.server_port}" and
                    self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}")

        def do_GET(self):
            path = urlsplit(self.path).path
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                return self._send(403, {"error": "Invalid host."})
            if path in ("/static/worker_v011.css", "/static/gc.css"):
                name = path.removeprefix("/static/")
                raw = (Path(__file__).parent / name).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/css; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                return self.wfile.write(raw)
            if path == "/":
                html = (Path(__file__).parent / "home.html").read_text(encoding="utf-8")
                html = html.replace("__APP_NONCE__", nonce)
                raw = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'nonce-" + nonce +
                                 "'; style-src 'self' 'nonce-" + nonce + "'; connect-src 'self'; "
                                 "img-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                return self.wfile.write(raw)
            if path == "/api/settings":
                if self.headers.get("X-App-Nonce") != nonce:
                    return self._send(403, {"error": "Unauthorized."})
                if settings is None:
                    return self._send(503, {"error": "Settings storage unavailable."})
                try:
                    return self._send(200, settings.public())
                except SettingsError:
                    return self._send(503, {"error": "Cannot read protected settings."})
            if path == "/api/definitions":
                return self._send(200, {"definitions": service.definitions()})
            if path == "/api/tasks":
                if self.headers.get("X-App-Nonce") != nonce:
                    return self._send(403, {"error": "Unauthorized."})
                include_archived = urlsplit(self.path).query == "include_archived=1"
                return self._send(200, {"tasks": service.journal.list(include_archived=include_archived)})
            if path.startswith("/api/promotion/"):
                if self.headers.get("X-App-Nonce") != nonce:
                    return self._send(403, {"error": "Unauthorized."})
                if service.promotion is None or promotion_credentials is None:
                    return self._send(503, {"error": "Promotion is not available."})
                try:
                    if path == "/api/promotion/settings":
                        return self._send(200, promotion_credentials.public())
                    if path == "/api/promotion/bluesky":  # public account facts only; never the app password
                        return self._send(200, service.promotion.bluesky_account())
                    route = _promotion_route(path)
                    if route and route[1] is None and route[2] == "detail":
                        return self._send(200, service.promotion.detail(route[0]))
                except SettingsError:
                    return self._send(503, {"error": "Cannot read protected promotion settings."})
                except ToolError as exc:
                    return self._send(404, {"error": str(exc)[:300]})
            return self._send(404, {"error": "Not found."})

        def _promotion_model(self):
            saved = settings.load() if settings is not None else {}
            key = saved.get("model_key")
            if not key:
                raise ToolError("Configure an AI model and API key in Settings first.")
            return ChatCompletionsModel(ModelSettings(saved["provider"], saved["model"]), api_key=lambda: key)

        def _promotion_post(self, path: str, payload: dict):
            promo = service.promotion
            if promo is None or promotion_credentials is None:
                return self._send(503, {"error": "Promotion is not available."})
            try:
                if path == "/api/promotion/settings":
                    return self._send(200, promotion_credentials.update(
                        payload.get("repository"), payload.get("token") or "",
                        payload.get("remove_token") is True))
                if path == "/api/promotion/bluesky":
                    if payload.get("remove") is True:
                        return self._send(200, promo.bluesky_disconnect())
                    return self._send(200, promo.bluesky_connect(payload.get("handle"), payload.get("app_password")))
                change = _change_route(path)
                if change:
                    task_id, change_id, verb = change
                    if verb == "edit":
                        promo.edit_change(task_id, change_id, payload.get("value"))
                        return self._send(200, {"ok": True})
                    if verb == "skip":
                        promo.skip_change(task_id, change_id)
                        return self._send(200, {"ok": True})
                    if verb == "approve":
                        return self._send(200, {"ok": True, "approved_sha256":
                                                promo.approve_change(task_id, change_id, payload.get("sha256"))})
                    if verb == "apply":
                        return self._send(200, promo.apply_change(task_id, change_id, payload.get("sha256")))
                    if verb == "verify":
                        return self._send(200, promo.verify_change(task_id, change_id))
                    return self._send(404, {"error": "Not found."})
                route = _promotion_route(path)
                if not route:
                    return self._send(404, {"error": "Not found."})
                task_id, action_id, verb = route
                if action_id is None:
                    if verb == "improve":
                        return self._send(200, {"improvement": promo.improve(task_id, self._promotion_model())})
                    return self._send(404, {"error": "Not found."})
                if verb == "regenerate":
                    return self._send(200, promo.regenerate(task_id, action_id, self._promotion_model()))
                if verb == "edit":
                    promo.edit(task_id, action_id, payload.get("title"), payload.get("body"))
                    return self._send(200, {"ok": True})
                if verb == "preflight":
                    return self._send(200, promo.preflight(task_id, action_id))
                if verb == "approve":
                    approved = promo.approve(task_id, action_id, payload.get("category"), payload.get("sha256"))
                    return self._send(200, {"ok": True, "status": "approved", "approved_sha256": approved})
                if verb == "publish":
                    return self._send(200, promo.publish(task_id, action_id, payload.get("sha256")))
                if verb == "bluesky_approve":
                    return self._send(200, promo.bluesky_approve(task_id, action_id, payload.get("sha256")))
                if verb == "bluesky_publish":
                    return self._send(200, promo.bluesky_publish(task_id, action_id, payload.get("sha256")))
                if verb == "bluesky_reconcile":
                    return self._send(200, promo.bluesky_reconcile(task_id, action_id))
                if verb == "bluesky_verify":
                    return self._send(200, promo.bluesky_verify(task_id, action_id))
                if verb == "record_publication":
                    return self._send(200, promo.record_manual_publication(
                        task_id, action_id, payload.get("url"), payload.get("confirmed"), payload.get("sha256")))
                if verb == "verify_publication":
                    return self._send(200, promo.verify_manual_publication(task_id, action_id))
                if verb == "reconcile":
                    return self._send(200, promo.reconcile(task_id, action_id))
                if verb == "monitor":
                    return self._send(200, promo.monitor(task_id, action_id))
                return self._send(404, {"error": "Not found."})
            except (ToolError, SettingsError) as exc:
                # Our own fixed messages (repository names, permission facts); never credentials.
                return self._send(400, {"error": str(exc)[:300]})

        def _discard_body(self) -> None:
            # Consume a small unread request body before replying, so Windows
            # does not reset the connection (unread receive data -> RST) and
            # the client reliably receives the error status. Never processed.
            self.close_connection = True
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return
            # Hard cap: a huge declared length is never read; that connection
            # is simply closed after the reply.
            if 0 < n <= MAX_DISCARD_BYTES:
                try:
                    self.connection.settimeout(5)  # never wait on a stalled client
                    self.rfile.read(n)
                except OSError:
                    pass

        def do_POST(self):
            if not self._authorized():
                self._discard_body()
                return self._send(403, {"error": "Unauthorized."})
            try:
                path = urlsplit(self.path).path
                limit = MAX_PROMOTION_REQUEST_BYTES if path.startswith("/api/promotion/") else MAX_REQUEST_BYTES
                n = int(self.headers.get("Content-Length", "0"))
                if n < 2 or n > limit:
                    self._discard_body()
                    return self._send(413, {"error": "Invalid request size."})
                payload = json.loads(self.rfile.read(n))
                if not isinstance(payload, dict):
                    return self._send(400, {"error": "Expected a JSON object."})
                if path.startswith("/api/promotion/"):
                    return self._promotion_post(path, payload)
                if path == "/api/settings":
                    if settings is None:
                        return self._send(503, {"error": "Settings storage unavailable."})
                    return self._send(200, settings.save(payload))
                if path == "/api/test-connection":
                    provider = payload.get("provider")
                    model_name = payload.get("model_name")
                    model_key = payload.get("model_key")
                    if not model_key and settings is not None:
                        saved = settings.load()
                        if provider == saved["provider"]:
                            model_key = saved["model_key"]
                    if not isinstance(model_key, str) or not model_key:
                        return self._send(400, {"error": "Enter a model API key."})
                    model = ChatCompletionsModel(
                        ModelSettings(provider, model_name), api_key=lambda: model_key
                    )
                    answer = model(
                        "This is a model-connection verification. Reply with the exact word OK.",
                        "Connection test; no GitHub content or data.",
                    )
                    return self._send(200, {
                        "status": "connected" if answer.strip() else "failed",
                        "note": "Live model request completed; no GitHub operation."
                    })
                if path == "/api/tasks":
                    if settings is None:
                        return self._send(503, {"error": "Settings storage unavailable."})
                    saved = settings.load()
                    payload = {**payload, "repository": saved["repository"],
                               "provider": saved["provider"], "model_name": saved["model"],
                               "model_key": saved["model_key"],
                               "discussion_token": saved["read_token"]}
                    task_id = service.start(payload)
                    return self._send(202, {"id": task_id, "status": "running"})
                if path.startswith("/api/tasks/") and path.endswith("/delete"):
                    parts = path.split("/")
                    if len(parts) != 5 or not parts[3].isdigit():
                        return self._send(404, {"error": "Not found."})
                    task_id = int(parts[3])
                    if service.journal.delete(task_id):
                        return self._send(200, {"id": task_id, "deleted": True,
                                                "scope": "local_work_only"})
                    return self._send(409, {
                        "error": "Only finished or failed tasks can be deleted."
                    })
                if path.startswith("/api/tasks/") and path.endswith("/review"):
                    task_id = int(path.split("/")[3])
                    if task_id > 0 and service.journal.review(task_id):
                        return self._send(200, {"id": task_id, "status": "finished", "posted": False})
                    return self._send(409, {"error": "Task does not need review."})
                return self._send(404, {"error": "Not found."})
            except (ToolError, SettingsError, ValueError, TypeError):
                # Do not echo input, secrets, or exception payload.
                return self._send(400, {"error": "Invalid task selection or connection settings."})

    return Handler


def main() -> int:
    from .bluesky import BlueskyCredentials
    from .promotion import PromotionCredentials, PromotionService, PromotionStore
    journal = Journal(data_directory() / "work.sqlite3")
    credentials = PromotionCredentials(data_directory())
    promotion = PromotionService(journal, PromotionStore(data_directory() / "work.sqlite3"), credentials,
                                 BlueskyCredentials(data_directory()))  # its own DPAPI file
    service = WorkService(journal, promotion)
    settings = EncryptedSettings(data_directory())
    nonce = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(service, nonce, settings, credentials))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"GitHub Community Agent Work Center: {url}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
