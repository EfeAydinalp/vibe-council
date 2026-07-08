"""v0.9.0 PR 4 — isolation lock-in tests for the preference system (tests only).

These are **tripwires**, not behavior. They prove that preferences influence *exactly* the
allowed CLI surfaces (review/diff preset floor + usage warning, and the doctor's advisory
staged-path lines) and **nothing else**:

- the guard / executor / Workbench / trust / proposal / importer / panel modules, and the
  council **prompt / ranking / synthesis** path, are all **preference-blind** — proven both by
  a static allowlist-first import/reference scan (any new consumer fails the suite) and by a
  **behavioral byte-identity** check (trust evaluation + executor dry-run are identical with
  and without a maximal valid PREFERENCES.md block);
- `vibe guide` / `vibe context export` stay **pointer-only** (never inline the schema block,
  its values, or the application reader);
- `vibe project doctor` stays **advisory** (READY / exit code stable across valid / missing /
  invalid blocks);
- the context pack never ingests the schema and stays 21/21 with a block present;
- `effective_suggestions` never reads or creates a `.council/profile.*` store.

Stdlib-only. No model/API/network. Fail-closed: a preference reaching a forbidden surface is a
security finding to surface, not to allowlist.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path

from backend import cli
from backend import preferences
from backend import context_pack as cp
from backend import workbench_trust as wt
from backend import workbench_executor as we
from tests.test_workbench_executor import _setup

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"

# The ONLY production modules allowed to touch the preference application surface.
_ALLOWED_PREF_IMPORTERS = {"cli.py"}                       # import backend.preferences
_ALLOWED_EFFECTIVE_SUGGESTIONS = {"preferences.py", "cli.py"}   # defines / calls it

# Surfaces that MUST remain preference-blind. A preference reaching any of these is a
# trust/behavior leak — a security finding, not something to allowlist.
_FORBIDDEN_MODULES = (
    "workbench_trust.py", "workbench_executor.py", "workbench_orchestrator.py",
    "workbench_runtime.py", "workbench_panel.py", "workbench_payloads.py",
    "workbench_commands.py", "workbench_auditor.py", "workbench_proposals.py",
    "workbench_proposal_importer.py", "council.py", "openrouter.py", "providers.py",
    "guards.py", "mcp_contract.py", "mcp_server.py", "mcp_stdio.py", "context_pack.py",
)

# A maximal *valid* block: every key set, and its path lists deliberately name paths that a
# naive (wrongly preference-reading) trust/executor might act on.
_MAXIMAL_BLOCK = {
    "schema": 1,
    "default_review_preset": "full",
    "require_usage_flag": True,
    "extra_sensitive_paths": ["docs/", "src/"],
    "never_stage_extra": ["docs/foo.md"],
}

_IMPORT_RE = re.compile(
    r"(from\s+\.\s+import\s+[^\n]*\bpreferences\b"
    r"|from\s+\.preferences\s+import"
    r"|import\s+backend\.preferences"
    r"|from\s+backend\s+import\s+[^\n]*\bpreferences\b"
    r"|from\s+backend\.preferences\s+import)")


def _module_texts():
    return {p.name: p.read_text(encoding="utf-8") for p in BACKEND.glob("*.py")}


def _write_block(root, obj):
    d = root / "docs/context/project"
    d.mkdir(parents=True, exist_ok=True)
    (d / "PREFERENCES.md").write_text(
        f"# prefs\n\n```json\n{json.dumps(obj)}\n```\n", encoding="utf-8")


class TestStaticImportIsolation(unittest.TestCase):
    """Allowlist-first scans over every backend/*.py: preferences has exactly one consumer."""

    def test_preferences_importer_set_is_exactly_cli(self):
        importers = {name for name, text in _module_texts().items()
                     if name != "preferences.py" and _IMPORT_RE.search(text)}
        self.assertEqual(importers, _ALLOWED_PREF_IMPORTERS,
                         f"backend.preferences importer set must be exactly "
                         f"{_ALLOWED_PREF_IMPORTERS}; got {sorted(importers)}")

    def test_effective_suggestions_reference_set_is_exactly_allowed(self):
        # The application reader must be *referenced* only where it is defined (preferences.py)
        # and where it is legitimately called (cli.py) — nowhere else in production code.
        refs = {name for name, text in _module_texts().items()
                if "effective_suggestions" in text}
        self.assertEqual(refs, _ALLOWED_EFFECTIVE_SUGGESTIONS,
                         f"effective_suggestions may only appear in "
                         f"{_ALLOWED_EFFECTIVE_SUGGESTIONS}; got {sorted(refs)}")

    def test_forbidden_modules_do_not_touch_preferences(self):
        texts = _module_texts()
        for mod in _FORBIDDEN_MODULES:
            self.assertIn(mod, texts, f"expected module missing: {mod}")
            text = texts[mod]
            self.assertIsNone(_IMPORT_RE.search(text),
                              f"{mod} must not import backend.preferences")
            self.assertNotIn("effective_suggestions", text,
                             f"{mod} must not reference effective_suggestions")
            self.assertNotIn("validate_preferences", text,
                             f"{mod} must not reference the preference validator")

    def test_cli_is_the_one_legitimate_consumer(self):
        # sanity: the allowlist is not vacuous — cli.py really does import + call it.
        cli_text = (BACKEND / "cli.py").read_text(encoding="utf-8")
        self.assertTrue(_IMPORT_RE.search(cli_text))
        self.assertIn("effective_suggestions", cli_text)


class TestTrustExecutorPreferenceBlind(unittest.TestCase):
    """Behavioral byte-identity: the deterministic trust boundary and the dry-run executor
    produce identical results with and without a maximal valid PREFERENCES.md block."""

    ACTIONS = (
        ("read_file", "docs/foo.md", None),
        ("write_file", "docs/foo.md", None),     # named in never_stage_extra + extra_sensitive
        ("edit_file", "src/mod.py", None),        # under extra_sensitive_paths "src/"
        ("run_command", None, "git status --short"),
        ("run_command", None, "rm -rf /"),        # metachar/blocked
        ("cloud_call", "docs/foo.md", None),
    )

    def _trust_summ(self, root):
        out = []
        for kind, target, command in self.ACTIONS:
            ev = wt.evaluate_action_payload(kind, target=target, command=command,
                                            project_root=root)
            out.append((ev.blocked, ev.allowed, ev.requires_approval, ev.risk_level,
                        tuple(ev.findings), ev.normalized_kind, ev.normalized_target,
                        ev.reason, ev.cloud_egress_required, ev.cloud_egress_approved,
                        wt.summarize_evaluation(ev)))
        return out

    def test_trust_evaluation_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            before = self._trust_summ(root)          # no block
            _write_block(root, _MAXIMAL_BLOCK)
            after = self._trust_summ(root)           # maximal block present
            self.assertEqual(before, after,
                             "trust evaluation must be preference-blind (byte-identical)")

    def test_executor_dry_run_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _task, _ap, act = _setup(root, kind="write_file", target="docs/foo.md")
            policy = wt.default_policy(root)

            def summ():
                r = we.dry_run_action(act.id, project_root=root, policy=policy)
                return (r.dry_run, r.executed, r.would_execute, r.blocked, r.preview,
                        we.summarize_execution_result(r))

            before = summ()
            _write_block(root, _MAXIMAL_BLOCK)       # a block that names docs/foo.md
            after = summ()
            self.assertEqual(before, after,
                             "executor dry-run must be preference-blind (byte-identical)")


class TestGuideExportPointerOnly(unittest.TestCase):
    """Guide / context-export never inline the schema block, its values, or the reader."""

    _NEEDLES = ("effective_suggestions", "```json", "require_usage_flag",
                "extra_sensitive_paths", "never_stage_extra")

    def test_context_export_never_leaks_preference_application(self):
        for agent in ("claude", "codex", "fable"):
            text = cli.agent_context_export(agent, project_root=REPO)
            for needle in self._NEEDLES:
                self.assertNotIn(needle, text, f"{agent} export leaked: {needle!r}")

    def test_guide_never_leaks_preference_application(self):
        for topic in ("claude", "codex", "fable"):
            g = cli.topic_guide(topic)
            for needle in self._NEEDLES:
                self.assertNotIn(needle, g, f"{topic} guide leaked: {needle!r}")


class TestDoctorStaysAdvisory(unittest.TestCase):
    """The doctor's READY / exit-code semantics are byte-stable across preference states."""

    def _ready(self, block_text):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            for rel in cli.PROJECT_VAULT_FILES + cli.PROJECT_CORE_DOCS:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("# x\nplaceholder\n", encoding="utf-8")
            (root / "docs/context/project/PREFERENCES.md").write_text(block_text, encoding="utf-8")
            _lines, ok = cli.project_doctor_report(root)
            return ok

    def test_ready_unchanged_for_valid_missing_invalid(self):
        valid = "# p\n\n```json\n" + json.dumps(_MAXIMAL_BLOCK) + "\n```\n"
        missing = "# p\n\njust prose.\n"
        invalid = "# p\n\n```json\n{ \"schema\": 1, \"default_review_preset\": \"premium\" }\n```\n"
        # all three seed an otherwise-READY repo -> preferences never flip READY.
        self.assertTrue(self._ready(valid))
        self.assertTrue(self._ready(missing))
        self.assertTrue(self._ready(invalid))


class TestReaderTouchesOnlyPreferencesMd(unittest.TestCase):
    """The reader reads exactly one file and never a `.council/profile.*` store."""

    def test_never_reads_local_profile(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _write_block(root, {"schema": 1, "default_review_preset": "cheap"})  # no floor
            (root / ".council").mkdir()
            (root / ".council" / "profile.json").write_text(
                '{"default_review_preset": "full", "x": "LEAK_ME"}\n', encoding="utf-8")
            s = preferences.effective_suggestions(root)
            # the local profile is never consulted: the committed block (cheap) yields no floor,
            # and nothing from the profile leaks in.
            self.assertIsNone(s.review_preset_floor)

    def test_writes_nothing_and_creates_no_council(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _write_block(root, _MAXIMAL_BLOCK)
            before = sorted(p.relative_to(root).as_posix()
                            for p in root.rglob("*") if p.is_file())
            preferences.effective_suggestions(root)
            after = sorted(p.relative_to(root).as_posix()
                           for p in root.rglob("*") if p.is_file())
            self.assertEqual(before, after)
            self.assertFalse((root / ".council").exists())


class TestContextPackUnaffected(unittest.TestCase):
    """The pack (STATUS + decisions) never ingests the schema and stays 21/21 with a block
    present (the real repo already carries a committed PREFERENCES.md block)."""

    def test_pack_stays_21_21_and_ingests_no_schema(self):
        ddir = REPO / "docs" / "decisions"
        status = REPO / "docs" / "context" / "project" / "STATUS.md"
        res = cp.build_pack(ddir, status, on="2026-07-04T00:00:00Z")
        report = cp.check_pack(res.text)
        self.assertTrue(report.ok, report.reasons)
        self.assertEqual(report.passed, report.total, report.reasons)
        for needle in ("effective_suggestions", "require_usage_flag", "extra_sensitive_paths"):
            self.assertNotIn(needle, res.text, f"pack ingested schema token: {needle!r}")


if __name__ == "__main__":
    unittest.main()
