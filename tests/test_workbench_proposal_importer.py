"""Tests for the proposal importer (backend/workbench_proposal_importer.py).

Stdlib-only (`unittest`). The importer's only side effects are JSON writes under a
**temp** `.council/runtime/` tree — no execution, no subprocess, no network/model
call, no panel. Tests cover: import of the three allowed kinds, server-side payload
artifact + hash, dedup/idempotency by proposal_id, conflict on changed content,
fail-closed on invalid input, linkage the existing executor invariant accepts (and a
real bounded write through the EXISTING executor in a temp project), and the CLI
file/stdin intake.
"""

import contextlib
import io
import json
import os
import unittest
import tempfile
from pathlib import Path
from unittest import mock

from backend import workbench_proposal_importer as wimp
from backend import workbench_proposals as wprop
from backend import workbench_runtime as wr
from backend import workbench_orchestrator as wo
from backend import workbench_payloads as wpay
from backend import workbench_executor as we
from backend import cli


def _write_proposal(pid="prop-write-1", target="docs/note.md",
                    content="hello from an agent\n"):
    return {
        "proposal_schema": 1,
        "proposal_id": pid,
        "agent": {"name": "claude-code", "role": "coder", "session": "s1"},
        "title": "Write a note",
        "summary": "Adds a small note file.",
        "action": {"kind": "write_file", "target": target,
                   "payload": {"content": content, "overwrite": False}},
    }


def _edit_proposal(pid="prop-edit-1"):
    return {
        "proposal_schema": 1,
        "proposal_id": pid,
        "agent": {"name": "fable"},
        "title": "Edit the note",
        "summary": "Rewords the note.",
        "action": {"kind": "edit_file", "target": "docs/note.md",
                   "payload": {"old_text": "hello", "new_text": "hi",
                               "max_replacements": 1}},
    }


def _command_proposal(pid="prop-cmd-1", label="git status --short"):
    return {
        "proposal_schema": 1,
        "proposal_id": pid,
        "agent": {"name": "codex", "role": "reviewer"},
        "title": "Check repo status",
        "summary": "Read-only status check before approval.",
        "action": {"kind": "run_command", "command_label": label},
    }


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _import(self, data):
        return wimp.import_proposal(data, project_root=self.root)


class TestImportCreatesRecords(_Base):
    def test_write_file_imports_one_task_approval_action(self):
        r = self._import(_write_proposal())
        self.assertTrue(r.ok)
        self.assertTrue(r.created)
        self.assertFalse(r.duplicate)
        task = wr.load_task(r.task_id, self.root)
        ap = wr.load_approval(r.approval_id, self.root)
        act = wr.load_action(r.action_id, self.root)
        self.assertIsNotNone(task)
        self.assertIsNotNone(ap)
        self.assertIsNotNone(act)
        self.assertEqual(len(wr.list_tasks(project_root=self.root)), 1)
        self.assertEqual(task.source, "agent:claude-code")
        self.assertEqual(ap.status, "pending")
        self.assertEqual(act.status, "pending")
        self.assertIn("workbench serve", r.next_step)

    def test_linkage_matches_executor_invariant_expectations(self):
        r = self._import(_write_proposal())
        task = wr.load_task(r.task_id, self.root)
        ap = wr.load_approval(r.approval_id, self.root)
        act = wr.load_action(r.action_id, self.root)
        self.assertEqual(act.approval_id, ap.id)
        self.assertEqual(act.task_id, task.id)
        self.assertIn(act.id, task.action_ids)
        self.assertIn(ap.id, task.approval_ids)
        # server-constructed internal convention matches the executor's parser
        self.assertEqual(ap.requested_action, "write_file:docs/note.md")
        self.assertEqual(act.kind, "write_file")
        self.assertEqual(act.command_or_path, "docs/note.md")

    def test_payload_artifact_exists_and_verifies_against_action(self):
        r = self._import(_write_proposal())
        self.assertTrue(r.payload_artifact)
        artifact = wpay.load_payload_artifact(r.action_id, self.root)
        self.assertIsNotNone(artifact)
        act = wr.load_action(r.action_id, self.root)
        ap = wr.load_approval(r.approval_id, self.root)
        task = wr.load_task(r.task_id, self.root)
        pv = wpay.verify_payload_against_action(artifact, act, ap, task)
        self.assertTrue(pv.ok, pv.findings)
        # hash was computed server-side from the submitted content
        expected = wpay.canonical_payload_hash("write_file", "docs/note.md",
                                               {"content": "hello from an agent\n",
                                                "overwrite": False})
        self.assertEqual(artifact.payload_hash, expected)

    def test_client_supplied_payload_hash_is_rejected_at_schema_level(self):
        data = _write_proposal()
        data["action"]["payload_hash"] = "sha256:deadbeef"
        r = self._import(data)
        self.assertFalse(r.ok)
        self.assertEqual(wr.list_tasks(project_root=self.root), [])

    def test_raw_payload_only_in_payload_artifact(self):
        content = "DISTINCTIVE-PAYLOAD-CONTENT-4242\n"
        r = self._import(_write_proposal(content=content))
        rr = wr.runtime_root(self.root)
        for sub in ("tasks", "approvals", "actions", "proposals"):
            for p in (rr / sub).glob("*.json"):
                self.assertNotIn("DISTINCTIVE-PAYLOAD-CONTENT-4242",
                                 p.read_text(encoding="utf-8"),
                                 f"raw payload leaked into {sub}/{p.name}")
        artifact = wpay.load_payload_artifact(r.action_id, self.root)
        self.assertEqual(artifact.payload["content"], content)  # the intended store

    def test_edit_file_imports_correctly(self):
        r = self._import(_edit_proposal())
        self.assertTrue(r.ok)
        self.assertTrue(r.payload_artifact)
        ap = wr.load_approval(r.approval_id, self.root)
        self.assertEqual(ap.requested_action, "edit_file:docs/note.md")
        artifact = wpay.load_payload_artifact(r.action_id, self.root)
        self.assertEqual(artifact.kind, "edit_file")

    def test_run_command_imports_without_payload_artifact(self):
        r = self._import(_command_proposal())
        self.assertTrue(r.ok)
        self.assertFalse(r.payload_artifact)
        self.assertIsNone(wpay.load_payload_artifact(r.action_id, self.root))
        ap = wr.load_approval(r.approval_id, self.root)
        self.assertEqual(ap.requested_action, "run_command:git status --short")
        act = wr.load_action(r.action_id, self.root)
        self.assertEqual(act.status, "pending")  # imported, never executed

    def test_advisory_audit_saved_and_linked(self):
        r = self._import(_write_proposal())
        ap = wr.load_approval(r.approval_id, self.root)
        self.assertIsNotNone(ap.audit_id)
        audit = wr.load_audit(ap.audit_id, self.root)
        self.assertIsNotNone(audit)
        self.assertEqual(r.audit_risk, audit.risk_level)
        self.assertFalse(r.audit_blocked)

    def test_invalid_proposal_creates_nothing(self):
        r = self._import({"proposal_schema": 1, "proposal_id": "bad"})
        self.assertFalse(r.ok)
        self.assertEqual(wr.list_tasks(project_root=self.root), [])
        rr = wr.runtime_root(self.root)
        self.assertFalse((rr / "proposals").exists())

    def test_import_never_executes(self):
        target = self.root / "docs" / "note.md"
        self._import(_write_proposal())
        self.assertFalse(target.exists())  # import is not execution


