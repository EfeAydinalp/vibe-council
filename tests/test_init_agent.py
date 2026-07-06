"""Tests for `vibe init-agent` report/dry-run mode (v0.8.0 PR 1).

Stdlib-only (`unittest`). `init-agent` is **report-only**: it composes the project-doctor
readiness checks and the guide markers to show what `vibe guide … --write` WOULD do — it
writes no files, creates no `.council/`, creates no CLAUDE.md/AGENTS.md/FABLE.md, runs no
commands, and makes no model/provider/network call. It has NO path argument. Tests cover
the pure `init_agent_report` builder + the CLI via the shared `run_cli` subprocess helper.
"""

import unittest
import tempfile
from pathlib import Path

from backend import cli
from tests.test_cli_smoke import run_cli

REPO = Path(__file__).resolve().parents[1]

DEFAULT_FILES = ("CLAUDE.md", "AGENTS.md", "FABLE.md")


def _seed_ready_repo(root: Path) -> None:
    """Create every required vault + core file so the doctor readiness probe resolves."""
    for rel in cli.PROJECT_VAULT_FILES + cli.PROJECT_CORE_DOCS:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {p.name}\n\nplaceholder\n", encoding="utf-8")


class TestInitAgentReportBuilder(unittest.TestCase):
    """Pure `init_agent_report` — reads files (in-memory), writes nothing."""

    def _report(self, root, agents=None, role=None):
        return "\n".join(cli.init_agent_report(
            root, agents or list(cli.GUIDE_TOPICS), role))

    def test_report_is_report_only_header(self):
        with tempfile.TemporaryDirectory() as t:
            text = self._report(Path(t))
            self.assertIn("agent onboarding report", text)
            self.assertIn("writes nothing", text)

    def test_report_includes_readiness(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _seed_ready_repo(root)
            text = self._report(root)
            self.assertIn("Readiness:", text)
            self.assertIn("Result:", text)
            self.assertIn("vibe project doctor", text)

    def test_report_includes_guide_and_export_next_steps(self):
        with tempfile.TemporaryDirectory() as t:
            text = self._report(Path(t))
            self.assertIn("vibe guide claude", text)
            self.assertIn("vibe context export --for claude", text)

    def test_report_states_council_not_real(self):
        with tempfile.TemporaryDirectory() as t:
            text = self._report(Path(t))
            self.assertIn("`/council` is NOT a real command", text)

    def test_report_states_tighten_only(self):
        with tempfile.TemporaryDirectory() as t:
            text = self._report(Path(t)).lower()
            self.assertIn("tighten", text)
            self.assertIn("never loosen", text)
            # names the rule classes it can never loosen
            self.assertIn("no-stage", text)
            self.assertIn("trust", text)

    def test_report_states_preferences_are_advice_only(self):
        with tempfile.TemporaryDirectory() as t:
            text = self._report(Path(t)).lower()
            self.assertIn("documentation/advice only", text)

    def test_would_create_when_file_absent(self):
        with tempfile.TemporaryDirectory() as t:
            text = self._report(Path(t), agents=["claude"])
            self.assertIn("CLAUDE.md: would create", text)

    def test_would_append_when_file_present_without_marker(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "CLAUDE.md").write_text("# My notes\n\nunrelated\n", encoding="utf-8")
            text = self._report(root, agents=["claude"])
            self.assertIn("CLAUDE.md: would append", text)

    def test_would_skip_when_marker_present(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            # the base claude marker is the Vibe Council Workflow heading
            (root / "CLAUDE.md").write_text(
                cli._topic_guide_marker("claude") + "\n\nalready onboarded\n",
                encoding="utf-8")
            text = self._report(root, agents=["claude"])
            self.assertIn("already present — would skip", text)

    def test_role_marker_distinct_from_base(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            # a file with only the BASE marker -> a ROLE report should still "would append"
            (root / "CLAUDE.md").write_text(
                cli._topic_guide_marker("claude") + "\n\nbase only\n", encoding="utf-8")
            text = self._report(root, agents=["claude"], role="coder")
            self.assertIn("role: coder", text)
            self.assertIn("CLAUDE.md: would append", text)

    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _seed_ready_repo(root)
            self.assertEqual(self._report(root), self._report(root))

    def test_report_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _seed_ready_repo(root)
            before = sorted(p.relative_to(root).as_posix()
                            for p in root.rglob("*") if p.is_file())
            self._report(root)
            after = sorted(p.relative_to(root).as_posix()
                           for p in root.rglob("*") if p.is_file())
            self.assertEqual(before, after)
            self.assertFalse((root / ".council").exists())
            for f in DEFAULT_FILES:
                self.assertFalse((root / f).exists(), f"created {f}")


class TestInitAgentCli(unittest.TestCase):
    def test_runs_and_exits_zero_on_real_repo(self):
        r = run_cli(["init-agent"], caller_cwd=REPO)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("agent onboarding report", r.stdout)
        self.assertIn("Readiness:", r.stdout)

    def test_stdout_writes_no_files_and_no_council(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _seed_ready_repo(root)
            before = set(p.name for p in root.rglob("*"))
            r = run_cli(["init-agent"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            after = set(p.name for p in root.rglob("*"))
            self.assertEqual(before, after)                 # nothing created
            self.assertFalse((root / ".council").exists())
            for f in DEFAULT_FILES:
                self.assertFalse((root / f).exists(), f"created {f}")

    def test_agent_and_role_filters(self):
        r = run_cli(["init-agent", "--agent", "codex", "--role", "reviewer"],
                    caller_cwd=REPO)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("role: reviewer", r.stdout)
        self.assertIn("AGENTS.md", r.stdout)                # codex default file
        self.assertNotIn("FABLE.md", r.stdout)              # fable not selected

    def test_no_path_argument(self):
        # PR 1 has NO path option — supplying one is an argparse error (exit 2).
        r = run_cli(["init-agent", "--path", "/tmp"], caller_cwd=REPO)
        self.assertEqual(r.returncode, 2)

    def test_invalid_agent_fails_cleanly(self):
        r = run_cli(["init-agent", "--agent", "gemini"], caller_cwd=REPO)
        self.assertEqual(r.returncode, 2)

    def test_help_lists_init_agent(self):
        r = run_cli(["--help"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("init-agent", r.stdout)


def _files(root: Path):
    return sorted(p.name for p in root.iterdir() if p.is_file())


class TestInitAgentWrite(unittest.TestCase):
    """v0.8.0 PR 2 — guarded `--write` append mode. Append-only, marker-skip idempotent,
    fixed per-topic targets only (no path argument), `--yes` required, no `.council/`."""

    def test_write_requires_agent(self):
        # a bare `--write` (no --agent) refuses — a write must name its target(s).
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            r = run_cli(["init-agent", "--write", "--yes"], caller_cwd=root)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(_files(root), [])              # nothing written
            self.assertIn("requires at least one --agent", r.stderr)

    def test_write_requires_yes(self):
        # `--write` without `--yes` refuses (deterministic confirmation gate).
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            r = run_cli(["init-agent", "--write", "--agent", "codex"], caller_cwd=root)
            self.assertEqual(r.returncode, 2)
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertIn("requires --yes", r.stderr)

    def test_write_claude_creates_only_claude_md(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            r = run_cli(["init-agent", "--write", "--agent", "claude", "--yes"],
                        caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((root / "CLAUDE.md").is_file())
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertFalse((root / "FABLE.md").exists())
            self.assertFalse((root / ".council").exists())
            self.assertIn("created", r.stdout)

    def test_write_codex_and_fable_target_files(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            run_cli(["init-agent", "--write", "--agent", "codex", "--yes"], caller_cwd=root)
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertFalse((root / "CLAUDE.md").exists())
        with tempfile.TemporaryDirectory() as t2:
            root2 = Path(t2)
            run_cli(["init-agent", "--write", "--agent", "fable", "--yes"], caller_cwd=root2)
            self.assertTrue((root2 / "FABLE.md").is_file())

    def test_write_multiple_agents(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            run_cli(["init-agent", "--write", "--agent", "claude", "--agent", "fable",
                     "--yes"], caller_cwd=root)
            self.assertTrue((root / "CLAUDE.md").is_file())
            self.assertTrue((root / "FABLE.md").is_file())
            self.assertFalse((root / "AGENTS.md").exists())   # codex not selected

    def test_write_is_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            run_cli(["init-agent", "--write", "--agent", "claude", "--role", "coder",
                     "--yes"], caller_cwd=root)
            text1 = (root / "CLAUDE.md").read_text(encoding="utf-8")
            r = run_cli(["init-agent", "--write", "--agent", "claude", "--role", "coder",
                         "--yes"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((root / "CLAUDE.md").read_text(encoding="utf-8"), text1)
            self.assertIn("skipped", r.stdout)
            # marker appears exactly once
            self.assertEqual(text1.count(cli._role_guide_marker("coder", "claude")), 1)

    def test_write_appends_and_preserves_existing_content(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "AGENTS.md").write_text("# My notes\n\nKEEP THIS\n", encoding="utf-8")
            r = run_cli(["init-agent", "--write", "--agent", "codex", "--yes"],
                        caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            body = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("KEEP THIS", body)                  # original preserved
            self.assertIn(cli._topic_guide_marker("codex"), body)  # section appended
            self.assertIn("appended", r.stdout)

    def test_write_existing_marker_not_duplicated(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "CLAUDE.md").write_text(
                cli._topic_guide_marker("claude") + "\n\nalready here\n", encoding="utf-8")
            before = (root / "CLAUDE.md").read_text(encoding="utf-8")
            r = run_cli(["init-agent", "--write", "--agent", "claude", "--yes"],
                        caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((root / "CLAUDE.md").read_text(encoding="utf-8"), before)
            self.assertIn("skipped", r.stdout)

    def test_write_matches_guide_write_content(self):
        # the section init-agent --write appends is byte-identical to `vibe guide … --write`.
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            run_cli(["init-agent", "--write", "--agent", "codex", "--role", "reviewer",
                     "--yes"], caller_cwd=root)
            via_init = (root / "AGENTS.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as t2:
            f = Path(t2) / "AGENTS.md"
            run_cli(["guide", "codex", "--role", "reviewer", "--write", str(f), "--yes"],
                    caller_cwd=Path(t2))
            via_guide = f.read_text(encoding="utf-8")
        self.assertEqual(via_init, via_guide)

    def test_write_creates_no_council_or_exports(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            run_cli(["init-agent", "--write", "--agent", "claude", "--yes"], caller_cwd=root)
            self.assertFalse((root / ".council").exists())
            # only CLAUDE.md is created — no export/pack/other files
            self.assertEqual([f for f in _files(root) if not f.startswith("uv-")],
                             ["CLAUDE.md"])

    def test_write_has_no_path_argument(self):
        # a positional path after --write is an argparse error (no target surface).
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            r = run_cli(["init-agent", "--write", "--agent", "claude", "CLAUDE.md", "--yes"],
                        caller_cwd=root)
            self.assertEqual(r.returncode, 2)

    def test_write_target_is_directory_fails_cleanly(self):
        # if CLAUDE.md exists as a DIRECTORY, --write refuses cleanly (no traceback).
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "CLAUDE.md").mkdir()
            r = run_cli(["init-agent", "--write", "--agent", "claude", "--yes"],
                        caller_cwd=root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("not a regular file", r.stderr)
            self.assertNotIn("Traceback", r.stderr)
            self.assertTrue((root / "CLAUDE.md").is_dir())   # untouched

    def test_write_invalid_role_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            r = run_cli(["init-agent", "--write", "--agent", "claude", "--role", "nope",
                         "--yes"], caller_cwd=root)
            self.assertEqual(r.returncode, 2)
            self.assertFalse((root / "CLAUDE.md").exists())


if __name__ == "__main__":
    unittest.main()
