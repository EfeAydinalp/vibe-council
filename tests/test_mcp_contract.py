"""Tests for the read-only MCP contract skeleton (backend/mcp_contract.py) + CLI.

Stdlib-only (`unittest`). The contract is **definition only** — these tests assert
the read-only/forbidden invariants and that the `vibe mcp contract` command is
read-only, deterministic, dependency-free, and writes nothing. No server, no
model/API/network.
"""

import json
import os
import unittest
import tempfile
from pathlib import Path

from backend import mcp_contract as mc
from tests.test_cli_smoke import run_cli


class TestContractModule(unittest.TestCase):
    def test_all_declared_tools_are_read_only(self):
        self.assertTrue(mc.READ_ONLY_TOOLS)
        for t in mc.READ_ONLY_TOOLS:
            self.assertTrue(mc.is_read_only_tool(t.name), t.name)
            self.assertFalse(mc.is_forbidden_tool(t.name), t.name)

    def test_forbidden_tools_are_flagged(self):
        for n in mc.FORBIDDEN_TOOLS:
            self.assertTrue(mc.is_forbidden_tool(n), n)
            self.assertFalse(mc.is_read_only_tool(n), n)

    def test_git_status_is_forbidden(self):
        # read-only elsewhere, but vibe-council MCP v0.4 exposes no git surface
        self.assertTrue(mc.is_forbidden_tool("git_status"))
        self.assertNotIn("git_status", mc.READ_ONLY_TOOL_NAMES)

    def test_resources_use_vibe_scheme(self):
        self.assertTrue(mc.READ_ONLY_RESOURCES)
        for r in mc.READ_ONLY_RESOURCES:
            self.assertTrue(r.uri.startswith(mc.MCP_SCHEME), r.uri)

    def test_contract_validation_passes(self):
        self.assertEqual(mc.validate_mcp_contract(), [])

    def test_read_only_and_forbidden_are_disjoint(self):
        self.assertEqual(mc.READ_ONLY_TOOL_NAMES & mc.FORBIDDEN_TOOL_NAMES, frozenset())

    def test_mutation_action_names_not_in_allowed_list(self):
        for n in ("promote_decision", "write_file", "edit_file", "delete_file",
                  "run_command", "git_commit", "git_push", "git_status",
                  "send_email", "deploy"):
            self.assertNotIn(n, mc.READ_ONLY_TOOL_NAMES, n)

    def test_mutation_name_heuristic(self):
        # defense-in-depth: a read-only tool accidentally named like a mutation
        # would be caught by the validator's heuristic.
        self.assertTrue(mc._looks_mutating("write_file"))
        self.assertTrue(mc._looks_mutating("promote_decision"))
        self.assertFalse(mc._looks_mutating("list_decisions"))
        self.assertFalse(mc._looks_mutating("get_context_pack"))

    def test_contract_dict_is_read_only_no_server(self):
        d = mc.contract_dict()
        self.assertTrue(d["read_only"])
        self.assertFalse(d["server_implemented"])
        self.assertEqual(d["scheme"], "vibe://")


class TestMcpCLI(unittest.TestCase):
    def test_prints_resources_and_tools(self):
        r = run_cli(["mcp", "contract"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("vibe://status", r.stdout)
        self.assertIn("list_decisions", r.stdout)
        self.assertIn("read-only", r.stdout.lower())

    def test_prints_forbidden_tools_and_boundary(self):
        r = run_cli(["mcp", "contract"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("promote_decision", r.stdout)   # a forbidden tool is listed
        self.assertIn("git_status", r.stdout)
        self.assertIn("Forbidden", r.stdout)

    def test_json_output_is_read_only(self):
        r = run_cli(["mcp", "contract", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertTrue(data["read_only"])
        self.assertFalse(data["server_implemented"])
        self.assertIn("forbidden_tools", data)
        self.assertIn("git_status", data["forbidden_tools"])

    def test_command_writes_nothing_and_needs_no_dependency(self):
        # deterministic, dependency-free: runs in a clean cwd and creates no files
        # (no .council/, no sockets, no MCP package required).
        with tempfile.TemporaryDirectory() as t:
            before = set(os.listdir(t))
            r = run_cli(["mcp", "contract"], caller_cwd=Path(t))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(set(os.listdir(t)), before)  # nothing written


if __name__ == "__main__":
    unittest.main()
