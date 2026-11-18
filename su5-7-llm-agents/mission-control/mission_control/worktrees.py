"""Manage private Git worktrees for dispatched tasks, without UI dependencies.

Each task checks out the whole repository from its last commit. Its working
folder preserves the project's location inside that repository.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

TASK_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")


class WorkspaceError(Exception):
    """A workspace operation could not complete."""


@dataclass(frozen=True)
class Workspace:
    """The main checkout, private checkout and starting commit for one task."""

    repo: Path
    worktree: Path
    branch: str
    base: str
    workdir: Path

    def to_dict(self) -> dict[str, str]:
        """Return string fields suitable for saving as JSON."""
        return {
            "repo": str(self.repo),
            "worktree": str(self.worktree),
            "branch": self.branch,
            "base": self.base,
            "workdir": str(self.workdir),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> Workspace:
        """Restore a workspace from its saved string fields."""
        return cls(
            repo=Path(data["repo"]),
            worktree=Path(data["worktree"]),
            branch=data["branch"],
            base=data["base"],
            workdir=Path(data["workdir"]),
        )


@dataclass(frozen=True)
class ChangeSummary:
    """All changes from a task's starting commit, including untracked files."""

    files: tuple[str, ...]
    insertions: int
    deletions: int
    diff: str


def _message(result: subprocess.CompletedProcess[str]) -> str:
    """Return Git's last error line, with a fallback for silent failures."""
    lines = (result.stderr.strip() or result.stdout.strip()).splitlines()
    return lines[-1] if lines else f"git exited with {result.returncode}"


def _run_git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run Git with a fixed locale and turn execution errors into readable errors."""
    try:
        return subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceError(f"Could not run git: {exc}") from exc


def _git(path: Path, *args: str) -> str:
    """Return successful Git output or raise a readable workspace error."""
    result = _run_git(path, *args)
    if result.returncode != 0:
        raise WorkspaceError(_message(result))
    return result.stdout


def repo_root(path: Path) -> Path:
    """Return the repository top containing path, or raise WorkspaceError."""
    return Path(_git(path, "rev-parse", "--show-toplevel").strip())


def create_workspace(project_dir: Path, worktrees_dir: Path, task_id: str) -> Workspace:
    """Create a task branch and whole-repository checkout at the last commit."""
    if TASK_ID_PATTERN.fullmatch(task_id) is None:
        raise WorkspaceError("Invalid task id: use 1-40 lowercase letters, digits or hyphens")
    project_dir = project_dir.resolve()
    repo = repo_root(project_dir)
    base = _git(repo, "rev-parse", "HEAD").strip()
    worktree = worktrees_dir.resolve() / f"task-{task_id}"
    branch = f"task/{task_id}"
    # Git accepts an existing empty folder, but dispatch must never reuse one.
    if worktree.exists() or worktree.is_symlink():
        raise WorkspaceError(f"Workspace folder already exists: {worktree}")
    try:
        worktree.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError(f"Could not create workspace folder: {exc}") from exc
    _git(repo, "worktree", "add", "-b", branch, str(worktree), base)
    return Workspace(repo, worktree, branch, base, worktree / project_dir.relative_to(repo))


def summarize_changes(ws: Workspace) -> ChangeSummary:
    """Stage private changes and summarize the complete difference from base."""
    _git(ws.worktree, "add", "-A")
    # NUL separators preserve tabs/newlines in filenames. Separate delete/add
    # entries for renames keep every path relative to the repository top.
    stats = _git(ws.worktree, "diff", "--cached", "--numstat", "--no-renames", "-z", ws.base)
    files: list[str] = []
    insertions = deletions = 0
    for entry in stats.split("\0"):
        if not entry:
            continue
        added, removed, name = entry.split("\t", 2)
        files.append(name)
        insertions += 0 if added == "-" else int(added)
        deletions += 0 if removed == "-" else int(removed)
    diff = _git(ws.worktree, "diff", "--cached", "--no-renames", ws.base)
    return ChangeSummary(tuple(sorted(files)), insertions, deletions, diff)


def commit_all(ws: Workspace, message: str) -> str | None:
    """Commit all private changes and return HEAD, or None when already clean."""
    _git(ws.worktree, "add", "-A")
    changes = _run_git(ws.worktree, "diff", "--cached", "--quiet")
    if changes.returncode == 0:
        return None
    if changes.returncode != 1:
        raise WorkspaceError(_message(changes))
    _git(ws.worktree, "commit", "-m", message)
    return _git(ws.worktree, "rev-parse", "HEAD").strip()


def merge_into_main(ws: Workspace, message: str) -> tuple[bool, str]:
    """Merge a task into the main checkout, aborting any resulting conflict."""
    current = _run_git(ws.repo, "symbolic-ref", "--short", "-q", "HEAD")
    branch = current.stdout.strip() or "HEAD"
    # A refused merge must not abort an unrelated merge already in progress.
    was_merging = _run_git(ws.repo, "rev-parse", "--verify", "-q", "MERGE_HEAD")
    result = _run_git(ws.repo, "merge", "--no-ff", "-m", message, ws.branch)
    if result.returncode == 0:
        return True, f"Merged {ws.branch} into {branch}"
    is_merging = _run_git(ws.repo, "rev-parse", "--verify", "-q", "MERGE_HEAD")
    if was_merging.returncode != 0 and is_merging.returncode == 0:
        conflicts = _run_git(ws.repo, "diff", "--name-only", "--diff-filter=U", "-z")
        names = sorted(name for name in conflicts.stdout.split("\0") if name)
        aborted = _run_git(ws.repo, "merge", "--abort")
        if aborted.returncode != 0:
            return False, _message(aborted)
        if names:
            return False, f"Merge conflict in: {', '.join(names)}"
    return False, _message(result)


def remove_workspace(ws: Workspace, delete_branch: bool = True) -> None:
    """Remove a private checkout and optionally its branch, tolerating absence."""
    removed = _run_git(ws.repo, "worktree", "remove", "--force", str(ws.worktree))
    if removed.returncode != 0:
        registered = _git(ws.repo, "worktree", "list", "--porcelain", "-z")
        if f"worktree {ws.worktree}" in registered.split("\0") or ws.worktree.exists():
            raise WorkspaceError(_message(removed))
    if delete_branch:
        exists = _run_git(ws.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{ws.branch}")
        if exists.returncode == 0:
            _git(ws.repo, "branch", "-D", ws.branch)
        elif exists.returncode != 1:
            raise WorkspaceError(_message(exists))
