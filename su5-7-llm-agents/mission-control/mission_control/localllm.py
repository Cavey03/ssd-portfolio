"""Parse what the local model server (Ollama) and nvidia-smi report, and control the server.

No UI code. The parse functions and their tests were written by the local model itself
(ornith-1.5:9b via Codex), see local-llm/agentic-runs/2026-11-18-localllm/; the reading
and control functions at the bottom by Claude Code.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from mission_control.containers import current_container_name


@dataclass(frozen=True)
class InstalledModel:
    """One model on disk (from Ollama's /api/tags)."""

    name: str
    size_bytes: int
    parameter_size: str | None      # details.parameter_size, e.g. "9.0B"
    quantization: str | None        # details.quantization_level, e.g. "Q4_K_M"


@dataclass(frozen=True)
class LoadedModel:
    """One model loaded in memory (from Ollama's /api/ps)."""

    name: str
    size_bytes: int                 # "size"
    vram_bytes: int                 # "size_vram"
    context_length: int | None      # "context_length"
    expires_at: datetime | None     # "expires_at"

    @property
    def gpu_percent(self) -> int:
        """How much of the model sits in GPU memory; below 100 means part spilled into RAM."""
        if self.size_bytes == 0:
            return 0
        return round(100 * self.vram_bytes / self.size_bytes)


@dataclass(frozen=True)
class GpuInfo:
    """The GPU's memory use and load (from nvidia-smi)."""

    name: str
    memory_used_mb: int
    memory_total_mb: int
    utilization_percent: int | None   # None when nvidia-smi prints "[N/A]"


def parse_timestamp(value: object) -> datetime | None:
    """Parse Ollama's timestamps, which have nanoseconds that datetime can't hold."""
    if not isinstance(value, str):
        return None
    if "." in value:
        date_part, frac = value.split(".", 1)
        date_part = date_part + "." + frac[:6]
    else:
        date_part = value
    if date_part.endswith("Z"):
        date_part = date_part[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(date_part)
    except ValueError:
        return None


def _models_list(text: str) -> list[object]:
    """Return the "models" list of an Ollama reply; ValueError if the reply isn't shaped like one."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"not JSON: {exc}") from exc
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        raise ValueError("'models' is not a list")
    return models


def parse_tags(text: str) -> tuple[InstalledModel, ...]:
    """Parse /api/tags: the installed models, sorted by name."""
    models = _models_list(text)

    result: list[InstalledModel] = []
    for entry in models:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        size = entry.get("size")
        size_bytes = size if isinstance(size, int) else 0
        details = entry.get("details")
        parameter_size = details.get("parameter_size") if isinstance(details, dict) else None
        quantization = details.get("quantization_level") if isinstance(details, dict) else None
        result.append(InstalledModel(
            name=name,
            size_bytes=size_bytes,
            parameter_size=parameter_size,
            quantization=quantization,
        ))
    return tuple(sorted(result, key=lambda m: m.name))


def parse_ps(text: str) -> tuple[LoadedModel, ...]:
    """Parse /api/ps: the models loaded in memory right now."""
    models = _models_list(text)

    result: list[LoadedModel] = []
    for entry in models:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        size = entry.get("size")
        size_bytes = size if isinstance(size, int) else 0
        size_vram = entry.get("size_vram")
        vram_bytes = size_vram if isinstance(size_vram, int) else 0
        context_length = entry.get("context_length")
        context_length = context_length if isinstance(context_length, int) else None
        expires_at = parse_timestamp(entry.get("expires_at"))
        result.append(LoadedModel(
            name=name,
            size_bytes=size_bytes,
            vram_bytes=vram_bytes,
            context_length=context_length,
            expires_at=expires_at,
        ))
    return tuple(result)


def parse_nvidia_smi(text: str) -> GpuInfo | None:
    """Parse nvidia-smi's CSV line "name, used MB, total MB, busy %"; None if it doesn't fit."""
    if not text.strip():
        return None
    first_line = text.splitlines()[0].strip()
    parts = first_line.split(",")
    if len(parts) < 4:
        return None
    try:
        name = parts[0].strip()
        used_mb = int(parts[1].strip())
        total_mb = int(parts[2].strip())
        raw_util = parts[3].strip()
    except ValueError:
        return None
    if raw_util == "[N/A]":
        util_percent: int | None = None
    else:
        try:
            util_percent = int(raw_util)
        except ValueError:
            return None
    return GpuInfo(
        name=name,
        memory_used_mb=used_mb,
        memory_total_mb=total_mb,
        utilization_percent=util_percent,
    )


# --- Reading and controlling the server (written by Claude Code) -------------------------------
# Everything above parses text; everything below talks to the outside world (HTTP, commands).

OLLAMA_URL = "http://127.0.0.1:11434"
"""Default server address (the user service listens only on this machine)."""
NVIDIA_SMI_QUERY = [
    "nvidia-smi",
    "--query-gpu=name,memory.used,memory.total,utilization.gpu",
    "--format=csv,noheader,nounits",
]


@dataclass(frozen=True)
class OllamaStatus:
    """Everything the Local LLM panel shows about the server."""

    running: bool
    version: str | None = None
    installed: tuple[InstalledModel, ...] = ()
    loaded: tuple[LoadedModel, ...] = ()
    error: str | None = None


def ollama_url() -> str:
    """Return the server address: $MISSION_CONTROL_OLLAMA_URL or the default."""
    return os.environ.get("MISSION_CONTROL_OLLAMA_URL", OLLAMA_URL).rstrip("/")


def host_command(argv: list[str]) -> list[str]:
    """Run `argv` on the host, even when Mission Control runs inside the `dev` container.

    `systemctl --user` and `nvidia-smi` belong to the host: `dev` has no NVIDIA tools
    and its own (empty) service manager.
    """
    if current_container_name() is not None:
        return ["distrobox-host-exec", *argv]
    return argv


def _get(url: str, timeout: float) -> str:
    """GET a URL and return the body as text (raises OSError/URLError on failure)."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def read_ollama(base_url: str | None = None, timeout: float = 1.5) -> OllamaStatus:
    """Ask the server for its version, installed models and loaded models.

    A server that doesn't answer is reported as stopped, not as an error: it is
    started by hand, so "stopped" is the normal state.
    """
    url = base_url or ollama_url()
    try:
        version = json.loads(_get(f"{url}/api/version", timeout)).get("version")
    except (OSError, ValueError, AttributeError):
        return OllamaStatus(running=False)
    version = version if isinstance(version, str) else None
    try:
        installed = parse_tags(_get(f"{url}/api/tags", timeout))
        loaded = parse_ps(_get(f"{url}/api/ps", timeout))
    except (OSError, ValueError) as exc:
        return OllamaStatus(running=True, version=version, error=f"bad reply from Ollama: {exc}")
    return OllamaStatus(running=True, version=version, installed=installed, loaded=loaded)


def read_gpu(timeout: float = 3.0) -> GpuInfo | None:
    """Return the GPU's memory use and load from nvidia-smi, or None if unavailable."""
    try:
        result = subprocess.run(
            host_command(NVIDIA_SMI_QUERY), capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return parse_nvidia_smi(result.stdout)


def set_service(start: bool, timeout: float = 20.0) -> tuple[bool, str]:
    """Start or stop the Ollama user service; return (ok, message for the user)."""
    verb = "start" if start else "stop"
    try:
        result = subprocess.run(
            host_command(["systemctl", "--user", verb, "ollama"]),
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Could not {verb} Ollama: {exc}"
    if result.returncode != 0:
        lines = result.stderr.strip().splitlines()
        return False, f"Could not {verb} Ollama: {lines[-1] if lines else f'exit code {result.returncode}'}"
    return True, "Ollama started" if start else "Ollama stopped"
