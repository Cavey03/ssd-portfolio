"""Tests for mission_control.gitinfo. Run with: python -m unittest -v"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from mission_control.gitinfo import find_projects, parse_porcelain_v2, read_status, scan_projects


def git(cwd: Path, *args: str) -> None:
    """Run a git command quietly, with a throwaway identity."""
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def make_repo(path: Path) -> Path:
    """Create a git repo with one commit."""
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    (path / "README.md").write_text("hello\n")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "first")
    return path


class ParsePorcelainTests(unittest.TestCase):
    def test_parses_branch_counts_and_changes(self) -> None:
        output = (
            "# branch.oid abc123\n"
            "# branch.head main\n"
            "# branch.upstream origin/main\n"
            "# branch.ab +2 -1\n"
            "1 .M N... 100644 100644 100644 aaa bbb app.py\n"
            "2 R. N... 100644 100644 100644 aaa bbb R100 new.py\told.py\n"
            "? notes.txt\n"
        )
        self.assertEqual(parse_porcelain_v2(output), ("main", 3, 2, 1))

    def test_no_upstream_means_none(self) -> None:
        output = "# branch.oid (initial)\n# branch.head main\n"
        self.assertEqual(parse_porcelain_v2(output), ("main", 0, None, None))


class ReadStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_clean_repo_without_remote(self) -> None:
        status = read_status(make_repo(self.root / "clean"))
        self.assertTrue(status.is_repo)
        self.assertEqual(status.branch, "main")
        self.assertEqual(status.changes, 0)
        self.assertIsNone(status.ahead)
        self.assertIsNone(status.error)

    def test_counts_modified_and_untracked_files(self) -> None:
        repo = make_repo(self.root / "dirty")
        (repo / "README.md").write_text("changed\n")
        (repo / "new.txt").write_text("new\n")
        self.assertEqual(read_status(repo).changes, 2)

    def test_counts_unpushed_commits(self) -> None:
        remote = self.root / "remote.git"
        git(self.root, "init", "-q", "--bare", str(remote))
        repo = make_repo(self.root / "work")
        git(repo, "remote", "add", "origin", str(remote))
        git(repo, "push", "-q", "-u", "origin", "main")
        self.assertEqual((read_status(repo).ahead, read_status(repo).behind), (0, 0))

        (repo / "more.txt").write_text("more\n")
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "second")
        self.assertEqual(read_status(repo).ahead, 1)

    def test_plain_folder_is_not_a_repo(self) -> None:
        folder = self.root / "plain"
        folder.mkdir()
        self.assertFalse(read_status(folder).is_repo)

    def test_plain_folders_without_markers_are_not_projects(self) -> None:
        (self.root / "A-folder").mkdir()
        (self.root / "file.txt").write_text("not a folder\n")
        self.assertEqual(scan_projects(self.root), [])

    def test_missing_root_returns_empty_list(self) -> None:
        self.assertEqual(scan_projects(self.root / "does-not-exist"), [])


class FindProjectsTests(unittest.TestCase):
    """The portfolio layout: ~/Projects is one repo with projects inside it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = make_repo(Path(self._tmp.name) / "Projects")
        for folder in ("su5/mission-control", "su5/local-llm", "tools/summaries"):
            (self.root / folder).mkdir(parents=True)
        (self.root / "su5/mission-control/CLAUDE.md").write_text("rules\n")
        (self.root / "su5/local-llm/AGENTS.md").write_text("rules\n")
        (self.root / "tools/summaries/build.py").write_text("print()\n")  # no marker
        make_repo(self.root / "particle-sim")
        (self.root / "particle-sim/CLAUDE.md").write_text("rules\n")
        for skipped in (".worktrees/task/CLAUDE.md", ".venv/x/CLAUDE.md", "particle-sim/sub/AGENTS.md"):
            (self.root / skipped).parent.mkdir(parents=True, exist_ok=True)
            (self.root / skipped).write_text("rules\n")
        git(self.root, "add", "su5", "tools")
        git(self.root, "commit", "-q", "-m", "projects")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_finds_marked_folders_and_separate_repos_only(self) -> None:
        keys = [p.relative_to(self.root).as_posix() for p in find_projects(self.root)]
        # Not found: hidden folders, .venv, a folder without a marker, folders inside another repo.
        self.assertEqual(keys, ["particle-sim", "su5/local-llm", "su5/mission-control"])

    def test_scan_order_root_then_inside_then_separate_repos(self) -> None:
        statuses = scan_projects(self.root)
        self.assertEqual(
            [(s.key, s.name, s.in_root_repo) for s in statuses],
            [
                (".", "Projects", False),
                ("su5/local-llm", "su5/local-llm", True),
                ("su5/mission-control", "su5/mission-control", True),
                ("particle-sim", "particle-sim", False),
            ],
        )
        self.assertEqual(statuses[2].path, self.root / "su5/mission-control")

    def test_changes_are_counted_per_folder(self) -> None:
        (self.root / "su5/mission-control/app.py").write_text("new\n")
        (self.root / "su5/mission-control/CLAUDE.md").write_text("edited\n")
        changes = {s.key: s.changes for s in scan_projects(self.root)}
        # The root also sees particle-sim/ and .venv/ etc. as untracked (no .gitignore in the test repo).
        self.assertEqual(changes["su5/mission-control"], 2)
        self.assertEqual(changes["su5/local-llm"], 0)
        self.assertGreaterEqual(changes["."], 2)
        self.assertEqual(changes["particle-sim"], 2)  # its own repo: the untracked CLAUDE.md and sub/

    def test_root_that_is_not_a_repo_lists_projects_without_git(self) -> None:
        plain = Path(self._tmp.name) / "plain"
        (plain / "tool").mkdir(parents=True)
        (plain / "tool/AGENTS.md").write_text("rules\n")
        make_repo(plain / "repo")
        statuses = scan_projects(plain)
        self.assertEqual([(s.key, s.is_repo) for s in statuses], [("tool", False), ("repo", True)])


    def test_missing_root_returns_empty_list(self) -> None:
        self.assertEqual(scan_projects(self.root / "does-not-exist"), [])


if __name__ == "__main__":
    unittest.main()