class TestDedupAndConflict(_Base):
    def test_duplicate_returns_existing_and_creates_no_duplicates(self):
        first = self._import(_write_proposal())
        second = self._import(_write_proposal())
        self.assertTrue(second.ok)
        self.assertTrue(second.duplicate)
        self.assertFalse(second.created)
        self.assertEqual(second.task_id, first.task_id)
        self.assertEqual(second.approval_id, first.approval_id)
        self.assertEqual(second.action_id, first.action_id)
        self.assertEqual(len(wr.list_tasks(project_root=self.root)), 1)

    def test_duplicate_id_with_changed_content_is_a_conflict(self):
        self._import(_write_proposal())
        changed = _write_proposal(content="materially different content\n")
        r = self._import(changed)
        self.assertFalse(r.ok)
        self.assertTrue(r.conflict)
        self.assertIn("different content", " ".join(r.errors))
        self.assertEqual(len(wr.list_tasks(project_root=self.root)), 1)  # nothing new

    def test_corrupt_dedup_record_fails_closed(self):
        # A dedup record that exists but can't be parsed must refuse the import
        # (fail closed) rather than silently re-create records (broken idempotency).
        self._import(_write_proposal())
        rec_path = wr.runtime_root(self.root) / "proposals" / "prop-write-1.json"
        rec_path.write_text("{corrupted", encoding="utf-8")
        r = self._import(_write_proposal())
        self.assertFalse(r.ok)
        self.assertTrue(r.conflict)
        self.assertIn("unreadable", " ".join(r.errors))
        self.assertEqual(len(wr.list_tasks(project_root=self.root)), 1)  # nothing new

    def test_dedup_record_holds_metadata_not_payload(self):
        self._import(_write_proposal(content="SECRET-ISH-CONTENT\n"))
        rec_path = wr.runtime_root(self.root) / "proposals" / "prop-write-1.json"
        self.assertTrue(rec_path.is_file())
        text = rec_path.read_text(encoding="utf-8")
        self.assertNotIn("SECRET-ISH-CONTENT", text)
        rec = json.loads(text)
        self.assertEqual(rec["agent"]["name"], "claude-code")
        self.assertEqual(rec["agent"]["role"], "coder")
        self.assertTrue(rec["fingerprint"].startswith("sha256:"))


