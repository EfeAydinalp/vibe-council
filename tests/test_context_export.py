"""Tests for the Claude Code context export (backend/context_pack.wrap_for_claude_code
+ `vibe context export claude-code`).

Stdlib-only (`unittest`). Deterministic, no model/API/network. The fake key below
is a synthetic fixture, not a real key.
"""

import unittest
import tempfile
from pathlib import Path

from backend import context_pack as cp
from tests.test_cli_smoke import run_cli
from tests.test_context_check import GOOD_PACK

FAKE_OR_KEY = "sk-or-v1-" + "a" * 40


class TestWrap(unittest.TestCase):
    def test_wrap_contains_required_sections(self):
        out = cp.wrap_for_claude_code(GOOD_PACK)
        self.assertIn("# Claude Code Context", out)
        self.assertIn("## How to use", out)
        self.assertIn("## Operator instruction", out)
        self.assertIn(cp.OPERATOR_INSTRUCTION, out)
        self.assertIn("## Context pack", out)
        self.assertIn("## Metadata", out)               # pack body embedded
        self.assertIn("## Next suggested commands", out)
        for cmd in ("vibe context build", "vibe context check",
                    "vibe decisions lint", "vibe lint --redaction"):
            self.assertIn(cmd, out)


class TestExportCLI(unittest.TestCase):
    def _pack(self, root: Path, content: str = GOOD_PACK) -> Path:
        p = root / ".council" / "context" / "pack-latest.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_export_from_valid_pack_default_path(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self._pack(root)
            r = run_cli(["context", "export", "claude-code"],
                        caller_cwd=root, key=None)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = root / ".council" / "context" / "claude-code-context.md"
            self.assertTrue(out.is_file())
            text = out.read_text(encoding="utf-8")
            self.assertIn("## Operator instruction", text)
            self.assertIn(cp.OPERATOR_INSTRUCTION, text)

    def test_missing_pack_message(self):
        with tempfile.TemporaryDirectory() as t:
            r = run_cli(["context", "export", "claude-code"], caller_cwd=Path(t))
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("vibe context build", r.stderr)

    def test_check_failure_blocks_export(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            bad = GOOD_PACK.replace("## Decision index (older)", "## Other")
            self._pack(root, bad)
            r = run_cli(["context", "export", "claude-code"], caller_cwd=root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("context check failed", r.stderr)
            self.assertFalse((root / ".council" / "context"
                              / "claude-code-context.md").exists())

    def test_redaction_critical_blocks_export(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self._pack(root, GOOD_PACK + f"\nleaked {FAKE_OR_KEY}\n")
            r = run_cli(["context", "export", "claude-code"], caller_cwd=root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("critical redaction", r.stderr.lower())
            self.assertFalse((root / ".council" / "context"
                              / "claude-code-context.md").exists())

    def test_docs_output_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self._pack(root)
            r = run_cli(["context", "export", "claude-code",
                         "--output", "docs/cc.md"], caller_cwd=root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("refusing", r.stderr.lower())
            self.assertFalse((root / "docs" / "cc.md").exists())

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self._pack(root)
            r = run_cli(["context", "export", "claude-code", "--dry-run"],
                        caller_cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((root / ".council" / "context"
                              / "claude-code-context.md").exists())


if __name__ == "__main__":
    unittest.main()
