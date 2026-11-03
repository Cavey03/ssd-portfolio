"""Dashboard panels."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from mission_control.containers import ContainerInfo, ContainerResult
from mission_control.gitinfo import ProjectStatus

# Status colours (kept in line with the accent in app.tcss)
OK = "#50d6c5"
WARN = "#e5c07b"
INFO = "#61afef"
ALERT = "#e06c75"
MUTED = "#8795a8"


class _TablePanel(Vertical):
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


class _PlaceholderPanel(_TablePanel):
    """A panel that still shows fake rows (not implemented yet)."""

    ROWS: ClassVar[tuple[tuple[str, ...], ...]]

    def populate(self) -> None:
        """Load the fake rows."""
        self.set_label("PLACEHOLDER DATA")
        for row in self.ROWS:
            self.table.add_row(*row, key=row[0])


class ProjectsPanel(_TablePanel):
    """Folders in the projects root with their live git status."""

    PANEL_TITLE = "Projects"
    COLUMNS = ("Name", "Branch", "Changes", "Sync")

    def show(self, root: Path, statuses: list[ProjectStatus]) -> None:
        """Replace the rows with fresh statuses, keeping the selected project."""
        table = self.table
        selected = self.selected_name
        table.clear()
        for status in statuses:
            table.add_row(*_project_cells(status), key=status.name)

        names = [s.name for s in statuses]
        if selected in names:
            table.move_cursor(row=names.index(selected))

        repos = sum(s.is_repo for s in statuses)
        self.set_label(f"{root}  ·  {repos} repos")
        self.border_subtitle = f"updated {datetime.now():%H:%M:%S}"
        if not statuses:
            self.set_label(f"{root}  ·  no project folders found")


def _project_cells(status: ProjectStatus) -> tuple[Text, Text, Text, Text]:
    """Turn a ProjectStatus into the four styled table cells."""
    name = Text(status.name, style="bold")

    if not status.is_repo:
        return name, Text("—", style=MUTED), Text("not a git repo", style=MUTED), Text("")
    if status.error:
        return name, Text("—", style=MUTED), Text(f"⚠ {status.error}", style=ALERT), Text("")

    branch_style = WARN if status.branch == "(detached)" else ""
    branch = Text(status.branch or "?", style=branch_style)

    if status.changes:
        changes = Text(f"● {status.changes} changed", style=WARN)
    else:
        changes = Text("✓ clean", style=OK)

    if status.ahead is None:
        sync = Text("no remote", style=MUTED)
    elif status.ahead == 0 and status.behind == 0:
        sync = Text("✓ synced", style=OK)
    else:
        sync = Text()
        if status.ahead:
            sync.append(f"↑{status.ahead} to push", style=INFO)
        if status.behind:
            if sync:
                sync.append("  ")
            sync.append(f"↓{status.behind} to pull", style=ALERT)

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
        selected = self.selected_name
        self.table.clear()
        self.containers = {container.name: container for container in result.containers}
        for container in result.containers:
            self.table.add_row(*_container_cells(container, current), key=container.name)
        names = list(self.containers)
        if selected in names:
            self.table.move_cursor(row=names.index(selected))
        if result.error:
            self.set_label(Text(f"⚠ {result.error}", style=ALERT))
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


def _container_cells(container: ContainerInfo, current: str | None) -> tuple[Text, Text, Text]:
    """Turn a container summary into three styled table cells.

    The uptime goes into the State cell (e.g. "● running · 1h") so the panel
    fits in the narrow right-hand column without a horizontal scrollbar.
    """
    name = container.name + (" (this)" if container.name == current else "")
    if container.state == "running":
        state = Text(f"● {container.state}", style=OK)
        uptime = _short_uptime(container.status_text)
        if uptime:
            state.append(f" · {uptime}", style=MUTED)
    elif container.state in ("exited", "stopped"):
        state = Text(f"○ {container.state}", style=MUTED)
    else:
        state = Text(f"● {container.state}", style=WARN)
    image = container.image
    registry, separator, remainder = image.partition("/")
    if separator and ("." in registry or ":" in registry or registry == "localhost"):
        image = remainder
    return Text(name, style="bold"), state, Text(image)


class AgentsPanel(_PlaceholderPanel):
    """Display fake agent activity."""

    PANEL_TITLE = "Agents"
    COLUMNS = ("Agent", "Status", "Project")
    ROWS = (
        ("claude", "Idle (demo)", "ssd-portfolio"),
        ("codex", "Idle (demo)", "mission-control"),
        ("agy", "Idle (demo)", "—"),
    )
