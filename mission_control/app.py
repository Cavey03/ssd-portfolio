"""Mission Control app: layout, refresh loop and keyboard actions."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header
from textual.worker import get_current_worker

from mission_control.containers import (
    current_container_name, list_containers, start_container, stop_container,
)
from mission_control.gitinfo import default_projects_root, scan_projects
from mission_control.launcher import launch_agent
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
        self._container_action_pending = False

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
        self.refresh_containers()
        self.set_interval(AUTO_REFRESH_SECONDS, self.refresh_projects)
        self.set_interval(AUTO_REFRESH_SECONDS, self.refresh_containers)

    @work(thread=True, exclusive=True, group="projects")
    def refresh_projects(self) -> None:
        """Scan the projects in a background thread so the UI never freezes."""
        statuses = scan_projects(self.projects_root)
        self.call_from_thread(
            self.query_one(ProjectsPanel).show, self.projects_root, statuses
        )

    @work(thread=True, exclusive=True, group="containers")
    def refresh_containers(self) -> None:
        """Read host container status without blocking the UI."""
        result = list_containers()
        current = current_container_name()
        if not get_current_worker().is_cancelled:
            self.call_from_thread(self.query_one(ContainersPanel).show, result, current)

    def action_refresh(self) -> None:
        """Refresh all live panels now."""
        self.refresh_projects()
        self.refresh_containers()
        self.notify("Refreshing projects and containers…", timeout=2)

    def action_toggle_container(self) -> None:
        """Start or stop the selected container, protecting our own runtime."""
        if self._container_action_pending:
            self.notify("A container action is already in progress.", severity="warning")
            return
        container = self.query_one(ContainersPanel).selected_container
        if container is None:
            self.notify("Select a container first.", severity="warning")
            return
        stopping = container.state == "running"
        if stopping and container.name == current_container_name():
            self.notify(
                f"Cannot stop {container.name}: Mission Control is running inside it.",
                severity="warning",
            )
            return
        if not stopping and container.state not in ("exited", "stopped", "created", "configured"):
            self.notify(f"Cannot toggle a container in state '{container.state}'.", severity="warning")
            return
        self._container_action_pending = True
        self.notify(f"{'Stopping' if stopping else 'Starting'} {container.name}…")
        self.toggle_container(container.name, stopping)

    @work(thread=True, exclusive=True, group="container-actions")
    def toggle_container(self, name: str, stopping: bool) -> None:
        """Run a container action in a worker and report its result."""
        action = stop_container if stopping else start_container
        ok, message = action(name)
        self.call_from_thread(self._finish_container_action, ok, message)

    def _finish_container_action(self, ok: bool, message: str) -> None:
        """Report completion and refresh the container panel."""
        self._container_action_pending = False
        self.notify(message, severity="information" if ok else "error")
        self.refresh_containers()

    def action_launch(self, agent: str) -> None:
        """Launch an agent for the selected project without blocking the UI."""
        project = self.query_one(ProjectsPanel).selected_name
        if project is None:
            self.notify("Select a project first.", severity="warning")
            return
        project_dir = self.projects_root / project

        def launch() -> None:
            ok, message = launch_agent(agent, project_dir)
            self.call_from_thread(
                self.notify, message, severity="information" if ok else "error"
            )

        self.run_worker(launch, thread=True, group="launch")
