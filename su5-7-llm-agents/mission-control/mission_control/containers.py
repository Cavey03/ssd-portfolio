"""Read and control host Distrobox containers without UI code."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

LIST_TIMEOUT_SECONDS = 10
ACTION_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class ContainerInfo:
    """Summary of one Distrobox container."""

    name: str
    state: str
    image: str
    status_text: str


@dataclass(frozen=True)
class ContainerResult:
    """Container listing or a readable error."""

    containers: list[ContainerInfo]
    error: str | None = None


def parse_podman_json(output: str) -> list[ContainerInfo]:
    """Parse a Podman listing, raising ValueError for invalid JSON or shape."""
    entries = json.loads(output)
    if not isinstance(entries, list):
        raise ValueError("Expected a JSON list from podman")

    containers = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Expected a container object from podman")
        names = entry.get("Names")
        name = names[0] if isinstance(names, list) and names else names
        # A nameless entry cannot be selected or controlled safely.
        if not isinstance(name, str) or not name.strip():
            continue
        containers.append(ContainerInfo(
            name=name,
            state=str(entry.get("State") or "unknown").lower(),
            image=str(entry.get("Image") or "—"),
            status_text=str(entry.get("Status") or "—"),
        ))
    return sorted(containers, key=lambda container: container.name.lower())


def current_container_name(containerenv_path: Path = Path("/run/.containerenv")) -> str | None:
    """Read the current container name from the environment or containerenv."""
    name = os.environ.get("CONTAINER_ID", "").strip()
    if name:
        return name
    try:
        for line in containerenv_path.read_text().splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and key == "name":
                return value.strip().strip("\"'") or None
    except (OSError, UnicodeError):
        pass
    return None


def _podman_command(*args: str) -> list[str]:
    """Build a host Podman command, also supporting execution on the host."""
    if current_container_name() is None and shutil.which("podman"):
        return ["podman", *args]
    return ["distrobox-host-exec", "podman", *args]


def _run_podman(*args: str, timeout: int) -> tuple[bool, str]:
    """Run Podman with a timeout and turn command failures into messages."""
    try:
        result = subprocess.run(
            _podman_command(*args),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"podman {args[0]} timed out after {timeout}s"
    except (OSError, UnicodeError) as exc:
        return False, str(exc)
    if result.returncode != 0:
        lines = result.stderr.strip().splitlines()
        return False, lines[-1] if lines else f"podman exited with {result.returncode}"
    return True, result.stdout


def list_containers() -> ContainerResult:
    """List only Distrobox containers, returning errors without raising."""
    ok, output = _run_podman(
        "ps", "-a", "--filter", "label=manager=distrobox", "--format", "json",
        timeout=LIST_TIMEOUT_SECONDS,
    )
    if not ok:
        return ContainerResult([], error=output)
    try:
        return ContainerResult(parse_podman_json(output))
    except ValueError as exc:
        return ContainerResult([], error=f"Invalid podman output: {exc}")


def start_container(name: str) -> tuple[bool, str]:
    """Start a named container without raising on command failure."""
    if not name.strip():
        return False, "Select a container first."
    ok, message = _run_podman("start", "--", name, timeout=ACTION_TIMEOUT_SECONDS)
    return ok, f"Started {name}." if ok else message


def stop_container(name: str) -> tuple[bool, str]:
    """Stop a named container, refusing to stop the app's own container."""
    if not name.strip():
        return False, "Select a container first."
    if name == current_container_name():
        return False, f"Cannot stop {name}: Mission Control is running inside it."
    ok, message = _run_podman("stop", "--", name, timeout=ACTION_TIMEOUT_SECONDS)
    return ok, f"Stopped {name}." if ok else message
