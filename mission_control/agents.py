"""Find running AI coding agents (Claude Code, Codex, Antigravity) and their folders.

Distrobox shares the host's process list with the container, so /proc inside
`dev` shows every agent on the machine, whether it runs on the host or in a
container. For each process we read:
  /proc/<pid>/cmdline  which program it is
  /proc/<pid>/cwd      which folder (project) it works in
  /proc/<pid>/stat     when it started
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

PROC = Path("/proc")


@dataclass(frozen=True)
class AgentProcess:
    """One running agent session."""

    agent: str
    """"claude", "codex" or "agy"."""
    pid: int
    cwd: Path | None
    started: float | None
    """Start time as a Unix timestamp, if known."""


def identify_agent(argv0: str, comm: str) -> str | None:
    """Return the agent name for a process, or None if it isn't an agent session.

    argv0 is the first word of the command line; comm is the kernel's short name.
    """
    base = os.path.basename(argv0)
    # Codex keeps background helper daemons running; those aren't sessions.
    if "app-server-daemon" in argv0:
        return None
    if base == "claude" or "/claude/versions/" in argv0:
        return "claude"
    # The real binary is named "codex"; "codex-linux-sandbox" etc. are helpers
    # that run single commands for a session.
    if base == "codex":
        return "codex"
    if base == "agy" or comm == "agy":
        return "agy"
    return None


def _boot_time(proc: Path) -> float | None:
    """Return the system boot time (Unix timestamp) from /proc/stat."""
    try:
        for line in (proc / "stat").read_text().splitlines():
            if line.startswith("btime "):
                return float(line.split()[1])
    except (OSError, ValueError):
        pass
    return None


def _stat_fields(stat_text: str) -> list[str]:
    """Split /proc/<pid>/stat into fields after the process name.

    The name (field 2) can contain spaces, so we split after its closing ")".
    The returned list starts at field 3 (state); field N is at index N - 3.
    """
    return stat_text.rsplit(")", 1)[1].split()


def _start_time(stat_text: str, boot_time: float | None) -> float | None:
    """Turn /proc/<pid>/stat's start field into a Unix timestamp."""
    if boot_time is None:
        return None
    try:
        ticks = int(_stat_fields(stat_text)[19])  # field 22: start time in clock ticks
        return boot_time + ticks / os.sysconf("SC_CLK_TCK")
    except (IndexError, ValueError, OSError):
        return None


def _host_cwds(pids: list[int]) -> dict[int, Path]:
    """Ask the host for the folders of processes the container may not inspect.

    Rootless containers run in their own user namespace, so the kernel hides
    /proc/<pid>/cwd of host processes from them. One distrobox-host-exec call
    reads them all on the host side.
    """
    if not pids or not shutil.which("distrobox-host-exec"):
        return {}
    script = 'for p in "$@"; do printf "%s %s\\n" "$p" "$(readlink /proc/$p/cwd)"; done'
    try:
        result = subprocess.run(
            ["distrobox-host-exec", "sh", "-c", script, "sh", *map(str, pids)],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    cwds: dict[int, Path] = {}
    for line in result.stdout.splitlines():
        pid, _, path = line.partition(" ")
        if pid.isdigit() and path.startswith("/"):
            cwds[int(pid)] = Path(path)
    return cwds


def find_agents(proc: Path = PROC, ask_host: bool = True) -> list[AgentProcess]:
    """Return every running agent session, oldest first.

    Helper processes started by an agent (a child of the same agent) are
    skipped, so each session appears once.
    """
    boot_time = _boot_time(proc)
    found: list[AgentProcess] = []
    parents: dict[int, int] = {}
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
            comm = (entry / "comm").read_text().strip()
        except OSError:
            continue  # the process ended or isn't readable
        argv0 = argv[0].decode(errors="replace") if argv and argv[0] else ""
        agent = identify_agent(argv0, comm)
        if agent is None:
            continue
        try:
            cwd: Path | None = Path(os.readlink(entry / "cwd"))
        except OSError:
            cwd = None
        try:
            stat_text = (entry / "stat").read_text()
            started = _start_time(stat_text, boot_time)
            parents[int(entry.name)] = int(_stat_fields(stat_text)[1])  # field 4: parent pid
        except (OSError, IndexError, ValueError):
            started = None
        found.append(AgentProcess(agent, int(entry.name), cwd, started))

    by_pid = {a.pid: a for a in found}
    found = [
        a for a in found
        if by_pid.get(parents.get(a.pid, 0), None) is None
        or by_pid[parents[a.pid]].agent != a.agent
    ]
    missing = [a.pid for a in found if a.cwd is None]
    if ask_host and missing:
        host = _host_cwds(missing)
        found = [
            AgentProcess(a.agent, a.pid, host.get(a.pid, a.cwd), a.started) for a in found
        ]
    return sorted(found, key=lambda a: (a.started or 0, a.pid))


def describe_folder(cwd: Path | None, projects_root: Path) -> str:
    """Describe an agent's folder relative to the projects root.

    /var/home is the real path of /home on Fedora Atomic, so both are normalised.
    """
    if cwd is None:
        return "?"

    def norm(p: Path) -> str:
        text = str(p)
        return text.removeprefix("/var") if text.startswith("/var/home/") else text

    path, root, home = norm(cwd), norm(projects_root), norm(Path.home())
    if path == root:
        return "~/Projects"
    if path.startswith(root + "/"):
        parts = path[len(root) + 1 :].split("/")
        if parts[0] == ".worktrees" and len(parts) > 1:
            return f"{parts[1]} (worktree)"
        return parts[0]
    if path == home:
        return "~"
    if path.startswith(home + "/"):
        return "~/" + path[len(home) + 1 :]
    return path


def format_age(started: float | None, now: float | None = None) -> str:
    """Return a short age such as "45s", "12m" or "3h"."""
    if started is None:
        return "?"
    seconds = max(0, int((now or time.time()) - started))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"
