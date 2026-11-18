"""Launcher and installer tests using fake commands and temporary homes only."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MC = REPO / "scripts/mc"
INSTALL = REPO / "scripts/install.sh"


class ScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="mission-control-scripts-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root / "fake-bin"
        self.bin.mkdir()
        self.home = self.root / "test home"
        self.data = self.root / "test data"
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "XDG_DATA_HOME": str(self.data),
            "PATH": f"{self.bin}:{os.defpath}",
            "CONTAINER_ID": "",
            "MISSION_CONTROL_CONTAINERENV": str(self.root / "absent-containerenv"),
        }
        # A real distrobox is never called, even if a detection assertion fails.
        self.fake_command("distrobox", 'printf "%s\\n" "$@"\n')
        for command in ("desktop-file-validate", "update-desktop-database"):
            self.fake_command(command, "exit 0\n")

    def fake_command(self, name: str, body: str) -> Path:
        path = self.bin / name
        path.write_text("#!/bin/bash\nset -euo pipefail\n" + body)
        path.chmod(0o755)
        return path

    def run_script(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(script), *args], env=self.env, cwd=self.root,
            capture_output=True, text=True, timeout=10,
        )

    def copy_launcher(self) -> Path:
        script = self.root / "checkout with spaces/scripts/mc"
        script.parent.mkdir(parents=True)
        shutil.copy2(MC, script)
        return script


class McLauncherTests(ScriptTests):
    def fake_venv(self, repo: Path, works_on_host: bool = True, venv: str = ".venv") -> Path:
        """A fake venv python: `-c ...` is the host check, anything else "runs the app".

        It prints its own venv name first, so tests can see which venv ran the app.
        """
        python = repo / venv / "bin/python"
        python.parent.mkdir(parents=True)
        check = "exit 0" if works_on_host else "exit 1"
        python.write_text(
            '#!/bin/bash\n'
            f'if [[ "${{1-}}" == -c ]]; then {check}; fi\n'
            f'printf "%s\\n" {venv} "$PWD" "$@"\n'
        )
        python.chmod(0o755)
        return python

    def test_host_runs_app_on_host_when_venv_works(self) -> None:
        script = self.copy_launcher()
        repo = script.parent.parent
        self.fake_venv(repo)
        link = self.root / "mc"
        link.symlink_to(script)
        result = self.run_script(link, "--example", "two words", "$(literal)")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            ".venv", str(repo), "-m", "mission_control", "--example", "two words", "$(literal)",
        ])

    def test_host_prefers_host_venv(self) -> None:
        script = self.copy_launcher()
        repo = script.parent.parent
        self.fake_venv(repo)
        self.fake_venv(repo, venv=".venv-host")
        result = self.run_script(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0], ".venv-host")

    def test_host_venv_used_when_dev_venv_breaks_on_host(self) -> None:
        # The real case: dev's .venv is Python 3.14, the host has 3.15.
        script = self.copy_launcher()
        repo = script.parent.parent
        self.fake_venv(repo, works_on_host=False)
        self.fake_venv(repo, venv=".venv-host")
        result = self.run_script(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[:2], [".venv-host", str(repo)])

    def test_broken_host_venv_falls_through_to_dev_venv(self) -> None:
        script = self.copy_launcher()
        repo = script.parent.parent
        self.fake_venv(repo)
        self.fake_venv(repo, works_on_host=False, venv=".venv-host")
        result = self.run_script(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0], ".venv")

    def test_host_falls_back_to_dev_when_venv_does_not_work(self) -> None:
        script = self.copy_launcher()
        self.fake_venv(script.parent.parent, works_on_host=False)
        link = self.root / "mc"
        link.symlink_to(script)
        result = self.run_script(link, "--example", "two words")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "enter", "dev", "--", str(script.resolve()), "--example", "two words",
        ])
        self.assertIn("Quit it with q", result.stderr)

    def test_host_without_venv_falls_back_to_dev(self) -> None:
        script = self.copy_launcher()
        result = self.run_script(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[:3], ["enter", "dev", "--"])

    def test_other_container_is_rejected(self) -> None:
        self.env["CONTAINER_ID"] = "other"
        result = self.run_script(MC)
        self.assertEqual(result.returncode, 1)
        self.assertIn("run mc on the host or inside dev", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_metadata_detects_other_or_unnamed_container(self) -> None:
        metadata = self.root / "containerenv"
        self.env["MISSION_CONTROL_CONTAINERENV"] = str(metadata)
        for content in ('name="other"\n', 'engine="podman"\n'):
            with self.subTest(content=content):
                metadata.write_text(content)
                result = self.run_script(MC)
                self.assertEqual(result.returncode, 1)
                self.assertIn("run mc on the host or inside dev", result.stderr)

    def test_missing_venv_shows_setup(self) -> None:
        self.env["CONTAINER_ID"] = "dev"
        script = self.copy_launcher()
        result = self.run_script(script)
        self.assertEqual(result.returncode, 1)
        for command in (
            "distrobox enter dev", "python3 -m venv .venv",
            "source .venv/bin/activate", "pip install -r requirements.txt",
        ):
            self.assertIn(command, result.stderr)
        cd_line = next(line for line in result.stderr.splitlines() if line.startswith("cd "))
        self.assertEqual(shlex.split(cd_line), ["cd", str(script.parent.parent)])

    def test_dev_runs_fake_python_from_repo_and_preserves_arguments(self) -> None:
        script = self.copy_launcher()
        repo = script.parent.parent
        python = repo / ".venv/bin/python"
        python.parent.mkdir(parents=True)
        python.write_text('#!/bin/bash\nprintf "%s\\n" "$PWD" "$@"\n')
        python.chmod(0o755)
        metadata = self.root / "containerenv"
        metadata.write_text('engine="podman"\nname="dev"\n')
        self.env["MISSION_CONTROL_CONTAINERENV"] = str(metadata)
        link = self.root / "mc"
        link.symlink_to(script)
        for container in ("", "dev"):
            with self.subTest(container=container):
                self.env["CONTAINER_ID"] = container
                result = self.run_script(link, "--example", "two words", "")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), [
                    str(repo), "-m", "mission_control", "--example", "two words", "",
                ])

    def test_help_needs_no_container_or_venv(self) -> None:
        script = self.copy_launcher()
        for container in ("", "dev", "other"):
            with self.subTest(container=container):
                self.env["CONTAINER_ID"] = container
                result = self.run_script(script, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Usage: mc", result.stdout)
                self.assertNotIn("enter\n", result.stdout)


class McInstallerTests(ScriptTests):
    @property
    def launcher(self) -> Path:
        return self.home / ".local/bin/mc"

    @property
    def desktop(self) -> Path:
        return self.data / "applications/mission-control.desktop"

    def test_install_is_repeatable_and_uninstall_removes_both(self) -> None:
        for _ in range(2):
            result = self.run_script(INSTALL)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Linked", result.stdout)
            self.assertIn("Wrote", result.stdout)
            self.assertTrue(self.launcher.is_symlink())
            self.assertEqual(self.launcher.readlink(), MC)
            content = self.desktop.read_text()
            self.assertNotIn("@MC_PATH@", content)
            self.assertIn(f'Exec=konsole --hide-menubar -e "{self.launcher}"\n', content)
            self.assertIn("Terminal=false\n", content)
            self.assertIn("Icon=utilities-system-monitor\n", content)
        result = self.run_script(INSTALL, "--uninstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Removed {self.launcher}", result.stdout)
        self.assertIn(f"Removed {self.desktop}", result.stdout)
        self.assertFalse(self.launcher.is_symlink())
        self.assertFalse(self.desktop.exists())
        self.assertEqual(self.run_script(INSTALL, "--uninstall").returncode, 0)

    def test_regular_file_is_preserved(self) -> None:
        self.launcher.parent.mkdir(parents=True)
        self.launcher.write_text("existing command\n")
        result = self.run_script(INSTALL)
        self.assertEqual(result.returncode, 1)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(self.launcher.read_text(), "existing command\n")
        self.assertFalse(self.desktop.exists())
        self.assertEqual(self.run_script(INSTALL, "--uninstall").returncode, 0)
        self.assertEqual(self.launcher.read_text(), "existing command\n")

    def test_existing_symlink_is_replaced(self) -> None:
        self.launcher.parent.mkdir(parents=True)
        self.launcher.symlink_to(self.root / "old-target")
        result = self.run_script(INSTALL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.launcher.readlink(), MC)

    def test_default_data_home(self) -> None:
        del self.env["XDG_DATA_HOME"]
        result = self.run_script(INSTALL)
        self.assertEqual(result.returncode, 0, result.stderr)
        desktop = self.home / ".local/share/applications/mission-control.desktop"
        self.assertTrue(desktop.is_file())
        result = self.run_script(INSTALL, "--uninstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(desktop.exists())

    def test_optional_desktop_tools_receive_only_temporary_paths(self) -> None:
        self.fake_command("desktop-file-validate", 'printf "validate:%s\\n" "$@"\n')
        self.fake_command("update-desktop-database", 'printf "update:%s\\n" "$@"\n')
        result = self.run_script(INSTALL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"validate:{self.desktop}\n", result.stdout)
        self.assertIn(f"update:{self.desktop.parent}\n", result.stdout)
        result = self.run_script(INSTALL, "--uninstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("validate:", result.stdout)
        self.assertIn(f"update:{self.desktop.parent}\n", result.stdout)

    def test_desktop_exec_escapes_special_characters(self) -> None:
        self.home = self.root / 'home "quote" $dollar `tick` \\slash %field'
        self.env["HOME"] = str(self.home)
        result = self.run_script(INSTALL)
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(line for line in self.desktop.read_text().splitlines() if line.startswith("Exec="))
        # Desktop value escaping is decoded before command-line quoting and field codes.
        value = line.removeprefix("Exec=").replace("\\\\", "\\")
        args = shlex.split(value.replace("%%", "%"))
        # shlex preserves backslashes before $ and `; desktop Exec parsing removes them.
        executable = args[-1].replace("\\$", "$").replace("\\`", "`")
        self.assertEqual(executable, str(self.launcher))


if __name__ == "__main__":
    unittest.main()
