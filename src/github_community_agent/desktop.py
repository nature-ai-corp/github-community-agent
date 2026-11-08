"""Independent Windows-first desktop UI for the real read-only application runtime.

Tkinter uses the Python standard library. Credentials exist only in UI memory;
none are persisted, logged, exported, or sent to GitHub issue content/model text.
Each workflow executes the actual GitHub + model adapters, not mock/demo data.
"""
from __future__ import annotations

import json
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, TOP, VERTICAL, W, X, BooleanVar, StringVar, Tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .ai_review import CommunityAnalyst
from .discussion_review import review_discussions
from .errors import ToolError
from .model_provider import ChatCompletionsModel, ModelSettings
from .runtime import CommunityRuntime, CommunitySettings

WORKFLOWS = {
    "Review Issues": "review_issues",
    "Review Discussions": "review_discussions",
    "Draft Replies": "draft_replies",
    "Community Report": "community_report",
}


def execute_workflow(repository: str, workflow: str, *, provider: str,
                     model_name: str, model_key: str,
                     discussion_token: str = "", target: str = "issue",
                     number: int | None = None) -> dict:
    """One real request from UI. Secret values are not returned in the result."""
    if workflow not in WORKFLOWS.values():
        raise ToolError("Unsupported community workflow.")
    settings = CommunitySettings(repository.strip())
    model_settings = ModelSettings(provider, model_name.strip())
    if not model_key:
        raise ToolError("Enter a model API key in Settings for this session.")
    model = ChatCompletionsModel(model_settings, api_key=lambda: model_key)
    runtime = CommunityRuntime(settings,
                               discussion_token=lambda: discussion_token or None,
                               model=model)
    if workflow == "review_discussions":
        result = review_discussions(runtime, model)
    elif workflow in ("review_issues", "community_report"):
        result = CommunityAnalyst(runtime, model).run(workflow)
    else:
        result = runtime.run("draft_replies", target=target, number=number)
    if result.get("posted") is not False or result.get("read_only") is not True:
        raise ToolError("Workflow did not confirm read-only execution.")
    return result


