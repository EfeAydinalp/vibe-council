"""Tests for `vibe project doctor` (read-only onboarding diagnostics, PR #104).

Stdlib-only (`unittest`). The doctor is **read-only**: it inspects files + runs a
read-only `git status`, and reports readiness — it never writes a file, never creates
`.council/`, and makes no model/provider/network call. Tests cover the pure
`project_doctor_report` helper (deterministic fixtures), CLI exit codes via the shared
`run_cli` subprocess helper, and staged-file detection in a throwaway git repo.
"""

import os
import shutil
import subprocess
import unittest
import tempfile
from pathlib import Path

from backend import cli
from tests.test_cli_smoke import run_cli

REPO = Path(__file__).resolve().parents[1]
_GIT = shutil.which("git")


def _seed_ready_repo(root: Path) -> None:
    """Create every required vault + core file (empty-ish) so the doctor reports READY
    on file presence."""
    for rel in cli.PROJECT_VAULT_FILES + cli.PROJECT_CORE_DOCS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {p.name}\n\nplaceholder\n", encoding="utf-8")


class TestDoctorPureReport(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _report(self):
        return cli.project_doctor_report(self.root)

    def test_ready_when_all_required_files_present(self):
        _seed_ready_repo(self.root)
        lines, ok = self._report()
        text = "\n".join(lines)
        self.assertTrue(ok, text)
        self.assertIn("READY", text)
        self.assertNotIn("[MISS]", text)

    def test_output_mentions_guides_and_council_future(self):
        _seed_ready_repo(self.root)
        text = "\n".join(self._report()[0])
        self.assertIn("vibe guide claude --role coder --write", text)
        self.assertIn("vibe guide codex", text)
        self.assertIn("vibe guide fable", text)
        self.assertIn("NOT a real vibe CLI command", text)  # /council future only

    def test_output_reports_context_health(self):
        # In a fixture repo the pack is thin, so context health is advisory (not 21/21);
        # the doctor must still report a context-check line and not fail on it.
        _seed_ready_repo(self.root)
        text = "\n".join(self._report()[0])
        self.assertIn("Context health", text)
        self.assertIn("context check", text)

    def test_missing_vault_file_is_not_ready(self):
        _seed_ready_repo(self.root)
        (self.root / "docs/context/project/ROADMAP.md").unlink()
        lines, ok = self._report()
        text = "\n".join(lines)
        self.assertFalse(ok)
        self.assertIn("[MISS] docs/context/project/ROADMAP.md", text)
        self.assertIn("NOT READY", text)
        self.assertIn("Next steps", text)

    def test_missing_core_doc_is_not_ready(self):
        _seed_ready_repo(self.root)
        (self.root / "docs/agent-quickstart.md").unlink()
        lines, ok = self._report()
        text = "\n".join(lines)
        self.assertFalse(ok)
        self.assertIn("[MISS] docs/agent-quickstart.md", text)

    def test_report_writes_no_files_and_no_council(self):
        _seed_ready_repo(self.root)
        before = sorted(p.relative_to(self.root).as_posix()
                        for p in self.root.rglob("*") if p.is_file())
        self._report()
        after = sorted(p.relative_to(self.root).as_posix()
                       for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(before, after)                      # nothing written
        self.assertFalse((self.root / ".council").exists())   # no .council/ created


class TestDoctorCli(unittest.TestCase):
    def test_passes_on_real_repo(self):
        # The real repo has all required files; doctor should report READY, exit 0.
        r = run_cli(["project", "doctor"], caller_cwd=REPO)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("READY", r.stdout)
        self.assertIn("context check 21/21", r.stdout)

    def test_missing_files_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as t:
            r = run_cli(["project", "doctor"], caller_cwd=Path(t))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("NOT READY", r.stdout)

    def test_invalid_action_is_usage_error(self):
        r = run_cli(["project", "bogus"])
        self.assertEqual(r.returncode, 2)  # argparse choices

    def test_projects_list_still_works_no_collision(self):
        r = run_cli(["projects", "list"])
        self.assertEqual(r.returncode, 0, r.stderr)
        # `project doctor` and `projects list` are distinct subcommands.
        r2 = run_cli(["project", "doctor"], caller_cwd=REPO)
        self.assertIn("onboarding readiness", r2.stdout)

    def test_help_lists_project_command(self):
        r = run_cli(["help"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("project doctor", r.stdout)


@unittest.skipUnless(_GIT, "git not available")
class TestDoctorStagedFileDetection(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _seed_ready_repo(self.root)
        self._git("init")
        self._git("config", "user.email", "t@t.invalid")
        self._git("config", "user.name", "t")

    def tearDown(self):
        self._tmp.cleanup()

    def _git(self, *args):
        subprocess.run(["git", "-C", str(self.root), *args],
                       capture_output=True, text=True, check=False)

    def test_staged_env_is_flagged_and_not_ready(self):
        (self.root / ".env").write_text("OPENROUTER_API_KEY=secret\n", encoding="utf-8")
        self._git("add", "-f", ".env")  # -f: force past any ignore
        lines, ok = cli.project_doctor_report(self.root)
        text = "\n".join(lines)
        self.assertFalse(ok, text)
        self.assertIn("[FAIL]", text)
        self.assertIn(".env", text)

    def test_staged_council_runtime_is_flagged(self):
        rt = self.root / ".council" / "runtime"
        rt.mkdir(parents=True)
        (rt / "task.json").write_text("{}\n", encoding="utf-8")
        self._git("add", "-f", ".council/runtime/task.json")
        lines, ok = cli.project_doctor_report(self.root)
        text = "\n".join(lines)
        self.assertFalse(ok, text)
        self.assertIn("[FAIL]", text)
        self.assertIn(".council/runtime/", text)

    def test_clean_git_repo_is_ready(self):
        # required files present, nothing dangerous staged -> READY.
        self._git("add", "docs")
        lines, ok = cli.project_doctor_report(self.root)
        self.assertTrue(ok, "\n".join(lines))
        self.assertIn("no dangerous staged files", "\n".join(lines))

    def test_untracked_env_is_not_flagged(self):
        # an UNTRACKED .env (not staged) is fine — doctor only flags staged risk.
        (self.root / ".env").write_text("x=1\n", encoding="utf-8")
        lines, ok = cli.project_doctor_report(self.root)
        self.assertTrue(ok, "\n".join(lines))


class TestDoctorNonGitDegradesGracefully(unittest.TestCase):
    def test_non_git_dir_warns_not_fails_on_git(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _seed_ready_repo(root)  # files present, but not a git repo
            lines, ok = cli.project_doctor_report(root)
            text = "\n".join(lines)
            self.assertTrue(ok, text)  # missing-git is a warning, not a failure
            self.assertIn("git unavailable or not a git repo", text)


if __name__ == "__main__":
    unittest.main()
