"""Tests for the project vault scaffold (docs/context/project/*.md, v0.6.2).

Stdlib-only (`unittest`). These assert the committed vault files exist, are curated and
public-safe (frame `/council` as a future idea, carry no-stage/never-store guidance), and
that the context pack — which is a *budgeted projection* built only from STATUS.md +
decisions, not the whole vault — never leaks a private plan filename. No model/API/network.
"""

import json
import re
import unittest
from pathlib import Path

from backend import context_pack as cp

REPO = Path(__file__).resolve().parents[1]
VAULT = REPO / "docs" / "context" / "project"

VAULT_FILES = ("README.md", "STATUS.md", "ROADMAP.md", "DECISIONS.md", "PROGRESS.md",
               "RISKS.md", "WORKFLOWS.md", "NOTES.md",
               # v0.7 PR A — project profile/preferences scaffold (documentation only).
               "PROFILE.md", "PREFERENCES.md", "AGENT-ROLES.md",
               # v0.8.1 PR 5 — capped release-history index (docs only).
               "RELEASES.md")

# The v0.7 personalization scaffold files (public-safe, committed, read-as-documentation).
PROFILE_FILES = ("PROFILE.md", "PREFERENCES.md", "AGENT-ROLES.md")

PRIVATE_PLAN_NAMES = (
    "commercialization-and-hosted-platform-feasibility.md",
    "v0.3.1-hardening-and-dogfood.md",
)


def _read(name: str) -> str:
    return (VAULT / name).read_text(encoding="utf-8")


class TestVaultFilesExist(unittest.TestCase):
    def test_all_vault_files_exist(self):
        for name in VAULT_FILES:
            self.assertTrue((VAULT / name).is_file(), f"missing vault file: {name}")

    def test_vault_files_are_nonempty_markdown(self):
        for name in VAULT_FILES:
            text = _read(name)
            self.assertGreater(len(text.strip()), 0, name)
            self.assertTrue(text.lstrip().startswith("#"), f"{name} should start with a heading")

    def test_vault_file_set_is_deterministic(self):
        # The committed *.md set under the vault root is exactly the scaffold (stable,
        # explicit — no stray/generated files committed here).
        md = {p.name for p in VAULT.glob("*.md")}
        self.assertEqual(md, set(VAULT_FILES))


class TestVaultContentGuardrails(unittest.TestCase):
    def test_readme_explains_purpose_and_read_before_coding(self):
        r = _read("README.md")
        self.assertIn("project vault", r.lower())
        self.assertIn("read this vault before", r.lower())
        # never-store guidance
        self.assertIn("Never store", r)
        self.assertIn("secrets", r)

    def test_council_is_framed_as_future_not_real(self):
        # Any vault file mentioning /council must frame it as NOT a real command today.
        for name in ("ROADMAP.md", "RISKS.md"):
            t = _read(name)
            if "/council" in t:
                self.assertTrue(
                    ("does **not** exist" in t) or ("does not exist" in t)
                    or ("not a real" in t.lower()) or ("future" in t.lower()),
                    f"{name} mentions /council without framing it as future/not-real")
        # the real CLI is vibe
        self.assertIn("vibe", _read("WORKFLOWS.md"))

    def test_never_store_warnings_present(self):
        # The vault as a whole carries no-stage / never-store guidance.
        risks = _read("RISKS.md")
        workflows = _read("WORKFLOWS.md")
        self.assertIn(".council/", workflows)
        self.assertIn("No-stage checklist", workflows)
        self.assertIn("secrets", risks)
        self.assertIn("never", risks.lower())

    def test_decisions_is_index_not_canonical_store(self):
        d = _read("DECISIONS.md")
        self.assertIn("docs/decisions/", d)               # points at the canonical store
        self.assertIn("index", d.lower())
        # explicitly states it is not the canonical store
        self.assertIn("canonical store", d.lower())
        self.assertIn("not", d.lower().split("canonical store")[0][-40:])

    def test_decisions_records_key_high_level_decisions(self):
        d = _read("DECISIONS.md").lower()
        self.assertIn("approval is separate from execution", d)
        self.assertIn("local-first", d)
        self.assertIn("fable", d)                          # architect/lead policy
        self.assertIn("project-vault root", d)


