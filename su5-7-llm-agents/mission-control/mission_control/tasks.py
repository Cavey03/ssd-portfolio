"""Dispatched tasks: one AI worker, one git worktree, one review, then merge or discard.

Life of a task:
  1. planned   the orchestrator (or the owner) chose a worker and wrote its brief
  2. running   a detached supervisor process (`python -m mission_control task _run <id>`)
               created a git worktree and runs the worker in it, inside the `dev`
               container, with a time limit
  3. done / failed / timeout
               the supervisor recorded the changes (files, diff) and asked the
               orchestrator for a review
  4. merged / discarded
               the owner decided: merge commits the worktree and merges its branch
               into the main checkout; discard deletes worktree and branch

Each task lives in its own folder under ~/.local/state/mission-control/tasks/<id>/:
task.json (the record), worker.log, diff.patch and last-message.txt. The
supervisor runs on its own, so tasks keep going when Mission Control is closed.
"""

from __future__ import annotations

import json
import os
import secrets
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from mission_control.containers import current_container_name
from mission_control.agents import profile_model
from mission_control.localllm import read_ollama
from mission_control.orchestrator import OrchestratorError, Plan, Review, plan_task, review_task
from mission_control.worktrees import (
    Workspace, WorkspaceError, commit_all, create_workspace, merge_into_main, remove_workspace,
    summarize_changes,
)

STATE_DIR = Path(
    os.environ.get("MISSION_CONTROL_STATE", Path.home() / ".local" / "state" / "mission-control")
)
DECISIONS_FILE = "decisions.jsonl"
GRACE_SECONDS = 60
"""Extra time after the worker's limit before the supervisor kills it itself."""
ACTIVE = ("planned", "running")
FINISHED = ("done", "failed", "timeout")
CLOSED = ("merged", "discarded")

WORKER_RULES = """

Rules for this run:
- You work unattended in a separate git worktree of the project; nobody can answer questions.
- Change only files inside this project folder. Do NOT commit and do NOT push.
- Run the project's tests if it has any, and fix what fails.
- Finish with a short summary of what you changed and the test result."""


@dataclass
class Task:
    """One dispatched task (saved as task.json)."""

    id: str
    title: str
    project: str
    """Absolute path of the project folder (in the main checkout)."""
    agent: str
    """"local", "codex" or "claude"."""
    model: str | None
    brief: str
    reason: str
    time_limit: int
    """Seconds."""
    status: str = "planned"
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None
    exit_code: int | None = None
    workspace: dict[str, str] | None = None
    files: list[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    review: dict[str, object] | None = None
    error: str | None = None
    pid: int | None = None
    """Supervisor process id while running."""

    @property
    def folder(self) -> Path:
        return tasks_dir() / self.id

    @property
    def ws(self) -> Workspace | None:
        return Workspace.from_dict(self.workspace) if self.workspace else None

    @property
    def review_obj(self) -> Review | None:
        return Review.from_dict(self.review) if self.review else None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Task:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})  # type: ignore[arg-type]


def tasks_dir() -> Path:
    """Folder holding one sub-folder per task."""
    return STATE_DIR / "tasks"


def new_task_id(now: float | None = None) -> str:
    """A sortable, readable id that is also a valid branch name: 20261118-1342-a1b2."""
    stamp = time.strftime("%Y%m%d-%H%M", time.localtime(now or time.time()))
    return f"{stamp}-{secrets.token_hex(2)}"


def save_task(task: Task) -> None:
    """Write task.json atomically (write a temp file, then rename), so readers never see half a file."""
    task.folder.mkdir(parents=True, exist_ok=True)
    tmp = task.folder / "task.json.tmp"
    tmp.write_text(json.dumps(asdict(task), indent=2))
    os.replace(tmp, task.folder / "task.json")


def load_task(task_id: str) -> Task:
    """Read one task; FileNotFoundError if it doesn't exist."""
    return Task.from_dict(json.loads((tasks_dir() / task_id / "task.json").read_text()))


def list_tasks(limit: int = 30) -> list[Task]:
    """The newest tasks first. Unreadable records are skipped."""
    try:
        folders = sorted(tasks_dir().iterdir(), reverse=True)
    except OSError:
        return []
    found: list[Task] = []
    for folder in folders:
        try:
            found.append(Task.from_dict(json.loads((folder / "task.json").read_text())))
        except (OSError, ValueError, TypeError):
            continue
        if len(found) >= limit:
            break
    return found


