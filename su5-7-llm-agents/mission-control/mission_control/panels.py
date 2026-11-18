"""Dashboard panels.

Colours come from the active theme (see themes.py). Each panel remembers the
last data it showed, so recolour() can redraw it instantly when the theme
changes instead of waiting for the next refresh.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.binding import Binding
from textual.widgets import DataTable, Static

from mission_control.agents import AgentProcess, describe_folder, format_age
from mission_control.containers import ContainerInfo, ContainerResult
from mission_control.gitinfo import ProjectStatus
from mission_control.localllm import GpuInfo, LoadedModel, OllamaStatus
from mission_control.tasks import Task
from mission_control.themes import DEFAULT_PALETTE, Palette, palette_from_variables
from mission_control.usage import ClaudeUsage, CodexUsage, LocalUsage

# Mission Teal colours as constants, used as defaults for the cell helpers.
OK = DEFAULT_PALETTE.ok
WARN = DEFAULT_PALETTE.warn
INFO = DEFAULT_PALETTE.info
ALERT = DEFAULT_PALETTE.alert
MUTED = DEFAULT_PALETTE.muted

AGENT_NAMES = ("claude", "codex", "agy")


class _ThemedPanel(Vertical):
    """A panel that draws with the active theme and can redraw on theme change."""

    _last: tuple[Any, ...] | None = None

    @property
    def palette(self) -> Palette:
        """Plain colours for the active theme."""
        try:
            return palette_from_variables(self.app.get_css_variables())
        except Exception:  # not attached to an app (shouldn't happen when mounted)
            return DEFAULT_PALETTE

    def show(self, *args: Any) -> None:  # overridden by each panel
        raise NotImplementedError

    def recolour(self) -> None:
        """Redraw the last data with the current theme's colours."""
        if self._last is not None:
            self.show(*self._last)


