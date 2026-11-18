"""Container data and headless UI tests; all Podman commands are mocked."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mission_control.app import MissionControlApp
from mission_control.containers import (
    ACTION_TIMEOUT_SECONDS,
    LIST_TIMEOUT_SECONDS,
    ContainerInfo,
    ContainerResult,
    current_container_name,
    list_containers,
    parse_podman_json,
    start_container,
    stop_container,
)
from mission_control.panels import (
    ALERT,
    MUTED,
    OK,
    WARN,
    ContainersPanel,
    _container_cells,
    _short_uptime,
)


class ParsePodmanTests(unittest.TestCase):
    def test_realistic_listing_is_sorted(self) -> None:
        output = json.dumps([
            {"Names": ["work"], "State": "exited", "Image": "docker.io/library/debian:13",
             "Status": "Exited (0) 2 hours ago", "Labels": {"manager": "distrobox"}},
            {"Names": ["Dev"], "State": "running",
             "Image": "registry.fedoraproject.org/fedora-toolbox:44",
             "Status": "Up 1 hour", "Labels": {"manager": "distrobox"}},
        ])
        self.assertEqual(parse_podman_json(output), [
            ContainerInfo("Dev", "running", "registry.fedoraproject.org/fedora-toolbox:44", "Up 1 hour"),
            ContainerInfo("work", "exited", "docker.io/library/debian:13", "Exited (0) 2 hours ago"),
        ])

    def test_missing_fields_and_string_name(self) -> None:
        self.assertEqual(
            parse_podman_json('[{}, {"Names": []}, {"Names": "minimal"}]'),
            [ContainerInfo("minimal", "unknown", "—", "—")],
        )

    def test_empty_listing(self) -> None:
        self.assertEqual(parse_podman_json("[]"), [])

    def test_invalid_json_or_shape(self) -> None:
        for output in ("not json", "{}", "null", "[1]"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                parse_podman_json(output)


class CurrentContainerTests(unittest.TestCase):
    def test_environment_takes_precedence(self) -> None:
        with patch.dict(os.environ, {"CONTAINER_ID": "dev"}):
            self.assertEqual(current_container_name(Path("/missing/containerenv")), "dev")

    def test_containerenv_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            path = Path(tmp) / "containerenv"
            path.write_text('engine="podman-5.8.9"\nname="dev"\nid="abc123"\n')
            self.assertEqual(current_container_name(path), "dev")
            path.write_text('engine="podman"\n')
            self.assertIsNone(current_container_name(path))
            self.assertIsNone(current_container_name(Path(tmp) / "missing"))


class ContainerCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run = patch("mission_control.containers.subprocess.run").start()
        self.current = patch("mission_control.containers.current_container_name", return_value="dev").start()
        self.which = patch("mission_control.containers.shutil.which", return_value=None).start()
        self.addCleanup(patch.stopall)
        self.run.return_value = subprocess.CompletedProcess([], 0, "[]", "")

    def test_list_filters_on_host_with_timeout(self) -> None:
        self.assertEqual(list_containers(), ContainerResult([]))
        self.run.assert_called_once_with(
            ["distrobox-host-exec", "podman", "ps", "-a", "--filter",
             "label=manager=distrobox", "--format", "json"],
            capture_output=True, text=True, timeout=LIST_TIMEOUT_SECONDS, check=False,
        )

    def test_direct_host_podman(self) -> None:
        self.current.return_value = None
        self.which.return_value = "/usr/bin/podman"
        list_containers()
        self.assertEqual(self.run.call_args.args[0][0], "podman")

    def test_inside_container_always_uses_host(self) -> None:
        self.which.return_value = "/usr/bin/podman"
        list_containers()
        self.assertEqual(self.run.call_args.args[0][0], "distrobox-host-exec")

    def test_list_failure_has_readable_error(self) -> None:
        self.run.return_value = subprocess.CompletedProcess([], 125, "", "detail\nHost unavailable\n")
        self.assertEqual(list_containers(), ContainerResult([], "Host unavailable"))

    def test_invalid_listing_is_reported(self) -> None:
        self.run.return_value.stdout = "invalid json"
        result = list_containers()
        self.assertEqual(result.containers, [])
        self.assertIn("Invalid podman output", result.error or "")

    def test_command_exceptions_are_reported(self) -> None:
        for error in (FileNotFoundError("missing command"), subprocess.TimeoutExpired("podman", 30)):
            with self.subTest(error=error):
                self.run.side_effect = error
                result = list_containers()
                self.assertEqual(result.containers, [])
                self.assertTrue(result.error)
                for action in (start_container, stop_container):
                    ok, message = action("work")
                    self.assertFalse(ok)
                    self.assertTrue(message)

    def test_stop_refuses_current_container_without_subprocess(self) -> None:
        ok, message = stop_container("dev")
        self.assertFalse(ok)
        self.assertIn("running inside", message)
        self.run.assert_not_called()

    def test_start_and_stop_use_safe_arguments_and_action_timeout(self) -> None:
        for action, verb in ((start_container, "start"), (stop_container, "stop")):
            with self.subTest(verb=verb):
                self.assertTrue(action("work")[0])
                self.run.assert_called_with(
                    ["distrobox-host-exec", "podman", verb, "--", "work"],
                    capture_output=True, text=True, timeout=ACTION_TIMEOUT_SECONDS, check=False,
                )

    def test_actions_report_nonzero_exit(self) -> None:
        self.run.return_value = subprocess.CompletedProcess([], 125, "", "permission denied")
        for action in (start_container, stop_container):
            self.assertEqual(action("work"), (False, "permission denied"))
        self.run.return_value.stderr = ""
        self.assertEqual(start_container("work"), (False, "podman exited with 125"))

    def test_empty_name_does_not_run_command(self) -> None:
        for action in (start_container, stop_container):
            self.assertFalse(action("")[0])
        self.run.assert_not_called()


class ContainerCellsTests(unittest.TestCase):
    def test_states_and_current_container_marker(self) -> None:
        for state, symbol, colour in (("running", "●", OK), ("exited", "○", MUTED),
                                      ("stopped", "○", MUTED), ("paused", "●", WARN)):
            with self.subTest(state=state):
                cells = _container_cells(ContainerInfo(
                    "dev", state, "registry.fedoraproject.org/fedora-toolbox:44", "Up 1 hour",
                ), "dev")
                self.assertEqual(len(cells), 3)
                self.assertEqual(cells[0].plain, "dev (this)")
                uptime = " · 1h" if state == "running" else ""
                self.assertEqual(cells[1].plain, f"{symbol} {state}{uptime}")
                self.assertEqual(cells[1].style, colour)
                self.assertEqual(cells[2].plain, "fedora-toolbox:44")

    def test_short_uptime(self) -> None:
        cases = {
            "Up 5 minutes": "5m",
            "Up About an hour": "1h",
            "Up About a minute": "1m",
            "Up Less than a second": "<1s",
            "Up 3 days": "3d",
            "Up 2 weeks": "2w",
            "Exited (0) 2 hours ago": "",
            "": "",
            "Up": "",
        }
        for status, expected in cases.items():
            with self.subTest(status=status):
                self.assertEqual(_short_uptime(status), expected)


class ContainersAppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.dev = ContainerInfo("dev", "running", "fedora:44", "Up 1 hour")
        self.work = ContainerInfo("work", "exited", "debian:13", "Exited (0)")
        self.listing = ContainerResult([self.dev, self.work])
        self.list_mock = patch("mission_control.app.list_containers", return_value=self.listing).start()
        patch("mission_control.app.scan_projects", return_value=[]).start()
        patch("mission_control.app.current_container_name", return_value="dev").start()
        self.start = patch("mission_control.app.start_container", return_value=(True, "Started work.")).start()
        self.stop = patch("mission_control.app.stop_container", return_value=(True, "Stopped work.")).start()
        self.addCleanup(patch.stopall)

    async def test_headless_mount_refresh_selection_and_error(self) -> None:
        app = MissionControlApp()
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            panel = app.query_one(ContainersPanel)
            self.assertEqual(panel.table.row_count, 2)
            panel.table.move_cursor(row=1)
            panel.show(ContainerResult([ContainerInfo("alpha", "created", "a", ""), self.work]), "dev")
            self.assertEqual(panel.selected_name, "work")
            await pilot.press("r")
            await app.workers.wait_for_complete()
            self.assertGreaterEqual(self.list_mock.call_count, 2)
            self.assertEqual(panel.selected_name, "work")
            with patch.object(panel, "set_label") as label:
                panel.show(ContainerResult([], "Host unavailable"), "dev")
                self.assertEqual(label.call_args.args[0].style, panel.palette.alert)
                self.assertIn("Host unavailable", label.call_args.args[0].plain)
            self.assertIsNone(panel.selected_container)

    async def test_self_stop_and_empty_selection_warn(self) -> None:
        app = MissionControlApp()
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            with patch.object(app, "notify") as notify:
                await pilot.press("s")
                self.assertEqual(notify.call_args.kwargs["severity"], "warning")
                self.assertIn("running inside", notify.call_args.args[0])
                app.query_one(ContainersPanel).show(ContainerResult([]), "dev")
                await pilot.press("s")
                self.assertIn("Select a container", notify.call_args.args[0])
            self.start.assert_not_called()
            self.stop.assert_not_called()

    async def test_start_stop_notifications_and_refresh(self) -> None:
        app = MissionControlApp()
        async with app.run_test():
            await app.workers.wait_for_complete()
            panel = app.query_one(ContainersPanel)
            panel.table.move_cursor(row=1)
            with patch.object(app, "notify") as notify:
                app.action_toggle_container()
                self.assertEqual(notify.call_args.args[0], "Starting work…")
                app.action_toggle_container()
                self.assertEqual(notify.call_args.kwargs["severity"], "warning")
                await app.workers.wait_for_complete()
                self.start.assert_called_once_with("work")
                notify.assert_any_call("Started work.", severity="information")
                running = ContainerInfo("work", "running", "debian:13", "Up 1 second")
                panel.show(ContainerResult([running]), "dev")
                self.stop.return_value = (False, "permission denied")
                app.action_toggle_container()
                self.assertEqual(notify.call_args.args[0], "Stopping work…")
                await app.workers.wait_for_complete()
                self.stop.assert_called_once_with("work")
                notify.assert_any_call("permission denied", severity="error")
            self.assertFalse(app._container_action_pending)
            self.assertGreaterEqual(self.list_mock.call_count, 3)


if __name__ == "__main__":
    unittest.main()
