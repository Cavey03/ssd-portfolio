"""Launch command and headless UI tests; no terminals or agents are started."""

from __future__ import annotations

import shlex
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from mission_control.app import MissionControlApp
from mission_control.containers import ContainerResult
from mission_control.gitinfo import ProjectStatus
from mission_control.launcher import AGENTS, build_launch_command, launch_agent
from mission_control.panels import ProjectsPanel


class LaunchCommandTests(unittest.TestCase):
    def test_in_container_command(self) -> None:
        self.assertEqual(
            build_launch_command("codex", Path("/home/Kyle/Projects/mission-control"), "dev"),
            [
                "distrobox-host-exec", "konsole", "--new-tab", "--workdir",
                "/home/Kyle/Projects/mission-control", "-e", "distrobox", "enter", "dev",
                "--", "bash", "-lc", "cd /home/Kyle/Projects/mission-control && exec codex",
            ],
        )

    def test_on_host_command_defaults_to_dev(self) -> None:
        self.assertEqual(
            build_launch_command("claude", Path("/projects/example"), None),
            [
                "konsole", "--new-tab", "--workdir", "/projects/example", "-e",
                "distrobox", "enter", "dev", "--", "bash", "-lc",
                "cd /projects/example && exec claude",
            ],
        )

    def test_current_container_is_used(self) -> None:
        self.assertEqual(
            build_launch_command("agy", Path("/projects/example"), "work"),
            [
                "distrobox-host-exec", "konsole", "--new-tab", "--workdir",
                "/projects/example", "-e", "distrobox", "enter", "work", "--",
                "bash", "-lc", "cd /projects/example && exec agy",
            ],
        )

    def test_path_with_spaces_and_quotes(self) -> None:
        project_dir = Path("/projects/Kyle's \"test\" project; $(touch nope)")
        command = build_launch_command("codex", project_dir, "dev")
        self.assertEqual(command, [
            "distrobox-host-exec", "konsole", "--new-tab", "--workdir", str(project_dir),
            "-e", "distrobox", "enter", "dev", "--", "bash", "-lc",
            "cd '/projects/Kyle'\"'\"'s \"test\" project; $(touch nope)' && exec codex",
        ])
        self.assertEqual(shlex.split(command[-1]), ["cd", str(project_dir), "&&", "exec", "codex"])


class LaunchAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.project_dir = Path(tmp.name) / "mission-control"
        self.project_dir.mkdir()
        popen_patch = patch("mission_control.launcher.subprocess.Popen")
        self.popen = popen_patch.start()
        self.addCleanup(popen_patch.stop)
        current_patch = patch("mission_control.launcher.current_container_name", return_value="dev")
        self.current = current_patch.start()
        self.addCleanup(current_patch.stop)

    def test_agents_start_detached_on_host_and_in_container(self) -> None:
        for container in ("dev", None):
            self.current.return_value = container
            for name, command in AGENTS.items():
                with self.subTest(container=container, agent=name):
                    self.popen.reset_mock()
                    self.assertEqual(
                        launch_agent(name, self.project_dir),
                        (True, f"Launched {name} in mission-control"),
                    )
                    self.popen.assert_called_once_with(
                        build_launch_command(command, self.project_dir, container),
                        start_new_session=True,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

    def test_unknown_agent(self) -> None:
        self.assertEqual(launch_agent("Other", self.project_dir), (False, "Unknown agent: Other"))
        self.popen.assert_not_called()

    def test_missing_folder(self) -> None:
        missing = self.project_dir / "missing"
        self.assertEqual(
            launch_agent("Codex", missing),
            (False, f"Project folder does not exist: {missing}"),
        )
        self.popen.assert_not_called()

    def test_file_is_not_a_project_folder(self) -> None:
        file = self.project_dir / "file"
        file.touch()
        self.assertFalse(launch_agent("Codex", file)[0])
        self.popen.assert_not_called()

    def test_oserror_is_reported(self) -> None:
        for error in (FileNotFoundError("konsole missing"), PermissionError("permission denied")):
            with self.subTest(error=error):
                self.popen.side_effect = error
                self.assertEqual(
                    launch_agent("Codex", self.project_dir),
                    (False, f"Could not launch Codex: {error}"),
                )

    def test_folder_check_oserror_is_reported(self) -> None:
        with patch.object(Path, "is_dir", side_effect=OSError("folder unavailable")):
            self.assertEqual(
                launch_agent("Codex", self.project_dir),
                (False, "Could not launch Codex: folder unavailable"),
            )
        self.popen.assert_not_called()


class LaunchAppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.root = Path("/projects")
        self.projects = [
            ProjectStatus("first", self.root / "first", False),
            ProjectStatus("mission-control", self.root / "mission-control", True),
        ]
        for target, value in (
            ("mission_control.app.scan_projects", self.projects),
            ("mission_control.app.list_containers", ContainerResult([])),
            ("mission_control.app.current_container_name", "dev"),
        ):
            mock_patch = patch(target, return_value=value)
            mock_patch.start()
            self.addCleanup(mock_patch.stop)
        launch_patch = patch("mission_control.app.launch_agent")
        self.launch = launch_patch.start()
        self.addCleanup(launch_patch.stop)

    async def test_keys_launch_selected_project_in_thread(self) -> None:
        app = MissionControlApp(projects_root=self.root)
        main_thread = threading.get_ident()
        launch_threads: list[int] = []

        def launched(agent: str, project_dir: Path) -> tuple[bool, str]:
            launch_threads.append(threading.get_ident())
            return True, f"Launched {agent} in {project_dir.name}"

        self.launch.side_effect = launched
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            app.query_one(ProjectsPanel).table.move_cursor(row=1)
            with patch.object(app, "notify") as notify:
                for key, agent in (("1", "Claude"), ("2", "Codex"), ("3", "Agy")):
                    await pilot.press(key)
                    await app.workers.wait_for_complete()
                    self.launch.assert_called_with(agent, self.root / "mission-control")
                    notify.assert_any_call(
                        f"Launched {agent} in mission-control", severity="information"
                    )
        self.assertEqual(len(launch_threads), 3)
        self.assertTrue(all(thread != main_thread for thread in launch_threads))

    async def test_launch_error_notification(self) -> None:
        self.launch.return_value = False, "Could not launch Codex: konsole missing"
        app = MissionControlApp(projects_root=self.root)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            with patch.object(app, "notify") as notify:
                await pilot.press("2")
                await app.workers.wait_for_complete()
                notify.assert_any_call(
                    "Could not launch Codex: konsole missing", severity="error"
                )

    async def test_empty_selection_does_not_launch(self) -> None:
        app = MissionControlApp(projects_root=self.root)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            app.query_one(ProjectsPanel).show(self.root, [])
            with patch.object(app, "notify") as notify:
                await pilot.press("1")
                await app.workers.wait_for_complete()
                notify.assert_called_once_with("Select a project first.", severity="warning")
            self.launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
