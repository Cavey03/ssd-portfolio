"""Tests for mission_control.agents and mission_control.usage (fake /proc and logs)."""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path

from mission_control.agents import describe_folder, find_agents, format_age, identify_agent
from mission_control.panels import format_tokens
from mission_control.usage import (
    LocalUsage,
    parse_claude_config,
    parse_codex_rate_limits,
    read_claude_usage,
    read_codex_usage,
    read_local_usage,
    session_local_tokens,
)


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

    def test_agent_is_named_by_its_project(self) -> None:
        root = Path.home() / "Projects"
        projects = (".", "su5-7-llm-agents/mission-control", "su5-7-llm-agents/local-llm", "particle-sim")
        cases = [
            (root / "su5-7-llm-agents/mission-control/tests", "mission-control"),
            (root / "su5-7-llm-agents/local-llm", "local-llm"),
            (root / "su5-7-llm-agents/environment", "su5-7-llm-agents"),  # not a project: first folder
            (root / "particle-sim/src", "particle-sim"),
            (root / "su5-7-llm-agents/mission-control-old", "su5-7-llm-agents"),  # prefix, not inside
            (root, "~/Projects"),
        ]
        for cwd, expected in cases:
            with self.subTest(cwd=cwd):
                self.assertEqual(describe_folder(cwd, root, projects), expected)

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

    LOCAL_LINE = json.dumps({  # what a session on the local model (Ollama) writes
        "type": "event_msg",
        "payload": {"type": "token_count", "rate_limits": {
            "limit_id": "codex", "primary": None, "secondary": None, "plan_type": None}},
    })

    def test_local_model_snapshot_is_skipped(self) -> None:
        self.assertIsNone(parse_codex_rate_limits(self.LOCAL_LINE, 1.0, self.NOW))
        future = time.time() + 3600
        with tempfile.TemporaryDirectory() as tmp:
            day = Path(tmp) / "2026" / "11" / "18"
            day.mkdir(parents=True)
            gpt = day / "rollout-gpt.jsonl"
            gpt.write_text(self.line(future, future) + "\n")
            local = day / "rollout-local.jsonl"  # newer, but has no limits
            local.write_text(self.LOCAL_LINE + "\n")
            os.utime(gpt, (1_000, 1_000))
            usage = read_codex_usage(Path(tmp))
        assert usage is not None
        self.assertEqual(usage.five_hour.used_percent, 15.0)

    def test_no_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(read_codex_usage(Path(tmp)))


class LocalUsageTests(unittest.TestCase):
    """Tokens of Codex sessions on the local model (Ollama)."""

    @staticmethod
    def session(provider: str, totals: list[int]) -> str:
        lines = [json.dumps({"type": "session_meta", "payload": {"model_provider": provider}})]
        for total in totals:
            lines.append(json.dumps({"type": "event_msg", "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": total - 10, "output_tokens": 10, "total_tokens": total}}}}))
        lines.append(json.dumps({"type": "event_msg", "payload": {"type": "token_count", "info": None}}))
        return "\n".join(lines) + "\n"

    def write(self, root: Path, name: str, text: str, mtime: float) -> Path:
        path = root / name
        path.write_text(text)
        os.utime(path, (mtime, mtime))
        return path

    def test_session_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = self.write(root, "a.jsonl", self.session("ollama", [100, 2500]), 1.0)
            cloud = self.write(root, "b.jsonl", self.session("openai", [999]), 1.0)
            broken = self.write(root, "c.jsonl", "not json\n", 1.0)
            self.assertEqual(session_local_tokens(local), 2500)  # the last running total counts
            self.assertIsNone(session_local_tokens(cloud))
            self.assertIsNone(session_local_tokens(broken))

    def test_today_and_week(self) -> None:
        now = datetime(2026, 11, 18, 15, 0).timestamp()
        day = 24 * 3600
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "today.jsonl", self.session("ollama", [2_000_000]), now - 3600)
            self.write(root, "yesterday.jsonl", self.session("ollama", [300_000]), now - day)
            self.write(root, "old.jsonl", self.session("ollama", [5_000_000]), now - 8 * day)
            self.write(root, "gpt.jsonl", self.session("openai", [7_000]), now - 60)
            usage = read_local_usage(root, now)
        self.assertEqual(usage, LocalUsage(2_000_000, 1, 2_300_000, 2))

    def test_log_is_reread_only_when_it_changes(self) -> None:
        now = time.time()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "s.jsonl", self.session("ollama", [10]), now - 60)
            self.assertEqual(read_local_usage(root, now).today_tokens, 10)
            with patch("mission_control.usage.session_local_tokens") as reader:
                read_local_usage(root, now)
                reader.assert_not_called()  # unchanged: served from the cache
            self.write(root, "s.jsonl", self.session("ollama", [10, 50]), now - 30)
            self.assertEqual(read_local_usage(root, now).today_tokens, 50)

    def test_format_tokens(self) -> None:
        for count, text in ((999, "999"), (1_234, "1.2K"), (2_207_237, "2.2M")):
            self.assertEqual(format_tokens(count), text)


class ClaudeUsageTests(unittest.TestCase):
    NOW = datetime(2026, 11, 3, 21, 0, tzinfo=timezone.utc).timestamp()

    def config(self, five_hour_reset: str = "2026-11-03T22:40:00.1+00:00") -> str:
        """A trimmed-down ~/.claude.json with the usage cache."""
        return json.dumps({
            "numStartups": 5,
            "cachedUsageUtilization": {
                "fetchedAtMs": 1793730755733,
                "utilization": {
                    "five_hour": {"utilization": 4, "resets_at": five_hour_reset},
                    "seven_day": {"utilization": 29, "resets_at": "2026-11-07T13:00:00.1+00:00"},
                    "seven_day_opus": None,
                },
            },
        })

    def test_parses_cached_limits(self) -> None:
        usage = parse_claude_config(self.config(), self.NOW)
        assert usage is not None
        self.assertEqual(usage.five_hour.used_percent, 4)
        self.assertEqual(usage.five_hour.window_minutes, 300)
        self.assertEqual(usage.weekly.used_percent, 29)
        self.assertAlmostEqual(usage.observed_at, 1793730755.733)

    def test_window_that_already_reset_counts_as_zero(self) -> None:
        usage = parse_claude_config(self.config("2026-11-03T20:00:00+00:00"), self.NOW)
        assert usage is not None
        self.assertEqual(usage.five_hour.used_percent, 0.0)

    def test_missing_or_odd_data(self) -> None:
        self.assertIsNone(parse_claude_config("not json", self.NOW))
        self.assertIsNone(parse_claude_config('{"numStartups": 1}', self.NOW))
        self.assertIsNone(parse_claude_config('{"cachedUsageUtilization": {"utilization": 3}}', self.NOW))
        usage = parse_claude_config(
            '{"cachedUsageUtilization": {"utilization": {"five_hour": {"utilization": "x"}}}}', self.NOW
        )
        assert usage is not None
        self.assertIsNone(usage.five_hour)
        self.assertIsNone(usage.weekly)
        self.assertIsNone(usage.observed_at)

    def test_reads_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".claude.json"
            self.assertIsNone(read_claude_usage(path))  # missing file
            path.write_text(self.config())
            usage = read_claude_usage(path, now=self.NOW)  # fixed time: the sample's windows mustn't expire
        assert usage is not None
        self.assertEqual(usage.weekly.used_percent, 29)


if __name__ == "__main__":
    unittest.main()
