"""Launch agents in detached host Konsole tabs without UI code."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from mission_control.containers import current_container_name

AGENTS: dict[str, list[str]] = {
    "Claude": ["claude"],
    "Codex": ["codex"],
    "Agy": ["agy"],
    # Codex on the local model: the "local" profile points it at Ollama (local-llm/README.md).
    "Local": ["codex", "-p", "local"],
}


def build_launch_command(
    agent_cmd: str | list[str], project_dir: Path, container: str | None
) -> list[str]:
    """Build a host Konsole command that enters the project in Distrobox.

    It opens a new Konsole window. With --new-tab, Konsole adds the tab to the
    most recently used window, which can be hard to find.
    `agent_cmd` is a program name or a full argument list; every word is quoted.
    """
    argv = [agent_cmd] if isinstance(agent_cmd, str) else agent_cmd
    command = [
        "konsole", "--workdir", str(project_dir), "-e",
        "distrobox", "enter", container or "dev", "--", "bash", "-lc",
        f"cd {shlex.quote(str(project_dir))} && exec {shlex.join(argv)}",
    ]
    if container is not None:
        return ["distrobox-host-exec", *command]
    return command


def launch_agent(
    agent_name: str, project_dir: Path, model: str | None = None
) -> tuple[bool, str]:
    """Start an agent independently of the dashboard, returning launch errors.

    `model` picks the model (`-m`), used for the local model.
    """
    agent_cmd = AGENTS.get(agent_name)
    if agent_cmd is None:
        return False, f"Unknown agent: {agent_name}"
    if model:
        agent_cmd = [*agent_cmd, "-m", model]
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
    what = f"{agent_name} ({model})" if model else agent_name
    return True, f"Launched {what} in {project_dir.name}"
