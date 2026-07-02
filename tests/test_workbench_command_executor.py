"""Tests for real `run_command` execution (backend/workbench_executor.py, PR #80).

Stdlib-only (`unittest`). Real execution exists ONLY for resolver-allowlisted (PR #79)
command labels, behind the full invariant + a fresh deterministic trust re-check —
exactly the same gate the dry-run preview already uses. `subprocess.run` is
monkeypatched for most tests (asserts argv/cwd/env/timeout/capture_output/text/shell);
one smoke test runs a real, harmless, cross-platform command (`git status --short`) to
prove the wiring actually works end-to-end. Temp dirs only; no real-repo
`.council/runtime/` artifacts. No provider/model/network calls.
"""

import subprocess
import unittest
import tempfile
from pathlib import Path

from backend import workbench_executor as we
from backend import workbench_runtime as wr
from backend import workbench_trust as wt

FIXED = "2026-07-02T00:00:00Z"


def _setup(root, kind="run_command", target="git status --short", appr_status="approve",
          act_status="pending"):
    task = wr.new_task("T", on=FIXED)
    wr.save_task(task, root)
    ap = wr.create_approval(task.id, title="x", requested_action=f"{kind}:{target}",
                            risk_level="medium", project_root=root, on=FIXED)
    if appr_status != "pending":
        wr.record_approval_decision(ap.id, appr_status, project_root=root, on=FIXED)
    act = wr.new_action(task.id, kind, command_or_path=target, approval_id=ap.id, on=FIXED)
    act.status = act_status
    wr.save_action(act, root)
    t = wr.load_task(task.id, root)
    t.action_ids.append(act.id)
    wr.save_task(t, root)
    return task, ap, act


class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Recorder:
    """Monkeypatch target for `subprocess.run` — records the call and returns a
    canned result (or raises), never actually spawning a process."""

    def __init__(self, result=None, exc=None):
        self.result = result if result is not None else _FakeCompleted()
        self.exc = exc
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.result


class _PatchSubprocess:
    def __init__(self, recorder: _Recorder):
        self.recorder = recorder
        self._orig = None

    def __enter__(self):
        self._orig = subprocess.run
        subprocess.run = self.recorder
        return self.recorder

    def __exit__(self, *exc):
        subprocess.run = self._orig


