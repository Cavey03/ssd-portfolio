"""Dashboard panels."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

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

    def set_label(self, text: str) -> None:
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


class ContainersPanel(_PlaceholderPanel):
    """Display a fake development container."""

    PANEL_TITLE = "Containers"
    COLUMNS = ("Name", "Status", "Image")
    ROWS = (("dev", "Running (demo)", "demo:latest"),)


class AgentsPanel(_PlaceholderPanel):
    """Display fake agent activity."""

    PANEL_TITLE = "Agents"
    COLUMNS = ("Agent", "Status", "Project")
    ROWS = (
        ("claude", "Idle (demo)", "ssd-portfolio"),
        ("codex", "Idle (demo)", "mission-control"),
        ("agy", "Idle (demo)", "—"),
    )
