"""UX-output tests for the v0.3.1 CLI polish (PR #51).

Stdlib-only (`unittest`); drives the CLI as a subprocess via the shared
``run_cli`` helper. No model/API/network. The fake key below is a synthetic
fixture, not a real key.
"""

import tempfile
import unittest
from pathlib import Path

from tests.test_cli_smoke import run_cli

FAKE_OR_KEY = "sk-or-v1-" + "a" * 40


def _seed_repo(root: Path, n: int = 3) -> None:
    ddir = root / "docs" / "decisions"
    ddir.mkdir(parents=True)
    for i in range(n):
        stem = f"rec{i:02d}"
        (ddir / f"2026-06-{10 + i:02d}-{stem}.md").write_text(
            f"---\nid: DEC-202606{10 + i:02d}-{stem}\nstatus: accepted\n"
            f"date: 2026-06-{10 + i:02d}\ntags: [t]\nrelated: []\npublished: true\n"
            f"---\n\n# {stem}\n\n## Context\n\nc\n\n## Decision\n\nd\n\n"
            "## Rationale\n\nr\n\n## Alternatives considered\n\n- **Alt** rejected\n\n"
            "## Consequences\n\nx\n\n## Next actions\n\nn\n\n## Related links\n\nl\n",
            encoding="utf-8")
    sd = root / "docs" / "context" / "project"
    sd.mkdir(parents=True)
    (sd / "STATUS.md").write_text("# Status\n\nok\n", encoding="utf-8")


class TestRedactionLintVerdict(unittest.TestCase):
    def test_passed_verdict(self):
        with tempfile.TemporaryDirectory() as t:
            doc = Path(t) / "clean.md"
            doc.write_text("# Clean\n\nNothing secret here.\n", encoding="utf-8")
            r = run_cli(["lint", "--redaction", str(doc)], caller_cwd=Path(t))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("redaction lint passed:", r.stderr)
            self.assertIn("0 critical", r.stderr)

    def test_failed_verdict(self):
        with tempfile.TemporaryDirectory() as t:
            doc = Path(t) / "leak.md"
            doc.write_text(f"# Leak\n\nkey {FAKE_OR_KEY} oops\n", encoding="utf-8")
            r = run_cli(["lint", "--redaction", str(doc)], caller_cwd=Path(t))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("redaction lint FAILED:", r.stderr)
            self.assertNotIn(FAKE_OR_KEY, r.stderr + r.stdout)  # secret stays masked


