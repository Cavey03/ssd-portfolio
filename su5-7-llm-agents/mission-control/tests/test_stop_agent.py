"""Tests for stopping agents: stop_agent() and the confirm dialog in the app."""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mission_control.agents import AgentProcess, stop_agent
from mission_control.app import MissionControlApp
from mission_control.containers import ContainerResult
from mission_control.dialogs import ConfirmScreen
from mission_control.panels import AgentsPanel
from mission_control.localllm import OllamaStatus


class StopAgentTests(unittest.TestCase):
    """stop_agent() against a fake /proc; os.kill is always mocked."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.proc = Path(self._tmp.name)
        (self.proc / "stat").write_text("btime 1000\n")
        self.ticks = os.sysconf("SC_CLK_TCK")
        self.kill = patch("mission_control.agents.os.kill").start()
        self.addCleanup(patch.stopall)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def add(self, pid: int, argv0: str, start_ticks: int) -> AgentProcess:
        d = self.proc / str(pid)
        d.mkdir()
        (d / "cmdline").write_bytes(argv0.encode() + b"\0")
        (d / "comm").write_text(os.path.basename(argv0) + "\n")
        fields = ["S", "1"] + ["0"] * 17 + [str(start_ticks)]
        (d / "stat").write_text(f"{pid} (x) " + " ".join(fields) + "\n")
        return AgentProcess("codex", pid, None, 1000 + start_ticks / self.ticks)

    def test_sends_sigterm_to_matching_process(self) -> None:
        agent = self.add(500, "/usr/bin/codex", 100)
        ok, message = stop_agent(agent, self.proc)
        self.assertTrue(ok, message)
        self.kill.assert_called_once_with(500, signal.SIGTERM)

    def test_refuses_when_pid_was_reused_by_another_program(self) -> None:
        agent = self.add(501, "/usr/bin/codex", 100)
        (self.proc / "501" / "cmdline").write_bytes(b"/usr/bin/bash\0")
        (self.proc / "501" / "comm").write_text("bash\n")
        ok, _ = stop_agent(agent, self.proc)
        self.assertFalse(ok)
        self.kill.assert_not_called()

    def test_refuses_when_start_time_differs(self) -> None:
        agent = self.add(502, "/usr/bin/codex", 100)
        newer = AgentProcess("codex", 502, None, agent.started + 50)
        self.assertFalse(stop_agent(newer, self.proc)[0])
        self.kill.assert_not_called()

    def test_process_already_gone(self) -> None:
        ok, message = stop_agent(AgentProcess("codex", 999, None, 1.0), self.proc)
        self.assertFalse(ok)
        self.assertIn("already exited", message)

    def test_permission_error_falls_back_to_host(self) -> None:
        agent = self.add(503, "/usr/bin/codex", 100)
        self.kill.side_effect = PermissionError
        with patch("mission_control.agents.shutil.which", return_value="/usr/bin/distrobox-host-exec"), \
             patch("mission_control.agents.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            ok, _ = stop_agent(agent, self.proc)
        self.assertTrue(ok)
        self.assertEqual(run.call_args.args[0], ["distrobox-host-exec", "kill", "-TERM", "503"])

    def test_never_stops_itself(self) -> None:
        ok, _ = stop_agent(AgentProcess("codex", os.getpid(), None, None), self.proc)
        self.assertFalse(ok)
        self.kill.assert_not_called()


class StopAgentAppTests(unittest.IsolatedAsyncioTestCase):
    """The k key asks first and only stops on yes."""

    async def asyncSetUp(self) -> None:
        self.agent = AgentProcess("codex", 4242, Path.home() / "Projects" / "demo", None)
        patch("mission_control.app.find_agents", return_value=[self.agent]).start()
        patch("mission_control.app.scan_projects", return_value=[]).start()
        # Never contact the real Ollama server or GPU from tests.
        patch("mission_control.app.read_ollama", return_value=OllamaStatus(running=False)).start()
        patch("mission_control.app.read_gpu", return_value=None).start()
        patch("mission_control.app.read_local_usage", return_value=None).start()
        patch("mission_control.app.list_containers", return_value=ContainerResult([])).start()
        patch("mission_control.app.read_codex_usage", return_value=None).start()
        patch("mission_control.app.read_claude_usage", return_value=None).start()
        self.stop = patch("mission_control.app.stop_agent", return_value=(True, "Stopped.")).start()
        self.addCleanup(patch.stopall)

    async def test_no_cancels_and_yes_stops(self) -> None:
        app = MissionControlApp()
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(app.query_one(AgentsPanel).selected_agent, self.agent)

            await pilot.press("k")
            await pilot.pause()
            self.assertIsInstance(app.screen, ConfirmScreen)
            await pilot.press("n")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, ConfirmScreen)
            self.stop.assert_not_called()

            await pilot.press("k")
            await pilot.pause()
            await pilot.press("enter")  # "No" has focus, so Enter must not confirm
            await pilot.pause()
            self.stop.assert_not_called()

            await pilot.press("k")
            await pilot.pause()
            await pilot.press("y")
            await app.workers.wait_for_complete()
            self.stop.assert_called_once_with(self.agent)


if __name__ == "__main__":
    unittest.main()
