"""Tests for the execution payload artifact store (backend/workbench_payloads.py, PR #76).

Stdlib-only (`unittest`). Covers: canonical hashing (stable/sensitive to content,
excludes timestamps/metadata), save/load round trip, write-once behavior, and
tamper detection (content/kind/target mismatches). Temp dirs only; no real-repo
`.council/runtime/` artifacts. No shell/git/provider/model/network calls.
"""

import unittest
import tempfile
from pathlib import Path

from backend import workbench_payloads as wp
from backend import workbench_runtime as wr

FIXED = "2026-07-02T00:00:00Z"


def _action(kind="write_file", target="docs/foo.md", task_id="task-1",
           approval_id="appr-1", action_id="act-1"):
    act = wr.Action(id=action_id, task_id=task_id, approval_id=approval_id,
                    kind=kind, status="pending", command_or_path=target,
                    created_at=FIXED)
    return act


class TestCanonicalHash(unittest.TestCase):
    def test_stable_across_key_order(self):
        h1 = wp.canonical_payload_hash("write_file", "a.md",
                                       {"content": "x", "overwrite": False})
        h2 = wp.canonical_payload_hash("write_file", "a.md",
                                       {"overwrite": False, "content": "x"})
        self.assertEqual(h1, h2)

    def test_changes_when_content_changes(self):
        h1 = wp.canonical_payload_hash("write_file", "a.md", {"content": "x"})
        h2 = wp.canonical_payload_hash("write_file", "a.md", {"content": "y"})
        self.assertNotEqual(h1, h2)

    def test_changes_when_kind_or_target_changes(self):
        base = wp.canonical_payload_hash("write_file", "a.md", {"content": "x"})
        other_kind = wp.canonical_payload_hash("edit_file", "a.md", {"content": "x"})
        other_target = wp.canonical_payload_hash("write_file", "b.md", {"content": "x"})
        self.assertNotEqual(base, other_kind)
        self.assertNotEqual(base, other_target)

    def test_hash_prefix_is_sha256(self):
        h = wp.canonical_payload_hash("write_file", "a.md", {"content": "x"})
        self.assertTrue(h.startswith("sha256:"))
        self.assertEqual(len(h), len("sha256:") + 64)


class TestBuildArtifactExcludesMetadataFromHash(unittest.TestCase):
    def test_hash_excludes_timestamps_and_metadata(self):
        act = _action()
        a1 = wp.build_payload_artifact(act, {"content": "x"}, on="2026-01-01T00:00:00Z")
        a2 = wp.build_payload_artifact(act, {"content": "x"}, on="2099-01-01T00:00:00Z")
        self.assertEqual(a1.payload_hash, a2.payload_hash)
        self.assertNotEqual(a1.created_at, a2.created_at)

    def test_redacted_summary_has_no_raw_content(self):
        act = _action()
        artifact = wp.build_payload_artifact(act, {"content": "super-secret-value"})
        dumped = str(artifact.redacted_summary)
        self.assertNotIn("super-secret-value", dumped)
        self.assertEqual(artifact.redacted_summary["content_bytes"],
                         len("super-secret-value".encode("utf-8")))


class TestSaveLoadRoundTrip(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_round_trip(self):
        act = _action(action_id="act-rt")
        artifact = wp.build_payload_artifact(act, {"content": "hello", "overwrite": False})
        wp.save_payload_artifact(artifact, self.root)
        loaded = wp.load_payload_artifact("act-rt", self.root)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.action_id, "act-rt")
        self.assertEqual(loaded.payload, {"content": "hello", "overwrite": False})
        self.assertEqual(loaded.payload_hash, artifact.payload_hash)

    def test_load_missing_returns_none(self):
        self.assertIsNone(wp.load_payload_artifact("nope", self.root))

    def test_written_under_gitignored_runtime_payloads_dir(self):
        act = _action(action_id="act-path")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        wp.save_payload_artifact(artifact, self.root)
        expected = self.root / ".council" / "runtime" / "payloads" / "act-path.json"
        self.assertTrue(expected.is_file())

    def test_save_existing_without_overwrite_fails(self):
        act = _action(action_id="act-once")
        artifact = wp.build_payload_artifact(act, {"content": "first"})
        wp.save_payload_artifact(artifact, self.root)
        artifact2 = wp.build_payload_artifact(act, {"content": "second"})
        with self.assertRaises(wp.PayloadError):
            wp.save_payload_artifact(artifact2, self.root)
        # unchanged on disk
        loaded = wp.load_payload_artifact("act-once", self.root)
        self.assertEqual(loaded.payload, {"content": "first"})

    def test_save_existing_with_explicit_overwrite_replaces(self):
        act = _action(action_id="act-ow")
        artifact = wp.build_payload_artifact(act, {"content": "first"})
        wp.save_payload_artifact(artifact, self.root)
        artifact2 = wp.build_payload_artifact(act, {"content": "second"})
        wp.save_payload_artifact(artifact2, self.root, overwrite=True)
        loaded = wp.load_payload_artifact("act-ow", self.root)
        self.assertEqual(loaded.payload, {"content": "second"})

    def test_action_id_with_traversal_chars_is_sanitized_and_contained(self):
        act = _action(action_id="../../evil")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        path = wp._entry_path(self.root, artifact.action_id)
        payloads_dir = (self.root / ".council" / "runtime" / "payloads").resolve()
        self.assertEqual(path.parent, payloads_dir)


