"""Read the git status of project folders.

This module has no UI code, so it can be tested on its own. It runs one
`git status --porcelain=v2 --branch` per project. That machine-readable output
contains the branch, the ahead/behind counts against the upstream and one line
per changed file.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

GIT_TIMEOUT_SECONDS = 5


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


def read_status(path: Path) -> ProjectStatus:
    """Return the git status of a single folder."""
    if not (path / ".git").exists():
        return ProjectStatus(name=path.name, path=path, is_repo=False)

    env = {
        **os.environ,
        "LC_ALL": "C",
        # Don't take git's index lock while polling, so we never get in the
        # way of a git command (or AI agent) running in that repo.
        "GIT_OPTIONAL_LOCKS": "0",
    }
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain=v2", "--branch"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            env=env,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ProjectStatus(name=path.name, path=path, is_repo=True, error=str(exc))

    if result.returncode != 0:
        message = result.stderr.strip().splitlines()
        return ProjectStatus(
            name=path.name,
            path=path,
            is_repo=True,
            error=message[-1] if message else f"git exited with {result.returncode}",
        )

    branch, changes, ahead, behind = parse_porcelain_v2(result.stdout)
    return ProjectStatus(
        name=path.name,
        path=path,
        is_repo=True,
        branch=branch,
        changes=changes,
        ahead=ahead,
        behind=behind,
    )


def scan_projects(root: Path) -> list[ProjectStatus]:
    """Return the status of every visible sub-folder of `root`, sorted by name."""
    if not root.is_dir():
        return []
    folders = [p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")]
    return [read_status(p) for p in sorted(folders, key=lambda p: p.name.lower())]
