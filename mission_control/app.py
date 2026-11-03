"""Mission Control layout and placeholder keyboard actions."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header

from mission_control.panels import AgentsPanel, ContainersPanel, ProjectsPanel


class MissionControlApp(App[None]):
    """A development dashboard skeleton with fake data only."""

    TITLE = "Mission Control"
    CSS_PATH = "app.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "toggle_container", "Start/stop"),
        Binding("1", "launch('Claude')", "Claude"),
        Binding("2", "launch('Codex')", "Codex"),
        Binding("3", "launch('Agy')", "Agy"),
        Binding("tab", "focus_next", "Next panel", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="dashboard"):
            yield ProjectsPanel(id="projects", classes="panel")
            with Vertical(id="side-panels"):
                yield ContainersPanel(id="containers", classes="panel")
                yield AgentsPanel(id="agents", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        """Start keyboard navigation in the projects table."""
        self.query_one(ProjectsPanel).query_one(DataTable).focus()

    def action_refresh(self) -> None:
        """Describe the future refresh operation."""
        self.notify("Would refresh projects, containers, and agents.", title="Demo")

    def action_toggle_container(self) -> None:
        """Describe toggling the selected container."""
        container = self.query_one(ContainersPanel).selected_name
        if container is None:
            self.notify("Select a container first.", title="Demo")
            return
        self.notify(f"Would start/stop container '{container}'.", title="Demo")

    def action_launch(self, agent: str) -> None:
        """Describe launching an agent for the selected project."""
        project = self.query_one(ProjectsPanel).selected_name
        if project is None:
            self.notify("Select a project first.", title="Demo")
            return
        self.notify(
            f"Would launch {agent} for '{project}' in a new Konsole tab.",
            title="Demo",
        )
