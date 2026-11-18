"""Read AI subscription usage from the agents' local log files.

- Codex (ChatGPT): every session log contains `token_count` events with the
  real plan limits: the 5-hour and weekly windows as a used percentage, plus
  their reset times. We take the newest one.
- Claude Code: keeps the same numbers that its /usage command shows in a
  cache inside ~/.claude.json ("cachedUsageUtilization"): the 5-hour and
  weekly utilization in percent, with reset times. Claude Code refreshes that
  cache itself; we only read it. It is an internal format, so every field is
  treated as optional.
- Local model (Ollama): has no plan limits, so instead we count the tokens it
  processed: Codex sessions whose log says `model_provider: "ollama"`, using the
  last `total_token_usage` in each. That is roughly what those sessions would
  otherwise have cost in cloud usage.
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
class LocalUsage:
    """Tokens processed by the local model (Codex sessions on Ollama)."""

    today_tokens: int
    today_sessions: int
    week_tokens: int
    week_sessions: int
    """The last 7 days, including today."""


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
    five_hour, weekly = _window(limits.get("primary"), now), _window(limits.get("secondary"), now)
    if five_hour is None and weekly is None:
        # No limits at all: a session on the local model (Ollama has no plan) writes
        # all-null rate_limits. It says nothing about the ChatGPT plan, so skip it.
        return None
    return CodexUsage(
        plan=limits.get("plan_type"),
        five_hour=five_hour,
        weekly=weekly,
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


def read_claude_usage(
    config_path: Path = CLAUDE_CONFIG, now: float | None = None
) -> ClaudeUsage | None:
    """Return Claude's cached plan limits, or None if they aren't available.

    `now` defaults to the current time; tests pass a fixed time.
    """
    try:
        text = config_path.read_text()
    except OSError:
        return None
    return parse_claude_config(text, time.time() if now is None else now)


LOCAL_PROVIDERS = frozenset({"ollama"})
"""Codex `model_provider` values that mean the model ran on this machine."""
_local_cache: dict[Path, tuple[float, int | None]] = {}
"""log file -> (mtime, tokens or None for a cloud session); a log is only re-read when it changes."""


def session_local_tokens(log: Path) -> int | None:
    """Return the total tokens of a local-model session log, or None for a cloud session.

    The first line (`session_meta`) names the provider, so cloud logs are rejected
    after one line. `total_token_usage` is a running total; the last one counts.
    """
    with log.open(errors="replace") as f:
        try:
            meta = json.loads(f.readline())
        except json.JSONDecodeError:
            return None
        payload = meta.get("payload") if isinstance(meta, dict) else None
        if meta.get("type") != "session_meta" or not isinstance(payload, dict):
            return None
        if payload.get("model_provider") not in LOCAL_PROVIDERS:
            return None
        total = 0
        for line in f:
            if '"total_token_usage"' not in line:
                continue  # cheap check before parsing JSON
            try:
                info = json.loads(line)["payload"]["info"]["total_token_usage"]
                total = int(info["total_tokens"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
        return total


def read_local_usage(sessions_dir: Path = CODEX_SESSIONS, now: float | None = None) -> LocalUsage:
    """Add up the local model's tokens for today and the last 7 days.

    A session counts on the day it was last active (the log's modification time).
    """
    now = time.time() if now is None else now
    week_start = now - 7 * 24 * 3600
    today_start = datetime.fromtimestamp(now).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    today = [0, 0]
    week = [0, 0]
    try:
        logs = list(sessions_dir.rglob("*.jsonl"))
    except OSError:
        logs = []
    for log in logs:
        try:
            mtime = log.stat().st_mtime
            if mtime < week_start:
                continue
            cached = _local_cache.get(log)
            if cached is not None and cached[0] == mtime:
                tokens = cached[1]
            else:
                tokens = session_local_tokens(log)
                _local_cache[log] = (mtime, tokens)
        except OSError:
            continue
        if tokens is None:
            continue
        week[0] += tokens
        week[1] += 1
        if mtime >= today_start:
            today[0] += tokens
            today[1] += 1
    return LocalUsage(today[0], today[1], week[0], week[1])