class TestProfilePreferencesScaffold(unittest.TestCase):
    """v0.7 PR A — the PROFILE/PREFERENCES/AGENT-ROLES scaffold (documentation only)."""

    def test_scaffold_files_exist_and_are_markdown(self):
        for name in PROFILE_FILES:
            p = VAULT / name
            self.assertTrue(p.is_file(), f"missing scaffold file: {name}")
            text = _read(name)
            self.assertGreater(len(text.strip()), 0, name)
            self.assertTrue(text.lstrip().startswith("#"), f"{name} should start with a heading")

    def test_readme_lists_the_scaffold_files(self):
        r = _read("README.md")
        for name in PROFILE_FILES:
            self.assertIn(name, r, f"vault README does not list {name}")

    def test_each_scaffold_file_has_safe_to_commit_and_never_store_boundary(self):
        for name in PROFILE_FILES:
            t = _read(name).lower()
            self.assertIn("safe to commit", t, f"{name} missing safe-to-commit boundary")
            # never-store list mentions the core forbidden categories
            self.assertIn("never", t, f"{name} missing never-store guidance")
            self.assertIn("secret", t, f"{name} should name secrets in never-store list")
            self.assertIn(".council/runtime", t, f"{name} should name runtime payloads/artifacts")

    def test_each_scaffold_file_states_tighten_only_principle(self):
        for name in PROFILE_FILES:
            t = _read(name).lower()
            self.assertIn("tighten", t, f"{name} missing tighten-only principle")
            self.assertIn("never loosen", t, f"{name} should say it never loosens safety/security")

    def test_preferences_states_review_and_fable_policy(self):
        t = _read("PREFERENCES.md").lower()
        for token in ("cheap", "balanced", "full"):
            self.assertIn(token, t, f"PREFERENCES.md missing review preset '{token}'")
        self.assertIn("fable", t)                 # Fable usage policy
        self.assertIn("small", t)                 # small scoped PRs

    def test_agent_roles_states_model_header_convention(self):
        t = _read("AGENT-ROLES.md")
        self.assertIn("MODEL: OPUS/SONNET CODE", t)
        self.assertIn("MODEL: FABLE CODE", t)

    def test_scaffold_never_frames_council_as_a_real_command(self):
        # /council must be framed as a future idea, never a real CLI command.
        for name in PROFILE_FILES:
            t = _read(name)
            if "/council" in t:
                self.assertTrue(
                    ("does **not** exist" in t) or ("does not exist" in t)
                    or ("not a real" in t.lower()) or ("future" in t.lower()),
                    f"{name} mentions /council without framing it as future/not-real")

    def test_no_root_agents_md_created_by_this_scaffold(self):
        # PR A deliberately uses a vault AGENT-ROLES.md, NOT a root AGENTS.md (corruption risk).
        self.assertFalse((REPO / "AGENTS.md").exists(),
                         "root AGENTS.md must not be created by the profile scaffold")


class TestVaultInvariantConsistency(unittest.TestCase):
    """v0.7.1 PR 3 — pin that the vault files agree on the shared v0.7/v0.7.1
    invariants. Simple, robust text checks (no semantic parser): each file must carry
    ITS canonical part of the shared rule set, and the cross-file overlaps must hold."""

    def test_scaffold_files_state_tighten_only_and_safe_to_commit(self):
        # The three personalization files each state tighten-only + a safe-to-commit
        # boundary and each point at the vault AGENT-ROLES.md convention.
        for name in PROFILE_FILES:
            t = _read(name)
            low = t.lower()
            self.assertIn("tighten", low, f"{name}: missing tighten-only principle")
            self.assertIn("never loosen", low, f"{name}: missing never-loosen wording")
            self.assertIn("safe to commit", low, f"{name}: missing safe-to-commit boundary")
            self.assertIn("AGENT-ROLES.md", t, f"{name}: missing AGENT-ROLES.md reference")

    def test_all_vault_files_reference_agent_roles_convention(self):
        # Every core vault file references AGENT-ROLES.md (the canonical role-preference
        # source) so the root-AGENTS.md-is-not-canonical rule is discoverable everywhere.
        for name in ("README.md", "STATUS.md", "WORKFLOWS.md", "RISKS.md") + PROFILE_FILES:
            self.assertIn("AGENT-ROLES.md", _read(name),
                          f"{name} does not reference the AGENT-ROLES.md convention")

    def test_agent_roles_states_root_agents_not_preference_source(self):
        t = _read("AGENT-ROLES.md")
        low = t.lower()
        self.assertTrue("not the canonical preference source" in low
                        or "not a preference source" in low
                        or "guide-output target" in low,
                        "AGENT-ROLES.md must state root AGENTS.md is not the preference source")

    def test_readme_states_markdown_source_of_truth(self):
        r = _read("README.md")
        self.assertIn("Markdown", r)
        self.assertIn("canonical", r.lower())

    def test_workflows_is_canonical_no_stage_and_names_local_profile(self):
        w = _read("WORKFLOWS.md")
        self.assertIn("No-stage checklist", w)          # canonical no-stage list
        self.assertIn(".council/", w)
        self.assertIn(".council/profile.*", w)          # local/private profile treatment

    def test_risks_names_local_profile_and_agents_collision(self):
        r = _read("RISKS.md")
        self.assertIn(".council/profile.*", r)          # local/private profile leak risk
        self.assertIn("AGENT-ROLES.md", r)              # AGENTS.md collision entry


