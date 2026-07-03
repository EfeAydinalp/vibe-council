"""Tests for the agent proposal schema + validation (backend/workbench_proposals.py).

Stdlib-only (`unittest`). Validation is **pure**: these tests assert it never writes
a file, never creates `.council/` or runtime store entries, never imports
`subprocess`, and never echoes payload content into error messages. Temp dirs only;
no model/API/network, no execution. The three valid and two rejected examples from
docs/fable/06-proposal-schema.md appear verbatim.
"""

import os
import unittest
import tempfile
from pathlib import Path

from backend import workbench_proposals as wp
from backend import workbench_commands as wc
from backend import workbench_trust as wt


def _valid_write(**overrides):
    """The docs/fable/06 'Valid write_file' example (verbatim), with overrides."""
    p = {
        "proposal_schema": 1,
        "proposal_id": "c0ffee-write-readme-note",
        "agent": {"name": "fable", "role": "coder"},
        "title": "Add a usage note to docs/example.md",
        "summary": "Documents the new flag so users find it.",
        "action": {
            "kind": "write_file",
            "target": "docs/example.md",
            "payload": {"content": "# Example\n\nUsage note.\n", "overwrite": False},
        },
    }
    p.update(overrides)
    return p


def _valid_edit():
    """The docs/fable/06 'Valid edit_file' example (verbatim)."""
    return {
        "proposal_schema": 1,
        "proposal_id": "c0ffee-edit-parse-config",
        "agent": {"name": "claude-code", "role": "coder"},
        "title": "Null-check parseConfig",
        "summary": "Avoids a crash on missing config.",
        "action": {
            "kind": "edit_file",
            "target": "src/config.py",
            "payload": {"old_text": "cfg.value",
                        "new_text": "(cfg.value if cfg else None)",
                        "max_replacements": 1},
        },
    }


def _valid_command(label="python -m unittest discover -s tests -t ."):
    """The docs/fable/06 'Valid run_command' example (verbatim by default)."""
    return {
        "proposal_schema": 1,
        "proposal_id": "c0ffee-run-tests",
        "agent": {"name": "codex", "role": "reviewer"},
        "title": "Run the test suite",
        "summary": "Verify the change before approval.",
        "action": {"kind": "run_command", "command_label": label},
    }


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _validate(self, data):
        return wp.validate_proposal(data, project_root=self.root, policy=self.policy)

    def assertInvalid(self, data, fragment):
        v = self._validate(data)
        self.assertFalse(v.ok)
        self.assertIsNone(v.proposal)
        joined = " || ".join(v.errors)
        self.assertIn(fragment, joined,
                      f"expected {fragment!r} in errors, got: {joined}")
        return v


class TestValidProposals(_Base):
    def test_valid_write_file_proposal(self):
        v = self._validate(_valid_write())
        self.assertTrue(v.ok, v.errors)
        self.assertEqual(v.errors, [])
        p = v.proposal
        self.assertEqual(p.proposal_id, "c0ffee-write-readme-note")
        self.assertEqual(p.agent.name, "fable")
        self.assertEqual(p.action.kind, "write_file")
        self.assertEqual(p.action.target, "docs/example.md")
        self.assertFalse(p.action.payload["overwrite"])

    def test_valid_edit_file_proposal(self):
        v = self._validate(_valid_edit())
        self.assertTrue(v.ok, v.errors)
        self.assertEqual(v.proposal.action.payload["max_replacements"], 1)

    def test_edit_file_max_replacements_defaults_to_1(self):
        data = _valid_edit()
        del data["action"]["payload"]["max_replacements"]
        v = self._validate(data)
        self.assertTrue(v.ok, v.errors)
        self.assertEqual(v.proposal.action.payload["max_replacements"], 1)

    def test_valid_run_command_proposal(self):
        v = self._validate(_valid_command())
        self.assertTrue(v.ok, v.errors)
        self.assertEqual(v.proposal.action.command_label,
                         "python -m unittest discover -s tests -t .")
        self.assertEqual(v.proposal.action.target, "")

    def test_optional_role_session_scope_accepted(self):
        data = _valid_write()
        data["agent"]["session"] = "session-42"
        data["agent"]["role"] = "a custom free-text role"  # lenient, not an enum
        data["action"]["scope"] = {"files_changed": 1, "lines_changed": 8}
        v = self._validate(data)
        self.assertTrue(v.ok, v.errors)
        self.assertEqual(v.proposal.agent.session, "session-42")
        self.assertEqual(v.proposal.action.scope, {"files_changed": 1, "lines_changed": 8})

    def test_every_resolver_allowlist_label_validates(self):
        # Locks the schema side of the two-gate agreement: every resolver label is
        # proposable — and validating it executes nothing.
        for spec in wc.list_command_allowlist():
            v = self._validate(_valid_command(spec.label))
            self.assertTrue(v.ok, f"{spec.label!r}: {v.errors}")

    def test_summarize_validation_shapes(self):
        ok = self._validate(_valid_write())
        self.assertIn("[valid]", wp.summarize_validation(ok))
        bad = self._validate({"nope": 1})
        s = wp.summarize_validation(bad)
        self.assertIn("[invalid]", s)
        self.assertIn("error(s)", s)
        with self.assertRaises(wp.ProposalError):
            wp.summarize_validation(None)


