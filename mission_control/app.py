"""Mission Control app: layout, refresh loop and keyboard actions."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header

from mission_control.gitinfo import default_projects_root, scan_projects
from mission_control.panels import AgentsPanel, ContainersPanel, ProjectsPanel

AUTO_REFRESH_SECONDS = 10


class MissionControlApp(App[None]):
    """A dashboard for containers, projects and AI agents."""

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

    def __init__(self, projects_root: Path | None = None) -> None:
        super().__init__()
        self.projects_root = projects_root or default_projects_root()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="dashboard"):
            yield ProjectsPanel(id="projects", classes="panel")
            with Vertical(id="side-panels"):
                yield ContainersPanel(id="containers", classes="panel")
                yield AgentsPanel(id="agents", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        """Focus the projects table and start the refresh loop."""
        self.query_one(ProjectsPanel).table.focus()
        self.refresh_projects()
        self.set_interval(AUTO_REFRESH_SECONDS, self.refresh_projects)

    @work(thread=True, exclusive=True, group="projects")
    def refresh_projects(self) -> None:
        """Scan the projects in a background thread so the UI never freezes."""
        statuses = scan_projects(self.projects_root)
        self.call_from_thread(
            self.query_one(ProjectsPanel).show, self.projects_root, statuses
        )

    def action_refresh(self) -> None:
        """Refresh all live panels now."""
        self.refresh_projects()
        self.notify("Refreshed projects.", timeout=2)

    def action_toggle_container(self) -> None:
        """Describe toggling the selected container (not implemented yet)."""
        container = self.query_one(ContainersPanel).selected_name
        if container is None:
            self.notify("Select a container first.", title="Demo")
            return
        self.notify(f"Would start/stop container '{container}'.", title="Demo")

    def action_launch(self, agent: str) -> None:
        """Describe launching an agent for the selected project (not implemented yet)."""
        project = self.query_one(ProjectsPanel).selected_name
        if project is None:
            self.notify("Select a project first.", title="Demo")
            return
        self.notify(
            f"Would launch {agent} for '{project}' in a new Konsole tab.",
            title="Demo",
        )