class TestVerifyPayloadArtifact(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_verify_ok_for_untampered_artifact(self):
        act = _action(action_id="act-v1")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        v = wp.verify_payload_artifact(artifact)
        self.assertTrue(v.ok)

    def test_verify_detects_tampered_content(self):
        act = _action(action_id="act-v2")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        artifact.payload["content"] = "tampered"  # mutate after hashing
        v = wp.verify_payload_artifact(artifact)
        self.assertFalse(v.ok)
        self.assertIn("payload_hash mismatch", v.findings)

    def test_verify_detects_tampered_kind(self):
        act = _action(action_id="act-v3")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        artifact.kind = "edit_file"
        v = wp.verify_payload_artifact(artifact)
        self.assertFalse(v.ok)

    def test_verify_detects_tampered_target(self):
        act = _action(action_id="act-v4")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        artifact.target = "docs/other.md"
        v = wp.verify_payload_artifact(artifact)
        self.assertFalse(v.ok)

    def test_verify_missing_artifact(self):
        v = wp.verify_payload_artifact(None)
        self.assertFalse(v.ok)

    def test_disk_tamper_detected_on_reload(self):
        act = _action(action_id="act-disk")
        artifact = wp.build_payload_artifact(act, {"content": "orig"})
        wp.save_payload_artifact(artifact, self.root)
        path = wp._entry_path(self.root, "act-disk")
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        data["payload"]["content"] = "rewritten-on-disk"
        path.write_text(json.dumps(data), encoding="utf-8")
        reloaded = wp.load_payload_artifact("act-disk", self.root)
        v = wp.verify_payload_artifact(reloaded)
        self.assertFalse(v.ok)


class TestVerifyPayloadAgainstAction(unittest.TestCase):
    def test_matches(self):
        act = _action(action_id="act-m1", kind="write_file", target="docs/m.md",
                      task_id="task-m", approval_id="appr-m")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        v = wp.verify_payload_against_action(artifact, act)
        self.assertTrue(v.ok)

    def test_kind_mismatch(self):
        act = _action(action_id="act-m2", kind="write_file")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        act.kind = "edit_file"  # live action changed after artifact was built
        v = wp.verify_payload_against_action(artifact, act)
        self.assertFalse(v.ok)
        self.assertTrue(any("kind mismatch" in f for f in v.findings))

    def test_target_mismatch(self):
        act = _action(action_id="act-m3", target="docs/a.md")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        act.command_or_path = "docs/b.md"
        v = wp.verify_payload_against_action(artifact, act)
        self.assertFalse(v.ok)
        self.assertTrue(any("target mismatch" in f for f in v.findings))

    def test_approval_id_mismatch(self):
        act = _action(action_id="act-m4", approval_id="appr-a")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        act.approval_id = "appr-b"
        v = wp.verify_payload_against_action(artifact, act)
        self.assertFalse(v.ok)
        self.assertTrue(any("approval_id mismatch" in f for f in v.findings))

    def test_task_id_mismatch(self):
        act = _action(action_id="act-m5", task_id="task-a")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        act.task_id = "task-b"
        v = wp.verify_payload_against_action(artifact, act)
        self.assertFalse(v.ok)
        self.assertTrue(any("task_id mismatch" in f for f in v.findings))

    def test_missing_action(self):
        act = _action(action_id="act-m6")
        artifact = wp.build_payload_artifact(act, {"content": "x"})
        v = wp.verify_payload_against_action(artifact, None)
        self.assertFalse(v.ok)


class TestSummarize(unittest.TestCase):
    def test_summary_has_no_raw_content(self):
        act = _action(target="docs/secretpath.md")
        artifact = wp.build_payload_artifact(act, {"content": "top-secret-content"})
        s = wp.summarize_payload_artifact(artifact)
        self.assertNotIn("top-secret-content", s)
        self.assertIn("secretpath.md", s)
        self.assertIn("kind=write_file", s)

    def test_summary_none(self):
        self.assertEqual(wp.summarize_payload_artifact(None), "[payload] none")


if __name__ == "__main__":
    unittest.main()
