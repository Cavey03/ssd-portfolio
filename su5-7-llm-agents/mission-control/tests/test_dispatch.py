"""Tests for Dispatch: orchestrator replies, the task store, the supervisor, merge/discard, CLI and UI.

No real agent, orchestrator call or ~/.local/state is used: workers are small shell scripts,
the orchestrator is mocked, and every task lives in a temporary folder.
Run with: python -m unittest -v
"""

from __future__ import annotations

import io
import json
import os
import shlex
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from mission_control import cli, tasks
from mission_control.orchestrator import (
    OrchestratorError, Plan, Review, _ask, build_plan_prompt, parse_plan, project_context,
)
from mission_control.worktrees import TASK_ID_PATTERN

MODELS = ["gemma4:12b", "ornith-1.5:9b"]


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "Test")
    git(path, "config", "user.email", "t@example.com")
    (path / "app.py").write_text("x = 1\n")
    (path / "CLAUDE.md").write_text("# Demo\nA tiny demo project.\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "start")
    return path


class ParsePlanTests(unittest.TestCase):
    def plan(self, **data: object) -> dict[str, object]:
        return {"agent": "codex", "model": None, "reason": "r", "brief": "b", "time_limit_minutes": 25, **data}

    def test_valid_plans(self) -> None:
        self.assertEqual(parse_plan(self.plan(), MODELS, True, None).agent, "codex")
        local = parse_plan(self.plan(agent="local", model="gemma4:12b"), MODELS, True, "ornith-1.5:9b")
        self.assertEqual((local.agent, local.model), ("local", "gemma4:12b"))

    def test_corrections(self) -> None:
        # Unknown local model -> the default; a model for a cloud worker is dropped; minutes clamped.
        local = parse_plan(self.plan(agent="local", model="nope"), MODELS, True, "ornith-1.5:9b")
        self.assertEqual(local.model, "ornith-1.5:9b")
        self.assertIsNone(parse_plan(self.plan(model="gpt-x"), MODELS, True, None).model)
        self.assertEqual(parse_plan(self.plan(time_limit_minutes=500), MODELS, True, None).time_limit_minutes, 60)

    def test_impossible_plans(self) -> None:
        with self.assertRaises(OrchestratorError):
            parse_plan(self.plan(agent="robot"), MODELS, True, None)
        with self.assertRaises(OrchestratorError):  # local chosen while the server is off
            parse_plan(self.plan(agent="local"), MODELS, False, None)

    def test_prompt_mentions_local_state(self) -> None:
        self.assertIn("NOT running", build_plan_prompt("t", "c", MODELS, False, None))
        running = build_plan_prompt("t", "c", MODELS, True, "ornith-1.5:9b")
        self.assertIn("default: ornith-1.5:9b", running)
        self.assertIn("SMALL, single-step", running)  # the routing rules are included


class AskTests(unittest.TestCase):
    def reply(self, stdout: str, code: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], code, stdout, "boom\n")

    def test_structured_output(self) -> None:
        out = json.dumps({"is_error": False, "structured_output": {"agent": "codex"}})
        with patch("mission_control.orchestrator.subprocess.run", return_value=self.reply(out)) as run:
            self.assertEqual(_ask("p", {"type": "object"}, 5), {"agent": "codex"})
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["claude", "-p", "--model", "opus"])
        self.assertIn("--json-schema", command)
        self.assertEqual(command[command.index("--tools") + 1], "")  # no tools for the orchestrator

    def test_errors(self) -> None:
        for stdout in ("not json", json.dumps({"is_error": True, "result": "limit"}), json.dumps({"x": 1})):
            with self.subTest(stdout=stdout), \
                    patch("mission_control.orchestrator.subprocess.run", return_value=self.reply(stdout)), \
                    self.assertRaises(OrchestratorError):
                _ask("p", {}, 5)
        with patch("mission_control.orchestrator.subprocess.run", side_effect=FileNotFoundError), \
                self.assertRaises(OrchestratorError):
            _ask("p", {}, 5)

    def test_project_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = project_context(make_repo(Path(tmp) / "demo"))
        self.assertIn("A tiny demo project.", context)
        self.assertIn("app.py", context)


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        patch.object(tasks, "STATE_DIR", self.root / "state").start()
        self.addCleanup(patch.stopall)

    def task(self, **changes: object) -> tasks.Task:
        data = dict(id=tasks.new_task_id(), title="Add x", project=str(self.root), agent="codex",
                    model=None, brief="Do x", reason="r", time_limit=60)
        data.update(changes)
        return tasks.Task(**data)  # type: ignore[arg-type]

    def test_ids_are_valid_branch_names(self) -> None:
        self.assertTrue(TASK_ID_PATTERN.fullmatch(tasks.new_task_id()))

    def test_save_load_list(self) -> None:
        older, newer = self.task(id="20261118-1000-aaaa"), self.task(id="20261118-1100-bbbb")
        for t in (older, newer):
            tasks.save_task(t)
        self.assertEqual(tasks.load_task(older.id), older)
        self.assertEqual([t.id for t in tasks.list_tasks()], [newer.id, older.id])  # newest first
        (self.root / "state/tasks/broken").mkdir()
        self.assertEqual(len(tasks.list_tasks()), 2)  # unreadable records are skipped

    def test_make_task_logs_decision(self) -> None:
        suggested = Plan("codex", None, "multi-file", "brief", 25)
        chosen = Plan("claude", None, "changed by the owner", "brief", 25)
        task = tasks.make_task("Add x", self.root, chosen, suggested)
        record = json.loads((self.root / "state" / tasks.DECISIONS_FILE).read_text())
        self.assertEqual(record["task"], task.id)
        self.assertTrue(record["overridden"])
        self.assertEqual(record["suggested"]["agent"], "codex")

    def test_worker_commands(self) -> None:
        local = tasks.worker_command(self.task(agent="local", model="gemma4:12b"), self.root, self.root / "m")
        self.assertEqual(local[:6], ["codex", "exec", "-p", "local", "-m", "gemma4:12b"])
        self.assertIn("Do NOT commit", local[-1])
        codex = tasks.worker_command(self.task(), self.root, self.root / "m")
        self.assertEqual(codex[:4], ["codex", "exec", "-s", "workspace-write"])
        claude = tasks.worker_command(self.task(agent="claude"), self.root, self.root / "m")
        self.assertEqual(claude[:4], ["claude", "-p", "--permission-mode", "acceptEdits"])
        (self.root / ".venv/bin").mkdir(parents=True)
        (self.root / ".venv/bin/python").write_text("")
        self.assertIn(".venv/bin/python", tasks.worker_command(self.task(), self.root, self.root / "m")[-1])

    def test_in_dev_command(self) -> None:
        with patch("mission_control.tasks.current_container_name", return_value=None):
            command = tasks.in_dev_command(["codex", "exec", "it's"], Path("/w d"), 600)
        self.assertEqual(command[:4], ["distrobox", "enter", "dev", "--"])
        self.assertIn("timeout -k 30 600 codex exec 'it'\"'\"'s'", command[-1])
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", command[-1])
        with patch("mission_control.tasks.current_container_name", return_value="dev"):
            self.assertEqual(tasks.in_dev_command(["x"], Path("/w"), 5)[0], "bash")

    def test_commit_subject_has_no_worker_name(self) -> None:
        subject = tasks.commit_subject(self.task(agent="local", model="ornith-1.5:9b", title="word " * 30))
        self.assertTrue(subject.startswith("Task "))
        self.assertLessEqual(len(subject), 72)  # git convention for a subject line
        self.assertNotIn("ornith", subject)

    def test_mark_lost(self) -> None:
        task = self.task(status="running", pid=999_999_999)
        tasks.save_task(task)
        self.assertEqual(tasks.mark_lost(task).status, "failed")