class TestMonkeypatchedRealExecution(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _exec(self, action_id):
        return we.execute_action(action_id, project_root=self.root, policy=self.policy,
                                 dry_run=False)

    def test_valid_allowlisted_command_executes_with_fixed_argv_shell_false(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0, stdout="clean\n", stderr=""))
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertEqual(len(rec.calls), 1)
        args, kwargs = rec.calls[0]
        self.assertEqual(args[0], ["git", "status", "--short"])
        self.assertFalse(kwargs["shell"])
        self.assertTrue(r.executed)
        self.assertEqual(wr.load_action(act.id, self.root).status, "completed")

    def test_subprocess_receives_resolver_argv_not_parsed_action_string(self):
        _t, _ap, act = _setup(self.root, target="vibe lint --redaction")
        rec = _Recorder(_FakeCompleted(returncode=0))
        with _PatchSubprocess(rec):
            self._exec(act.id)
        args, _kwargs = rec.calls[0]
        # never the raw action string, never shlex-split — the resolver's fixed argv
        self.assertNotEqual(args[0], "vibe lint --redaction")
        self.assertEqual(args[0][1:3], ["-m", "backend.cli"])

    def test_cwd_is_project_root(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0))
        with _PatchSubprocess(rec):
            self._exec(act.id)
        _args, kwargs = rec.calls[0]
        self.assertEqual(kwargs["cwd"], str(self.root))

    def test_env_is_sanitized_and_excludes_fake_api_key(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0))
        import os
        os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-should-never-appear-in-subprocess-env"
        try:
            with _PatchSubprocess(rec):
                self._exec(act.id)
        finally:
            del os.environ["OPENROUTER_API_KEY"]
        _args, kwargs = rec.calls[0]
        env = kwargs["env"]
        self.assertNotIn("OPENROUTER_API_KEY", env)
        self.assertNotIn("sk-or-v1-should-never-appear-in-subprocess-env", str(env))

    def test_timeout_and_capture_settings_passed_through(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0))
        with _PatchSubprocess(rec):
            self._exec(act.id)
        _args, kwargs = rec.calls[0]
        self.assertGreater(kwargs["timeout"], 0)
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(kwargs["text"])

    def test_exit_zero_marks_completed(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0, stdout="ok\n"))
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.executed)
        self.assertEqual(r.exit_code, 0)
        self.assertEqual(wr.load_action(act.id, self.root).status, "completed")

    def test_nonzero_exit_marks_failed(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=1, stdout="", stderr="boom"))
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.executed)  # it ran to completion, just reported failure
        self.assertEqual(r.exit_code, 1)
        self.assertEqual(wr.load_action(act.id, self.root).status, "failed")

    def test_timeout_marks_failed_no_retry(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(exc=subprocess.TimeoutExpired(cmd=["git"], timeout=60))
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertFalse(r.executed)
        self.assertTrue(r.timed_out)
        self.assertEqual(wr.load_action(act.id, self.root).status, "failed")
        self.assertEqual(len(rec.calls), 1)  # no retry

    def test_output_is_captured_and_bounded(self):
        _t, _ap, act = _setup(self.root)
        big = "x" * 200_000
        rec = _Recorder(_FakeCompleted(returncode=0, stdout=big))
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.output_truncated)
        self.assertLess(len(r.stdout_summary.encode("utf-8")), 100_000)

    def test_output_not_truncated_when_small(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0, stdout="tiny"))
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertFalse(r.output_truncated)
        self.assertEqual(r.stdout_summary, "tiny")

    def test_result_summary_stored_safely_no_giant_blob(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0, stdout="x" * 100_000))
        with _PatchSubprocess(rec):
            self._exec(act.id)
        stored = wr.load_action(act.id, self.root).result_summary
        self.assertLessEqual(len(stored), 2000)
        self.assertIn("git status --short", stored)

    def test_critical_secret_in_output_blocks_not_stores(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(
            returncode=0, stdout="sk-or-v1-abcdefghijklmnopqrstuvwxyz0123456789\n"))
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertFalse(r.executed)
        stored = wr.load_action(act.id, self.root).result_summary
        self.assertNotIn("sk-or-v1", stored)
        self.assertEqual(wr.load_action(act.id, self.root).status, "blocked")

    def test_dry_run_still_never_calls_subprocess(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0))
        with _PatchSubprocess(rec):
            r = we.execute_action(act.id, project_root=self.root, policy=self.policy,
                                  dry_run=True)
        self.assertEqual(len(rec.calls), 0)
        self.assertTrue(r.would_execute)
        self.assertFalse(r.executed)

    # --- invariant / fail-closed cases (no subprocess.run call at all) -------- #

    def test_unapproved_approval_blocks_no_subprocess_call(self):
        _t, _ap, act = _setup(self.root, appr_status="pending")
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_rejected_approval_blocks(self):
        _t, _ap, act = _setup(self.root, appr_status="reject")
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_held_approval_blocks(self):
        _t, _ap, act = _setup(self.root, appr_status="hold")
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_non_pending_action_blocks(self):
        _t, _ap, act = _setup(self.root, act_status="completed")
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_action_approval_mismatch_blocks(self):
        _t, ap, act = _setup(self.root)
        other = wr.create_approval(_t.id, title="y", requested_action="run_command:git status --short",
                                   risk_level="medium", project_root=self.root, on=FIXED)
        act.approval_id = other.id
        wr.save_action(act, self.root)
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_trust_blocked_command_blocks(self):
        _t, _ap, act = _setup(self.root, target="git status --short && rm -rf /")
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_resolver_known_but_trust_blocked_blocks(self):
        policy = wt.TrustPolicy(project_root=str(self.root), allowed_read_roots=[str(self.root)],
                                allowed_write_roots=[str(self.root)], allowed_commands=())
        _t, _ap, act = _setup(self.root)
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = we.execute_action(act.id, project_root=self.root, policy=policy, dry_run=False)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_trust_allowed_but_resolver_unknown_blocks(self):
        # "git diff --stat" is trust-allowlisted but not on the (smaller) resolver
        # allowlist -> blocked, no subprocess call.
        _t, _ap, act = _setup(self.root, target="git diff --stat")
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_unknown_command_blocks(self):
        _t, _ap, act = _setup(self.root, target="curl http://example.com")
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_extra_arg_blocks(self):
        _t, _ap, act = _setup(self.root, target="git status --short --extra")
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_shell_metachar_blocks(self):
        _t, _ap, act = _setup(self.root, target="git status --short; echo hi")
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = self._exec(act.id)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)

    def test_denied_cwd_segment_blocks(self):
        # A self-consistent fixture entirely under a denied-segment root (the only way
        # cwd can ever be denied — cwd is always project_root, never derived from the
        # action). Belt-and-suspenders: trust/resolver don't key off project_root for
        # run_command, so this exercises the executor's own _cwd_is_safe guard.
        denied_root = self.root / ".council" / "sub"
        denied_root.mkdir(parents=True)
        _t, _ap, act = _setup(denied_root)
        rec = _Recorder()
        with _PatchSubprocess(rec):
            r = we.execute_action(act.id, project_root=denied_root, policy=None, dry_run=False)
        self.assertTrue(r.blocked)
        self.assertEqual(len(rec.calls), 0)