class TestEnvelopeRejections(_Base):
    def test_rejects_non_dict_input(self):
        for bad in (None, [], "x", 42):
            v = wp.validate_proposal(bad, project_root=self.root, policy=self.policy)
            self.assertFalse(v.ok)
            self.assertIn("must be a JSON object", v.errors[0])

    def test_rejects_malformed_json(self):
        data, err = wp.parse_proposal_json("{not json")
        self.assertIsNone(data)
        self.assertIn("malformed JSON", err)

    def test_rejects_non_object_json(self):
        for text in ("[1,2]", '"str"', "42"):
            data, err = wp.parse_proposal_json(text)
            self.assertIsNone(data)
            self.assertIn("single object", err)
        data, err = wp.parse_proposal_json("")
        self.assertIsNone(data)

    def test_parse_valid_json_object(self):
        data, err = wp.parse_proposal_json('{"a": 1}')
        self.assertIsNone(err)
        self.assertEqual(data, {"a": 1})

    def test_rejects_unknown_schema_version(self):
        for version in (0, 2, "1", None, True):
            self.assertInvalid(_valid_write(proposal_schema=version),
                               "proposal_schema")

    def test_rejects_missing_or_bad_proposal_id(self):
        data = _valid_write()
        del data["proposal_id"]
        self.assertInvalid(data, "proposal_id")
        self.assertInvalid(_valid_write(proposal_id=""), "proposal_id")
        self.assertInvalid(_valid_write(proposal_id="x" * 121), "120")
        for bad in ("has space", "path/sep", "dot../dot", "uniçode", "a\\b"):
            self.assertInvalid(_valid_write(proposal_id=bad), "[A-Za-z0-9._-]")

    def test_rejects_missing_agent_name(self):
        data = _valid_write()
        del data["agent"]
        self.assertInvalid(data, "'agent' is required")
        self.assertInvalid(_valid_write(agent={"role": "coder"}), "agent.name")
        self.assertInvalid(_valid_write(agent={"name": ""}), "agent.name")
        self.assertInvalid(_valid_write(agent="fable"), "must be an object")

    def test_rejects_missing_title_or_summary(self):
        for key in ("title", "summary"):
            data = _valid_write()
            del data[key]
            self.assertInvalid(data, f"'{key}'")
            self.assertInvalid(_valid_write(**{key: "   "}), f"'{key}'")

    def test_rejects_unknown_top_level_key(self):
        self.assertInvalid(_valid_write(extra_field="x"), "unknown key 'extra_field'")

    def test_rejects_unknown_agent_and_scope_keys(self):
        data = _valid_write()
        data["agent"]["api_key"] = "nope"
        self.assertInvalid(data, "unknown key 'api_key'")
        data = _valid_write()
        data["action"]["scope"] = {"files_changed": 1, "surprise": 2}
        self.assertInvalid(data, "unknown key 'surprise'")

    def test_rejects_bad_scope_values(self):
        for bad in (-1, "3", True, None):
            data = _valid_write()
            data["action"]["scope"] = {"files_changed": bad}
            self.assertInvalid(data, "non-negative integer")


