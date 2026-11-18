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
from mission_control.agents import (
    AgentProcess, describe_folder, find_agents, format_age, stop_agent,
)
from mission_control.dialogs import ConfirmScreen
from mission_control.gitinfo import ProjectStatus, default_projects_root, scan_projects
from mission_control.launcher import launch_agent
from mission_control.panels import AgentsPanel, ContainersPanel, ProjectsPanel, UsagePanel, _ThemedPanel
from mission_control.settings import load_settings, save_setting
from mission_control.themes import (
    AGENT_VARIABLE_DEFAULTS, DEFAULT_THEME, THEME_NAMES, THEMES, next_theme,
)
from mission_control.usage import read_claude_usage, read_codex_usage

AUTO_REFRESH_SECONDS = 10
USAGE_REFRESH_SECONDS = 60


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
        Binding("k", "stop_agent", "Stop agent"),
        Binding("t", "cycle_theme", "Theme"),
        Binding("tab", "focus_next", "Next panel", priority=True),
    ]

    def __init__(self, projects_root: Path | None = None) -> None:
        super().__init__()
        self.projects_root = projects_root or default_projects_root()
        for theme in THEMES:
            self.register_theme(theme)
        saved = load_settings().get("theme")
        self.theme = saved if isinstance(saved, str) and saved in self.available_themes else DEFAULT_THEME
        self._container_action_pending = False
        self._project_keys: tuple[str, ...] = ()
        """Project folders from the last scan; the Agents panel names agents by them."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="dashboard"):
            with Vertical(id="main-panels"):
                yield ProjectsPanel(id="projects", classes="panel")
                yield UsagePanel(id="usage", classes="panel")
            with Vertical(id="side-panels"):
                yield ContainersPanel(id="containers", classes="panel")
                yield AgentsPanel(id="agents", classes="panel")
        yield Footer()

    def get_theme_variable_defaults(self) -> dict[str, str]:
        """Defaults for our extra theme variables, so built-in themes work too."""
        return dict(AGENT_VARIABLE_DEFAULTS)

    def watch_theme(self, theme: str) -> None:
        """Remember the new theme and recolour the panels straight away.

        This also runs when the theme is changed from the command palette (Ctrl+P).
        """
        save_setting("theme", theme)
        if not self.screen_stack:
            return  # still starting up (theme set in __init__): nothing to redraw yet
        for panel in self.query(_ThemedPanel):
            panel.recolour()

    def action_cycle_theme(self) -> None:
        """Switch to the next of our own themes."""
        self.theme = next_theme(self.theme)
        self.notify(f"Theme: {THEME_NAMES.get(self.theme, self.theme)}", timeout=2)

    def on_mount(self) -> None:
        """Focus the projects table and start the refresh loop."""
        self.query_one(ProjectsPanel).table.focus()
        self.refresh_projects()
        self.refresh_containers()
        self.refresh_agents()
        self.refresh_usage()
        self.set_interval(AUTO_REFRESH_SECONDS, self.refresh_projects)
        self.set_interval(AUTO_REFRESH_SECONDS, self.refresh_containers)
        self.set_interval(AUTO_REFRESH_SECONDS, self.refresh_agents)
        self.set_interval(USAGE_REFRESH_SECONDS, self.refresh_usage)

    @work(thread=True, exclusive=True, group="projects")
    def refresh_projects(self) -> None:
        """Scan the projects in a background thread so the UI never freezes."""
        statuses = scan_projects(self.projects_root)
        self.call_from_thread(self._show_projects, statuses)

    def _show_projects(self, statuses: list[ProjectStatus]) -> None:
        """Show the scan (UI thread) and remember the project folders for the Agents panel."""
        self._project_keys = tuple(s.key or s.name for s in statuses)
        self.query_one(ProjectsPanel).show(self.projects_root, statuses)

    @work(thread=True, exclusive=True, group="containers")
    def refresh_containers(self) -> None:
        """Read host container status without blocking the UI."""
        result = list_containers()
        current = current_container_name()
        if not get_current_worker().is_cancelled:
            self.call_from_thread(self.query_one(ContainersPanel).show, result, current)

    @work(thread=True, exclusive=True, group="agents")
    def refresh_agents(self) -> None:
        """Find running agent sessions in a background thread."""
        agents = find_agents()
        if not get_current_worker().is_cancelled:
            self.call_from_thread(
                self.query_one(AgentsPanel).show, agents, self.projects_root, self._project_keys
            )

    @work(thread=True, exclusive=True, group="usage")
    def refresh_usage(self) -> None:
        """Read subscription usage from the agents' local files in a background thread."""
        codex, claude = read_codex_usage(), read_claude_usage()
        if not get_current_worker().is_cancelled:
            self.call_from_thread(self.query_one(UsagePanel).show, codex, claude)

    def action_refresh(self) -> None:
        """Refresh all live panels now."""
        self.refresh_projects()
        self.refresh_containers()
        self.refresh_agents()
        self.refresh_usage()
        self.notify("Refreshing…", timeout=2)

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

    def action_stop_agent(self) -> None:
        """Ask for confirmation, then stop the agent selected in the Agents panel."""
        agent = self.query_one(AgentsPanel).selected_agent
        if agent is None:
            self.notify("Select an agent in the Agents panel first.", severity="warning")
            return
        where = describe_folder(agent.cwd, self.projects_root, self._project_keys)
        question = f"Stop {agent.agent} in {where}?"
        detail = (
            f"pid {agent.pid}, running for {format_age(agent.started)}.\n"
            "Unsaved work in that session will be lost. If it's still open in a window, "
            "quitting it there (/quit or /exit) is the cleaner way."
        )

        def answered(confirmed: bool | None) -> None:
            if confirmed:
                self.stop_agent_worker(agent)

        self.push_screen(ConfirmScreen(question, detail), answered)

    @work(thread=True, group="agent-actions")
    def stop_agent_worker(self, agent: AgentProcess) -> None:
        """Stop the agent in the background, then report and refresh."""
        ok, message = stop_agent(agent)
        self.call_from_thread(self.notify, message, severity="information" if ok else "error")
        self.call_from_thread(self.refresh_agents)

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