class TestReleasesIndex(unittest.TestCase):
    """v0.8.1 PR 5 — the capped RELEASES.md release-history index (docs + tests only).

    Per docs/fable/v0.8.x-architecture-plan.md §4 vault boundary / §6 PR 5: a newest-first
    index, one line per release, HARD CAP 30 visible entries with an inline oldest-entries
    roll-up rule, pointing at the canonical docs/releases/ notes without inlining them. It is
    an index/working-memory aid, not a replacement for docs/releases or CHANGELOG.
    """

    # The five releases the plan/task require to be linked (each has a canonical note file).
    _REQUIRED_RELEASE_NOTES = ("v0.8.0", "v0.7.1", "v0.7.0", "v0.6.3", "v0.6.0")
    # Match one release entry line: "- **vX.Y.Z** — ...".
    _ENTRY_RE = re.compile(r"^- \*\*v\d+\.\d+\.\d+\*\*", re.MULTILINE)

    def test_releases_index_exists_and_is_markdown(self):
        p = VAULT / "RELEASES.md"
        self.assertTrue(p.is_file(), "missing vault file: RELEASES.md")
        text = _read("RELEASES.md")
        self.assertGreater(len(text.strip()), 0)
        self.assertTrue(text.lstrip().startswith("#"), "RELEASES.md should start with a heading")

    def test_release_entries_are_capped_at_30(self):
        # HARD CAP 30 visible release entries (one line per release).
        entries = self._ENTRY_RE.findall(_read("RELEASES.md"))
        self.assertGreater(len(entries), 0, "RELEASES.md lists no release entries")
        self.assertLessEqual(len(entries), 30,
                             f"RELEASES.md exceeds the hard cap of 30 entries ({len(entries)})")

    def test_documents_cap_and_collapse_policy(self):
        t = _read("RELEASES.md").lower()
        self.assertIn("cap", t, "RELEASES.md must document its cap policy")
        self.assertIn("30", t, "RELEASES.md must state the hard cap of 30")
        # the collapse / roll-up rule for oldest entries on overflow
        self.assertTrue("collapse" in t or "roll up" in t or "roll-up" in t,
                        "RELEASES.md must document the oldest-entries collapse/roll-up rule")

    def test_links_to_existing_release_notes(self):
        t = _read("RELEASES.md")
        for ver in self._REQUIRED_RELEASE_NOTES:
            rel = f"../../releases/{ver}.md"
            self.assertIn(rel, t, f"RELEASES.md does not link {rel}")
            self.assertTrue((REPO / "docs" / "releases" / f"{ver}.md").is_file(),
                            f"linked release note missing on disk: {ver}.md")

    def test_states_it_is_an_index_not_a_replacement(self):
        # Must point at the canonical sources and say it does not duplicate them.
        t = _read("RELEASES.md")
        low = t.lower()
        self.assertIn("docs/releases/", t)          # canonical detailed notes
        self.assertIn("CHANGELOG", t)               # canonical chronological change list
        self.assertTrue("not" in low and ("replacement" in low or "duplicate" in low),
                        "RELEASES.md must state it is an index, not a replacement/duplicate")

    def test_does_not_inline_full_release_note_bodies(self):
        # An index, not a notes dump: each entry is a single short line. Guard against a
        # release note body being pasted in by keeping the whole file small.
        lines = _read("RELEASES.md").splitlines()
        self.assertLessEqual(len(lines), 60, "RELEASES.md looks too large for an index file")

    def test_readme_lists_releases_index(self):
        self.assertIn("RELEASES.md", _read("README.md"),
                      "vault README does not list RELEASES.md")

    def test_status_points_to_releases_index(self):
        self.assertIn("RELEASES.md", _read("STATUS.md"),
                      "STATUS.md does not point at RELEASES.md for release history")

    def test_status_stays_current_state_focused(self):
        # STATUS.md keeps a current-state focus and delegates long history to RELEASES.md.
        s = _read("STATUS.md")
        self.assertIn("## Current state", s)
        self.assertIn("RELEASES.md", s)

    def test_workflows_documents_status_trimming(self):
        w = _read("WORKFLOWS.md")
        self.assertIn("Trimming STATUS history", w)
        self.assertIn("RELEASES.md", w)
        # no new command was introduced — curation stays human
        self.assertIn("no command", w.lower())

    def test_no_private_plan_names_in_releases_index(self):
        t = _read("RELEASES.md")
        for name in PRIVATE_PLAN_NAMES:
            self.assertNotIn(name, t, f"RELEASES.md references a private plan name: {name}")


