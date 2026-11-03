"""Dashboard panels populated with explicit placeholder data."""

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static


class _PlaceholderPanel(Vertical):
    """Show a titled, selectable table of fake rows."""

    PANEL_TITLE: ClassVar[str]
    COLUMNS: ClassVar[tuple[str, ...]]
    ROWS: ClassVar[tuple[tuple[str, ...], ...]]

    def compose(self) -> ComposeResult:
        yield Static("PLACEHOLDER DATA", classes="demo-label")
        yield DataTable[str](cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        """Set the border title and load the demo rows."""
        self.border_title = self.PANEL_TITLE
        table = self.query_one(DataTable)
        table.add_columns(*self.COLUMNS)
        table.add_rows(self.ROWS)

    @property
    def selected_name(self) -> str | None:
        """Return the name in the selected row, if present."""
        table = self.query_one(DataTable)
        if not table.row_count:
            return None
        return str(table.get_row_at(table.cursor_row)[0])


class ProjectsPanel(_PlaceholderPanel):
    """Display fake projects and their git summaries."""

    PANEL_TITLE = "Projects"
    COLUMNS = ("Name", "Branch", "Changes", "Unpushed")
    ROWS = (
        ("ssd-portfolio", "demo/main", "3", "1"),
        ("mission-control", "demo/main", "2", "0"),
    )


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
