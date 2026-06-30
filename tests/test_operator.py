"""Tests for the minimal operator status (backend/operator.py) + CLI.

Stdlib-only (`unittest`). No model/API/network.
"""

import json
import unittest
import tempfile
from pathlib import Path

from backend import operator as op
from tests.test_cli_smoke import run_cli


class TestModule(unittest.TestCase):
    def test_status_path_under_operator_dir(self):
        p = op.status_path(Path("/some/root"))
        self.assertEqual(p.name, "status.json")
        self.assertEqual(p.parent.name, "operator")
        self.assertEqual(p.parent.parent.name, ".council")

    def test_read_missing_is_none(self):
        with tempfile.TemporaryDirectory() as t:
            data, err = op.read_status(op.status_path(Path(t)))
            self.assertIsNone(data)
            self.assertIsNone(err)

    def test_write_then_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as t:
            p = op.status_path(Path(t))
            doc, err = op.write_status(p, state="done", message="all green",
                                       next_action="ship it", source="ci",
                                       severity="info", on="2026-06-30T00:00:00Z")
            self.assertIsNone(err)
            self.assertEqual(doc["state"], "done")
            data, rerr = op.read_status(p)
            self.assertIsNone(rerr)
            self.assertEqual(data["message"], "all green")
            self.assertEqual(data["version"], op.VERSION)

    def test_invalid_state_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = op.status_path(Path(t))
            doc, err = op.write_status(p, state="bogus")
            self.assertIsNone(doc)
            self.assertIn("invalid state", err)
            self.assertFalse(p.exists())

    def test_invalid_severity_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = op.status_path(Path(t))
            doc, err = op.write_status(p, state="idle", severity="boom")
            self.assertIsNone(doc)
            self.assertIn("invalid severity", err)

    def test_refuses_path_outside_operator_dir(self):
        with tempfile.TemporaryDirectory() as t:
            outside = Path(t) / "evil.json"
            doc, err = op.write_status(outside, state="idle")
            self.assertIsNone(doc)
            self.assertIn("refusing", err)
            self.assertFalse(outside.exists())

    def test_clean_strips_control_and_caps(self):
        long = "a" * 1000
        out = op._clean("line1\nline2\twith\x00ctrl  spaces  " + long)
        self.assertNotIn("\x00", out)
        self.assertNotIn("\n", out)
        self.assertLessEqual(len(out), op.MAX_FIELD)

    def test_invalid_json_reads_as_error(self):
        with tempfile.TemporaryDirectory() as t:
            p = op.status_path(Path(t))
            p.parent.mkdir(parents=True)
            p.write_text("{not valid json", encoding="utf-8")
            data, err = op.read_status(p)
            self.assertIsNone(data)
            self.assertIsNotNone(err)


class TestCLI(unittest.TestCase):
    def _status_file(self, root: Path):
        p = op.status_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def test_missing_prints_helpful_message(self):
        with tempfile.TemporaryDirectory() as t:
            r = run_cli(["operator", "status"], caller_cwd=Path(t), key=None)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("No operator status yet", r.stdout)

    def test_set_then_status(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            s = run_cli(["operator", "set", "--state", "needs_input",
                         "--message", "awaiting approval",
                         "--next-action", "promote"], caller_cwd=root)
            self.assertEqual(s.returncode, 0, s.stderr)
            self.assertTrue(op.status_path(root).is_file())
            r = run_cli(["operator", "status"], caller_cwd=root)
            self.assertEqual(r.returncode, 0)
            self.assertIn("needs_input", r.stdout)
            self.assertIn("awaiting approval", r.stdout)
            self.assertIn("promote", r.stdout)

    def test_status_json(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            op.write_status(op.status_path(root), state="done", message="ok",
                            on="2026-06-30T00:00:00Z")
            r = run_cli(["operator", "status", "--json"], caller_cwd=root)
            self.assertEqual(r.returncode, 0)
            data = json.loads(r.stdout)
            self.assertEqual(data["state"], "done")

    def test_invalid_json_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self._status_file(root).write_text("{broken", encoding="utf-8")
            r = run_cli(["operator", "status"], caller_cwd=root)
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("Traceback", r.stderr)
            self.assertIn("invalid", r.stderr.lower())


if __name__ == "__main__":
    unittest.main()
