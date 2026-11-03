"""Read AI subscription usage from the agents' local log files.

- Codex (ChatGPT): every session log contains `token_count` events with the
  real plan limits: the 5-hour and weekly windows as a used percentage, plus
  their reset times. We take the newest one.
- Claude Code: keeps the same numbers that its /usage command shows in a
  cache inside ~/.claude.json ("cachedUsageUtilization"): the 5-hour and
  weekly utilization in percent, with reset times. Claude Code refreshes that
  cache itself; we only read it. It is an internal format, so every field is
  treated as optional.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CODEX_SESSIONS = Path.home() / ".codex" / "sessions"
CLAUDE_CONFIG = Path.home() / ".claude.json"


@dataclass(frozen=True)
class LimitWindow:
    """One rate-limit window, e.g. the 5-hour or weekly limit."""

    used_percent: float
    window_minutes: int
    resets_at: float | None


@dataclass(frozen=True)
class CodexUsage:
    """Latest known ChatGPT/Codex plan limits."""

    plan: str | None
    five_hour: LimitWindow | None
    weekly: LimitWindow | None
    observed_at: float
    """When this snapshot was written (mtime of the log file)."""


@dataclass(frozen=True)
class ClaudeUsage:
    """Latest known Claude plan limits."""

    five_hour: LimitWindow | None
    weekly: LimitWindow | None
    observed_at: float | None
    """When Claude Code fetched these numbers."""


def _window(data: object, now: float) -> LimitWindow | None:
    """Parse one rate-limit window. A window whose reset time has passed counts as 0%."""
    if not isinstance(data, dict):
        return None
    try:
        used = float(data["used_percent"])
        minutes = int(data["window_minutes"])
    except (KeyError, TypeError, ValueError):
        return None
    resets = data.get("resets_at")
    resets_at = float(resets) if isinstance(resets, (int, float)) else None
    if resets_at is not None and resets_at <= now:
        used = 0.0  # the window has reset since the log was written
    return LimitWindow(used, minutes, resets_at)


def parse_codex_rate_limits(line: str, observed_at: float, now: float) -> CodexUsage | None:
    """Parse a Codex log line holding a `rate_limits` object."""
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    payload = record.get("payload", record) if isinstance(record, dict) else None
    limits = payload.get("rate_limits") if isinstance(payload, dict) else None
    if not isinstance(limits, dict):
        return None
    return CodexUsage(
        plan=limits.get("plan_type"),
        five_hour=_window(limits.get("primary"), now),
        weekly=_window(limits.get("secondary"), now),
        observed_at=observed_at,
    )


def read_codex_usage(sessions_dir: Path = CODEX_SESSIONS) -> CodexUsage | None:
    """Return the newest rate-limit snapshot from the Codex session logs."""
    now = time.time()
    try:
        logs = sorted(sessions_dir.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return None
    for log in logs[:10]:  # the newest few are enough
        try:
            lines = log.read_text(errors="replace").splitlines()
            mtime = log.stat().st_mtime
        except OSError:
            continue
        for line in reversed(lines):
            if '"rate_limits"' in line:
                usage = parse_codex_rate_limits(line, mtime, now)
                if usage is not None:
                    return usage
    return None


def _parse_timestamp(text: object) -> float | None:
    """Parse an ISO 8601 time such as "2026-11-03T22:40:00.16+00:00"."""
    if not isinstance(text, str):
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _claude_window(data: object, minutes: int, now: float) -> LimitWindow | None:
    """Turn {"utilization": 4, "resets_at": "..."} into a LimitWindow."""
    if not isinstance(data, dict):
        return None
    value = data.get("utilization")
    if not isinstance(value, (int, float)):
        return None
    return _window(
        {"used_percent": value, "window_minutes": minutes, "resets_at": _parse_timestamp(data.get("resets_at"))},
        now,
    )


def parse_claude_config(text: str, now: float) -> ClaudeUsage | None:
    """Read the cached plan utilization out of ~/.claude.json's contents."""
    try:
        config = json.loads(text)
    except json.JSONDecodeError:
        return None
    cache = config.get("cachedUsageUtilization") if isinstance(config, dict) else None
    if not isinstance(cache, dict) or not isinstance(cache.get("utilization"), dict):
        return None
    utilization = cache["utilization"]
    fetched_ms = cache.get("fetchedAtMs")
    return ClaudeUsage(
        five_hour=_claude_window(utilization.get("five_hour"), 300, now),
        weekly=_claude_window(utilization.get("seven_day"), 10080, now),
        observed_at=fetched_ms / 1000 if isinstance(fetched_ms, (int, float)) else None,
    )


def read_claude_usage(config_path: Path = CLAUDE_CONFIG) -> ClaudeUsage | None:
    """Return Claude's cached plan limits, or None if they aren't available."""
    try:
        text = config_path.read_text()
    except OSError:
        return None
    return parse_claude_config(text, time.time())