class _TablePanel(_ThemedPanel):
    """A titled panel holding one selectable table.

    Each row's key is the item's name, so the selection survives refreshes even
    when the cells are styled text.
    """

    PANEL_TITLE: ClassVar[str]
    COLUMNS: ClassVar[tuple[str, ...]]

    def compose(self) -> ComposeResult:
        yield Static("", classes="panel-label")
        yield DataTable(cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        """Set the border title, create the columns, then fill the table.

        Subclasses override populate() rather than on_mount(): Textual calls the
        on_mount of every class in the chain itself, so overriding it again
        would set things up twice or in the wrong order.
        """
        self.border_title = self.PANEL_TITLE
        self.query_one(DataTable).add_columns(*self.COLUMNS)
        self.populate()

    def populate(self) -> None:
        """Fill the table with initial rows. Default: leave it empty."""

    @property
    def table(self) -> DataTable:
        """The panel's table widget."""
        return self.query_one(DataTable)

    @property
    def selected_name(self) -> str | None:
        """Return the name of the selected row, if any."""
        table = self.table
        if not table.row_count:
            return None
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return row_key.value

    def set_label(self, text: str | Text) -> None:
        """Set the small line of text above the table."""
        self.query_one(".panel-label", Static).update(text)

    def _restore_selection(self, selected: str | None, keys: list[str]) -> None:
        if selected in keys:
            self.table.move_cursor(row=keys.index(selected))


class ProjectsPanel(_TablePanel):
    """The projects below the projects root with their live git status.

    Row keys are paths relative to the root ("." is the root), so the launch
    keys can open an agent in exactly that folder.
    """

    PANEL_TITLE = "Projects"
    COLUMNS = ("Name", "Branch", "Changes", "Sync")

    def show(self, root: Path, statuses: list[ProjectStatus]) -> None:
        """Replace the rows with fresh statuses, keeping the selected project."""
        self._last = (root, statuses)
        pal = self.palette
        selected = self.selected_name
        self.table.clear()
        keys = [s.key or s.name for s in statuses]
        for status, key in zip(statuses, keys):
            self.table.add_row(*_project_cells(status, pal), key=key)
        self._restore_selection(selected, keys)

        if statuses:
            repos = sum(s.is_repo and not s.in_root_repo for s in statuses)
            self.set_label(f"{root}  ·  {len(statuses)} projects  ·  {repos} repos")
        else:
            self.set_label(f"{root}  ·  no projects found")
        self.border_subtitle = f"updated {datetime.now():%H:%M:%S}"


def _project_cells(
    status: ProjectStatus, pal: Palette = DEFAULT_PALETTE
) -> tuple[Text, Text, Text, Text]:
    """Turn a ProjectStatus into the four styled table cells.

    Folders inside the root repo are indented under it and leave Branch and Sync
    to the root's row, because they share them.
    """
    if status.in_root_repo:
        name = Text().append("  └ ", style=pal.muted).append(status.name)  # only the glyph is dim
    else:
        name = Text(status.name, style="bold")

    if not status.is_repo:
        return name, Text("—", style=pal.muted), Text("not a git repo", style=pal.muted), Text("")
    if status.error:
        return name, Text("—", style=pal.muted), Text(f"⚠ {status.error}", style=pal.alert), Text("")

    branch_style = pal.warn if status.branch == "(detached)" else ""
    branch = Text(status.branch or "?", style=branch_style)

    if status.changes:
        changes = Text(f"● {status.changes} changed", style=pal.warn)
    else:
        changes = Text("✓ clean", style=pal.ok)
    if status.in_root_repo:
        return name, Text("·", style=pal.muted), changes, Text("")

    if status.ahead is None:
        sync = Text("no remote", style=pal.muted)
    elif status.ahead == 0 and status.behind == 0:
        sync = Text("✓ synced", style=pal.ok)
    else:
        sync = Text()
        if status.ahead:
            sync.append(f"↑{status.ahead} to push", style=pal.info)
        if status.behind:
            if sync:
                sync.append("  ")
            sync.append(f"↓{status.behind} to pull", style=pal.alert)

    return name, branch, changes, sync


class ContainersPanel(_TablePanel):
    """Distrobox containers with their live host status."""

    PANEL_TITLE = "Containers"
    COLUMNS = ("Name", "State", "Image")

    def populate(self) -> None:
        """Show a loading label until the first background scan finishes."""
        self.containers: dict[str, ContainerInfo] = {}
        self.set_label("Loading containers…")

    @property
    def selected_container(self) -> ContainerInfo | None:
        """Return the selected container's latest status."""
        return self.containers.get(self.selected_name or "")

    def show(self, result: ContainerResult, current: str | None) -> None:
        """Replace the rows, preserving selection and marking this container."""
        self._last = (result, current)
        pal = self.palette
        selected = self.selected_name
        self.table.clear()
        self.containers = {container.name: container for container in result.containers}
        for container in result.containers:
            self.table.add_row(*_container_cells(container, current, pal), key=container.name)
        names = list(self.containers)
        self._restore_selection(selected, names)
        if result.error:
            self.set_label(Text(f"⚠ {result.error}", style=pal.alert))
        else:
            count = len(names)
            self.set_label(
                f"{count} container{'s' if count != 1 else ''}"
                if names
                else "No Distrobox containers found"
            )
        self.border_subtitle = f"updated {datetime.now():%H:%M:%S}"


_UNIT_SUFFIXES = {
    "second": "s", "minute": "m", "hour": "h", "day": "d", "week": "w", "month": "mo", "year": "y",
}


def _short_uptime(status_text: str) -> str:
    """Shorten podman's "Up About an hour" / "Up 5 minutes" to "1h" / "5m".

    Returns "" for anything that isn't an "Up ..." status.
    """
    words = status_text.lower().split()
    if len(words) < 3 or words[0] != "up":
        return ""
    amount, unit = words[1], words[2].rstrip("s")
    if amount in ("about", "less"):
        # "About an hour", "About a minute", "Less than a second"
        amount, unit = ("<1", "second") if amount == "less" else ("1", words[-1].rstrip("s"))
    suffix = _UNIT_SUFFIXES.get(unit)
    return f"{amount}{suffix}" if suffix and (amount.isdigit() or amount == "<1") else ""


def _container_cells(
    container: ContainerInfo, current: str | None, pal: Palette = DEFAULT_PALETTE
) -> tuple[Text, Text, Text]:
    """Turn a container summary into three styled table cells.

    The uptime goes into the State cell (e.g. "● running · 1h") so the panel
    fits in the narrow right-hand column without a horizontal scrollbar.
    """
    name = container.name + (" (this)" if container.name == current else "")
    if container.state == "running":
        state = Text(f"● {container.state}", style=pal.ok)
        uptime = _short_uptime(container.status_text)
        if uptime:
            state.append(f" · {uptime}", style=pal.muted)
    elif container.state in ("exited", "stopped"):
        state = Text(f"○ {container.state}", style=pal.muted)
    else:
        state = Text(f"● {container.state}", style=pal.warn)
    image = container.image
    registry, separator, remainder = image.partition("/")
    if separator and ("." in registry or ":" in registry or registry == "localhost"):
        image = remainder
    return Text(name, style="bold"), state, Text(image)


class AgentsPanel(_TablePanel):
    """Running AI agent sessions and the folder each one works in."""

    PANEL_TITLE = "Agents"
    COLUMNS = ("Agent", "Project", "Age")

    def populate(self) -> None:
        """Show a loading label until the first scan finishes."""
        self.agents: dict[str, AgentProcess] = {}
        self.set_label("Looking for agents…")

    @property
    def selected_agent(self) -> AgentProcess | None:
        """The agent session in the selected row, if any."""
        return self.agents.get(self.selected_name or "")

    def show(
        self, agents: list[AgentProcess], projects_root: Path, projects: Sequence[str] = ()
    ) -> None:
        """Replace the rows (one per session, keyed by process id)."""
        self._last = (agents, projects_root, projects)
        pal = self.palette
        selected = self.selected_name
        self.table.clear()
        self.agents = {str(a.pid): a for a in agents}
        for agent in agents:
            name = Text(f"● {agent.agent}", style=f"bold {pal.agent(agent.agent)}")
            if agent.local_model:
                name.append(f" · {agent.local_model}", style=pal.info)  # running on the local GPU
            self.table.add_row(
                name,
                Text(describe_folder(agent.cwd, projects_root, projects)),
                Text(format_age(agent.started), style=pal.muted),
                key=str(agent.pid),
            )
        self._restore_selection(selected, list(self.agents))

        label = Text()
        for name in AGENT_NAMES:
            count = sum(a.agent == name for a in agents)
            if label:
                label.append("  ·  ", style=pal.muted)
            label.append(f"{name} {count}", style=pal.agent(name) if count else pal.muted)
            local = sum(a.agent == name and a.local_model is not None for a in agents)
            if local:
                label.append(f" ({local} local)", style=pal.info)
        self.set_label(label if agents else Text("No agents running", style=pal.muted))
        self.border_subtitle = f"updated {datetime.now():%H:%M:%S}"


class LocalLLMPanel(_TablePanel):
    """The local model server (Ollama): its models, what's loaded, and the GPU.

    The selected row is the model that key 4 launches Codex with. The profile's
    default model (★) is selected until you pick another one.
    """

    PANEL_TITLE = "Local LLM"
    COLUMNS = ("Model", "Size", "State")
    BAR_WIDTH = 16

    def compose(self) -> ComposeResult:
        yield Static("", classes="panel-label")
        yield Static("", classes="gpu-line")
        yield DataTable(cursor_type="row", zebra_stripes=True)

    def populate(self) -> None:
        """Show a loading label until the first check finishes."""
        self.status: OllamaStatus | None = None
        self.default_model: str | None = None
        self.set_label("Checking Ollama…")

    @property
    def running(self) -> bool:
        """True if the last check found the Ollama server running."""
        return self.status is not None and self.status.running

    @property
    def selected_model(self) -> str | None:
        """The model to launch: the selected row, else the profile's default."""
        if not self.running:
            return None
        return self.selected_name or self.default_model

    def show(self, status: OllamaStatus, gpu: GpuInfo | None, default_model: str | None) -> None:
        """Replace the rows and the status lines."""
        self._last = (status, gpu, default_model)
        pal = self.palette
        first_fill = self.status is None or not self.status.running
        selected = None if first_fill else self.selected_name
        self.status, self.default_model = status, default_model
        self.table.clear()
        loaded = {m.name: m for m in status.loaded}
        for model in status.installed:
            name = Text(model.name, style="bold" if model.name in loaded else "")
            if model.name == default_model:
                name.append(" ★", style=pal.info)
            size = Text(f"{model.size_bytes / 1e9:.1f} GB", style=pal.muted)
            self.table.add_row(name, size, _loaded_cell(loaded.get(model.name), pal), key=model.name)
        names = [m.name for m in status.installed]
        self._restore_selection(selected or default_model, names)

        if not status.running:
            label = Text("○ Ollama stopped", style=pal.muted).append("  ·  press o to start", style=pal.muted)
        else:
            label = Text(f"● Ollama {status.version or ''} running".replace("  ", " "), style=pal.ok)
            if status.error:
                label.append(f"  ⚠ {status.error}", style=pal.alert)
        self.set_label(label)
        self.query_one(".gpu-line", Static).update(_gpu_line(gpu, self.BAR_WIDTH, pal))
        self.border_subtitle = f"updated {datetime.now():%H:%M:%S}"


def _loaded_cell(model: LoadedModel | None, pal: Palette = DEFAULT_PALETTE) -> Text:
    """The State cell: idle, or loaded with its context size and how much is on the GPU."""
    if model is None:
        return Text("idle", style=pal.muted)
    cell = Text("● loaded", style=pal.ok)
    if model.context_length:
        cell.append(f" · {model.context_length // 1024}K ctx", style=pal.muted)
    if model.gpu_percent >= 100:
        cell.append(" · 100% GPU", style=pal.muted)
    else:
        # Part of the model spilled into normal RAM: it works, but much slower.
        cell.append(f" · {model.gpu_percent}% GPU", style=pal.warn)
    return cell


def _gpu_line(gpu: GpuInfo | None, bar_width: int, pal: Palette = DEFAULT_PALETTE) -> Text:
    """One line: GPU name, a memory bar, used/total and how busy it is.

    The memory comes from nvidia-smi, not Ollama: `ollama ps` under-reports
    gemma4 (local-llm/README.md), and other programs use the GPU too.
    """
    if gpu is None:
        return Text("GPU  not available (nvidia-smi)", style=pal.muted)
    name = gpu.name.removeprefix("NVIDIA ").removeprefix("GeForce ")
    percent = 100 * gpu.memory_used_mb / gpu.memory_total_mb if gpu.memory_total_mb else 0
    line = Text(f"GPU  {name}  ", style="bold")
    line.append_text(_bar(percent, bar_width, pal))
    line.append(f"  {gpu.memory_used_mb / 1024:.1f} / {gpu.memory_total_mb / 1024:.1f} GB", style="")
    if gpu.utilization_percent is not None:
        line.append(f"  ·  {gpu.utilization_percent}% busy", style=pal.muted)
    return line


class TasksPanel(_TablePanel):
    """Dispatched tasks, newest first: worker, progress, changes and Opus's review.

    Its keys (view, merge, discard) only apply here, so they appear in the
    footer only while this panel has focus.
    """

    PANEL_TITLE = "Tasks"
    COLUMNS = ("Task", "Worker", "Status", "Age")
    BINDINGS = [
        Binding("v", "app.view_task", "View task"),
        Binding("m", "app.merge_task", "Merge"),
        Binding("x", "app.discard_task", "Discard"),
    ]

    def populate(self) -> None:
        self.tasks: dict[str, Task] = {}
        self.alive: set[str] = set()
        self.set_label("No tasks yet: select a project and press d to dispatch one")

    @property
    def selected_task(self) -> Task | None:
        return self.tasks.get(self.selected_name or "")

    def show(self, tasks: list[Task], alive: set[str]) -> None:
        """Replace the rows. `alive` holds the ids whose supervisor is still working."""
        self._last = (tasks, alive)
        pal = self.palette
        selected = self.selected_name
        self.table.clear()
        self.tasks = {t.id: t for t in tasks}
        self.alive = alive
        for task in tasks:
            title = task.title if len(task.title) <= 34 else task.title[:33] + "…"
            self.table.add_row(
                Text(title, style="" if task.status not in ("merged", "discarded") else pal.muted),
                _worker_cell(task, pal),
                _task_status_cell(task, task.id in alive, pal),
                Text(format_age(task.created), style=pal.muted),
                key=task.id,
            )
        self._restore_selection(selected, list(self.tasks))
        if tasks:
            running = sum(t.status == "running" for t in tasks)
            waiting = sum(t.status in ("done", "failed", "timeout") for t in tasks)
            self.set_label(f"{running} running  ·  {waiting} waiting for your decision  ·  d new task")
        self.border_subtitle = f"updated {datetime.now():%H:%M:%S}"


def _worker_cell(task: Task, pal: Palette = DEFAULT_PALETTE) -> Text:
    if task.agent == "local":
        return Text(f"local · {task.model}", style=pal.info)
    return Text(task.agent, style=pal.agent(task.agent))


VERDICT_STYLE = {"approve": ("✓ approve", "ok"), "changes": ("△ changes", "warn"), "reject": ("✗ reject", "alert")}


def _task_status_cell(task: Task, alive: bool, pal: Palette = DEFAULT_PALETTE) -> Text:
    """E.g. "● running 2m/10m", "✓ done · 2 files · ✓ approve", "⏱ timeout · reviewing…"."""
    colours = {"ok": pal.ok, "warn": pal.warn, "alert": pal.alert}
    if task.status == "planned":
        return Text("○ starting…", style=pal.muted)
    if task.status == "running":
        elapsed = format_age(task.started) if task.started else "0s"
        return Text(f"● running {elapsed} / {task.time_limit // 60}m", style=pal.info)
    if task.status in ("merged", "discarded"):
        return Text(f"{'⇢' if task.status == 'merged' else '–'} {task.status}", style=pal.muted)
    symbol, style = {"done": ("✓ done", pal.ok), "timeout": ("⏱ timeout", pal.warn),
                     "failed": ("✗ failed", pal.alert)}[task.status]
    cell = Text(symbol, style=style)
    cell.append(f" · {len(task.files)} file{'s' if len(task.files) != 1 else ''}", style=pal.muted)
    if task.review:
        label, colour = VERDICT_STYLE.get(str(task.review.get("verdict")), ("? review", "warn"))
        cell.append(" · ")
        cell.append(label, style=colours[colour])
    elif alive:
        cell.append(" · reviewing…", style=pal.info)
    return cell


def task_details(task: Task, worker_output: str, diff: str, pal: Palette = DEFAULT_PALETTE) -> Text:
    """The full text for the task view (v)."""
    text = Text()
    text.append(f"{task.title}\n", style="bold")
    text.append(f"task {task.id}  ·  {task.project}\n\n", style=pal.muted)
    text.append("Worker  ", style="bold")
    text.append_text(_worker_cell(task, pal))
    text.append(f"   time limit {task.time_limit // 60} min\n")
    text.append("Why     ", style="bold")
    text.append(f"{task.reason}\n")
    text.append("Status  ", style="bold")
    text.append_text(_task_status_cell(task, False, pal))
    if task.exit_code is not None:
        text.append(f"  (exit code {task.exit_code})", style=pal.muted)
    text.append("\n")
    if task.error:
        text.append(f"Problem {task.error}\n", style=pal.alert)
    if task.review:
        review = task.review_obj
        assert review is not None
        label, _ = VERDICT_STYLE.get(review.verdict, (review.verdict, ""))
        text.append("\nReview by Opus: ", style="bold")
        text.append(f"{label}\n")
        text.append(f"{review.summary}\n")
        for concern in review.concerns:
            text.append(f"  • {concern}\n", style=pal.warn)
    if task.files:
        text.append(f"\nChanged files (+{task.insertions} −{task.deletions})\n", style="bold")
        for name in task.files:
            text.append(f"  {name}\n")
    if worker_output:
        text.append("\nWorker's summary\n", style="bold")
        text.append(worker_output[-2500:].strip() + "\n")
    if diff:
        text.append("\nDiff\n", style="bold")
        for line in diff.splitlines()[:400]:
            style = pal.ok if line.startswith("+") else pal.alert if line.startswith("-") else ""
            text.append(line + "\n", style=style)
    text.append("\nEsc to close.  On the Tasks panel: m merge, x discard.", style=pal.muted)
    return text


class UsagePanel(_ThemedPanel):
    """Subscription usage: the real plan limits of Codex and Claude."""

    BAR_WIDTH = 20

    def compose(self) -> ComposeResult:
        yield Static("Reading usage…", classes="usage-body")

    def on_mount(self) -> None:
        self.border_title = "Usage"

    def show(
        self, codex: CodexUsage | None, claude: ClaudeUsage | None, local: LocalUsage | None = None
    ) -> None:
        """Render the two cloud plans with the same bar layout, then the local model's tokens."""
        self._last = (codex, claude, local)
        pal = self.palette
        text = Text()
        plan = f"  ({codex.plan.title()} plan)" if codex and codex.plan else ""
        _provider(text, pal, "ChatGPT · Codex", pal.agent("codex"), plan, codex,
                  "no Codex sessions found yet", self.BAR_WIDTH)
        text.append("\n\n")
        _provider(text, pal, "Claude", pal.agent("claude"), "", claude,
                  "no cached usage yet (run /usage in Claude Code once)", self.BAR_WIDTH)
        if local is not None:
            text.append("\n\n")
            _local(text, pal, local)
        self.query_one(".usage-body", Static).update(text)
        self.border_subtitle = f"updated {datetime.now():%H:%M:%S}"


def _provider(
    text: Text,
    pal: Palette,
    name: str,
    colour: str,
    extra: str,
    usage: CodexUsage | ClaudeUsage | None,
    missing: str,
    bar_width: int,
) -> None:
    """Append one provider's heading, 5-hour and weekly bars to `text`."""
    text.append(name, style=f"bold {colour}")
    text.append(extra, style=pal.muted)
    if usage is None:
        text.append(f"\n  {missing}", style=pal.muted)
        return
    if usage.observed_at:
        text.append(f"  as of {_when(usage.observed_at)}", style=pal.muted)
    for label, window in (("5-hour", usage.five_hour), ("weekly", usage.weekly)):
        text.append(f"\n  {label:<7}")
        if window is None:
            text.append("unknown", style=pal.muted)
            continue
        text.append_text(_bar(window.used_percent, bar_width, pal))
        text.append(f" {window.used_percent:>3.0f}%", style="bold")
        if window.resets_at:
            text.append(f"  resets {_when(window.resets_at)}", style=pal.muted)


def _local(text: Text, pal: Palette, local: LocalUsage) -> None:
    """Append the local model's row: no limits, so tokens processed instead of a bar."""
    text.append("Local · Ollama", style=f"bold {pal.info}")
    text.append("  (no limits: runs on my GPU)", style=pal.muted)
    for label, tokens, sessions in (
        ("today", local.today_tokens, local.today_sessions),
        ("7 days", local.week_tokens, local.week_sessions),
    ):
        text.append(f"\n  {label:<7}")
        if not sessions:
            text.append("no local sessions", style=pal.muted)
            continue
        text.append(f"{format_tokens(tokens)} tokens", style="bold")
        text.append(f"  ·  {sessions} session{'s' if sessions != 1 else ''}", style=pal.muted)


def format_tokens(count: int) -> str:
    """1234 -> "1.2K", 2207237 -> "2.2M"."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def _bar(percent: float, width: int, pal: Palette = DEFAULT_PALETTE) -> Text:
    """A coloured bar: "ok" colour below 60 %, "warn" below 85 %, "alert" above."""
    filled = round(max(0.0, min(percent, 100.0)) / 100 * width)
    colour = pal.ok if percent < 60 else pal.warn if percent < 85 else pal.alert
    bar = Text("█" * filled, style=colour)
    bar.append("░" * (width - filled), style=pal.muted)
    return bar


def _when(timestamp: float) -> str:
    """"21:37" for today, otherwise "Mon 09:17"."""
    moment = datetime.fromtimestamp(timestamp)
    if moment.date() == datetime.now().date():
        return f"{moment:%H:%M}"
    return f"{moment:%a %H:%M}"