class TestImportedActionsUseExistingExecutor(_Base):
    def test_imported_write_file_executes_after_approval(self):
        r = self._import(_write_proposal())
        wo.decide_approval(r.approval_id, "approve", project_root=self.root)
        res = we.execute_action(r.action_id, project_root=self.root, dry_run=False)
        self.assertTrue(res.executed)
        target = self.root / "docs" / "note.md"
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_text(encoding="utf-8"), "hello from an agent\n")
        self.assertEqual(wr.load_action(r.action_id, self.root).status, "completed")

    def test_imported_write_file_blocked_without_approval(self):
        r = self._import(_write_proposal())
        res = we.execute_action(r.action_id, project_root=self.root, dry_run=False)
        self.assertFalse(res.executed)
        self.assertTrue(res.blocked)
        self.assertFalse((self.root / "docs" / "note.md").exists())

    def test_imported_command_dry_run_would_execute_after_approval(self):
        r = self._import(_command_proposal())
        wo.decide_approval(r.approval_id, "approve", project_root=self.root)
        res = we.execute_action(r.action_id, project_root=self.root, dry_run=True)
        self.assertTrue(res.would_execute)
        self.assertFalse(res.executed)  # dry run: existing behavior, nothing ran


class TestImporterPurityGuarantees(_Base):
    def test_importer_never_imports_subprocess(self):
        self.assertNotIn("subprocess", getattr(wimp, "__dict__", {}))

    def test_import_proposal_text_malformed_json_creates_nothing(self):
        r = wimp.import_proposal_text("{not json", project_root=self.root)
        self.assertFalse(r.ok)
        self.assertIn("malformed JSON", r.errors[0])
        self.assertEqual(os.listdir(self.root), [])  # no .council/ at all

    def test_summaries_are_log_safe(self):
        r = self._import(_write_proposal(content="NEVER-IN-LOGS\n"))
        self.assertNotIn("NEVER-IN-LOGS", wimp.summarize_import(r))
        self.assertNotIn("NEVER-IN-LOGS", json.dumps(wimp.result_to_dict(r)))


class TestProposeCli(unittest.TestCase):
    """In-process CLI tests: `vibe workbench propose <file|->` with the caller cwd
    pointed at a temp project root."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._env = mock.patch.dict(os.environ, {"VIBE_CALLER_CWD": str(self.root)})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def _run(self, argv, stdin_text=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            if stdin_text is not None:
                with mock.patch("sys.stdin", io.StringIO(stdin_text)):
                    code = cli.main(argv)
            else:
                code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_cli_reads_file_and_imports(self):
        pfile = self.root / "proposal.json"
        pfile.write_text(json.dumps(_write_proposal(pid="cli-file-1")),
                         encoding="utf-8")
        code, out, err = self._run(["workbench", "propose", str(pfile)])
        self.assertEqual(code, 0)
        body = json.loads(out)
        self.assertTrue(body["ok"])
        self.assertTrue(body["created"])
        self.assertIsNotNone(wr.load_task(body["task_id"], self.root))
        self.assertIn("[workbench]", err)

    def test_cli_reads_stdin(self):
        code, out, _err = self._run(["workbench", "propose", "-"],
                                    stdin_text=json.dumps(_command_proposal(pid="cli-stdin-1")))
        self.assertEqual(code, 0)
        body = json.loads(out)
        self.assertTrue(body["ok"])
        self.assertEqual(body["kind"], "run_command")

    def test_cli_rejects_invalid_json_nonzero_exit(self):
        pfile = self.root / "bad.json"
        pfile.write_text("{definitely not json", encoding="utf-8")
        code, out, _err = self._run(["workbench", "propose", str(pfile)])
        self.assertNotEqual(code, 0)
        body = json.loads(out)
        self.assertFalse(body["ok"])

    def test_cli_failure_creates_no_runtime_files(self):
        pfile = self.root / "bad.json"
        pfile.write_text("{nope", encoding="utf-8")
        self._run(["workbench", "propose", str(pfile)])
        self.assertFalse((self.root / ".council").exists())

    def test_cli_missing_file_arg_is_usage_error(self):
        code, _out, err = self._run(["workbench", "propose"])
        self.assertEqual(code, 2)
        self.assertIn("Usage", err)

    def test_cli_never_prints_raw_payload(self):
        pfile = self.root / "proposal.json"
        pfile.write_text(json.dumps(_write_proposal(
            pid="cli-secret-1", content="CLI-DISTINCTIVE-CONTENT\n")), encoding="utf-8")
        code, out, err = self._run(["workbench", "propose", str(pfile)])
        self.assertEqual(code, 0)
        self.assertNotIn("CLI-DISTINCTIVE-CONTENT", out)
        self.assertNotIn("CLI-DISTINCTIVE-CONTENT", err)

    def test_cli_duplicate_import_is_ok_and_stable(self):
        pfile = self.root / "proposal.json"
        pfile.write_text(json.dumps(_write_proposal(pid="cli-dup-1")),
                         encoding="utf-8")
        code1, out1, _ = self._run(["workbench", "propose", str(pfile)])
        code2, out2, _ = self._run(["workbench", "propose", str(pfile)])
        self.assertEqual((code1, code2), (0, 0))
        b1, b2 = json.loads(out1), json.loads(out2)
        self.assertTrue(b2["duplicate"])
        self.assertEqual(b1["task_id"], b2["task_id"])


if __name__ == "__main__":
    unittest.main()
