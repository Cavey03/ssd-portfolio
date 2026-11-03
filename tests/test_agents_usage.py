"""Tests for mission_control.agents and mission_control.usage (fake /proc and logs)."""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from mission_control.agents import describe_folder, find_agents, format_age, identify_agent
from mission_control.usage import parse_codex_rate_limits, read_claude_usage, read_codex_usage


class IdentifyAgentTests(unittest.TestCase):
    def test_known_agents_and_helpers(self) -> None:
        cases = [
            ("/home/k/.local/share/claude/versions/2.1.317", "2.1.317", "claude"),
            ("claude", "claude", "claude"),
            ("/usr/local/lib/node_modules/@openai/codex/vendor/bin/codex", "codex", "codex"),
            ("/home/k/.codex/packages/app-server-daemon/releases/x/bin/codex", "codex", None),
            ("/home/k/.codex/tmp/arg0/codex-linux-sandbox", "codex-linux-san", None),
            ("agy", "agy", "agy"),
            ("/usr/bin/bash", "bash", None),
            ("", "", None),
        ]
        for argv0, comm, expected in cases:
            with self.subTest(argv0=argv0):
                self.assertEqual(identify_agent(argv0, comm), expected)


class DescribeFolderTests(unittest.TestCase):
    def test_folders(self) -> None:
        home = Path.home()
        root = home / "Projects"
        var_root = Path("/var" + str(root))  # Fedora Atomic's real path for /home
        cases = [
            (root / "mission-control" / "tests", "mission-control"),
            (var_root / "ssd-portfolio", "ssd-portfolio"),
            (root / ".worktrees" / "mc-launch", "mc-launch (worktree)"),
            (root, "~/Projects"),
            (home, "~"),
            (home / "Downloads", "~/Downloads"),
            (Path("/tmp/x"), "/tmp/x"),
            (None, "?"),
        ]
        for cwd, expected in cases:
            with self.subTest(cwd=cwd):
                self.assertEqual(describe_folder(cwd, root), expected)

    def test_format_age(self) -> None:
        now = 1_000_000.0
        self.assertEqual(format_age(now - 5, now), "5s")
        self.assertEqual(format_age(now - 125, now), "2m")
        self.assertEqual(format_age(now - 7300, now), "2h")
        self.assertEqual(format_age(now - 3 * 86400, now), "3d")
        self.assertEqual(format_age(None, now), "?")


