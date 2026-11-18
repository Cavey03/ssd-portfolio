"""Find the projects in ~/Projects and read their git status.

This module has no UI code, so it can be tested on its own. It runs one
`git status --porcelain=v2 --branch` per project. That machine-readable output
contains the branch, the ahead/behind counts against the upstream and one line
per changed file.

~/Projects is itself one git repo (the portfolio), so a "project" is either:
  * the root repo itself,
  * a folder inside it with its own CLAUDE.md or AGENTS.md (for example
    su5-7-llm-agents/mission-control). Its status is the root repo's status
    limited to that folder (`git status -- <folder>`), or
  * a separate git repo somewhere below the root (for example particle-sim, or
    a submodule). We don't look inside it.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

GIT_TIMEOUT_SECONDS = 5
PROJECT_MARKERS = ("CLAUDE.md", "AGENTS.md")
"""A folder holding one of these files is a project."""
SKIP_DIRS = frozenset({".venv", "venv", "node_modules", "__pycache__"})
"""Never searched (big, and never projects). Hidden folders are skipped too."""
MAX_DEPTH = 4
"""How many folder levels below the root are searched for projects."""


@dataclass(frozen=True)
class ProjectStatus:
    """Git summary for one project folder."""

    name: str
    path: Path
    is_repo: bool
    branch: str | None = None
    changes: int = 0
    """Number of modified, staged, untracked or conflicted files."""
    ahead: int | None = None
    """Commits not yet pushed. None means the branch has no upstream (remote)."""
    behind: int | None = None
    """Commits on the remote not yet pulled. None means no upstream."""
    error: str | None = None
    key: str = ""
    """Path relative to the projects root ("." for the root itself); unique per row."""
    in_root_repo: bool = False
    """A folder inside the root repo: it shares the root's branch and sync."""


def default_projects_root() -> Path:
    """Return the projects folder: $MISSION_CONTROL_PROJECTS or ~/Projects."""
    override = os.environ.get("MISSION_CONTROL_PROJECTS")
    return Path(override).expanduser() if override else Path.home() / "Projects"


def parse_porcelain_v2(output: str) -> tuple[str | None, int, int | None, int | None]:
    """Parse `git status --porcelain=v2 --branch` output.

    Returns (branch, changes, ahead, behind).
    """
    branch: str | None = None
    changes = 0
    ahead: int | None = None
    behind: int | None = None

    for line in output.splitlines():
        if line.startswith("# branch.head "):
            branch = line.removeprefix("# branch.head ")
        elif line.startswith("# branch.ab "):
            # Format: "# branch.ab +<ahead> -<behind>"
            plus, minus = line.removeprefix("# branch.ab ").split()
            ahead, behind = int(plus), abs(int(minus))
        elif line[:2] in ("1 ", "2 ", "u ", "? "):
            # 1 = changed, 2 = renamed/copied, u = unmerged, ? = untracked
            changes += 1

    return branch, changes, ahead, behind


def is_git_repo(path: Path) -> bool:
    """True if `path` is the top of a git repo (.git is a folder, or a file for submodules/worktrees)."""
    return (path / ".git").exists()


def read_status(path: Path, folder: str | None = None, key: str | None = None) -> ProjectStatus:
    """Return the git status of the repo at `path`.

    With `folder` (relative to `path`), only changes inside that folder are counted.
    """
    name = path.name if key in (None, ".") else key  # the root shows its folder name
    target = path / folder if folder else path
    extra = {"key": key or name, "in_root_repo": folder is not None}
    if not is_git_repo(path):
        return ProjectStatus(name=name, path=target, is_repo=False, **extra)

    env = {
        **os.environ,
        "LC_ALL": "C",
        # Don't take git's index lock while polling, so we never get in the
        # way of a git command (or AI agent) running in that repo.
        "GIT_OPTIONAL_LOCKS": "0",
    }
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain=v2", "--branch",
             *(["--", folder] if folder else [])],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            env=env,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ProjectStatus(name=name, path=target, is_repo=True, error=str(exc), **extra)

    if result.returncode != 0:
        message = result.stderr.strip().splitlines()
        return ProjectStatus(
            name=name,
            path=target,
            is_repo=True,
            error=message[-1] if message else f"git exited with {result.returncode}",
            **extra,
        )

    branch, changes, ahead, behind = parse_porcelain_v2(result.stdout)
    return ProjectStatus(
        name=name,
        path=target,
        is_repo=True,
        branch=branch,
        changes=changes,
        ahead=ahead,
        behind=behind,
        **extra,
    )


def find_projects(root: Path, max_depth: int = MAX_DEPTH) -> list[Path]:
    """Return the project folders below `root` (not `root` itself), in folder order.

    A project is a separate git repo or a folder with a CLAUDE.md / AGENTS.md.
    The search doesn't go inside separate repos: they are one project each.
    """
    found: list[Path] = []

    def walk(folder: Path, depth: int) -> None:
        try:
            entries = sorted(
                (e for e in os.scandir(folder) if e.is_dir(follow_symlinks=False)),
                key=lambda e: e.name.lower(),
            )
        except OSError:
            return  # unreadable folder: skip it rather than fail the whole scan
        for entry in entries:
            if entry.name.startswith(".") or entry.name in SKIP_DIRS:
                continue
            path = Path(entry.path)
            if is_git_repo(path):
                found.append(path)
                continue
            if any((path / marker).is_file() for marker in PROJECT_MARKERS):
                found.append(path)
            if depth < max_depth:
                walk(path, depth + 1)

    walk(root, 1)
    return found


def scan_projects(root: Path) -> list[ProjectStatus]:
    """Return the status of every project, in display order.

    Order: the root repo, the projects inside it, then the separate repos.
    """
    if not root.is_dir():
        return []
    root_is_repo = is_git_repo(root)
    inside: list[ProjectStatus] = []
    separate: list[ProjectStatus] = []
    for path in find_projects(root):
        key = path.relative_to(root).as_posix()
        if is_git_repo(path):
            separate.append(read_status(path, key=key))
        elif root_is_repo:
            inside.append(read_status(root, folder=key, key=key))
        else:
            inside.append(ProjectStatus(name=key, path=path, is_repo=False, key=key))
    head = [read_status(root, key=".")] if root_is_repo else []
    return head + inside + separate
