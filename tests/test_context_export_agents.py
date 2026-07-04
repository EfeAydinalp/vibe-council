"""Tests for `vibe context export --for <agent>` (read-only onboarding handoff, PR #105).

Stdlib-only (`unittest`). The export is read-only: it prints Markdown to stdout by
default (writes nothing, creates no `.council/`), or writes an explicit `--output` file
(never overwriting). No model/provider/network. Covers the pure `agent_context_export`
builder and the CLI via the shared `run_cli` subprocess helper.
"""

import unittest
import tempfile
from pathlib import Path

from backend import cli
from tests.test_cli_smoke import run_cli

REPO = Path(__file__).resolve().parents[1]

PRIVATE_PLAN_NAMES = (
    "commercialization-and-hosted-platform-feasibility.md",
    "v0.3.1-hardening-and-dogfood.md",
)


class TestAgentExportBuilder(unittest.TestCase):
    """Pure `agent_context_export` — no I/O beyond in-memory reads; writes nothing."""

    def _export(self, agent, role=None):
        return cli.agent_context_export(agent, role=role, project_root=REPO)

    def test_all_agents_build(self):
        for agent in ("claude", "codex", "fable"):
            text = self._export(agent)
            self.assertIn("vibe-council onboarding context", text)
            self.assertIn(cli._TOPIC_LABEL[agent], text)

    def test_invalid_agent_raises(self):
        with self.assertRaises(ValueError):
            self._export("gemini")

    def test_mentions_vibe_and_council_future(self):
        text = self._export("claude")
        self.assertIn("real CLI is **`vibe`**", text)
        self.assertIn("NOT a real command today", text)

    def test_includes_vault_pointers_not_full_dump(self):
        text = self._export("claude")
        for rel, _desc in cli._VAULT_POINTERS:
            self.assertIn(rel, text)                      # pointer present
        self.assertIn("read these directly — not inlined here", text)
        # It must NOT inline the actual vault file bodies. STATUS.md is large; a
        # distinctive committed STATUS line must not appear in the (lean) export.
        status_body = (REPO / "docs/context/project/STATUS.md").read_text(encoding="utf-8")
        # pick a long, distinctive substring from deep in STATUS.md
        needle = "Snapshot date"  # near the top; still shouldn't be inlined
        self.assertIn(needle, status_body)
        self.assertNotIn(needle, text)
        # sanity: the export stays lean (well under the vault's total size)
        self.assertLess(len(text), 12000)

    def test_includes_never_stage_warnings(self):
        text = self._export("codex")
        self.assertIn("Do not store secrets", text)      # vault-pointer warning
        self.assertIn(".council/runtime/", text)         # from the reused guide common rules
        self.assertIn("Never stage", text)               # guide never-stage list

    def test_recommends_project_doctor(self):
        self.assertIn("vibe project doctor", self._export("fable"))

    def test_includes_workbench_proposal_flow(self):
        text = self._export("claude")
        self.assertIn("vibe workbench propose", text)
        self.assertIn("no auto-execution", text.lower())

    def test_includes_context_health_in_memory(self):
        text = self._export("claude")
        self.assertIn("Context health", text)
        self.assertIn("21/21", text)                     # real repo is healthy

    def test_fable_export_includes_budget_policy(self):
        text = self._export("fable")
        self.assertIn("Fable is expensive", text)
        self.assertIn("technical lead / architect", text)
        self.assertIn("Opus/Sonnet implement routine PRs", text)

    def test_role_tailoring_when_provided(self):
        text = self._export("codex", role="reviewer")
        self.assertIn("role: reviewer", text)
        self.assertIn("### Role: reviewer", text)

    def test_no_private_plan_names_leaked(self):
        # The export must not surface a private plan filename (the reused guide/never-stage
        # text references .council/ etc. but not the private plan filenames).
        for agent in ("claude", "codex", "fable"):
            text = self._export(agent)
            for name in PRIVATE_PLAN_NAMES:
                self.assertNotIn(name, text, f"{agent}: leaked private plan name {name}")


class TestAgentExportCli(unittest.TestCase):
    def test_stdout_export_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            before = set(p.name for p in root.iterdir())
            r = run_cli(["context", "export", "--for", "claude"], caller_cwd=REPO)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("onboarding context", r.stdout)
            self.assertEqual(before, set(p.name for p in root.iterdir()))  # nothing written here

    def test_stdout_export_creates_no_council(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            # caller cwd is REPO (so vault/health resolve), but no .council should be
            # created in the throwaway run cwd regardless.
            r = run_cli(["context", "export", "--for", "fable"], caller_cwd=REPO)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((root / ".council").exists())

    def test_invalid_agent_fails(self):
        r = run_cli(["context", "export", "--for", "gemini"], caller_cwd=REPO)
        self.assertEqual(r.returncode, 2)  # argparse choices

    def test_output_writes_when_absent(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "onboard.md"
            r = run_cli(["context", "export", "--for", "codex", "--output", str(out)],
                        caller_cwd=REPO)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.is_file())
            self.assertIn("Codex", out.read_text(encoding="utf-8"))
            self.assertIn("[context-export] wrote", r.stderr)

    def test_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "onboard.md"
            out.write_text("keep me\n", encoding="utf-8")
            r = run_cli(["context", "export", "--for", "codex", "--output", str(out)],
                        caller_cwd=REPO)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("refusing to overwrite", r.stderr)
            self.assertEqual(out.read_text(encoding="utf-8"), "keep me\n")  # untouched

    def test_legacy_claude_code_export_still_recognized(self):
        # Without a built pack it fails gracefully (unchanged behavior), not a crash.
        with tempfile.TemporaryDirectory() as t:
            r = run_cli(["context", "export", "claude-code"], caller_cwd=Path(t))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("pack not found", r.stderr)


if __name__ == "__main__":
    unittest.main()
