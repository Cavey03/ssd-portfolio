"""Tests for the parts of mission_control.localllm that talk to Ollama, nvidia-smi and systemctl.

Nothing real is contacted: HTTP and commands are mocked. (The parsing functions are tested in
test_localllm.py.) Run with: python -m unittest -v
"""

from __future__ import annotations

import io
import subprocess
import unittest
import urllib.error
from unittest.mock import patch

from mission_control.localllm import (
    NVIDIA_SMI_QUERY, host_command, read_gpu, read_ollama, set_service,
)

TAGS = '{"models":[{"name":"ornith-1.5:9b","size":6550813657,"details":{"parameter_size":"9.0B"}}]}'
PS = '{"models":[{"name":"ornith-1.5:9b","size":10,"size_vram":10,"context_length":65536}]}'


def fake_server(replies: dict[str, str | Exception]):
    """A stand-in for urllib.request.urlopen that answers by URL path."""

    def urlopen(url: str, timeout: float):
        reply = replies[url.rsplit("/api/", 1)[1]]
        if isinstance(reply, Exception):
            raise reply
        return io.BytesIO(reply.encode())

    return urlopen


class ReadOllamaTests(unittest.TestCase):
    def read(self, replies: dict[str, str | Exception]):
        with patch("mission_control.localllm.urllib.request.urlopen", side_effect=fake_server(replies)):
            return read_ollama("http://test")

    def test_stopped_server_is_not_an_error(self) -> None:
        status = self.read({"version": urllib.error.URLError("Connection refused")})
        self.assertFalse(status.running)
        self.assertIsNone(status.error)

    def test_running_server(self) -> None:
        status = self.read({"version": '{"version":"0.40.14"}', "tags": TAGS, "ps": PS})
        self.assertTrue(status.running)
        self.assertEqual(status.version, "0.40.14")
        self.assertEqual([m.name for m in status.installed], ["ornith-1.5:9b"])
        self.assertEqual(status.loaded[0].context_length, 65536)
        self.assertIsNone(status.error)

    def test_bad_reply_is_reported(self) -> None:
        status = self.read({"version": '{"version":"0.40.14"}', "tags": TAGS, "ps": "not json"})
        self.assertTrue(status.running)
        self.assertEqual(status.version, "0.40.14")
        self.assertIn("bad reply", status.error or "")

    def test_url_override(self) -> None:
        with patch.dict("os.environ", {"MISSION_CONTROL_OLLAMA_URL": "http://elsewhere:1/"}), \
                patch("mission_control.localllm.urllib.request.urlopen",
                      side_effect=urllib.error.URLError("x")) as urlopen:
            read_ollama()
        self.assertEqual(urlopen.call_args.args[0], "http://elsewhere:1/api/version")


class HostCommandTests(unittest.TestCase):
    def test_prefix_only_inside_a_container(self) -> None:
        with patch("mission_control.localllm.current_container_name", return_value="dev"):
            self.assertEqual(host_command(["nvidia-smi"]), ["distrobox-host-exec", "nvidia-smi"])
        with patch("mission_control.localllm.current_container_name", return_value=None):
            self.assertEqual(host_command(["nvidia-smi"]), ["nvidia-smi"])


class CommandTests(unittest.TestCase):
    def setUp(self) -> None:
        patch("mission_control.localllm.current_container_name", return_value="dev").start()
        self.run_mock = patch("mission_control.localllm.subprocess.run").start()
        self.addCleanup(patch.stopall)

    def reply(self, code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.run_mock.return_value = subprocess.CompletedProcess([], code, stdout, stderr)

    def test_read_gpu(self) -> None:
        self.reply(stdout="NVIDIA GeForce RTX 5070, 9351, 12227, 18\n")
        gpu = read_gpu()
        self.assertEqual((gpu.memory_used_mb, gpu.memory_total_mb), (9351, 12227))
        self.assertEqual(self.run_mock.call_args.args[0], ["distrobox-host-exec", *NVIDIA_SMI_QUERY])

    def test_read_gpu_failures(self) -> None:
        self.reply(code=9)
        self.assertIsNone(read_gpu())
        for error in (OSError("no such file"), subprocess.TimeoutExpired("nvidia-smi", 3)):
            self.run_mock.side_effect = error
            self.assertIsNone(read_gpu())

    def test_set_service(self) -> None:
        self.reply()
        self.assertEqual(set_service(True), (True, "Ollama started"))
        self.assertEqual(
            self.run_mock.call_args.args[0],
            ["distrobox-host-exec", "systemctl", "--user", "start", "ollama"],
        )
        self.assertEqual(set_service(False), (True, "Ollama stopped"))
        self.assertEqual(self.run_mock.call_args.args[0][-2], "stop")

    def test_set_service_failures(self) -> None:
        self.reply(code=5, stderr="Failed to start ollama.service: Unit not found.\n")
        self.assertEqual(
            set_service(True), (False, "Could not start Ollama: Failed to start ollama.service: Unit not found.")
        )
        self.run_mock.side_effect = subprocess.TimeoutExpired("systemctl", 20)
        ok, message = set_service(False)
        self.assertFalse(ok)
        self.assertTrue(message.startswith("Could not stop Ollama:"))


if __name__ == "__main__":
    unittest.main()