def log_decision(record: dict[str, object]) -> None:
    """Append one routing decision to decisions.jsonl (transparency only; never training data)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with (STATE_DIR / DECISIONS_FILE).open("a") as f:
        f.write(json.dumps({"time": time.time(), **record}) + "\n")


def venv_hint(project_dir: Path) -> str:
    """Tell the worker about the project's Python venv: worktrees don't have one (it's gitignored)."""
    python = project_dir / ".venv" / "bin" / "python"
    if not python.exists():
        return ""
    return (f"\n- The project's Python environment is NOT in the worktree. Run Python and tests with "
            f"{python} (it imports the worktree's code when run from here). Don't modify it.")


def worker_command(task: Task, workdir: Path, last_message: Path) -> list[str]:
    """The agent's command line for an unattended run in `workdir`."""
    prompt = task.brief + WORKER_RULES + venv_hint(Path(task.project))
    if task.agent == "local":
        return ["codex", "exec", "-p", "local", "-m", task.model or "ornith-1.5:9b",
                "-s", "workspace-write", "-o", str(last_message), prompt]
    if task.agent == "codex":
        return ["codex", "exec", "-s", "workspace-write", "-o", str(last_message), prompt]
    if task.agent == "claude":
        # acceptEdits: file edits inside the folder are allowed; other tools need the listed permissions.
        return ["claude", "-p", "--permission-mode", "acceptEdits",
                "--allowedTools", "Bash(python3 -m unittest:*)", "Bash(*/.venv/bin/python -m unittest:*)",
                "Bash(git status:*)", "Bash(git diff:*)", "--", prompt]
    raise ValueError(f"unknown agent: {task.agent}")


def in_dev_command(argv: list[str], workdir: Path, time_limit: int) -> list[str]:
    """Run argv in `workdir` inside the `dev` container (where codex lives), with a time limit.

    `timeout` ends the worker after `time_limit` seconds (exit code 124). `-k 30`
    kills it 30 s later if it ignores the polite signal.
    """
    # PYTHONDONTWRITEBYTECODE: running tests must not leave __pycache__/*.pyc files behind,
    # or they end up in the diff of projects that don't ignore them (found by the first review).
    script = (f"cd {shlex.quote(str(workdir))} && export PYTHONDONTWRITEBYTECODE=1 && "
              f"exec timeout -k 30 {time_limit} {shlex.join(argv)}")
    if current_container_name() == "dev":
        return ["bash", "-lc", script]
    return ["distrobox", "enter", "dev", "--", "bash", "-lc", script]


def start_task(task: Task) -> Task:
    """Save the task and start its supervisor as a detached process. Returns the saved task."""
    save_task(task)
    package_root = Path(__file__).resolve().parents[1]
    with (task.folder / "supervisor.log").open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "mission_control", "task", "_run", task.id],
            cwd=package_root,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,  # keeps running when Mission Control or its terminal closes
            env={**os.environ, "MISSION_CONTROL_STATE": str(STATE_DIR)},
        )
    task.pid = process.pid
    save_task(task)
    return task


def run_task(task_id: str, worktrees_dir: Path | None = None) -> Task:
    """The supervisor: create the worktree, run the worker, record changes, get a review."""
    task = load_task(task_id)
    project = Path(task.project)
    worktrees_dir = worktrees_dir or _worktrees_dir(project)
    task.status, task.started, task.pid = "running", time.time(), os.getpid()
    try:
        ws = create_workspace(project, worktrees_dir, task.id)
    except WorkspaceError as exc:
        return _finish(task, "failed", error=f"could not create the worktree: {exc}")
    task.workspace = ws.to_dict()
    save_task(task)

    last_message = task.folder / "last-message.txt"
    command = in_dev_command(worker_command(task, ws.workdir, last_message), ws.workdir, task.time_limit)
    try:
        with (task.folder / "worker.log").open("w") as log:
            log.write(f"$ {shlex.join(command)[:2000]}\n\n")
            log.flush()
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=task.time_limit + GRACE_SECONDS, check=False)
        code = result.returncode
    except subprocess.TimeoutExpired:
        code = 124
    except OSError as exc:
        return _finish(task, "failed", error=f"could not start the worker: {exc}")
    task.exit_code = code
    status = "done" if code == 0 else "timeout" if code in (124, 137) else "failed"

    try:
        changes = summarize_changes(ws)
    except WorkspaceError as exc:
        return _finish(task, status, error=f"could not read the changes: {exc}")
    task.files, task.insertions, task.deletions = list(changes.files), changes.insertions, changes.deletions
    (task.folder / "diff.patch").write_text(changes.diff)
    task.status = status
    save_task(task)

    if changes.files:
        outcome = {"done": "finished normally", "timeout": "stopped by the time limit",
                   "failed": f"exited with code {code}"}[status]
        try:
            review = review_task(task.title, task.brief, _agent_label(task), outcome, changes.diff,
                                 worker_output(task))
            task.review = review.to_dict()
        except OrchestratorError as exc:
            task.error = f"review failed: {exc}"
    return _finish(task, status)


