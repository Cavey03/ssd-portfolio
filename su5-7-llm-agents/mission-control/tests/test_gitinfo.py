"""Tests for mission_control.gitinfo. Run with: python -m unittest -v"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from mission_control.gitinfo import parse_porcelain_v2, read_status, scan_projects


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

    def test_scan_sorts_and_skips_hidden_folders(self) -> None:
        make_repo(self.root / "b-project")
        (self.root / "A-folder").mkdir()
        (self.root / ".hidden").mkdir()
        (self.root / "file.txt").write_text("not a folder\n")
        names = [s.name for s in scan_projects(self.root)]
        self.assertEqual(names, ["A-folder", "b-project"])

    def test_missing_root_returns_empty_list(self) -> None:
        self.assertEqual(scan_projects(self.root / "does-not-exist"), [])


if __name__ == "__main__":
    unittest.main()
