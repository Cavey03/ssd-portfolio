"""Tests for themes, the palette and remembering the chosen theme."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mission_control.agents import AgentProcess
from mission_control.app import MissionControlApp
from mission_control.containers import ContainerResult
from mission_control.panels import AgentsPanel
from mission_control.localllm import OllamaStatus
from mission_control.settings import load_settings, save_setting, settings_path
from mission_control.themes import (
    DEFAULT_THEME,
    THEMES,
    next_theme,
    palette_from_variables,
)


class IsolatedSettings(unittest.TestCase):
    """Give each test its own empty settings folder."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        env = patch.dict(os.environ, {"MISSION_CONTROL_CONFIG_DIR": self._tmp.name})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(self._tmp.cleanup)


class ThemeCycleTests(unittest.TestCase):
    def test_cycles_through_our_themes_and_wraps(self) -> None:
        names = [t.name for t in THEMES]
        self.assertEqual(names[0], DEFAULT_THEME)
        for current, expected in zip(names, names[1:] + names[:1]):
            self.assertEqual(next_theme(current), expected)

    def test_builtin_theme_jumps_back_to_first(self) -> None:
        self.assertEqual(next_theme("nord"), DEFAULT_THEME)


class PaletteTests(unittest.TestCase):
    def test_plain_colours_from_variables(self) -> None:
        pal = palette_from_variables({
            "success": "#00ff9f",
            "warning": "#FCEE0A",
            "error": "#ff2a6d99",   # alpha is dropped: Rich can't use it
            "primary": "#00f0ff",
            "foreground": "#ffffff",
            "background": "#000000",
            "agent-codex": "#123456",
        })
        self.assertEqual(pal.ok.lower(), "#00ff9f")
        self.assertEqual(pal.alert.lower(), "#ff2a6d")
        self.assertEqual(len(pal.muted), 7)  # a solid "#rrggbb" blend
        self.assertEqual(pal.agent("codex").lower(), "#123456")
        self.assertTrue(pal.agent("claude").startswith("#"))  # falls back to the default

    def test_bad_values_fall_back(self) -> None:
        pal = palette_from_variables({"success": "auto 60%", "foreground": "nonsense"})
        for colour in (pal.ok, pal.warn, pal.alert, pal.info, pal.muted):
            self.assertRegex(colour, r"^#[0-9A-Fa-f]{6}$")


class SettingsTests(IsolatedSettings):
    def test_save_and_load(self) -> None:
        self.assertEqual(load_settings(), {})
        save_setting("theme", "crt-amber")
        save_setting("other", 1)
        self.assertEqual(load_settings(), {"theme": "crt-amber", "other": 1})
        self.assertEqual(settings_path().parent, Path(self._tmp.name))

    def test_broken_file_is_ignored(self) -> None:
        settings_path().write_text("{ not json")
        self.assertEqual(load_settings(), {})
        save_setting("theme", "crt-green")
        self.assertEqual(json.loads(settings_path().read_text()), {"theme": "crt-green"})


class AppThemeTests(IsolatedSettings, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        super().setUp()
        agent = AgentProcess("codex", 4242, Path.home() / "Projects" / "demo", None)
        patch("mission_control.app.find_agents", return_value=[agent]).start()
        patch("mission_control.app.scan_projects", return_value=[]).start()
        # Never contact the real Ollama server or GPU from tests.
        patch("mission_control.app.read_ollama", return_value=OllamaStatus(running=False)).start()
        patch("mission_control.app.read_gpu", return_value=None).start()
        patch("mission_control.app.list_containers", return_value=ContainerResult([])).start()
        patch("mission_control.app.read_codex_usage", return_value=None).start()
        patch("mission_control.app.read_claude_usage", return_value=None).start()
        self.addCleanup(patch.stopall)

    def agent_cell_style(self, app: MissionControlApp) -> str:
        table = app.query_one(AgentsPanel).table
        return str(table.get_row_at(0)[0].style)

    async def test_starts_with_default_theme(self) -> None:
        app = MissionControlApp()
        async with app.run_test():
            self.assertEqual(app.theme, DEFAULT_THEME)

    async def test_t_cycles_recolours_and_remembers(self) -> None:
        app = MissionControlApp()
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            before = self.agent_cell_style(app)

            await pilot.press("t")
            await pilot.pause()
            self.assertEqual(app.theme, THEMES[1].name)
            self.assertNotEqual(self.agent_cell_style(app), before)  # redrawn instantly
            self.assertEqual(load_settings()["theme"], THEMES[1].name)

        # A new app starts with the remembered theme.
        again = MissionControlApp()
        async with again.run_test():
            self.assertEqual(again.theme, THEMES[1].name)

    async def test_unknown_saved_theme_falls_back(self) -> None:
        save_setting("theme", "does-not-exist")
        app = MissionControlApp()
        async with app.run_test():
            self.assertEqual(app.theme, DEFAULT_THEME)

    async def test_builtin_theme_works(self) -> None:
        app = MissionControlApp()
        async with app.run_test() as pilot:
            app.theme = "nord"
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertTrue(self.agent_cell_style(app).startswith("bold #"))


if __name__ == "__main__":
    unittest.main()
