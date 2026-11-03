"""Launch agents in detached host Konsole tabs without UI code."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from mission_control.containers import current_container_name

AGENTS = {"Claude": "claude", "Codex": "codex", "Agy": "agy"}


def build_launch_command(agent_cmd: str, project_dir: Path, container: str | None) -> list[str]:
    """Build a host Konsole command that enters the project in Distrobox.

    It opens a new Konsole window. With --new-tab, Konsole adds the tab to the
    most recently used window, which can be hard to find.
    """
    command = [
        "konsole", "--workdir", str(project_dir), "-e",
        "distrobox", "enter", container or "dev", "--", "bash", "-lc",
        f"cd {shlex.quote(str(project_dir))} && exec {shlex.quote(agent_cmd)}",
    ]
    if container is not None:
        return ["distrobox-host-exec", *command]
    return command


def launch_agent(agent_name: str, project_dir: Path) -> tuple[bool, str]:
    """Start an agent independently of the dashboard, returning launch errors."""
    agent_cmd = AGENTS.get(agent_name)
    if agent_cmd is None:
        return False, f"Unknown agent: {agent_name}"
    try:
        if not project_dir.is_dir():
            return False, f"Project folder does not exist: {project_dir}"
        subprocess.Popen(
            build_launch_command(agent_cmd, project_dir, current_container_name()),
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, ValueError) as exc:
        return False, f"Could not launch {agent_name}: {exc}"
    return True, f"Launched {agent_name} in {project_dir.name}"
