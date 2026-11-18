"""Test task workspaces using only disposable repositories.

Run with: python3 -m unittest tests.test_worktrees -v
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mission_control.worktrees import (
    ChangeSummary,
    Workspace,
    WorkspaceError,
    commit_all,
    create_workspace,
    merge_into_main,
    remove_workspace,
    repo_root,
    summarize_changes,
)


def git(path: Path, *args: str) -> str:
    """Run a checked Git command in a temporary test repository."""
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env={**os.environ, "LC_ALL": "C"},
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout


class WorktreeTests(unittest.TestCase):
    """Exercise the public API against real Git without touching user repos."""

    def setUp(self) -> None:
        """Create a committed repository and an isolated Git configuration."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        # User hooks, signing and rename preferences must not affect fixtures.
        configuration = patch.dict(os.environ, {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        })
        configuration.start()
        self.addCleanup(configuration.stop)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "user.email", "t@example.com")
        self.project = self.repo / "sub" / "proj"
        self.project.mkdir(parents=True)
        (self.project / "app.py").write_text("original\n", encoding="utf-8")
        (self.repo / "modify.txt").write_text("old\nkeep\n", encoding="utf-8")
        (self.repo / "delete.txt").write_text("delete me\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "Initial commit")
        self.base = git(self.repo, "rev-parse", "HEAD").strip()
        self.worktrees = self.root / "workspaces"

    def workspace(self, task_id: str = "example") -> Workspace:
        """Create a workspace for the nested project in the temporary repo."""
        return create_workspace(self.project, self.worktrees, task_id)

    def test_create_for_subfolder(self) -> None:
        """Check out the whole repository with the original project location."""
        ws = self.workspace()
        self.assertEqual(ws.repo, self.repo)
        self.assertEqual(ws.worktree, self.worktrees / "task-example")
        self.assertEqual(ws.branch, "task/example")
        self.assertEqual(ws.base, self.base)
        self.assertEqual(ws.workdir, ws.worktree / "sub" / "proj")
        self.assertTrue(ws.workdir.is_dir())
        self.assertTrue((ws.worktree / "modify.txt").is_file())
        self.assertEqual(git(ws.worktree, "branch", "--show-current").strip(), ws.branch)
        self.assertEqual(git(self.repo, "rev-parse", ws.branch).strip(), self.base)

    def test_create_for_repo_top(self) -> None:
        """Use the checkout top as workdir for a top-level project."""
        ws = create_workspace(self.repo, self.worktrees, "top")
        self.assertEqual(ws.workdir, ws.worktree)
        self.assertEqual(ws.base, self.base)

    def test_create_ignores_main_uncommitted_changes(self) -> None:
        """Start from HEAD while preserving the main checkout's dirty files."""
        (self.project / "app.py").write_text("main edits\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text("main only\n", encoding="utf-8")
        before = git(self.repo, "status", "--porcelain")
        ws = self.workspace()
        self.assertEqual((ws.workdir / "app.py").read_text(), "original\n")
        self.assertFalse((ws.worktree / "untracked.txt").exists())
        self.assertEqual(git(self.repo, "status", "--porcelain"), before)

    def test_repo_root(self) -> None:
        """Find the repository top from both the top and a nested folder."""
        self.assertEqual(repo_root(self.project), self.repo)
        self.assertEqual(repo_root(self.repo), self.repo)

    def test_invalid_task_ids(self) -> None:
        """Reject invalid ids before creating folders or branches."""
        for task_id in ("", "Bad", "a b", "../x", "a" * 41, "-abc", "a\n"):
            with self.subTest(task_id=task_id):
                with self.assertRaises(WorkspaceError):
                    self.workspace(task_id)
        self.assertFalse(self.worktrees.exists())

    def test_boundary_task_ids(self) -> None:
        """Accept a single digit and the maximum allowed id length."""
        for task_id in ("0", "a" * 40):
            with self.subTest(task_id=task_id):
                self.assertTrue(self.workspace(task_id).worktree.is_dir())

    def test_non_repo(self) -> None:
        """Report plain folders as workspace errors."""
        plain = self.root / "plain"
        plain.mkdir()
        with self.assertRaises(WorkspaceError):
            repo_root(plain)
        with self.assertRaises(WorkspaceError):
            create_workspace(plain, self.worktrees, "plain")

    def test_duplicate_id(self) -> None:
        """Refuse to reuse a task id without damaging its original checkout."""
        ws = self.workspace()
        with self.assertRaises(WorkspaceError):
            self.workspace()
        self.assertTrue(ws.worktree.is_dir())
        self.assertEqual(git(ws.worktree, "rev-parse", "HEAD").strip(), self.base)

    def test_existing_branch(self) -> None:
        """Refuse a preexisting branch even when its checkout folder is absent."""
        git(self.repo, "branch", "task/example")
        with self.assertRaises(WorkspaceError):
            self.workspace()
        self.assertFalse((self.worktrees / "task-example").exists())

    def test_existing_empty_folder(self) -> None:
        """Refuse even an empty destination folder instead of letting Git reuse it."""
        folder = self.worktrees / "task-example"
        folder.mkdir(parents=True)
        with self.assertRaises(WorkspaceError):
            self.workspace()
        self.assertEqual(git(self.repo, "branch", "--list", "task/example"), "")

    def test_summary_includes_modified_deleted_and_new_files(self) -> None:
        """Count every changed path and include untracked file contents in the diff."""
        ws = self.workspace()
        (ws.worktree / "modify.txt").write_text("new\nkeep\nextra\n", encoding="utf-8")
        (ws.worktree / "delete.txt").unlink()
        (ws.worktree / "new.txt").write_text("new content\nsecond\n", encoding="utf-8")
        (ws.worktree / "folder").mkdir()
        (ws.worktree / "folder" / "added.txt").write_text("nested\n", encoding="utf-8")
        summary = summarize_changes(ws)
        self.assertEqual(summary.files, ("delete.txt", "folder/added.txt", "modify.txt", "new.txt"))
        self.assertEqual((summary.insertions, summary.deletions), (5, 2))
        self.assertIn("+new content\n", summary.diff)
        self.assertIn("+nested\n", summary.diff)
        self.assertIn("deleted file mode", summary.diff)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_summary_includes_agent_commits_and_later_edits(self) -> None:
        """Compare against base even after the agent commits some changes itself."""
        ws = self.workspace()
        (ws.worktree / "committed.txt").write_text("committed content\n", encoding="utf-8")
        git(ws.worktree, "add", "-A")
        git(ws.worktree, "commit", "-q", "-m", "Agent's own commit")
        (ws.worktree / "later.txt").write_text("later content\n", encoding="utf-8")
        summary = summarize_changes(ws)
        self.assertEqual(summary.files, ("committed.txt", "later.txt"))
        self.assertEqual((summary.insertions, summary.deletions), (2, 0))
        self.assertIn("+committed content\n", summary.diff)
        self.assertIn("+later content\n", summary.diff)

    def test_empty_summary(self) -> None:
        """Return a completely empty summary for an unchanged workspace."""
        self.assertEqual(summarize_changes(self.workspace()), ChangeSummary((), 0, 0, ""))

    def test_binary_summary(self) -> None:
        """Include binary paths without treating Git's dash counts as numbers."""
        ws = self.workspace()
        (ws.worktree / "data.bin").write_bytes(b"\x00\x01\x02")
        summary = summarize_changes(ws)
        self.assertEqual(summary.files, ("data.bin",))
        self.assertEqual((summary.insertions, summary.deletions), (0, 0))
        self.assertIn("Binary files", summary.diff)

    def test_summary_preserves_unusual_filenames(self) -> None:
        """Keep spaces, tabs, newlines and non-ASCII characters in relative paths."""
        ws = self.workspace()
        names = ("with space.txt", "with\ttab.txt", "with\nnewline.txt", "café.txt")
        for name in names:
            (ws.worktree / name).write_text("new\n", encoding="utf-8")
        summary = summarize_changes(ws)
        self.assertEqual(summary.files, tuple(sorted(names)))
        self.assertEqual((summary.insertions, summary.deletions), (4, 0))

    def test_summary_rename_includes_both_paths(self) -> None:
        """Represent a moved file with repository-relative old and new paths."""
        ws = self.workspace()
        (ws.worktree / "modify.txt").rename(ws.worktree / "renamed.txt")
        summary = summarize_changes(ws)
        self.assertEqual(summary.files, ("modify.txt", "renamed.txt"))
        self.assertEqual((summary.insertions, summary.deletions), (2, 2))

    def test_commit_all(self) -> None:
        """Return a commit SHA once, then None when nothing remains to commit."""
        ws = self.workspace()
        (ws.workdir / "new.txt").write_text("new\n", encoding="utf-8")
        sha = commit_all(ws, "Task changes")
        self.assertIsNotNone(sha)
        self.assertEqual(sha, git(ws.worktree, "rev-parse", "HEAD").strip())
        self.assertNotEqual(sha, ws.base)
        self.assertEqual(git(ws.worktree, "log", "-1", "--format=%s").strip(), "Task changes")
        self.assertIsNone(commit_all(ws, "Nothing left"))

    def test_commit_all_clean_workspace(self) -> None:
        """Leave HEAD unchanged when the workspace has never been modified."""
        ws = self.workspace()
        self.assertIsNone(commit_all(ws, "Nothing changed"))
        self.assertEqual(git(ws.worktree, "rev-parse", "HEAD").strip(), ws.base)

    def test_merge_into_main(self) -> None:
        """Bring committed task files into main using a two-parent merge commit."""
        ws = self.workspace()
        (ws.workdir / "new.txt").write_text("task file\n", encoding="utf-8")
        task_sha = commit_all(ws, "Task commit")
        self.assertEqual(merge_into_main(ws, "Merge task"), (True, "Merged task/example into main"))
        self.assertEqual((self.project / "new.txt").read_text(), "task file\n")
        parents = git(self.repo, "rev-list", "--parents", "-1", "HEAD").split()
        self.assertEqual(parents[1:], [self.base, task_sha])
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s").strip(), "Merge task")

    def test_merge_conflict_aborts_cleanly(self) -> None:
        """List conflicting paths and restore main's commit, index and files."""
        ws = self.workspace()
        for name in ("modify.txt", "sub/proj/app.py"):
            (ws.worktree / name).write_text("task version\n", encoding="utf-8")
            (self.repo / name).write_text("main version\n", encoding="utf-8")
        commit_all(ws, "Task changes")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "Main changes")
        main_head = git(self.repo, "rev-parse", "HEAD")
        self.assertEqual(
            merge_into_main(ws, "Conflicting merge"),
            (False, "Merge conflict in: modify.txt, sub/proj/app.py"),
        )
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), main_head)
        self.assertFalse((self.repo / ".git" / "MERGE_HEAD").exists())
        self.assertEqual((self.project / "app.py").read_text(), "main version\n")

    def test_merge_refused_for_uncommitted_changes(self) -> None:
        """Preserve main's staged, unstaged and untracked files on a refused merge."""
        ws = self.workspace()
        (ws.workdir / "app.py").write_text("task changes\n", encoding="utf-8")
        commit_all(ws, "Task changes")
        (self.project / "app.py").write_text("staged main\n", encoding="utf-8")
        git(self.repo, "add", "sub/proj/app.py")
        (self.project / "app.py").write_text("unstaged main\n", encoding="utf-8")
        (self.repo / "private.txt").write_text("untracked\n", encoding="utf-8")
        before = (
            git(self.repo, "rev-parse", "HEAD"), git(self.repo, "status", "--porcelain"),
            git(self.repo, "diff"), git(self.repo, "diff", "--cached"),
        )
        success, message = merge_into_main(ws, "Refused merge")
        self.assertFalse(success)
        self.assertTrue(message)
        self.assertEqual(before, (
            git(self.repo, "rev-parse", "HEAD"), git(self.repo, "status", "--porcelain"),
            git(self.repo, "diff"), git(self.repo, "diff", "--cached"),
        ))
        self.assertEqual((self.repo / "private.txt").read_text(), "untracked\n")
        self.assertFalse((self.repo / ".git" / "MERGE_HEAD").exists())

    def test_merge_missing_branch_returns_failure(self) -> None:
        """Report a Git refusal without raising a workspace error."""
        ws = self.workspace()
        remove_workspace(ws)
        success, message = merge_into_main(ws, "Missing task")
        self.assertFalse(success)
        self.assertTrue(message)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD").strip(), self.base)

    def test_remove_workspace_twice(self) -> None:
        """Force-remove dirty task files and the branch, tolerating a second call."""
        ws = self.workspace()
        (ws.workdir / "untracked.txt").write_text("discard\n", encoding="utf-8")
        remove_workspace(ws)
        self.assertFalse(ws.worktree.exists())
        self.assertEqual(git(self.repo, "branch", "--list", ws.branch), "")
        self.assertNotIn(str(ws.worktree), git(self.repo, "worktree", "list", "--porcelain"))
        remove_workspace(ws)

    def test_remove_keeps_branch_when_requested(self) -> None:
        """Leave the task branch available when only its checkout is removed."""
        ws = self.workspace()
        remove_workspace(ws, delete_branch=False)
        self.assertFalse(ws.worktree.exists())
        self.assertEqual(git(self.repo, "rev-parse", ws.branch).strip(), self.base)
        remove_workspace(ws, delete_branch=False)
        remove_workspace(ws)
        self.assertEqual(git(self.repo, "branch", "--list", ws.branch), "")

    def test_workspace_serialization(self) -> None:
        """Round-trip every field through a dictionary containing only strings."""
        ws = self.workspace()
        data = ws.to_dict()
        self.assertEqual(set(data), {"repo", "worktree", "branch", "base", "workdir"})
        self.assertTrue(all(isinstance(value, str) for value in data.values()))
        self.assertEqual(Workspace.from_dict(data), ws)

    def test_git_execution_errors(self) -> None:
        """Wrap missing executables and timeouts in readable workspace errors."""
        for error in (FileNotFoundError("git missing"), subprocess.TimeoutExpired("git", 60)):
            with self.subTest(error=error):
                with patch("mission_control.worktrees.subprocess.run", side_effect=error):
                    with self.assertRaises(WorkspaceError):
                        repo_root(self.repo)

    def test_git_subprocess_options(self) -> None:
        """Keep every production Git command shell-free, bounded and in C locale."""
        with patch("mission_control.worktrees.subprocess.run", wraps=subprocess.run) as run:
            ws = self.workspace()
            summarize_changes(ws)
            commit_all(ws, "No changes")
            merge_into_main(ws, "Already merged")
            remove_workspace(ws)
        for call in run.call_args_list:
            self.assertIsInstance(call.args[0], list)
            self.assertEqual(call.args[0][0], "git")
            self.assertEqual(call.kwargs["timeout"], 60)
            self.assertTrue(call.kwargs["capture_output"])
            self.assertTrue(call.kwargs["text"])
            self.assertFalse(call.kwargs["check"])
            self.assertEqual(call.kwargs["env"]["LC_ALL"], "C")
            self.assertFalse(call.kwargs.get("shell", False))


if __name__ == "__main__":
    unittest.main()