class TestNoDynamicArgsNoShellParsing(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_shell_true_never_used(self):
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0))
        with _PatchSubprocess(rec):
            we.execute_action(act.id, project_root=self.root, policy=self.policy,
                              dry_run=False)
        self.assertFalse(rec.calls[0][1]["shell"])

    def test_no_shlex_import_in_executor_module(self):
        import backend.workbench_executor as we_mod
        self.assertNotIn("shlex", getattr(we_mod, "__dict__", {}))

    def test_no_dynamic_args_argv_matches_resolver_exactly(self):
        from backend import workbench_commands as wc
        _t, _ap, act = _setup(self.root)
        rec = _Recorder(_FakeCompleted(returncode=0))
        with _PatchSubprocess(rec):
            we.execute_action(act.id, project_root=self.root, policy=self.policy,
                              dry_run=False)
        spec = wc.resolve_command_label("git status --short")
        self.assertEqual(rec.calls[0][0][0], list(spec.argv))


class TestNoNetworkPackageDeployInAllowlist(unittest.TestCase):
    def test_allowlist_has_no_network_package_deploy_git_push_commands(self):
        from backend import workbench_commands as wc
        forbidden = ("curl", "wget", "pip", "npm", "install", "push", "deploy", "docker")
        for spec in wc.list_command_allowlist():
            joined = " ".join(spec.argv).lower()
            for word in forbidden:
                self.assertNotIn(word, joined, f"{spec.label!r} argv contains {word!r}")


class TestFileExecutionUnaffected(unittest.TestCase):
    """Regression guard: write_file/edit_file real execution (PR #74/#76) must be
    unaffected by run_command real execution existing now."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_write_file_execution_still_works(self):
        task = wr.new_task("T", on=FIXED)
        wr.save_task(task, self.root)
        ap = wr.create_approval(task.id, title="x", requested_action="write_file:docs/x.md",
                                risk_level="medium", project_root=self.root, on=FIXED)
        wr.record_approval_decision(ap.id, "approve", project_root=self.root, on=FIXED)
        act = wr.new_action(task.id, "write_file", command_or_path="docs/x.md",
                            approval_id=ap.id, on=FIXED)
        wr.save_action(act, self.root)
        t = wr.load_task(task.id, self.root)
        t.action_ids.append(act.id)
        wr.save_task(t, self.root)

        r = we.execute_action(act.id, project_root=self.root, policy=self.policy,
                              dry_run=False, payload={"content": "hello\n"})
        self.assertTrue(r.executed)
        self.assertEqual((self.root / "docs" / "x.md").read_text(encoding="utf-8"), "hello\n")


class TestRealSubprocessSmoke(unittest.TestCase):
    """One real, harmless, cross-platform smoke test (git status --short, no
    monkeypatch) proving the wiring actually works end-to-end, not just in mocks."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.policy = wt.default_policy(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_real_git_status_short_runs_and_completes_or_fails_cleanly(self):
        _t, _ap, act = _setup(self.root)
        r = we.execute_action(act.id, project_root=self.root, policy=self.policy,
                              dry_run=False)
        # self.root is a fresh temp dir, not a git repo, so git exits non-zero; either
        # way the process must have actually run (executed=True) and left a safe,
        # bounded, non-raising result.
        self.assertTrue(r.executed)
        self.assertIsNotNone(r.exit_code)
        self.assertIn(wr.load_action(act.id, self.root).status, ("completed", "failed"))
        self.assertFalse(r.timed_out)


if __name__ == "__main__":
    unittest.main()