class TestActionRejections(_Base):
    def test_rejects_cloud_call_kind(self):
        data = _valid_write()
        data["action"] = {"kind": "cloud_call", "target": "anthropic"}
        self.assertInvalid(data, "action.kind")

    def test_rejects_read_file_and_unknown_kinds(self):
        for kind in ("read_file", "unknown", "delete_file", "", None, 3):
            data = _valid_write()
            data["action"] = {"kind": kind, "target": "docs/x.md",
                              "payload": {"content": "x"}}
            self.assertInvalid(data, "action.kind")

    def test_rejects_freeform_command(self):
        # The docs/fable/06 rejected example (verbatim label).
        v = self.assertInvalid(_valid_command("rm -rf / ; git push --force"),
                               "not an exact allowlisted command label")
        self.assertIsNone(v.proposal)

    def test_rejects_case_mutated_and_non_allowlisted_commands(self):
        for label in ("GIT STATUS --SHORT", "git status", "git push",
                      "git status --short extra", "vibe lint"):
            self.assertInvalid(_valid_command(label), "command label")

    def test_whitespace_normalized_label_accepted(self):
        # Whitespace collapse only — mirrors the resolver's normalization.
        v = self._validate(_valid_command("git   status    --short"))
        self.assertTrue(v.ok, v.errors)
        self.assertEqual(v.proposal.action.command_label, "git status --short")

    def test_rejects_run_command_with_payload_or_target(self):
        data = _valid_command()
        data["action"]["payload"] = {"content": "x"}
        self.assertInvalid(data, "never carries a payload")
        data = _valid_command()
        data["action"]["target"] = "docs/x.md"
        self.assertInvalid(data, "'target' is not valid")

    def test_rejects_command_label_on_file_action(self):
        data = _valid_write()
        data["action"]["command_label"] = "git status --short"
        self.assertInvalid(data, "only valid for run_command")

    def test_rejects_missing_command_label(self):
        data = _valid_command()
        del data["action"]["command_label"]
        self.assertInvalid(data, "command_label is required")


class TestPathRejections(_Base):
    def _with_target(self, target):
        data = _valid_write()
        data["action"]["target"] = target
        return data

    def test_rejects_posix_absolute_path(self):
        self.assertInvalid(self._with_target("/etc/passwd"), "relative path")

    def test_rejects_windows_absolute_path_even_on_posix(self):
        for target in ("C:\\Windows\\system32\\x.md", "c:/temp/x.md",
                       "\\\\server\\share\\x.md", "\\x.md"):
            self.assertInvalid(self._with_target(target), "relative path")

    def test_rejects_traversal(self):
        for target in ("..", "../x.md", "docs/../../x.md", "docs\\..\\..\\x.md"):
            self.assertInvalid(self._with_target(target), "traversal")

    def test_rejects_denylisted_targets(self):
        for target in (".env", ".council/x.json", ".git/config", "id_rsa",
                       "docs/plans/commercialization-and-hosted-platform-feasibility.md"):
            self.assertInvalid(self._with_target(target), "not permitted")

    def test_rejects_missing_target(self):
        data = _valid_write()
        del data["action"]["target"]
        self.assertInvalid(data, "action.target is required")


class TestSmuggledFieldRejections(_Base):
    def test_rejects_smuggled_payload_hash_and_status(self):
        # The docs/fable/06 rejected example (verbatim shape).
        data = {
            "proposal_schema": 1,
            "proposal_id": "bad-smuggle",
            "agent": {"name": "x"},
            "title": "t", "summary": "s",
            "action": {"kind": "write_file", "target": "docs/x.md",
                       "payload": {"content": "hi"},
                       "payload_hash": "sha256:deadbeef", "status": "approved"},
        }
        v = self._validate(data)
        self.assertFalse(v.ok)
        joined = " ".join(v.errors)
        self.assertIn("payload_hash", joined)
        self.assertIn("status", joined)
        self.assertIn("server-minted", joined)

    def test_rejects_all_forbidden_fields_at_every_level(self):
        for key in ("payload_hash", "action_id", "approval_id", "task_id",
                    "audit_id", "decision_id", "status", "risk", "risk_level",
                    "verdict", "blocked", "findings", "argv", "env", "cwd",
                    "timeout", "timeout_seconds", "shell", "command",
                    "requested_action"):
            for level in ("top", "agent", "action", "payload"):
                data = _valid_write()
                if level == "top":
                    data[key] = "x"
                elif level == "agent":
                    data["agent"][key] = "x"
                elif level == "action":
                    data["action"][key] = "x"
                else:
                    data["action"]["payload"][key] = "x"
                v = self._validate(data)
                self.assertFalse(v.ok, f"{key} at {level} was not rejected")
                self.assertIn(key, " ".join(v.errors))

    def test_rejects_argv_env_cwd_timeout_shell_on_command(self):
        for key, val in (("argv", ["git", "push"]), ("env", {"X": "1"}),
                         ("cwd", "/"), ("timeout", 9999), ("shell", True)):
            data = _valid_command()
            data["action"][key] = val
            self.assertInvalid(data, key)

    def test_rejects_internal_requested_action_convention(self):
        self.assertInvalid(_valid_write(requested_action="write_file:docs/x.md"),
                           "requested_action")