class TestContextBuildBudgetNote(unittest.TestCase):
    def test_budget_note_on_trim(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _seed_repo(root, n=4)
            r = run_cli(["context", "build", "--max-chars", "1500"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("exceeded the 1500-char budget", r.stderr)
            self.assertIn("--max-chars", r.stderr)

    def test_no_budget_note_when_roomy(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _seed_repo(root, n=2)
            r = run_cli(["context", "build", "--max-chars", "50000"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("exceeded the", r.stderr)


class TestContextCheckAdvisorySuffix(unittest.TestCase):
    def test_advisory_miss_suffix(self):
        # a pack with required sections/constraints but missing advisory signals
        with tempfile.TemporaryDirectory() as t:
            pack = Path(t) / "pack.md"
            pack.write_text(
                "## Metadata\n\n## Project identity\n\n## Current status\n\n"
                "## Recent decisions\n\n## Decision index\n\n## Constraints\n\n"
                "raw .council gitignored; curated/redacted docs; redaction guard; "
                'license "Question 0".\n',
                encoding="utf-8")
            r = run_cli(["context", "check", "--file", str(pack),
                         "--min-score", "0.3"], caller_cwd=Path(t))
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn("advisory miss(es)", r.stdout)


class TestDecisionsHelpBoundary(unittest.TestCase):
    def test_help_mentions_promotion_boundary(self):
        r = run_cli(["decisions", "--help"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertIn("Promotion boundary", out)
        self.assertIn("LOCAL", out)
        self.assertIn("human-reviewed", out)


class TestRoleAwareGuide(unittest.TestCase):
    """Role-aware `vibe guide claude --role <role>` output (v0.6.1). Read-only stdout
    generator — no repo writes, no model/network."""

    ROLES = ("task-shaper", "planner", "coder", "reviewer", "release-manager")

    def test_plain_guide_still_works(self):
        r = run_cli(["guide", "claude"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Vibe Council Workflow", r.stdout)

    def test_each_role_prints_role_specific_content(self):
        markers = {
            "task-shaper": "task-shaper",
            "planner": "must-have",
            "coder": "PROPOSE",
            "reviewer": "advice, not authority",
            "release-manager": "No git tag",
        }
        for role in self.ROLES:
            r = run_cli(["guide", "claude", "--role", role])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(f"role: {role}", r.stdout)
            self.assertIn(f"### Role: {role}", r.stdout)
            self.assertIn(markers[role], r.stdout,
                          f"{role}: missing role-specific marker")

    def test_invalid_role_fails_clearly(self):
        r = run_cli(["guide", "claude", "--role", "nonsense"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid choice", r.stderr)

    def test_guide_mentions_vibe_not_council_command(self):
        r = run_cli(["guide", "claude", "--role", "coder"])
        self.assertIn("CLI is `vibe`, not `/council`", r.stdout)
        # /council must be framed as a future idea, never as a runnable command
        self.assertIn("does NOT exist today", r.stdout)

    def test_guide_includes_no_stage_warnings(self):
        for role in self.ROLES:
            r = run_cli(["guide", "claude", "--role", role])
            out = r.stdout
            self.assertIn(".council/runtime/payloads/", out, role)
            self.assertIn("secrets", out, role)
            self.assertIn("uv.lock", out, role)
            self.assertIn(".env", out, role)

    def test_coder_role_mentions_workbench_proposal_flow(self):
        r = run_cli(["guide", "claude", "--role", "coder"])
        self.assertIn("vibe workbench propose", r.stdout)
        self.assertIn("pending", r.stdout)

    def test_release_manager_role_mentions_no_tag_without_approval(self):
        r = run_cli(["guide", "claude", "--role", "release-manager"])
        self.assertIn("No git tag", r.stdout)
        self.assertIn("unless the user explicitly allows", r.stdout)

    def test_guide_writes_no_files(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            before = set(p.name for p in root.iterdir())
            r = run_cli(["guide", "claude", "--role", "coder"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            after = set(p.name for p in root.iterdir())
            self.assertEqual(before, after)  # nothing written to the project dir

    def test_role_write_now_writes_the_file(self):
        # `--write` with `--role` is now supported (opt-in write mode); it appends to
        # the file rather than printing the guide to stdout. (Full coverage in
        # TestRoleAwareGuideWrite.)
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            out = root / "OUT.md"
            r = run_cli(["guide", "claude", "--role", "coder", "--write", str(out),
                         "--yes"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())
            self.assertIn("[written]", r.stderr)

    def test_help_lists_role_option(self):
        r = run_cli(["guide", "--help"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--role", r.stdout)
        self.assertIn("coder", r.stdout)

    def test_parser_choices_match_guide_roles(self):
        # The --role choices must stay in lockstep with GUIDE_ROLES / _ROLE_BLOCKS.
        from backend import cli
        self.assertEqual(set(cli.GUIDE_ROLES), set(self.ROLES))
        for role in cli.GUIDE_ROLES:
            self.assertIn(role, cli._ROLE_BLOCKS)
        # the public helper is defensive for direct (non-argparse) callers
        with self.assertRaises(ValueError):
            cli.role_guide("not-a-role")


class TestRoleAwareGuideWrite(unittest.TestCase):
    """Opt-in `--write` for role-aware guides (v0.6.1). Appends a role section to a
    CLAUDE.md-style file; never overwrites; stdout-only mode still writes nothing."""

    def test_plain_guide_write_still_works(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            f = root / "CLAUDE.md"
            r = run_cli(["guide", "claude", "--write", str(f), "--yes"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(f.exists())
            self.assertIn("Vibe Council Workflow", f.read_text(encoding="utf-8"))

    def test_role_write_creates_file_and_reports_path(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            f = root / "AGENTS.md"
            r = run_cli(["guide", "claude", "--role", "coder", "--write", str(f),
                         "--yes"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(f.exists())
            self.assertIn("[written]", r.stderr)
            self.assertIn("AGENTS.md", r.stderr)

    def test_role_write_content_includes_role_and_common_rules(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            f = root / "AGENTS.md"
            run_cli(["guide", "claude", "--role", "coder", "--write", str(f), "--yes"],
                    caller_cwd=root)
            text = f.read_text(encoding="utf-8")
            self.assertIn("### Role: coder", text)
            self.assertIn("PROPOSE", text)                       # coder-specific
            self.assertIn("vibe workbench propose", text)        # Workbench flow
            self.assertIn("CLI is `vibe`, not `/council`", text)  # vibe not /council
            self.assertIn("does NOT exist today", text)          # /council future only
            self.assertIn(".council/runtime/payloads/", text)    # never-stage
            self.assertIn("secrets", text)
            self.assertIn("uv.lock", text)

    def test_role_write_does_not_overwrite_or_duplicate(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            f = root / "AGENTS.md"
            f.write_text("# Existing project notes\n\nkeep me\n", encoding="utf-8")
            r1 = run_cli(["guide", "claude", "--role", "coder", "--write", str(f),
                          "--yes"], caller_cwd=root)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            after_first = f.read_text(encoding="utf-8")
            self.assertIn("keep me", after_first)                # original preserved
            self.assertIn("### Role: coder", after_first)
            # re-run: skipped, not duplicated, not overwritten
            r2 = run_cli(["guide", "claude", "--role", "coder", "--write", str(f),
                          "--yes"], caller_cwd=root)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("already contains", r2.stderr)
            self.assertIn("not modifying", r2.stderr)
            self.assertEqual(f.read_text(encoding="utf-8"), after_first)  # byte-identical

    def test_different_roles_can_coexist_in_one_file(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            f = root / "AGENTS.md"
            run_cli(["guide", "claude", "--role", "coder", "--write", str(f), "--yes"],
                    caller_cwd=root)
            run_cli(["guide", "claude", "--role", "reviewer", "--write", str(f), "--yes"],
                    caller_cwd=root)
            text = f.read_text(encoding="utf-8")
            self.assertIn("(role: coder)", text)
            self.assertIn("(role: reviewer)", text)

    def test_stdout_only_role_mode_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            before = set(p.name for p in root.iterdir())
            r = run_cli(["guide", "claude", "--role", "planner"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("### Role: planner", r.stdout)
            self.assertEqual(before, set(p.name for p in root.iterdir()))

    def test_role_write_to_new_file_has_no_leading_blank_lines(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            f = root / "AGENTS.md"  # does not exist yet
            run_cli(["guide", "claude", "--role", "coder", "--write", str(f), "--yes"],
                    caller_cwd=root)
            text = f.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("## vibe-council agent guide (role: coder)"),
                            f"unexpected leading content: {text[:40]!r}")

    def test_role_write_creates_no_council_dir(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            run_cli(["guide", "claude", "--role", "coder", "--write",
                     str(root / "AGENTS.md"), "--yes"], caller_cwd=root)
            self.assertFalse((root / ".council").exists())

    def test_invalid_role_with_write_still_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            f = root / "AGENTS.md"
            r = run_cli(["guide", "claude", "--role", "nope", "--write", str(f),
                         "--yes"], caller_cwd=root)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(f.exists())


class TestCodexFableGuideTopics(unittest.TestCase):
    """Codex and Fable guide topics reuse the role-aware guide machinery (v0.6.1).
    claude behavior is preserved; codex/fable add their own emphasis + default files."""

    def test_claude_topic_unchanged(self):
        r = run_cli(["guide", "claude"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Claude Code instructions for vibe-council", r.stdout)

    def test_codex_topic_prints_codex_guidance(self):
        r = run_cli(["guide", "codex"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Codex instructions for vibe-council", r.stdout)
        self.assertIn("Codex-specific notes", r.stdout)
        self.assertIn("reviewer, context, and guardrail", r.stdout)
        self.assertIn("vibe workbench propose", r.stdout)  # Workbench flow

    def test_fable_topic_prints_budget_lead_guidance(self):
        r = run_cli(["guide", "fable"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Fable instructions for vibe-council", r.stdout)
        self.assertIn("Fable is expensive", r.stdout)
        self.assertIn("technical lead / architect", r.stdout)
        self.assertIn("Opus/Sonnet implement routine PRs", r.stdout)

    def test_role_works_for_codex_and_fable(self):
        r = run_cli(["guide", "codex", "--role", "reviewer"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Codex instructions for vibe-council", r.stdout)
        self.assertIn("role: reviewer", r.stdout)
        self.assertIn("### Role: reviewer", r.stdout)
        self.assertIn("Codex-specific notes", r.stdout)  # topic framing present
        r2 = run_cli(["guide", "fable", "--role", "planner"])
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("Fable instructions for vibe-council", r2.stdout)
        self.assertIn("role: planner", r2.stdout)
        self.assertIn("### Role: planner", r2.stdout)

    def test_all_topics_say_vibe_not_council(self):
        for topic in ("codex", "fable"):
            r = run_cli(["guide", topic])
            self.assertIn("CLI is `vibe`, not `/council`", r.stdout, topic)
            self.assertIn("does NOT exist today", r.stdout, topic)
            self.assertIn(".council/runtime/payloads/", r.stdout, topic)  # never-stage
            self.assertIn("secrets", r.stdout, topic)

    def test_invalid_topic_fails_clearly(self):
        r = run_cli(["guide", "gemini"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid choice", r.stderr)

    def test_invalid_role_still_fails_for_codex(self):
        r = run_cli(["guide", "codex", "--role", "nope"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid choice", r.stderr)

    def test_codex_write_default_file_is_agents_md(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            f = root / "AGENTS.md"
            r = run_cli(["guide", "codex", "--write", str(f), "--yes"], caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(f.exists())
            self.assertIn("[written]", r.stderr)
            self.assertIn("Codex-specific notes", f.read_text(encoding="utf-8"))

    def test_fable_role_write_marker_skip_and_coexist(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            f = root / "AGENTS.md"
            run_cli(["guide", "codex", "--write", str(f), "--yes"], caller_cwd=root)
            run_cli(["guide", "fable", "--role", "coder", "--write", str(f), "--yes"],
                    caller_cwd=root)
            text = f.read_text(encoding="utf-8")
            self.assertIn("## vibe-council agent guide (codex)", text)
            self.assertIn("## vibe-council agent guide (fable, role: coder)", text)
            # re-run does not overwrite/duplicate
            r = run_cli(["guide", "fable", "--role", "coder", "--write", str(f),
                         "--yes"], caller_cwd=root)
            self.assertIn("already contains", r.stderr)
            self.assertEqual(f.read_text(encoding="utf-8"), text)  # byte-identical

    def test_stdout_only_topic_mode_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            before = set(p.name for p in root.iterdir())
            run_cli(["guide", "codex"], caller_cwd=root)
            run_cli(["guide", "fable", "--role", "planner"], caller_cwd=root)
            self.assertEqual(before, set(p.name for p in root.iterdir()))

    def test_topic_write_creates_no_council_dir(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            run_cli(["guide", "fable", "--write", str(root / "FABLE.md"), "--yes"],
                    caller_cwd=root)
            self.assertFalse((root / ".council").exists())

    def test_help_lists_topics(self):
        r = run_cli(["guide", "--help"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("codex", r.stdout)
        self.assertIn("fable", r.stdout)

    def test_write_to_missing_parent_dir_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            target = root / "nope" / "AGENTS.md"  # parent dir does not exist
            r = run_cli(["guide", "codex", "--write", str(target), "--yes"],
                        caller_cwd=root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("does not exist", r.stderr)
            self.assertFalse(target.exists())

    def test_public_helpers_are_topic_aware_and_defensive(self):
        from backend import cli
        self.assertEqual(set(cli.GUIDE_TOPICS), {"claude", "codex", "fable"})
        self.assertIn("Codex", cli.topic_guide("codex"))
        self.assertIn("Fable", cli.role_guide("coder", "fable"))
        with self.assertRaises(ValueError):
            cli.role_guide("coder", "gemini")
        with self.assertRaises(ValueError):
            cli.topic_guide("gemini")


if __name__ == "__main__":
    unittest.main()
