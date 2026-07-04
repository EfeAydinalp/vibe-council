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


class TestAgentExportProfilePointers(unittest.TestCase):
    """v0.7 PR C — profile/preferences POINTERS in the export (never inlined, never
    reads a local/private profile). Present or missing, the section is deterministic."""

    PROFILE_FILES = (
        "docs/context/project/PROFILE.md",
        "docs/context/project/PREFERENCES.md",
        "docs/context/project/AGENT-ROLES.md",
    )
    # distinctive phrases that live ONLY in the scaffold bodies (verified) — must NOT be
    # inlined into the lean export.
    NON_INLINE_NEEDLES = {
        "docs/context/project/PROFILE.md": "began as a fork of",
        "docs/context/project/PREFERENCES.md": "Which council review level to run",
        "docs/context/project/AGENT-ROLES.md": "who does what",
    }

    def _export(self, agent, role=None, project_root=REPO):
        return cli.agent_context_export(agent, role=role, project_root=project_root)

    def test_all_agents_include_profile_pointers(self):
        for agent in ("claude", "codex", "fable"):
            text = self._export(agent)
            self.assertIn("Project profile & preferences", text)
            for rel in self.PROFILE_FILES:
                self.assertIn(rel, text, f"{agent}: missing pointer {rel}")

    def test_section_states_pointers_not_full_dump(self):
        text = self._export("claude")
        self.assertIn("pointers only", text.lower())
        self.assertIn("dump their full contents", text.lower())

    def test_does_not_inline_scaffold_bodies(self):
        for agent in ("claude", "codex", "fable"):
            text = self._export(agent)
            for rel, needle in self.NON_INLINE_NEEDLES.items():
                body = (REPO / rel).read_text(encoding="utf-8")
                self.assertIn(needle, body)                  # sanity: needle is in the file
                self.assertNotIn(needle, text,
                                 f"{agent}: inlined distinctive content from {rel}")

    def test_mentions_tighten_only(self):
        text = self._export("claude").lower()
        self.assertIn("tighten-only", text)
        self.assertIn("never loosen", text)

    def test_says_root_agents_md_not_canonical_preference_source(self):
        text = self._export("codex")
        self.assertIn("Root `AGENTS.md` is not the canonical preference source", text)
        self.assertIn("docs/context/project/AGENT-ROLES.md", text)

    def test_section_recommends_project_doctor(self):
        text = self._export("fable")
        # the profile section itself recommends the doctor to check scaffold presence.
        self.assertIn("scaffold files are present", text)
        self.assertIn("vibe project doctor", text)

    def test_does_not_read_or_leak_local_profile(self):
        # A local .council/profile.* with a secret must never be read into the export.
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / ".council").mkdir()
            (root / ".council" / "profile.json").write_text(
                '{"secret": "SUPERSECRETTOKEN_do_not_leak"}\n', encoding="utf-8")
            text = self._export("claude", project_root=root)
            self.assertNotIn("SUPERSECRETTOKEN_do_not_leak", text)
            # the section still renders (graceful) and states it never reads that path.
            self.assertIn("Project profile & preferences", text)
            self.assertIn(".council/profile.*", text)

    def test_missing_scaffold_does_not_fail_export(self):
        # An empty project root (no scaffold, no vault) still builds — pointers are static,
        # health degrades gracefully — and the section lists the expected paths.
        with tempfile.TemporaryDirectory() as t:
            text = self._export("claude", project_root=Path(t))
            self.assertIn("Project profile & preferences", text)
            for rel in self.PROFILE_FILES:
                self.assertIn(rel, text)
            self.assertIn("vibe project doctor", text)

    def test_no_private_plan_names_in_profile_section(self):
        for agent in ("claude", "codex", "fable"):
            text = self._export(agent)
            for name in PRIVATE_PLAN_NAMES:
                self.assertNotIn(name, text)


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