class TestPreferenceSchemaV1(unittest.TestCase):
    """v0.8.2 PR 7 — the tighten-only preference schema v1 (docs + tests only).

    Per docs/fable/v0.8.x-architecture-plan.md §3 Q1/Q4 / §6 PR 7: a single bounded fenced
    `json` block in PREFERENCES.md carries `schema: 1` + exactly four tighten-only keys. This
    suite is a *strict test-side reader* — it mirrors the future validator's rules so the docs
    stay honest — plus consistency checks. NO production code parses/applies the block yet.
    """

    SPEC = REPO / "docs" / "fable" / "preference-schema-v1.md"
    ALLOWED_KEYS = {"schema", "default_review_preset", "extra_sensitive_paths",
                    "never_stage_extra", "require_usage_flag"}
    PRESET_ENUM = {"cheap", "balanced", "full"}
    MAX_BLOCK_BYTES = 4096
    _JSON_FENCE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)

    def _prefs(self):
        return _read("PREFERENCES.md")

    def _json_blocks(self, text):
        return self._JSON_FENCE.findall(text)

    def _canonical_block(self):
        blocks = self._json_blocks(self._prefs())
        self.assertGreaterEqual(len(blocks), 1, "PREFERENCES.md has no ```json schema block")
        # The machine region is the FIRST json block, and there must be exactly one.
        self.assertEqual(len(blocks), 1,
                         "PREFERENCES.md must contain exactly one ```json block (the machine region)")
        return blocks[0]

    # --- presence / section --------------------------------------------------- #

    def test_spec_file_exists_and_is_markdown(self):
        self.assertTrue(self.SPEC.is_file(), "missing normative spec docs/fable/preference-schema-v1.md")
        text = self.SPEC.read_text(encoding="utf-8")
        self.assertTrue(text.lstrip().startswith("#"))
        self.assertIn("schema v1", text.lower())

    def test_preferences_has_schema_section_and_points_to_spec(self):
        p = self._prefs()
        self.assertIn("Machine-readable preferences", p)
        self.assertIn("schema v1", p.lower())
        self.assertIn("docs/fable/preference-schema-v1.md", p)

    # --- the block: bounded, valid, allowed keys/types ------------------------ #

    def test_block_is_size_bounded(self):
        block = self._canonical_block()
        self.assertLessEqual(len(block.encode("utf-8")), self.MAX_BLOCK_BYTES,
                             "schema block exceeds the 4096-byte bound")

    def test_block_is_valid_json_object(self):
        obj = json.loads(self._canonical_block())
        self.assertIsInstance(obj, dict, "top level must be a JSON object")

    def test_block_declares_schema_version_1(self):
        obj = json.loads(self._canonical_block())
        self.assertEqual(obj.get("schema"), 1, "block must carry \"schema\": 1")

    def test_block_uses_only_allowed_v1_keys(self):
        obj = json.loads(self._canonical_block())
        extra = set(obj) - self.ALLOWED_KEYS
        self.assertEqual(extra, set(), f"block has non-v1 keys: {extra}")

    def test_default_review_preset_is_in_enum_and_not_premium(self):
        obj = json.loads(self._canonical_block())
        if "default_review_preset" in obj:
            self.assertIn(obj["default_review_preset"], self.PRESET_ENUM)
            self.assertNotEqual(obj["default_review_preset"], "premium",
                                "premium must never be nameable (loosening)")

    def test_path_arrays_are_relative_no_dotdot_no_drive(self):
        obj = json.loads(self._canonical_block())
        for key in ("extra_sensitive_paths", "never_stage_extra"):
            if key in obj:
                self.assertIsInstance(obj[key], list, f"{key} must be an array")
                for item in obj[key]:
                    self.assertIsInstance(item, str)
                    self.assertFalse(item.startswith("/"), f"{key}: absolute path {item!r}")
                    self.assertFalse(re.match(r"^[A-Za-z]:", item), f"{key}: drive letter {item!r}")
                    self.assertNotIn("..", item, f"{key}: '..' segment {item!r}")

    def test_require_usage_flag_is_bool(self):
        obj = json.loads(self._canonical_block())
        if "require_usage_flag" in obj:
            self.assertIsInstance(obj["require_usage_flag"], bool)

    # --- normative safety wording (tighten-only + forbidden vocabulary) ------- #

    def test_docs_state_not_active_behavior_yet(self):
        low = (self._prefs() + self.SPEC.read_text(encoding="utf-8")).lower()
        self.assertIn("not active", low)
        # explicitly: no command parses/applies it, validator is a later PR, application is v0.9.x
        self.assertTrue("no command reads" in low or "no command parses" in low
                        or "nothing parses or applies" in low)
        self.assertIn("v0.9.x", low)

    def test_docs_state_tighten_only(self):
        low = (self._prefs() + self.SPEC.read_text(encoding="utf-8")).lower()
        self.assertIn("tighten-only", low)
        self.assertIn("never", low)

    def test_spec_forbids_loosening_and_boundary_changes(self):
        low = self.SPEC.read_text(encoding="utf-8").lower()
        # forbids loosening safety/security/no-stage/trust
        self.assertTrue("loosen" in low and ("safety" in low or "trust" in low))
        # forbids Workbench executor/trust boundary changes
        self.assertIn("executor", low)
        self.assertIn("trust-boundary", low.replace("trust boundary", "trust-boundary"))
        # forbids shell/auto-execution/network/hosted
        for token in ("shell", "auto-execution", "network", "hosted"):
            self.assertIn(token, low, f"spec must forbid {token} behavior")
        # forbids hiding/suppressing dissenting council opinions
        self.assertTrue("suppress" in low or "hide" in low)
        self.assertIn("dissent", low)

    def test_preferences_names_forbidden_envelope(self):
        low = self._prefs().lower()
        self.assertIn("no vocabulary to loosen", low)
        self.assertIn("executor/trust boundary", low)
        self.assertTrue("suppress" in low or "hide/suppress" in low)

    def test_spec_documents_council_personas_as_future_not_v1(self):
        text = self.SPEC.read_text(encoding="utf-8")
        low = text.lower()
        self.assertIn("persona", low)
        # personas are future v0.9.x, NOT part of v1 / not applied here
        self.assertIn("v0.9.x", text)
        self.assertTrue("out of scope for schema v1" in low or "not part of schema v1" in low,
                        "spec must state personas are not part of schema v1")
        self.assertIn("defined, parsed, selected, or applied in this pr", low)
        # a couple of the named lenses are documented
        self.assertIn("Cost Skeptic", text)
        self.assertIn("Security Guardian", text)

    # --- cross-file consistency ----------------------------------------------- #

    def test_agent_roles_points_to_schema_and_states_not_runtime_override(self):
        t = _read("AGENT-ROLES.md")
        low = t.lower()
        self.assertIn("preference-schema-v1.md", t)
        self.assertTrue("never override runtime" in low or "not a runtime override" in low)
        self.assertIn("pointer-only", low)

    def test_risks_names_schema_persona_hidden_behavior_risk(self):
        t = _read("RISKS.md")
        low = t.lower()
        self.assertIn("persona", low)
        self.assertTrue("hidden behavior" in low or "policy override" in low)
        self.assertIn("tighten-only", low)

    def test_workflows_documents_editing_the_schema_safely(self):
        w = _read("WORKFLOWS.md")
        self.assertIn("Editing the preference schema safely", w)
        self.assertIn("preference-schema-v1.md", w)
        self.assertIn("tighten", w.lower())

    def test_pack_does_not_ingest_preference_schema(self):
        # The pack is built from STATUS.md + decisions only. A token distinctive to the schema
        # block/spec must never reach the pack (STATUS deliberately avoids the literal key name).
        needle = "require_usage_flag"
        self.assertIn(needle, self._prefs())            # sanity: it's in PREFERENCES.md
        self.assertNotIn(needle, _read("STATUS.md"))    # and NOT in the pack's STATUS input
        ddir = REPO / "docs" / "decisions"
        status = VAULT / "STATUS.md"
        res = cp.build_pack(ddir, status, on="2026-07-04T00:00:00Z")
        self.assertNotIn(needle, res.text, "context pack ingested the preference schema")


