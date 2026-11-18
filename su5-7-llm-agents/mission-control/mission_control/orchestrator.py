"""The orchestrator: Opus plans each dispatched task and reviews the result.

Design: orchestrator–workers. A strong model (Opus 5.5, through `claude -p`) decides
which worker should do a task (the local model, Codex/GPT or Claude), writes the
worker's brief and time limit, and later reviews the worker's changes. The owner
confirms the plan before anything starts and approves every merge.

Both calls use `claude -p` with no tools and `--json-schema`, so the reply is
validated JSON. The routing rules below come from measured experience: the
local 9B model looped on a large task but finished a small one quickly
(local-llm/agentic-runs/2026-11-18-localllm/).

The decisions are logged (tasks.DECISIONS) for transparency. They are NOT
training data: Anthropic's terms forbid training models on Claude's output.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ORCHESTRATOR_MODEL = "opus"
PLAN_TIMEOUT_SECONDS = 180
REVIEW_TIMEOUT_SECONDS = 300
AGENTS = ("local", "codex", "claude")
MAX_DIFF_CHARS = 60_000
MAX_LOG_CHARS = 6_000

ROUTING_RULES = """\
Choose ONE worker for the task. Prefer the cheapest worker that will very likely succeed.

- "local": a 9B model on the owner's GPU (via Codex CLI). Free, offline and private, but weak:
  it handles SMALL, single-step, well-specified tasks touching one or two files (add a function or a
  test, fix a clear bug, add docstrings, rename, small refactor). It loops in its own reasoning on
  larger tasks and struggles to find its own small mistakes. Only allowed when the local server is
  running. Time limit 10 minutes. Its brief must be short and concrete: name the exact files and
  functions, give examples, and end with "Write the change first, then run the tests, then fix."