class FindAgentsTests(unittest.TestCase):
    """Build a fake /proc tree and check what find_agents reports."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.proc = Path(self._tmp.name)
        (self.proc / "stat").write_text("cpu 1 2 3\nbtime 1000\n")
        self.work = self.proc / "work"
        self.work.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def add(self, pid: int, argv0: str, comm: str, ppid: int, start_ticks: int, cwd: bool = True) -> None:
        d = self.proc / str(pid)
        d.mkdir()
        (d / "cmdline").write_bytes(argv0.encode() + b"\0--flag\0")
        (d / "comm").write_text(comm + "\n")
        # Field 2 has a space in it on purpose, to test the ")" split.
        fields = ["S", str(ppid)] + ["0"] * 17 + [str(start_ticks)]
        (d / "stat").write_text(f"{pid} (my {comm}) " + " ".join(fields) + "\n")
        if cwd:
            os.symlink(self.work, d / "cwd")

    def test_finds_sessions_skips_helpers_and_children(self) -> None:
        self.add(10, "/x/claude/versions/2.1.0", "2.1.0", ppid=1, start_ticks=200)
        self.add(11, "/usr/bin/codex", "codex", ppid=1, start_ticks=100)
        self.add(12, "/usr/bin/codex", "codex", ppid=11, start_ticks=300)  # child of 11
        self.add(13, "/x/app-server-daemon/bin/codex", "codex", ppid=1, start_ticks=50)
        self.add(14, "/usr/bin/bash", "bash", ppid=1, start_ticks=10)
        self.add(15, "agy", "agy", ppid=1, start_ticks=400, cwd=False)
        (self.proc / "self").mkdir()  # non-numeric entries are ignored

        agents = find_agents(self.proc, ask_host=False)

        self.assertEqual([(a.agent, a.pid) for a in agents], [("codex", 11), ("claude", 10), ("agy", 15)])
        self.assertEqual(agents[0].cwd, self.work)
        self.assertIsNone(agents[2].cwd)
        ticks = os.sysconf("SC_CLK_TCK")
        self.assertAlmostEqual(agents[0].started, 1000 + 100 / ticks)


class CodexUsageTests(unittest.TestCase):
    NOW = 2_000_000_000.0

    def line(self, primary_reset: float, secondary_reset: float) -> str:
        return json.dumps({
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "rate_limits": {
                    "primary": {"used_percent": 15.0, "window_minutes": 300, "resets_at": primary_reset},
                    "secondary": {"used_percent": 2.0, "window_minutes": 10080, "resets_at": secondary_reset},
                    "plan_type": "plus",
                },
            },
        })

    def test_parses_limits(self) -> None:
        usage = parse_codex_rate_limits(self.line(self.NOW + 60, self.NOW + 600), 1.0, self.NOW)
        assert usage is not None
        self.assertEqual(usage.plan, "plus")
        self.assertEqual(usage.five_hour.used_percent, 15.0)
        self.assertEqual(usage.weekly.window_minutes, 10080)

    def test_window_that_already_reset_counts_as_zero(self) -> None:
        usage = parse_codex_rate_limits(self.line(self.NOW - 60, self.NOW + 600), 1.0, self.NOW)
        assert usage is not None
        self.assertEqual(usage.five_hour.used_percent, 0.0)
        self.assertEqual(usage.weekly.used_percent, 2.0)

    def test_bad_lines(self) -> None:
        self.assertIsNone(parse_codex_rate_limits("not json", 1.0, self.NOW))
        self.assertIsNone(parse_codex_rate_limits('{"payload": {}}', 1.0, self.NOW))

    def test_reads_newest_snapshot_from_logs(self) -> None:
        future = time.time() + 3600
        with tempfile.TemporaryDirectory() as tmp:
            day = Path(tmp) / "2026" / "11" / "03"
            day.mkdir(parents=True)
            log = day / "rollout.jsonl"
            older = json.loads(self.line(future, future))
            older["payload"]["rate_limits"]["primary"]["used_percent"] = 5.0
            log.write_text(json.dumps(older) + "\n" + self.line(future, future) + "\n{}\n")
            usage = read_codex_usage(Path(tmp))
        assert usage is not None
        self.assertEqual(usage.five_hour.used_percent, 15.0)

    def test_no_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(read_codex_usage(Path(tmp)))


class ClaudeUsageTests(unittest.TestCase):
    def test_counts_unique_messages_per_window(self) -> None:
        now = time.time()

        def entry(msg_id: str, hours_ago: float, out: int) -> str:
            ts = datetime.fromtimestamp(now - hours_ago * 3600, timezone.utc).isoformat().replace("+00:00", "Z")
            return json.dumps({
                "type": "assistant",
                "timestamp": ts,
                "message": {"id": msg_id, "usage": {"output_tokens": out}},
            })

        lines = [
            entry("a", 1, 100),
            entry("a", 1, 100),   # same message logged twice -> counted once
            entry("b", 4, 50),
            entry("c", 30, 1000),  # older than 5h, inside 7d
            entry("d", 200, 9999),  # older than 7d
            '{"type": "user", "message": {"content": "hi"}}',
            "garbage",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "-home-Kyle"
            project.mkdir()
            (project / "session.jsonl").write_text("\n".join(lines) + "\n")
            usage = read_claude_usage(Path(tmp), now=now)

        self.assertEqual((usage.requests_5h, usage.output_tokens_5h), (2, 150))
        self.assertEqual((usage.requests_7d, usage.output_tokens_7d), (3, 1150))


if __name__ == "__main__":
    unittest.main()