class TestReviewLensesDoc(unittest.TestCase):
    """v0.9.1 PR 6 — the council review-lenses documentation (docs only, no behavior).

    Locks that the lens doc exists, names the three primary lenses + four future stubs, and is
    framed as documentation-only with the binding safety envelope (no schema/runtime/prompt/
    ranking/synthesis change, dissent-preservation, tighten-only, no `.council/profile.*`, no UI).
    """

    LENS_DOC = REPO / "docs" / "fable" / "council-review-lenses.md"
    PRIMARY = ("Security Guardian", "Cost Skeptic", "Local-first Guardian")
    FUTURE = ("Product Strategist", "UX / User Advocate", "Risk Officer", "Commercialization Lens")
    # a phrase that lives ONLY in the lens doc body (used for the pack no-ingest check).
    _BODY_NEEDLE = "attack surface and trust-boundary erosion first"

    def _doc(self):
        return self.LENS_DOC.read_text(encoding="utf-8")

    def test_lens_doc_exists_and_is_markdown(self):
        self.assertTrue(self.LENS_DOC.is_file(), "missing docs/fable/council-review-lenses.md")
        text = self._doc()
        self.assertTrue(text.lstrip().startswith("#"))
        self.assertIn("review lens", text.lower())

    def test_three_primary_lenses_documented(self):
        text = self._doc()
        for lens in self.PRIMARY:
            self.assertIn(lens, text, f"primary lens not documented: {lens}")
        # sanity: the body needle used by the pack test really is in the doc.
        self.assertIn(self._BODY_NEEDLE, text)

    def test_future_lenses_are_marked_stubs(self):
        text = self._doc()
        low = text.lower()
        for lens in self.FUTURE:
            self.assertIn(lens, text, f"future lens stub missing: {lens}")
        # they are clearly future/not-elaborated.
        self.assertIn("future lenses (stubs", low)
        self.assertIn("*(future)*", text)

    def test_framing_is_documentation_only(self):
        low = self._doc().lower()
        self.assertIn("documentation only", low)
        self.assertIn("not applied, not schema, not validated", low)
        self.assertTrue("not a command" in low or "not a preference key" in low)
        self.assertIn("subject to change", low)

    def test_states_no_runtime_prompt_ranking_synthesis_change(self):
        low = self._doc().lower()
        for token in ("prompt construction", "ranking", "synthesis",
                      "model/provider selection", "schema"):
            self.assertIn(token, low, f"envelope must name: {token}")

    def test_states_dissent_preservation(self):
        low = self._doc().lower()
        self.assertIn("dissent", low)
        self.assertTrue("never" in low and ("suppress" in low or "outrank" in low
                                            or "downrank" in low))

    def test_states_tighten_only_no_loosening(self):
        low = self._doc().lower()
        self.assertTrue("tighten-only" in low or "only add" in low or "only ask for" in low)
        self.assertIn("never", low)
        self.assertTrue("loosen" in low or "override the review policy" in low)

    def test_states_workbench_trust_unaffected(self):
        low = self._doc().lower()
        self.assertTrue("executor" in low and "trust" in low)
        self.assertIn("guard", low)

    def test_states_no_local_profile_store_and_no_ui(self):
        text = self._doc()
        low = text.lower()
        self.assertIn(".council/profile.*", text)          # glob form, never a concrete filename
        self.assertTrue("no store" in low or "does not create or read" in low)
        self.assertIn("no", low)
        self.assertTrue("ui" in low or "dashboard" in low)

    def test_states_relationship_to_preference_system_unchanged(self):
        low = self._doc().lower()
        self.assertIn("preference", low)
        self.assertTrue("preferences.md machine-block semantics" in low
                        or "change nothing about it" in low
                        or "not part of the preference schema" in low)
        self.assertIn("v0.10.x", low)                       # behavior deferred

    def test_agent_roles_points_to_the_lens_doc(self):
        t = (VAULT / "AGENT-ROLES.md").read_text(encoding="utf-8")
        self.assertIn("docs/fable/council-review-lenses.md", t)
        self.assertIn("documentation only", t.lower())

    def test_pack_does_not_ingest_lens_content(self):
        # The pack is built from STATUS.md + decisions only; a distinctive lens-body phrase must
        # never reach it (STATUS deliberately avoids that phrase).
        self.assertNotIn(self._BODY_NEEDLE, _read("STATUS.md"))
        ddir = REPO / "docs" / "decisions"
        status = VAULT / "STATUS.md"
        res = cp.build_pack(ddir, status, on="2026-07-04T00:00:00Z")
        self.assertNotIn(self._BODY_NEEDLE, res.text, "context pack ingested lens content")

    def test_lens_names_absent_from_backend_code(self):
        # Lenses are documentation-only: no production module may hardcode a lens name. This is a
        # tripwire — if a future change wires a lens into prompt/ranking/synthesis, the council
        # client, the guards, or the Workbench guard/executor/trust code, it fails the suite and
        # forces an explicit review (lens *behavior* is a v0.10.x decision, not a v0.9.1 doc PR).
        backend = REPO / "backend"
        offenders = []
        for py in backend.glob("*.py"):
            text = py.read_text(encoding="utf-8")
            for lens in self.PRIMARY:
                if lens in text:
                    offenders.append(f"{py.name}:{lens}")
        self.assertEqual(offenders, [],
                         f"review-lens names must not appear in backend code (docs-only): "
                         f"{offenders}")