- "codex": GPT through Codex CLI (cloud, uses the owner's ChatGPT plan). Good at well-specified
  multi-file features and tests. Time limit 25 minutes.
- "claude": Claude Code (cloud, uses the owner's Claude plan). Best for ambiguous or design-heavy
  work, changes across many files, and anything needing judgement. Time limit 25 minutes.

Write the worker's brief as a precise instruction for that worker: what to change, where, how to
check it (tests), and what not to touch. Workers run unattended in a separate git worktree of the
project, cannot ask questions, and must not commit.
"""

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "agent": {"type": "string", "enum": list(AGENTS)},
        "model": {"type": ["string", "null"]},
        "reason": {"type": "string"},
        "brief": {"type": "string"},
        "time_limit_minutes": {"type": "integer", "minimum": 1, "maximum": 60},
    },
    "required": ["agent", "model", "reason", "brief", "time_limit_minutes"],
    "additionalProperties": False,
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["approve", "changes", "reject"]},
        "summary": {"type": "string"},
        "concerns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "summary", "concerns"],
    "additionalProperties": False,
}


class OrchestratorError(Exception):
    """The orchestrator couldn't be asked, or its reply was unusable."""


@dataclass(frozen=True)
class Plan:
    """The orchestrator's decision for one task."""

    agent: str
    model: str | None
    reason: str
    brief: str
    time_limit_minutes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "agent": self.agent, "model": self.model, "reason": self.reason,
            "brief": self.brief, "time_limit_minutes": self.time_limit_minutes,
        }


@dataclass(frozen=True)
class Review:
    """The orchestrator's review of a finished task."""

    verdict: str
    """"approve", "changes" (needs work) or "reject"."""
    summary: str
    concerns: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {"verdict": self.verdict, "summary": self.summary, "concerns": list(self.concerns)}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Review:
        concerns = data.get("concerns")
        return cls(
            verdict=str(data.get("verdict", "")),
            summary=str(data.get("summary", "")),
            concerns=tuple(str(c) for c in concerns) if isinstance(concerns, list) else (),
        )


def project_context(project_dir: Path, max_files: int = 150, max_rules_lines: int = 60) -> str:
    """Describe a project for the orchestrator: its rules file and its tracked files."""
    parts = [f"Project folder: {project_dir.name} ({project_dir})"]
    for name in ("CLAUDE.md", "AGENTS.md", "README.md"):
        rules = project_dir / name
        if rules.is_file():
            try:
                lines = rules.read_text(errors="replace").splitlines()[:max_rules_lines]
            except OSError:
                continue
            parts.append(f"--- {name} (first {len(lines)} lines) ---\n" + "\n".join(lines))
            break  # one is enough to explain the project
    try:
        listing = subprocess.run(
            ["git", "-C", str(project_dir), "ls-files", "--", "."],
            capture_output=True, text=True, timeout=10, check=False,
        ).stdout.splitlines()
    except (OSError, subprocess.TimeoutExpired):
        listing = []
    if listing:
        more = f"\n(... {len(listing) - max_files} more)" if len(listing) > max_files else ""
        parts.append("--- tracked files ---\n" + "\n".join(listing[:max_files]) + more)
    return "\n\n".join(parts)


def _ask(prompt: str, schema: dict[str, object], timeout: float) -> dict[str, object]:
    """Ask the orchestrator model for JSON matching `schema` (no tools, nothing saved)."""
    command = [
        "claude", "-p", "--model", ORCHESTRATOR_MODEL, "--output-format", "json",
        "--no-session-persistence", "--tools", "", "--json-schema", json.dumps(schema), prompt,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise OrchestratorError("the claude command was not found") from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OrchestratorError(f"asking {ORCHESTRATOR_MODEL} failed: {exc}") from exc
    try:
        reply = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        lines = (result.stderr or result.stdout).strip().splitlines()
        raise OrchestratorError(lines[-1] if lines else f"claude exited with {result.returncode}") from exc
    if not isinstance(reply, dict) or reply.get("is_error"):
        raise OrchestratorError(str(reply.get("result") if isinstance(reply, dict) else reply)[:300])
    data = reply.get("structured_output")
    if not isinstance(data, dict):
        raise OrchestratorError("the reply had no structured output")
    return data


def build_plan_prompt(
    task: str, context: str, local_models: list[str], local_running: bool, default_local: str | None
) -> str:
    """The text the orchestrator gets when planning a task."""
    if local_running and local_models:
        local = f"running; installed models: {', '.join(local_models)}; default: {default_local or local_models[0]}"
    else:
        local = "NOT running, so do not choose \"local\""
    return (
        "You are the orchestrator of a small team of coding agents.\n\n"
        f"{ROUTING_RULES}\n"
        f"Local model server: {local}.\n"
        "For \"local\" set model to one of the installed models; for \"codex\" and \"claude\" set it to null "
        "(their default model).\n\n"
        f"TASK from the owner:\n{task}\n\n"
        f"PROJECT CONTEXT:\n{context}\n"
    )


def plan_task(
    task: str,
    project_dir: Path,
    local_models: list[str],
    local_running: bool,
    default_local: str | None = None,
) -> Plan:
    """Ask the orchestrator which worker should do `task`, with a brief and a time limit."""
    prompt = build_plan_prompt(task, project_context(project_dir), local_models, local_running, default_local)
    data = _ask(prompt, PLAN_SCHEMA, PLAN_TIMEOUT_SECONDS)
    return parse_plan(data, local_models, local_running, default_local)


def parse_plan(
    data: dict[str, object], local_models: list[str], local_running: bool, default_local: str | None
) -> Plan:
    """Check the orchestrator's plan against what is actually possible right now."""
    agent = data.get("agent")
    if agent not in AGENTS:
        raise OrchestratorError(f"unknown agent in plan: {agent!r}")
    if agent == "local" and not (local_running and local_models):
        raise OrchestratorError("the plan chose the local model, but it isn't running")
    model = data.get("model") if isinstance(data.get("model"), str) else None
    if agent == "local" and model not in local_models:
        model = default_local if default_local in local_models else local_models[0]
    if agent != "local":
        model = None
    try:
        minutes = max(1, min(60, int(data.get("time_limit_minutes", 10))))
    except (TypeError, ValueError):
        minutes = 10
    return Plan(
        agent=str(agent),
        model=model,
        reason=str(data.get("reason", "")),
        brief=str(data.get("brief", "")),
        time_limit_minutes=minutes,
    )


def build_review_prompt(title: str, brief: str, agent: str, outcome: str, diff: str, log_tail: str) -> str:
    """The text the orchestrator gets when reviewing a finished task."""
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + f"\n... (diff cut at {MAX_DIFF_CHARS} characters)"
    return (
        "You are reviewing the work of an AI coding agent before the owner decides whether to merge it.\n"
        "verdict: \"approve\" if it does the task correctly and safely, \"changes\" if it is close but needs "
        "fixes, \"reject\" if it is wrong, unsafe or off-task. summary: 2-4 sentences for the owner. "
        "concerns: specific problems (bugs, missing tests, files touched that shouldn't be), empty if none.\n\n"
        f"TASK: {title}\n\nBRIEF GIVEN TO THE WORKER ({agent}):\n{brief}\n\n"
        f"OUTCOME: {outcome}\n\n"
        f"END OF THE WORKER'S LOG:\n{log_tail[-MAX_LOG_CHARS:]}\n\n"
        f"DIFF:\n{diff or '(no changes)'}\n"
    )


def review_task(title: str, brief: str, agent: str, outcome: str, diff: str, log_tail: str) -> Review:
    """Ask the orchestrator to review a worker's changes."""
    data = _ask(build_review_prompt(title, brief, agent, outcome, diff, log_tail), REVIEW_SCHEMA,
                REVIEW_TIMEOUT_SECONDS)
    review = Review.from_dict(data)
    if review.verdict not in ("approve", "changes", "reject"):
        raise OrchestratorError(f"unknown verdict: {review.verdict!r}")
    return review
