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
import signal
import subprocess
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

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
    local_model: str | None = None
    """For a Codex session on a local model (Ollama): the model name, or "local" if unknown."""


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


CODEX_LOCAL_PROFILE = Path.home() / ".codex" / "local.config.toml"
"""The Codex profile for the local model (see local-llm/README.md, "Connecting Codex")."""
LOCAL_PROFILE_NAME = "local"


def profile_model(profile_path: Path = CODEX_LOCAL_PROFILE) -> str | None:
    """Return the `model = "..."` setting of the local Codex profile, if it can be read."""
    try:
        with profile_path.open("rb") as f:
            model = tomllib.load(f).get("model")
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return model if isinstance(model, str) and model else None


def codex_local_model(args: list[str], default_model: str | None) -> str | None:
    """Return which local model a Codex command line uses, or None for a cloud (GPT) session.

    `args` are the arguments after the program name. A session is local when it uses the
    local profile (`-p local`, `--profile local`, `--profile=local`) or `--oss`. The model comes
    from `-m`/`--model`, else the profile's default model, else just "local".
    """
    local = False
    model: str | None = None
    for i, arg in enumerate(args):
        following = args[i + 1] if i + 1 < len(args) else None
        if arg == "--oss":
            local = True
        elif arg in ("-p", "--profile") and following == LOCAL_PROFILE_NAME:
            local = True
        elif arg == f"--profile={LOCAL_PROFILE_NAME}":
            local = True
        elif arg in ("-m", "--model") and following:
            model = following
        elif arg.startswith("--model="):
            model = arg.removeprefix("--model=")
    if not local:
        return None
    return model or default_model or "local"


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
    default_local_model = profile_model()
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
        local_model = None
        if agent == "codex":
            args = [a.decode(errors="replace") for a in argv[1:] if a]
            local_model = codex_local_model(args, default_local_model)
        found.append(AgentProcess(agent, int(entry.name), cwd, started, local_model))

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
            AgentProcess(a.agent, a.pid, host.get(a.pid, a.cwd), a.started, a.local_model)
            for a in found
        ]
    return sorted(found, key=lambda a: (a.started or 0, a.pid))


def describe_folder(
    cwd: Path | None, projects_root: Path, projects: Sequence[str] = ()
) -> str:
    """Describe an agent's folder relative to the projects root.

    `projects` are the known project folders relative to the root (from the
    Projects panel, e.g. "su5-7-llm-agents/mission-control"). If the agent works
    inside one of them, the project's own folder name is shown ("mission-control").
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
        relative = path[len(root) + 1 :]
        parts = relative.split("/")
        if parts[0] == ".worktrees" and len(parts) > 1:
            return f"{parts[1]} (worktree)"
        inside = [p for p in projects if p != "." and (relative + "/").startswith(p + "/")]
        if inside:
            return max(inside, key=len).rsplit("/", 1)[-1]  # the deepest matching project
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


def _same_process(agent: AgentProcess, proc: Path) -> bool:
    """Check that agent.pid still belongs to the same agent session.

    Process ids get reused, so a pid alone isn't enough: the program and its
    start time must match what the panel showed.
    """
    entry = proc / str(agent.pid)
    try:
        argv = (entry / "cmdline").read_bytes().split(b"\0")
        comm = (entry / "comm").read_text().strip()
        stat_text = (entry / "stat").read_text()
    except OSError:
        return False
    argv0 = argv[0].decode(errors="replace") if argv and argv[0] else ""
    if identify_agent(argv0, comm) != agent.agent:
        return False
    if agent.started is None:
        return True
    started = _start_time(stat_text, _boot_time(proc))
    return started is not None and abs(started - agent.started) < 1.0


def stop_agent(agent: AgentProcess, proc: Path = PROC) -> tuple[bool, str]:
    """Ask an agent session to quit (SIGTERM). Never raises.

    Agents get SIGTERM, the polite "please exit" signal, so they can clean up.
    If the container isn't allowed to signal the host process, the same
    signal is sent from the host via distrobox-host-exec.
    """
    label = f"{agent.agent} (pid {agent.pid})"
    if agent.pid == os.getpid():
        return False, "Refusing to stop Mission Control itself."
    if not _same_process(agent, proc):
        return False, f"{label} has already exited."
    try:
        os.kill(agent.pid, signal.SIGTERM)
        return True, f"Stopped {label}."
    except ProcessLookupError:
        return False, f"{label} has already exited."
    except PermissionError:
        pass
    if not shutil.which("distrobox-host-exec"):
        return False, f"Not allowed to stop {label}."
    try:
        result = subprocess.run(
            ["distrobox-host-exec", "kill", "-TERM", str(agent.pid)],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Could not stop {label}: {exc}"
    if result.returncode != 0:
        return False, f"Could not stop {label}: {result.stderr.strip() or 'kill failed'}"
    return True, f"Stopped {label}."