class TestContextPackDoesNotLeakPrivatePlans(unittest.TestCase):
    # distinctive scaffold-body phrases (verified in PR C) — must NOT reach the pack.
    _PROFILE_BODY_NEEDLES = (
        "began as a fork of",              # PROFILE.md
        "Which council review level to run",  # PREFERENCES.md
        "who does what",                   # AGENT-ROLES.md
    )

    def test_pack_built_from_real_repo_has_no_private_plan_names(self):
        ddir = REPO / "docs" / "decisions"
        status = VAULT / "STATUS.md"
        res = cp.build_pack(ddir, status, on="2026-07-04T00:00:00Z")
        for name in PRIVATE_PLAN_NAMES:
            self.assertNotIn(name, res.text,
                             f"context pack leaked a private plan filename: {name}")

    def test_pack_does_not_ingest_full_vault_profile_content(self):
        # The pack is a budgeted projection (STATUS + decision index), not a vault dump —
        # distinctive scaffold *bodies* must never appear in it. Sanity: the needles do
        # live in their files.
        for rel, needle in zip(PROFILE_FILES, self._PROFILE_BODY_NEEDLES):
            self.assertIn(needle, (VAULT / rel).read_text(encoding="utf-8"))
        ddir = REPO / "docs" / "decisions"
        status = VAULT / "STATUS.md"
        res = cp.build_pack(ddir, status, on="2026-07-04T00:00:00Z")
        for needle in self._PROFILE_BODY_NEEDLES:
            self.assertNotIn(needle, res.text,
                             f"context pack ingested scaffold body content: {needle!r}")

    def test_pack_check_still_passes_on_real_repo(self):
        ddir = REPO / "docs" / "decisions"
        status = VAULT / "STATUS.md"
        res = cp.build_pack(ddir, status, on="2026-07-04T00:00:00Z")
        report = cp.check_pack(res.text)
        # all checks pass and no critical redaction; vault files present don't break it.
        self.assertTrue(report.ok, report.reasons)
        self.assertEqual(report.passed, report.total, report.reasons)

    def test_pack_does_not_ingest_releases_index(self):
        # The pack is built from STATUS.md + decisions only — the new RELEASES.md is never an
        # input. A phrase distinctive to RELEASES.md's body must not appear in the pack.
        needle = "early foundations"   # only in RELEASES.md's roll-up example
        self.assertIn(needle, (VAULT / "RELEASES.md").read_text(encoding="utf-8"))
        self.assertNotIn(needle, (VAULT / "STATUS.md").read_text(encoding="utf-8"))
        ddir = REPO / "docs" / "decisions"
        status = VAULT / "STATUS.md"
        res = cp.build_pack(ddir, status, on="2026-07-04T00:00:00Z")
        self.assertNotIn(needle, res.text, "context pack ingested RELEASES.md body content")


if __name__ == "__main__":
    unittest.main()