def _finish(task: Task, status: str, error: str | None = None) -> Task:
    task.status, task.finished, task.pid = status, time.time(), None
    if error:
        task.error = error
    save_task(task)
    return task


def _worktrees_dir(project: Path) -> Path:
    """Worktrees go in <projects root>/.worktrees (ignored by git), next to the other agents' worktrees."""
    root = Path(os.environ.get("MISSION_CONTROL_PROJECTS", Path.home() / "Projects")).expanduser()
    return root / ".worktrees"


def _agent_label(task: Task) -> str:
    return f"{task.agent} ({task.model})" if task.model else task.agent


def worker_output(task: Task) -> str:
    """The worker's final message if it wrote one, else the end of its log."""
    for name in ("last-message.txt", "worker.log"):
        try:
            text = (task.folder / name).read_text(errors="replace").strip()
        except OSError:
            continue
        if text:
            return text[-8000:]
    return ""


def is_alive(task: Task) -> bool:
    """True if the task's supervisor process still exists."""
    if task.pid is None:
        return False
    try:
        os.kill(task.pid, 0)  # signal 0: only checks that the process exists
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def commit_subject(task: Task, width: int = 45) -> str:
    """A short commit subject: "Task <id>: <first line of the title, cut at a word>"."""
    title = task.title.strip().splitlines()[0] if task.title.strip() else "(no title)"
    if len(title) > width:
        title = title[:width].rsplit(" ", 1)[0] + "…"
    return f"Task {task.id}: {title}"


def merge_task(task: Task) -> tuple[bool, str]:
    """Commit the worker's changes and merge them into the main checkout, then clean up."""
    if task.status not in FINISHED or task.ws is None:
        return False, f"Task {task.id} is {task.status}; only finished tasks can be merged."
    ws = task.ws
    try:
        # No AI attribution in commit messages (portfolio rule): which worker did it is in the task record.
        sha = commit_all(ws, commit_subject(task))
        if sha is None and not task.files:
            return False, "Nothing to merge: the worker changed no files."
        ok, message = merge_into_main(ws, f"Merge {commit_subject(task)}")
    except WorkspaceError as exc:
        return False, f"Merge failed: {exc}"
    if not ok:
        return False, message
    remove_workspace(ws)
    task.status = "merged"
    save_task(task)
    return True, message


def discard_task(task: Task) -> tuple[bool, str]:
    """Throw the worker's changes away: delete its worktree and branch."""
    if task.status == "running" and is_alive(task):
        return False, "The task is still running."
    if task.ws is not None:
        try:
            remove_workspace(task.ws)
        except WorkspaceError as exc:
            return False, f"Could not remove the worktree: {exc}"
    task.status = "discarded"
    save_task(task)
    return True, f"Discarded task {task.id}."


def mark_lost(task: Task) -> Task:
    """A 'running' task whose supervisor has died (for example after a reboot) is marked failed."""
    if task.status == "running" and not is_alive(task):
        task.status, task.error = "failed", "the supervisor process stopped unexpectedly"
        task.finished = time.time()
        save_task(task)
    return task


def local_state() -> tuple[list[str], bool, str | None]:
    """(installed local models, is the server running, the Codex profile's default model)."""
    status = read_ollama()
    return [m.name for m in status.installed], status.running, profile_model()


def ask_plan(title: str, project_dir: Path) -> Plan:
    """Ask the orchestrator for a plan, telling it what the local model can do right now."""
    models, running, default = local_state()
    return plan_task(title, project_dir, models, running, default)


def manual_plan(title: str, agent: str, model: str | None = None, minutes: int | None = None) -> Plan:
    """A plan chosen by the owner instead of the orchestrator: the brief is the task itself."""
    if agent == "local" and not model:
        model = local_state()[2] or "ornith-1.5:9b"
    return Plan(agent=agent, model=model if agent == "local" else None, reason="chosen by the owner",
                brief=title, time_limit_minutes=minutes or (10 if agent == "local" else 25))


def make_task(title: str, project_dir: Path, plan: Plan, suggested: Plan | None = None) -> Task:
    """Create (but don't start) a task from a plan, and log the decision.

    `suggested` is the orchestrator's original plan when the owner changed the worker.
    """
    task = Task(
        id=new_task_id(), title=title, project=str(project_dir), agent=plan.agent, model=plan.model,
        brief=plan.brief, reason=plan.reason, time_limit=plan.time_limit_minutes * 60,
    )
    log_decision({
        "task": task.id, "title": title, "project": str(project_dir),
        "suggested": (suggested or plan).to_dict(), "chosen": {"agent": plan.agent, "model": plan.model},
        "overridden": suggested is not None and (suggested.agent, suggested.model) != (plan.agent, plan.model),
    })
    return task