def evidence_record(result: dict, *, started_at: str, completed_at: str) -> dict:
    """Build app-generated provenance; never include credentials/config secrets."""
    if not isinstance(result, dict) or result.get("read_only") is not True or result.get("posted") is not False:
        raise ToolError("Cannot export unverified workflow evidence.")
    return {
        "application": "GitHub Community Agent",
        "evidence_schema": 1,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "source": "Actual application workflow invocation (not an automated test)",
        "human_review_required": True,
        "result": result,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CommunityDesktop:
    def __init__(self, root: Tk):
        self.root = root
        root.title("GitHub Community Agent — V1 Preview (Read Only)")
        root.geometry("990x780")
        root.minsize(760, 600)
        self.repo = StringVar(value="")
        self.provider = StringVar(value="openai")
        self.model_name = StringVar(value="gpt-4.1-mini")
        self.workflow = StringVar(value="Review Issues")
        self.target = StringVar(value="issue")
        self.number = StringVar(value="")
        self.model_key = StringVar(value="")
        self.github_token = StringVar(value="")
        self.status = StringVar(value="Configure a public repository and your model key to begin.")
        self.last_evidence: dict | None = None
        self.busy = False
        self.messages: queue.SimpleQueue = queue.SimpleQueue()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._build()
        self.root.after(100, self._drain)

    def _build(self):
        wrapper = ttk.Frame(self.root, padding=16)
        wrapper.pack(fill=BOTH, expand=True)
        ttk.Label(wrapper, text="GitHub Community Agent", font=("Segoe UI", 20, "bold")).pack(anchor=W)
        ttk.Label(wrapper, text="Independent desktop preview • Real GitHub & AI • Read only • No posting").pack(anchor=W, pady=(0, 12))

        settings = ttk.LabelFrame(wrapper, text="Connection settings (session-only, never saved)", padding=10)
        settings.pack(fill=X)
        ttk.Label(settings, text="Public repository (owner/name)").grid(row=0, column=0, sticky=W)
        ttk.Entry(settings, textvariable=self.repo, width=37).grid(row=1, column=0, padx=(0, 10), sticky="ew")
        ttk.Label(settings, text="Provider").grid(row=0, column=1, sticky=W)
        ttk.Combobox(settings, textvariable=self.provider, values=("openai", "deepseek"), state="readonly", width=13).grid(row=1, column=1, padx=(0, 10))
        ttk.Label(settings, text="Model").grid(row=0, column=2, sticky=W)
        ttk.Entry(settings, textvariable=self.model_name, width=23).grid(row=1, column=2, sticky="ew")
        ttk.Label(settings, text="Model API Key (memory only)").grid(row=2, column=0, sticky=W, pady=(10, 0))
        ttk.Entry(settings, textvariable=self.model_key, show="•").grid(row=3, column=0, padx=(0, 10), sticky="ew")
        ttk.Label(settings, text="GitHub Discussions READ Token (optional)").grid(row=2, column=1, columnspan=2, sticky=W, pady=(10, 0))
        ttk.Entry(settings, textvariable=self.github_token, show="•").grid(row=3, column=1, columnspan=2, sticky="ew")
        settings.columnconfigure(0, weight=3)
        settings.columnconfigure(2, weight=2)

        actions = ttk.LabelFrame(wrapper, text="Workflow — real application execution", padding=10)
        actions.pack(fill=X, pady=12)
        ttk.Label(actions, text="Workflow").grid(row=0, column=0, sticky=W)
        ttk.Combobox(actions, textvariable=self.workflow, values=tuple(WORKFLOWS),
                     width=22, state="readonly").grid(row=1, column=0, padx=(0, 10), sticky=W)
        ttk.Label(actions, text="Draft target").grid(row=0, column=1, sticky=W)
        ttk.Combobox(actions, textvariable=self.target, values=("issue", "discussion"),
                     state="readonly", width=14).grid(row=1, column=1, padx=(0, 10))
        ttk.Label(actions, text="Draft Issue/Discussion #").grid(row=0, column=2, sticky=W)
        ttk.Entry(actions, textvariable=self.number, width=12).grid(row=1, column=2, padx=(0, 10))
        self.run_button = ttk.Button(actions, text="Run real workflow", command=self._run)
        self.run_button.grid(row=1, column=3, padx=(10, 0))
        self.save_button = ttk.Button(actions, text="Export evidence…", command=self._export,
                                      state="disabled")
        self.save_button.grid(row=1, column=4, padx=(10, 0))
        ttk.Label(wrapper, textvariable=self.status, wraplength=900).pack(anchor=W, pady=(0, 8))

        ttk.Label(wrapper, text="Application-generated results and source references").pack(anchor=W)
        self.output = scrolledtext.ScrolledText(wrapper, wrap="word", font=("Consolas", 10))
        self.output.pack(fill=BOTH, expand=True)
        self.output.insert("1.0", "No workflow has run. Configure settings, select an action, and click Run real workflow.")
        self.output.configure(state="disabled")
        ttk.Label(wrapper, text="Human review required. All GitHub source text is untrusted; do not treat AI suggestions as verified facts.").pack(anchor=W, pady=(8, 0))

    def _run(self):
        if self.busy:
            return
        label = self.workflow.get()
        workflow = WORKFLOWS.get(label)
        if not workflow:
            messagebox.showerror("Invalid workflow", "Select a supported workflow.")
            return
        if workflow == "review_discussions" and not self.github_token.get():
            messagebox.showerror("GitHub token required", "Enter a dedicated Discussions read-only token.")
            return
        number = None
        if workflow == "draft_replies":
            try:
                number = int(self.number.get())
                if number <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Invalid item", "Enter a positive GitHub Issue/Discussion number.")
                return
        self.last_evidence = None
        self.save_button.configure(state="disabled")
        self.run_button.configure(state="disabled")
        self.busy = True
        started_at = _now()
        self.status.set(f"Running {label}: real GitHub read and selected model request…")
        kwargs = {
            "repository": self.repo.get(), "workflow": workflow,
            "provider": self.provider.get(), "model_name": self.model_name.get(),
            "model_key": self.model_key.get(), "discussion_token": self.github_token.get(),
            "target": self.target.get(), "number": number,
        }
        thread = threading.Thread(target=self._worker, args=(kwargs, started_at), daemon=True)
        thread.start()

    def _worker(self, kwargs: dict, started_at: str):
        try:
            result = execute_workflow(**kwargs)
            record = evidence_record(result, started_at=started_at, completed_at=_now())
            self.messages.put(("success", record))
        except ToolError as exc:
            self.messages.put(("error", str(exc)))
        except Exception:
            # Do not render exception bodies: upstream errors may contain secrets.
            self.messages.put(("error", "Workflow failed. Check repository access and model settings."))

    def _drain(self):
        try:
            while True:
                kind, value = self.messages.get_nowait()
                self.busy = False
                self.run_button.configure(state="normal")
                if kind == "success":
                    self.last_evidence = value
                    self.save_button.configure(state="normal")
                    self.status.set("Completed. No GitHub changes made. Verify sources and export evidence if needed.")
                    self._show(json.dumps(value, indent=2, ensure_ascii=False))
                else:
                    self.last_evidence = None
                    self.status.set("Workflow did not complete.")
                    self._show("ERROR: " + value)
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(100, self._drain)

    def _show(self, text: str):
        self.output.configure(state="normal")
        self.output.delete("1.0", END)
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _export(self):
        if self.last_evidence is None:
            return
        path = filedialog.asksaveasfilename(
            title="Export this run's evidence (may contain public GitHub content)",
            defaultextension=".json",
            filetypes=(("JSON", "*.json"),),
            initialfile="github-community-agent-evidence.json",
        )
        if not path:
            return
        try:
            # Do not automatically choose a path or silently overwrite user files.
            with Path(path).open("x", encoding="utf-8") as file:
                json.dump(self.last_evidence, file, indent=2, ensure_ascii=False)
                file.write("\n")
        except FileExistsError:
            messagebox.showerror("Already exists", "Choose a new filename; evidence is never overwritten.")
            return
        except OSError:
            messagebox.showerror("Export failed", "Unable to save evidence at the selected location.")
            return
        self.status.set("Evidence exported to the path you selected (no API keys included).")

    def _close(self):
        # Erase credentials from widgets and Python-held variables; no persistence.
        self.model_key.set("")
        self.github_token.set("")
        self.root.destroy()


def main() -> int:
    root = Tk()
    CommunityDesktop(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