class SupervisorTests(unittest.TestCase):
    """run_task with a fake worker (a shell script) in a temporary repo, then merge or discard."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = make_repo(self.root / "repo")
        patch.object(tasks, "STATE_DIR", self.root / "state").start()
        self.review = patch("mission_control.tasks.review_task",
                            return_value=Review("approve", "Looks right.", ())).start()
        self.addCleanup(patch.stopall)

    def run_worker(self, script: str) -> tasks.Task:
        """Run a task whose 'worker' is `script`, executed in the worktree."""
        task = tasks.Task(id=tasks.new_task_id(), title="Change app", project=str(self.repo), agent="codex",
                          model=None, brief="b", reason="r", time_limit=30)
        tasks.save_task(task)
        with patch("mission_control.tasks.in_dev_command",
                   side_effect=lambda argv, workdir, limit: ["bash", "-c", f"cd {shlex.quote(str(workdir))} && {script}"]):
            return tasks.run_task(task.id, worktrees_dir=self.root / "wt")

    def test_done_task_is_reviewed_then_merged(self) -> None:
        task = self.run_worker("echo 'x = 2' > app.py && echo new > notes.txt && echo finished")
        self.assertEqual(task.status, "done")
        self.assertEqual(task.files, ["app.py", "notes.txt"])
        self.assertEqual(task.review["verdict"], "approve")
        self.assertIn("finished", tasks.worker_output(task))
        self.assertIn("+x = 2", (task.folder / "diff.patch").read_text())

        ok, message = tasks.merge_task(task)
        self.assertTrue(ok, message)
        self.assertEqual((self.repo / "app.py").read_text(), "x = 2\n")
        self.assertEqual(tasks.load_task(task.id).status, "merged")
        self.assertFalse((self.root / "wt" / f"task-{task.id}").exists())
        log = git(self.repo, "log", "--format=%s", "-2")
        self.assertIn(f"Merge Task {task.id}", log)
        self.assertNotIn("codex", log)  # no worker name in commit messages

    def test_timeout_and_failure(self) -> None:
        self.assertEqual(self.run_worker("echo partial > app.py; exit 124").status, "timeout")
        self.assertEqual(self.run_worker("exit 3").status, "failed")

    def test_no_changes_means_no_review(self) -> None:
        task = self.run_worker("true")
        self.assertEqual((task.status, task.files, task.review), ("done", [], None))
        self.review.assert_not_called()
        self.assertFalse(tasks.merge_task(task)[0])

    def test_review_failure_is_recorded(self) -> None:
        self.review.side_effect = OrchestratorError("limit reached")
        task = self.run_worker("echo y > app.py")
        self.assertEqual(task.status, "done")
        self.assertIn("review failed: limit reached", task.error or "")

    def test_discard(self) -> None:
        task = self.run_worker("echo y > app.py")
        ok, _ = tasks.discard_task(task)
        self.assertTrue(ok)
        self.assertEqual((self.repo / "app.py").read_text(), "x = 1\n")
        self.assertEqual(tasks.load_task(task.id).status, "discarded")
        self.assertNotIn(f"task/{task.id}", git(self.repo, "branch"))


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = make_repo(self.root / "repo")
        patch.object(tasks, "STATE_DIR", self.root / "state").start()
        self.start = patch("mission_control.tasks.start_task", side_effect=lambda t: t).start()
        self.addCleanup(patch.stopall)

    def run_cli(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(list(argv))
        return code, out.getvalue()

    def test_dry_run_with_planning(self) -> None:
        plan = Plan("codex", None, "multi-file", "Do it well", 25)
        with patch("mission_control.tasks.ask_plan", return_value=plan), \
                patch("mission_control.cli.local_route", return_value="local"):
            code, out = self.run_cli("start", "Add x", "--project", str(self.repo), "--dry-run")
        self.assertIn("): local", out)
        self.assertEqual(code, 0)
        self.assertIn("Worker:     codex", out)
        self.assertIn("Not started.", out)
        self.start.assert_not_called()

    def test_start_with_chosen_worker(self) -> None:
        code, out = self.run_cli("start", "Add x", "--project", str(self.repo), "--agent", "codex", "-y")
        self.assertEqual(code, 0)
        self.assertIn("Started task", out)
        task = self.start.call_args.args[0]
        self.assertEqual((task.agent, task.brief, task.time_limit), ("codex", "Add x", 25 * 60))

    def test_not_a_repo_and_unknown_task(self) -> None:
        self.assertEqual(cli.main(["start", "x", "--project", str(self.root), "--agent", "codex", "-y"]), 1)
        self.assertEqual(cli.main(["show", "nope"]), 1)

    def test_list_and_show(self) -> None:
        task = tasks.Task(id="20261118-1200-abcd", title="Add x", project=str(self.repo), agent="local",
                          model="ornith-1.5:9b", brief="b", reason="small", time_limit=600, status="done",
                          files=["app.py"], review={"verdict": "changes", "summary": "Almost.", "concerns": ["c1"]})
        tasks.save_task(task)
        _, listing = self.run_cli("list")
        self.assertIn("20261118-1200-abcd  done", listing)
        self.assertIn("review:changes", listing)
        _, details = self.run_cli("show", task.id)
        self.assertIn("Review:  CHANGES: Almost.", details)
        self.assertIn("  - c1", details)


if __name__ == "__main__":
    unittest.main()


class DispatchAppTests(unittest.IsolatedAsyncioTestCase):
    """The d key, the Tasks panel and its v / m / x keys, with everything outside the app mocked."""

    async def asyncSetUp(self) -> None:
        from mission_control.containers import ContainerResult
        from mission_control.gitinfo import ProjectStatus
        from mission_control.localllm import OllamaStatus

        self.root = Path("/projects")
        self.task = tasks.Task(id="20261118-1200-abcd", title="Add x", project="/projects/demo", agent="codex",
                               model=None, brief="b", reason="r", time_limit=1500, status="done",
                               files=["app.py"], insertions=1, deletions=1,
                               review={"verdict": "approve", "summary": "Good.", "concerns": []})
        for target, value in (
            ("mission_control.app.scan_projects", [ProjectStatus("demo", self.root / "demo", True)]),
            ("mission_control.app.list_containers", ContainerResult([])),
            ("mission_control.app.find_agents", []),
            ("mission_control.app.read_codex_usage", None),
            ("mission_control.app.read_claude_usage", None),
            ("mission_control.app.read_local_usage", None),
            ("mission_control.app.read_ollama", OllamaStatus(running=False)),
            ("mission_control.app.read_gpu", None),
            ("mission_control.app.profile_model", None),
            ("mission_control.tasks.list_tasks", [self.task]),
            ("mission_control.tasks.ask_plan", Plan("codex", None, "multi-file", "Do it well", 25)),
        ):
            patch(target, return_value=value).start()
        self.start = patch("mission_control.tasks.start_task", side_effect=lambda t: t).start()
        self.merge = patch("mission_control.tasks.merge_task", return_value=(True, "Merged")).start()
        self.discard = patch("mission_control.tasks.discard_task", return_value=(True, "Discarded")).start()
        self.log = patch("mission_control.tasks.log_decision").start()
        patch("mission_control.router.local_route", return_value="codex").start()
        self.addCleanup(patch.stopall)

    async def test_dispatch_plans_then_starts(self) -> None:
        from mission_control.app import MissionControlApp
        from mission_control.dialogs import DispatchScreen

        app = MissionControlApp(projects_root=self.root)
        async with app.run_test(size=(160, 50)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.press("d")
            await pilot.pause()
            self.assertIsInstance(app.screen, DispatchScreen)
            await pilot.press(*"Add x", "enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertIn("Worker: codex", str(app.screen.query_one("#dispatch-plan").render()))
            self.assertIn("suggests: codex  (agrees with Opus)", str(app.screen.query_one("#dispatch-router").render()))
            await pilot.click("#start")
            await app.workers.wait_for_complete()
            await pilot.pause()
        task = self.start.call_args.args[0]
        self.assertEqual((task.title, task.agent, task.brief), ("Add x", "codex", "Do it well"))
        self.assertEqual(task.project, str(self.root / "demo"))
        self.assertEqual(self.log.call_args.args[0]["router"], "codex")

    async def test_task_keys(self) -> None:
        from mission_control.app import MissionControlApp
        from mission_control.dialogs import ConfirmScreen, TaskScreen
        from mission_control.panels import TasksPanel

        app = MissionControlApp(projects_root=self.root)
        async with app.run_test(size=(160, 50)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            panel = app.query_one(TasksPanel)
            self.assertEqual(panel.table.row_count, 1)
            self.assertIn("✓ approve", panel.table.get_row_at(0)[2].plain)
            panel.table.focus()

            await pilot.press("v")
            await pilot.pause()
            self.assertIsInstance(app.screen, TaskScreen)
            await pilot.press("escape")
            await pilot.pause()

            await pilot.press("m")
            await pilot.pause()
            self.assertIsInstance(app.screen, ConfirmScreen)
            await pilot.press("y")
            await app.workers.wait_for_complete()
            self.merge.assert_called_once()

            await pilot.press("x")
            await pilot.pause()
            await pilot.press("n")  # No: nothing discarded
            await app.workers.wait_for_complete()
            self.discard.assert_not_called()


class RouterTests(unittest.TestCase):
    """The fine-tuned router client: the right prompt, and None whenever it can't answer."""

    def reply(self, content: str):
        body = json.dumps({"message": {"content": content}}).encode()
        return patch("mission_control.router.urllib.request.urlopen", return_value=io.BytesIO(body))

    def test_suggestion(self) -> None:
        from mission_control import router
        with self.reply('{"agent": "claude"}') as urlopen:
            self.assertEqual(router.local_route("Redesign the auth layer"), "claude")
        sent = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(sent["messages"][0]["content"], router.SYSTEM_PROMPT)  # exactly the training prompt
        self.assertEqual(sent["messages"][1]["content"], "Task: Redesign the auth layer")
        self.assertEqual(sent["options"]["temperature"], 0)

    def test_unavailable_or_odd_answers(self) -> None:
        from mission_control import router
        for content in ('{"agent": "robot"}', "not json", "[]"):
            with self.subTest(content=content), self.reply(content):
                self.assertIsNone(router.local_route("x"))
        import urllib.error
        with patch("mission_control.router.urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            self.assertIsNone(router.local_route("x"))

    def test_prompt_matches_training_script(self) -> None:
        """The router must be asked exactly as it was trained (models/router-finetune/train_router.py)."""
        from mission_control import router
        script = Path(__file__).resolve().parents[3] / "models/router-finetune/train_router.py"
        if not script.exists():
            self.skipTest("training script not in this checkout")
        self.assertIn(f'SYSTEM_PROMPT = "{router.SYSTEM_PROMPT}"', script.read_text())