class TestPayloadShapeRejections(_Base):
    def test_write_file_requires_string_content(self):
        for bad in (None, 42, ["x"], {"t": 1}):
            data = _valid_write()
            data["action"]["payload"] = {"content": bad}
            self.assertInvalid(data, "string 'content'")
        data = _valid_write()
        del data["action"]["payload"]["content"]
        self.assertInvalid(data, "string 'content'")

    def test_write_file_payload_must_be_dict(self):
        data = _valid_write()
        data["action"]["payload"] = "just text"
        self.assertInvalid(data, "'payload' object")
        data = _valid_write()
        del data["action"]["payload"]
        self.assertInvalid(data, "'payload' object")

    def test_write_file_overwrite_must_be_bool(self):
        data = _valid_write()
        data["action"]["payload"]["overwrite"] = "yes"
        self.assertInvalid(data, "overwrite")

    def test_write_file_unknown_payload_key_rejected(self):
        data = _valid_write()
        data["action"]["payload"]["mode"] = "755"
        self.assertInvalid(data, "unknown key 'mode'")

    def test_edit_file_requires_nonempty_old_text(self):
        data = _valid_edit()
        data["action"]["payload"]["old_text"] = ""
        self.assertInvalid(data, "old_text")
        data = _valid_edit()
        del data["action"]["payload"]["old_text"]
        self.assertInvalid(data, "old_text")

    def test_edit_file_requires_string_new_text(self):
        data = _valid_edit()
        data["action"]["payload"]["new_text"] = 5
        self.assertInvalid(data, "new_text")

    def test_bad_max_replacements_rejected(self):
        for bad in (0, -1, "2", True, 1.5):
            data = _valid_edit()
            data["action"]["payload"]["max_replacements"] = bad
            self.assertInvalid(data, "max_replacements")

    def test_nul_bytes_rejected(self):
        data = _valid_write()
        data["action"]["payload"]["content"] = "a\x00b"
        self.assertInvalid(data, "NUL")
        data = _valid_edit()
        data["action"]["payload"]["new_text"] = "a\x00b"
        self.assertInvalid(data, "NUL")
        data = _valid_edit()
        data["action"]["payload"]["old_text"] = "a\x00b"
        self.assertInvalid(data, "NUL")

    def test_oversized_content_rejected(self):
        data = _valid_write()
        data["action"]["payload"]["content"] = "x" * (wp.MAX_CONTENT_BYTES + 1)
        self.assertInvalid(data, "exceeds")
        data = _valid_edit()
        data["action"]["payload"]["new_text"] = "y" * (wp.MAX_EDIT_TEXT_BYTES + 1)
        self.assertInvalid(data, "exceeds")


class TestExecutorContractAgreement(unittest.TestCase):
    """Drift guards: the proposal layer's local caps/kinds are deliberately defined
    without importing the executor (module purity) — these tests import the executor
    HERE and lock the agreement, so a future bound change can't silently drift."""

    def test_size_caps_match_executor_bounds(self):
        from backend import workbench_executor as we
        self.assertEqual(wp.MAX_CONTENT_BYTES, we.MAX_WRITE_BYTES)
        self.assertEqual(wp.MAX_EDIT_TEXT_BYTES, we.MAX_EDIT_BYTES)

    def test_proposal_kinds_are_a_subset_of_executor_real_exec_kinds(self):
        from backend import workbench_executor as we
        for kind in wp.ALLOWED_PROPOSAL_KINDS:
            self.assertIn(kind, we.REAL_EXEC_KINDS)
            self.assertIn(kind, we.SUPPORTED_KINDS)


class TestNoExecutionGuarantees(_Base):
    def test_module_never_imports_subprocess(self):
        # Validation must never be able to run anything, even by accident.
        self.assertNotIn("subprocess", getattr(wp, "__dict__", {}))

    def test_validation_writes_nothing(self):
        # Valid and invalid proposals (including run_command) leave the project
        # root byte-for-byte empty: no files, no .council/, no runtime store.
        self._validate(_valid_write())
        self._validate(_valid_edit())
        self._validate(_valid_command())
        self._validate(_valid_command("rm -rf /"))
        self._validate({"proposal_schema": 1})
        self.assertEqual(os.listdir(self.root), [])
        self.assertFalse((self.root / ".council").exists())

    def test_collects_all_errors_not_just_first(self):
        data = {"proposal_schema": 99, "proposal_id": "has space",
                "agent": {}, "action": {"kind": "cloud_call"}}
        v = self._validate(data)
        self.assertFalse(v.ok)
        self.assertGreaterEqual(len(v.errors), 4)  # version, id, title, summary,
        #                                            agent.name, kind — one pass

    def test_error_messages_never_echo_payload_content(self):
        secret = "DISTINCTIVE-SECRET-CONTENT-9x7q"
        data = _valid_write()
        data["action"]["payload"]["content"] = secret + "\x00"  # invalid via NUL
        v = self._validate(data)
        self.assertFalse(v.ok)
        self.assertNotIn(secret, " ".join(v.errors))
        self.assertNotIn(secret, wp.summarize_validation(v))


if __name__ == "__main__":
    unittest.main()
