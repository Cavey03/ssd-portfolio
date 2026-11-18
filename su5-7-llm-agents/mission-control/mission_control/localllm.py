"""Parse what the local model server (Ollama) and nvidia-smi report."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime


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
