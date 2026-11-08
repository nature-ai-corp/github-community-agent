"""Independent, loopback-only Work Center with dynamic product Task definitions.

Task entry selects ONE taxonomy route (Work Type OR Domain) before choosing
a definition. This app is not a NATURE AI Platform Task engine. Credential
material stays in the request/worker memory, never the SQLite work journal.
"""
from __future__ import annotations

import json
import os
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
from .errors import ToolError

MAX_REQUEST_BYTES = 12000


@dataclass(frozen=True)
class TaskDefinition:
    id: str
    title: str
    work_type: str
    domain: str
    workflow: str | None
    version: str
    enabled: bool


# Work Type is the V1 Community Management entry route. Domain is the
# V2 promotion target taxonomy, not Issues/Discussions task operations.
# An empty domain means this product task does not use a Domain classification.
DEFINITIONS = (
    TaskDefinition("review_issues", "Review Issues", "Community Management", "", "review_issues", "V1", True),
    TaskDefinition("review_discussions", "Review Discussions", "Community Management", "", "review_discussions", "V1", True),
    TaskDefinition("draft_issue", "Draft Issue Reply", "Community Management", "", "draft_replies", "V1", True),
    TaskDefinition("draft_discussion", "Draft Discussion Reply", "Community Management", "", "draft_replies", "V1", True),
    TaskDefinition("community_report", "Community Report", "Community Management", "", "community_report", "V1", True),
    TaskDefinition("promote_self", "Promote GitHub Community Agent", "Product Promotion", "Self-Promotion", None, "V2", False),
    TaskDefinition("promote_worker", "Promote Nature AI Worker", "Product Promotion", "Product Promotion", None, "V2", False),
    TaskDefinition("promote_other", "Promote Other Repository", "Product Promotion", "Product Promotion", None, "V2", False),
)
BY_ID = {d.id: d for d in DEFINITIONS}


def task_choices(route: str, value: str) -> list[TaskDefinition]:
    """Choice route is mutually exclusive; Task definitions own both classifications."""
    if route not in ("work_type", "domain"):
        raise ToolError("Choose Work Type or Domain, not both.")
    return [d for d in DEFINITIONS if value and getattr(d, route) == value]


def data_directory() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return base / "GitHubCommunityAgent"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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

    def _connect(self):
        return sqlite3.connect(self.db, timeout=15)

    def create(self, definition_id: str, repository: str) -> int:
        now = _utc()
        with self._connect() as con:
            row = con.execute(
                "INSERT INTO work(definition_id,repository,status,created_utc,updated_utc) VALUES (?,?,?,?,?)",
                (definition_id, repository, "running", now, now))
            return int(row.lastrowid)

    def finish(self, task_id: int, status: str, result: dict | None = None, error: str | None = None):
        if status not in ("finished", "needs_attention", "failed"):
            raise ValueError("Invalid terminal work status.")
        with self._connect() as con:
            con.execute(
                "UPDATE work SET status=?, updated_utc=?, result_json=?, error=? WHERE id=? AND status='running'",
                (status, _utc(), json.dumps(result, ensure_ascii=False) if result is not None else None,
                 error, task_id))

    def review(self, task_id: int) -> bool:
        with self._connect() as con:
            result = con.execute("UPDATE work SET status='finished', updated_utc=? "
                                 "WHERE id=? AND status='needs_attention'", (_utc(), task_id))
            return result.rowcount == 1

    def list(self) -> list[dict]:
        with self._connect() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM work ORDER BY id DESC LIMIT 200").fetchall()
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
            output.append(record)
        return output


class WorkService:
    def __init__(self, journal: Journal):
        self.journal = journal

    def definitions(self) -> list[dict]:
        return [asdict(d) for d in DEFINITIONS]

    def start(self, payload: dict) -> int:
        """Create a real Work record then launch one existing production workflow."""
        route = payload.get("route")
        selected = payload.get("selection")
        definition_id = payload.get("definition_id")
        definition = BY_ID.get(definition_id)
        if (not definition or not definition.enabled
                or definition not in task_choices(route, selected)):
            raise ToolError("Task must match the selected Work Type OR Domain.")
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
        from .model_provider import ModelSettings
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


def handler_factory(service: WorkService, nonce: str):
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
            if path == "/":
                html = (Path(__file__).parent / "home.html").read_text(encoding="utf-8")
                html = html.replace("__APP_NONCE__", nonce)
                raw = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'nonce-" + nonce +
                                 "'; style-src 'nonce-" + nonce + "'; connect-src 'self'; "
                                 "img-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                return self.wfile.write(raw)
            if path == "/api/definitions":
                return self._send(200, {"definitions": service.definitions()})
            if path == "/api/tasks":
                if self.headers.get("X-App-Nonce") != nonce:
                    return self._send(403, {"error": "Unauthorized."})
                return self._send(200, {"tasks": service.journal.list()})
            return self._send(404, {"error": "Not found."})

        def do_POST(self):
            if not self._authorized():
                return self._send(403, {"error": "Unauthorized."})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n < 2 or n > MAX_REQUEST_BYTES:
                    return self._send(413, {"error": "Invalid request size."})
                payload = json.loads(self.rfile.read(n))
                if not isinstance(payload, dict):
                    return self._send(400, {"error": "Expected a JSON object."})
                path = urlsplit(self.path).path
                if path == "/api/tasks":
                    task_id = service.start(payload)
                    return self._send(202, {"id": task_id, "status": "running"})
                if path.startswith("/api/tasks/") and path.endswith("/review"):
                    task_id = int(path.split("/")[3])
                    if task_id > 0 and service.journal.review(task_id):
                        return self._send(200, {"id": task_id, "status": "finished", "posted": False})
                    return self._send(409, {"error": "Task does not need review."})
                return self._send(404, {"error": "Not found."})
            except (ToolError, ValueError, TypeError):
                # Do not echo input, secrets, or exception payload.
                return self._send(400, {"error": "Invalid task selection or settings."})

    return Handler


def main() -> int:
    journal = Journal(data_directory() / "work.sqlite3")
    service = WorkService(journal)
    nonce = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(service, nonce))
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
