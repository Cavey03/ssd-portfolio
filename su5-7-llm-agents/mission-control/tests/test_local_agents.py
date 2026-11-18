"""Tests for local-model agents: detection, launching (key 4) and the Ollama key (o).

Run with: python -m unittest -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mission_control.agents import AgentProcess, codex_local_model, profile_model
from mission_control.app import MissionControlApp
from mission_control.containers import ContainerResult
from mission_control.dialogs import ConfirmScreen
from mission_control.gitinfo import ProjectStatus
from mission_control.launcher import build_launch_command, launch_agent
from mission_control.localllm import InstalledModel, LoadedModel, OllamaStatus
from mission_control.panels import AgentsPanel, LocalLLMPanel, ProjectsPanel


class CodexLocalModelTests(unittest.TestCase):
    def test_command_lines(self) -> None:
        cases = [
            ([], None),                                               # plain GPT session
            (["exec", "fix the bug"], None),
            (["-m", "gpt-6"], None),                                  # a model alone isn't local
            (["-p", "local"], "ornith-1.5:9b"),                       # profile default
            (["--profile", "local", "-m", "gemma4:12b"], "gemma4:12b"),
            (["--profile=local", "--model=gemma4:12b"], "gemma4:12b"),
            (["exec", "-p", "local", "-s", "workspace-write", "task"], "ornith-1.5:9b"),
            (["--oss"], "ornith-1.5:9b"),
            (["-p", "work"], None),                                   # another profile
            (["exec", "-p"], None),                                   # cut-off command line
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(codex_local_model(args, "ornith-1.5:9b"), expected)

    def test_unknown_default_model(self) -> None:
        self.assertEqual(codex_local_model(["-p", "local"], None), "local")

    def test_profile_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local.config.toml"
            self.assertIsNone(profile_model(path))                    # missing file
            path.write_text('model_provider = "ollama"\nmodel = "ornith-1.5:9b"\n')
            self.assertEqual(profile_model(path), "ornith-1.5:9b")
            path.write_text("model = [broken")
            self.assertIsNone(profile_model(path))                    # invalid TOML


class LocalLaunchTests(unittest.TestCase):
    def test_command_quotes_every_word(self) -> None:
        command = build_launch_command(
            ["codex", "-p", "local", "-m", "gemma4:12b"], Path("/projects/my app"), None
        )
        self.assertEqual(
            command[-1], "cd '/projects/my app' && exec codex -p local -m gemma4:12b"
        )

    def test_launch_local_with_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, \
                patch("mission_control.launcher.subprocess.Popen") as popen, \
                patch("mission_control.launcher.current_container_name", return_value=None):
            ok, message = launch_agent("Local", Path(tmp), "gemma4:12b")
        self.assertTrue(ok)
        self.assertEqual(message, f"Launched Local (gemma4:12b) in {Path(tmp).name}")
        self.assertTrue(popen.call_args.args[0][-1].endswith("exec codex -p local -m gemma4:12b"))


ORNITH = InstalledModel("ornith-1.5:9b", 6_550_813_657, "9.0B", "Q4_K_M")
GEMMA = InstalledModel("gemma4:12b", 8_021_618_941, "11.9B", "Q4_K_M")
RUNNING = OllamaStatus(
    running=True,
    version="0.40.14",
    installed=(GEMMA, ORNITH),
    loaded=(LoadedModel("ornith-1.5:9b", 7_682_517_892, 7_682_517_892, 65536, None),),
)
STOPPED = OllamaStatus(running=False)


class LocalAppTests(unittest.IsolatedAsyncioTestCase):
    """Keys 4 and o, with Ollama, the GPU and launching all mocked."""

    async def asyncSetUp(self) -> None:
        self.root = Path("/projects")
        self.local_agent = AgentProcess("codex", 4242, self.root / "demo", None, "ornith-1.5:9b")
        for target, value in (
            ("mission_control.app.scan_projects", [ProjectStatus("demo", self.root / "demo", True)]),
            ("mission_control.app.list_containers", ContainerResult([])),
            ("mission_control.app.find_agents", [self.local_agent]),
            ("mission_control.app.read_codex_usage", None),
            ("mission_control.app.read_claude_usage", None),
            ("mission_control.app.read_gpu", None),
            ("mission_control.app.read_local_usage", None),
            ("mission_control.app.profile_model", "ornith-1.5:9b"),
        ):
            patch(target, return_value=value).start()
        self.read_ollama = patch("mission_control.app.read_ollama", return_value=RUNNING).start()
        self.launch = patch("mission_control.app.launch_agent", return_value=(True, "ok")).start()
        self.service = patch("mission_control.app.set_service", return_value=(True, "done")).start()
        self.addCleanup(patch.stopall)

    async def test_panel_selects_default_model_and_shows_local_agent(self) -> None:
        app = MissionControlApp(projects_root=self.root)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            panel = app.query_one(LocalLLMPanel)
            self.assertEqual(panel.selected_model, "ornith-1.5:9b")
            name_cell = app.query_one(AgentsPanel).table.get_row_at(0)[0]
            self.assertEqual(name_cell.plain, "● codex · ornith-1.5:9b")

    async def test_key_4_launches_selected_model(self) -> None:
        app = MissionControlApp(projects_root=self.root)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.press("4")
            await app.workers.wait_for_complete()
            self.launch.assert_called_once_with("Local", self.root / "demo", "ornith-1.5:9b")

            # Pick the other model in the Local LLM panel (gemma4 sorts first).
            app.query_one(LocalLLMPanel).table.move_cursor(row=0)
            app.query_one(ProjectsPanel).table.focus()
            await pilot.press("4")
            await app.workers.wait_for_complete()
            self.launch.assert_called_with("Local", self.root / "demo", "gemma4:12b")

    async def test_key_4_warns_when_ollama_stopped(self) -> None:
        self.read_ollama.return_value = STOPPED
        app = MissionControlApp(projects_root=self.root)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            with patch.object(app, "notify") as notify:
                await pilot.press("4")
                await app.workers.wait_for_complete()
            self.launch.assert_not_called()
            notify.assert_called_once_with(
                "Ollama isn't running. Press o to start it first.", severity="warning"
            )

    async def test_key_o_starts_without_asking(self) -> None:
        self.read_ollama.return_value = STOPPED
        app = MissionControlApp(projects_root=self.root)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.press("o")
            await app.workers.wait_for_complete()
            self.service.assert_called_once_with(True)

    async def test_key_o_asks_before_stopping(self) -> None:
        app = MissionControlApp(projects_root=self.root)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.press("o")
            await pilot.pause()
            self.assertIsInstance(app.screen, ConfirmScreen)
            self.assertIn("1 agent session(s) use the local model", app.screen.detail)
            await pilot.press("n")
            await pilot.pause()
            self.service.assert_not_called()

            await pilot.press("o")
            await pilot.pause()
            await pilot.press("y")
            await app.workers.wait_for_complete()
            self.service.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
