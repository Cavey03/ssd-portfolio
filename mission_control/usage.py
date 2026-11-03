"""Read AI subscription usage from the agents' local log files.

- Codex (ChatGPT): every session log contains `token_count` events with the
  real plan limits: the 5-hour and weekly windows as a used percentage, plus
  their reset times. We take the newest one.
- Claude Code: the session logs contain token counts per message, but not the
  plan limit percentage. We add up the tokens for the last 5 hours and 7 days.
  This is an activity measure, not an official "% of limit".
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CODEX_SESSIONS = Path.home() / ".codex" / "sessions"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"

FIVE_HOURS = 5 * 3600
SEVEN_DAYS = 7 * 86400


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
    """Claude Code activity totals from local logs."""

    requests_5h: int
    output_tokens_5h: int
    requests_7d: int
    output_tokens_7d: int


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


def _parse_timestamp(text: str) -> float | None:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


def read_claude_usage(projects_dir: Path = CLAUDE_PROJECTS, now: float | None = None) -> ClaudeUsage:
    """Add up Claude Code requests and output tokens for the last 5 hours and 7 days.

    One API response is logged once per content block, so messages are
    counted once per unique message id.
    """
    now = now or time.time()
    seen: set[str] = set()
    req_5h = out_5h = req_7d = out_7d = 0
    try:
        logs = [p for p in projects_dir.rglob("*.jsonl") if p.stat().st_mtime >= now - SEVEN_DAYS]
    except OSError:
        logs = []
    for log in logs:
        try:
            handle = log.open(errors="replace")
        except OSError:
            continue
        with handle:
            for line in handle:
                if '"usage"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = record.get("message")
                if not isinstance(message, dict) or not isinstance(message.get("usage"), dict):
                    continue
                msg_id = message.get("id")
                if not msg_id or msg_id in seen:
                    continue
                seen.add(msg_id)
                ts = _parse_timestamp(record.get("timestamp", ""))
                if ts is None or ts < now - SEVEN_DAYS:
                    continue
                output = int(message["usage"].get("output_tokens") or 0)
                req_7d += 1
                out_7d += output
                if ts >= now - FIVE_HOURS:
                    req_5h += 1
                    out_5h += output
    return ClaudeUsage(req_5h, out_5h, req_7d, out_7d)
