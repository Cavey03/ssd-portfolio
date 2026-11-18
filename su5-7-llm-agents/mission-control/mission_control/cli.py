"""`mc task ...`: Dispatch from the command line (the same actions as the Tasks panel).

Examples:
  mc task start "add a --version flag to mc"            # Opus plans, you confirm, it runs
  mc task start "fix the typo in README" --agent local  # skip planning, choose the worker
  mc task list
  mc task show <id>        mc task diff <id>
  mc task merge <id>       mc task discard <id>
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from mission_control import tasks
from mission_control.orchestrator import AGENTS, OrchestratorError, Plan
from mission_control.router import ROUTER_MODEL, local_route
from mission_control.worktrees import WorkspaceError, repo_root


def _project(path: str | None) -> Path:
    """The project folder: --project, else the folder `mc` was started from."""
    folder = Path(path or os.environ.get("MISSION_CONTROL_CWD") or os.getcwd()).expanduser().resolve()
    repo_root(folder)  # raises WorkspaceError if it isn't inside a git repo
    return folder


def _confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _print_plan(plan: Plan) -> None:
    worker = f"{plan.agent} ({plan.model})" if plan.model else plan.agent
    print(f"Worker:     {worker}\nWhy:        {plan.reason}\nTime limit: {plan.time_limit_minutes} min")
    print("Brief:\n  " + plan.brief.replace("\n", "\n  "))


def _age(seconds: float) -> str:
    seconds = int(max(0, seconds))
    return f"{seconds // 60}m" if seconds < 3600 else f"{seconds // 3600}h"


def cmd_start(args: argparse.Namespace) -> int:
    project = _project(args.project)
    suggested: Plan | None = None
    router: str | None = None
    if args.agent:
        plan = tasks.manual_plan(args.text, args.agent, args.model, args.minutes)
    else:
        router = local_route(args.text)
        print(f"Local router ({ROUTER_MODEL}): {router or 'not available'}")
        print(f"Asking the orchestrator about {project.name}…", flush=True)
        suggested = plan = tasks.ask_plan(args.text, project)
    _print_plan(plan)
    if args.dry_run or not _confirm("Start this task?", args.yes):
        print("Not started.")
        return 0
    task = tasks.start_task(tasks.make_task(args.text, project, plan, suggested, router))
    print(f"Started task {task.id}. Follow it with: mc task show {task.id}")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    rows = [tasks.mark_lost(t) for t in tasks.list_tasks()]
    if not rows:
        print("No tasks yet.")
    for t in rows:
        worker = f"{t.agent}:{t.model}" if t.model else t.agent
        verdict = f" review:{t.review['verdict']}" if t.review else ""
        print(f"{t.id}  {t.status:<9} {worker:<22} {_age(time.time() - t.created):>4}  "
              f"{len(t.files)} files{verdict}  {t.title[:50]}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    t = tasks.mark_lost(tasks.load_task(args.id))
    print(f"Task {t.id}: {t.title}\nProject: {t.project}\nWorker:  {t.agent} {t.model or ''}")
    print(f"Status:  {t.status}" + (f" (exit {t.exit_code})" if t.exit_code is not None else ""))
    print(f"Why:     {t.reason}")
    if t.error:
        print(f"Problem: {t.error}")
    if t.files:
        print(f"Changes: {len(t.files)} files, +{t.insertions} -{t.deletions}")
        for name in t.files:
            print(f"  {name}")
    if t.review:
        r = t.review_obj
        assert r is not None
        print(f"Review:  {r.verdict.upper()}: {r.summary}")
        for concern in r.concerns:
            print(f"  - {concern}")
    output = tasks.worker_output(t)
    if output and t.status not in tasks.ACTIVE:
        print("\nWorker's summary:\n" + output[-1500:])
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    try:
        print((tasks.load_task(args.id).folder / "diff.patch").read_text(), end="")
    except FileNotFoundError:
        print("No diff yet (the task hasn't finished).")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    t = tasks.load_task(args.id)
    if not _confirm(f"Merge task {t.id} ({len(t.files)} files) into the main checkout?", args.yes):
        return 1
    ok, message = tasks.merge_task(t)
    print(message)
    return 0 if ok else 1


def cmd_discard(args: argparse.Namespace) -> int:
    t = tasks.load_task(args.id)
    if not _confirm(f"Discard task {t.id} and delete its worktree?", args.yes):
        return 1
    ok, message = tasks.discard_task(t)
    print(message)
    return 0 if ok else 1


def cmd_run(args: argparse.Namespace) -> int:
    """Internal: the supervisor process started by start_task."""
    tasks.run_task(args.id)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mc task", description="Dispatch coding tasks to AI workers.")
    sub = parser.add_subparsers(dest="command", required=True,
                                metavar="{start,list,show,diff,merge,discard}")

    start = sub.add_parser("start", help="plan and start a task")
    start.add_argument("text", help="what the worker should do")
    start.add_argument("--project", help="project folder (default: the current folder)")
    start.add_argument("--agent", choices=AGENTS, help="skip planning and use this worker")
    start.add_argument("--model", help="local model (with --agent local)")
    start.add_argument("--minutes", type=int, help="time limit (with --agent)")
    start.add_argument("--dry-run", action="store_true", help="only show the plan")
    start.add_argument("-y", "--yes", action="store_true", help="don't ask before starting")
    start.set_defaults(func=cmd_start)

    sub.add_parser("list", help="recent tasks").set_defaults(func=cmd_list)
    for name, func, text in (("show", cmd_show, "details, review and summary"),
                             ("diff", cmd_diff, "the worker's changes"),
                             ("_run", cmd_run, None)):  # internal: the supervisor
        p = sub.add_parser(name, help=text) if text else sub.add_parser(name)
        p.add_argument("id")
        p.set_defaults(func=func)
    for name, func, text in (("merge", cmd_merge, "commit and merge into the main checkout"),
                             ("discard", cmd_discard, "delete the worktree and branch")):
        p = sub.add_parser(name, help=text)
        p.add_argument("id")
        p.add_argument("-y", "--yes", action="store_true")
        p.set_defaults(func=func)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError:
        print(f"No task with id {getattr(args, 'id', '?')}.", file=sys.stderr)
    except (OrchestratorError, WorkspaceError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
    return 1
