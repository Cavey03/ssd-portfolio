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
from textual.widgets import DataTable, Static

from mission_control.agents import AgentProcess, describe_folder, format_age
from mission_control.containers import ContainerInfo, ContainerResult
from mission_control.gitinfo import ProjectStatus
from mission_control.themes import DEFAULT_PALETTE, Palette, palette_from_variables
from mission_control.usage import ClaudeUsage, CodexUsage

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
            self.table.add_row(
                Text(f"● {agent.agent}", style=f"bold {pal.agent(agent.agent)}"),
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
        self.set_label(label if agents else Text("No agents running", style=pal.muted))
        self.border_subtitle = f"updated {datetime.now():%H:%M:%S}"


class UsagePanel(_ThemedPanel):
    """Subscription usage: the real plan limits of Codex and Claude."""

    BAR_WIDTH = 20

    def compose(self) -> ComposeResult:
        yield Static("Reading usage…", classes="usage-body")

    def on_mount(self) -> None:
        self.border_title = "Usage"

    def show(self, codex: CodexUsage | None, claude: ClaudeUsage | None) -> None:
        """Render both providers with the same bar layout."""
        self._last = (codex, claude)
        pal = self.palette
        text = Text()
        plan = f"  ({codex.plan.title()} plan)" if codex and codex.plan else ""
        _provider(text, pal, "ChatGPT · Codex", pal.agent("codex"), plan, codex,
                  "no Codex sessions found yet", self.BAR_WIDTH)
        text.append("\n\n")
        _provider(text, pal, "Claude", pal.agent("claude"), "", claude,
                  "no cached usage yet (run /usage in Claude Code once)", self.BAR_WIDTH)
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
