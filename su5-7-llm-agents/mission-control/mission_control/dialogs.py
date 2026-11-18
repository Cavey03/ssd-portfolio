"""Small pop-up dialogs."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Select, Static
from textual.worker import get_current_worker

from mission_control.orchestrator import OrchestratorError, Plan


class ConfirmScreen(ModalScreen[bool]):
    """Ask a yes/no question. Returns True for yes.

    Keys: y = yes, n or Escape = no. The "No" button has focus, so pressing
    Enter by accident never confirms.
    """

    BINDINGS = [
        Binding("y", "answer(True)", "Yes"),
        Binding("n", "answer(False)", "No"),
        Binding("escape", "answer(False)", "Cancel"),
    ]

    def __init__(self, question: str, detail: str = "") -> None:
        super().__init__()
        self.question = question
        self.detail = detail

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Static(self.question, id="confirm-question")
            if self.detail:
                yield Static(self.detail, id="confirm-detail")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes (y)", variant="error", id="yes")
                yield Button("No (n)", variant="primary", id="no")

    def on_mount(self) -> None:
        self.query_one("#no", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_answer(self, answer: bool) -> None:
        self.dismiss(answer)


class DispatchScreen(ModalScreen["tuple[str, Plan, Plan | None] | None"]):
    """Describe a task, let the orchestrator plan it, then confirm or change the worker.

    Returns (task text, plan to run, orchestrator's original plan or None), or None if cancelled.
    The caller starts the task; this screen only asks.
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, project: Path, local_models: list[str], local_running: bool,
                 default_local: str | None) -> None:
        super().__init__()
        self.project = project
        self.local_models = local_models if local_running else []
        self.default_local = default_local
        self.plan: Plan | None = None

    def compose(self) -> ComposeResult:
        options = [(f"local · {m}", f"local:{m}") for m in self.local_models]
        options += [("codex (GPT, cloud)", "codex:"), ("claude (Claude Code, cloud)", "claude:")]
        with Vertical(id="dispatch-box"):
            yield Static(f"Dispatch a task to {self.project.name}", id="dispatch-title")
            yield Input(placeholder="What should be done? (Enter: ask Opus for a plan)", id="dispatch-task")
            yield Static("Opus picks the worker and writes its brief. You confirm before it starts.",
                         id="dispatch-plan")
            with Horizontal(id="dispatch-controls"):
                yield Select(options, prompt="Worker (after planning, or choose to skip it)",
                             id="dispatch-worker", allow_blank=True)
                yield Button("Start", variant="success", id="start", disabled=True)
                yield Button("Cancel", variant="primary", id="cancel")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        self.query_one("#dispatch-plan", Static).update(Text("Asking Opus for a plan… (10–30 s)", style="italic"))
        self.query_one("#start", Button).disabled = True
        self.ask(text)

    @work(thread=True, exclusive=True, group="plan")
    def ask(self, text: str) -> None:
        from mission_control.tasks import ask_plan  # imported here: tasks pulls in git and HTTP helpers
        try:
            plan: Plan | OrchestratorError = ask_plan(text, self.project)
        except OrchestratorError as exc:
            plan = exc
        if not get_current_worker().is_cancelled:
            self.app.call_from_thread(self.show_plan, plan)

    def show_plan(self, plan: Plan | OrchestratorError) -> None:
        box = self.query_one("#dispatch-plan", Static)
        if isinstance(plan, OrchestratorError):
            box.update(Text(f"Planning failed: {plan}\nChoose a worker yourself to start anyway.", style="bold"))
            return
        self.plan = plan
        worker = f"{plan.agent} · {plan.model}" if plan.model else plan.agent
        text = Text()
        text.append(f"Worker: {worker}", style="bold")
        text.append(f"   time limit {plan.time_limit_minutes} min\n")
        text.append(f"Why: {plan.reason}\n\n", style="italic")
        brief = plan.brief.splitlines()
        text.append("Brief:\n" + "\n".join(brief[:14]) + ("\n…" if len(brief) > 14 else ""))
        box.update(text)
        self.query_one(Select).value = f"{plan.agent}:{plan.model or ''}"
        self.query_one("#start", Button).disabled = False

    def on_select_changed(self, event: Select.Changed) -> None:
        self.query_one("#start", Button).disabled = event.value is Select.BLANK or not self._task_text()

    def _task_text(self) -> str:
        return self.query_one(Input).value.strip()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        choice = self.query_one(Select).value
        if choice is Select.BLANK or not self._task_text():
            return
        agent, _, model = str(choice).partition(":")
        if self.plan is not None and (agent, model or None) == (self.plan.agent, self.plan.model):
            self.dismiss((self._task_text(), self.plan, self.plan))
            return
        from mission_control.tasks import manual_plan
        chosen = manual_plan(self._task_text(), agent, model or None)
        if self.plan is not None:  # keep Opus's brief, change only the worker
            chosen = Plan(agent, chosen.model, f"changed by the owner (Opus suggested {self.plan.agent})",
                          self.plan.brief, chosen.time_limit_minutes)
        self.dismiss((self._task_text(), chosen, self.plan))

    def action_cancel(self) -> None:
        self.dismiss(None)


class TaskScreen(ModalScreen[None]):
    """Everything about one task: plan, status, review, changed files, worker summary, diff."""

    BINDINGS = [Binding("escape", "close", "Close"), Binding("q", "close", "Close")]

    def __init__(self, details: Text) -> None:
        super().__init__()
        self.details = details

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="task-box"):
            yield Static(self.details)

    def action_close(self) -> None:
        self.dismiss(None)
