"""Tests for the minimal read-only MCP stdio transport (backend/mcp_stdio.py).

Stdlib-only (`unittest`). The transport is a thin JSON-RPC adapter over the tested
`mcp_server` read layer — no new dependency, no socket, no daemon. These tests drive
`handle_request` / `serve_stdio` in process (via StringIO) with a bounded set of
requests; they assert the read-only surface, the forbidden/deferred boundaries, and
that no `.council/` files are written. The CLI `serve` help/usage is checked too.
"""

import io
import json
import os
import unittest
import tempfile
from pathlib import Path

from backend import mcp_stdio as mstdio
from backend import mcp_server as ms
from backend import mcp_contract as mc
from tests.test_cli_smoke import run_cli
from tests.test_mcp_server import _make_repo


def _req(rid, method, **params):
    m = {"jsonrpc": "2.0", "method": method}
    if rid is not None:
        m["id"] = rid
    if params:
        m["params"] = params
    return m


class TestRegistry(unittest.TestCase):
    def test_tools_list_matches_enabled_read_layer(self):
        names = [t["name"] for t in mstdio.tools_list()]
        self.assertEqual(set(names), set(ms.ENABLED_TOOLS))
        for t in mstdio.tools_list():
            self.assertIn("inputSchema", t)

    def test_resources_list_matches_enabled_read_layer(self):
        uris = [r["uri"] for r in mstdio.resources_list()]
        self.assertEqual(set(uris), set(ms.ENABLED_RESOURCES))

    def test_forbidden_tools_absent_from_transport(self):
        names = {t["name"] for t in mstdio.tools_list()}
        for n in mc.FORBIDDEN_TOOLS:
            self.assertNotIn(n, names)

    def test_deferred_tools_and_resources_absent(self):
        names = {t["name"] for t in mstdio.tools_list()}
        uris = {r["uri"] for r in mstdio.resources_list()}
        self.assertNotIn("list_rejected_alternatives", names)
        for u in ("vibe://rejected-alternatives", "vibe://release-notes", "vibe://constraints"):
            self.assertNotIn(u, uris)


class TestHandleRequest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_initialize_reports_protocol(self):
        resp = mstdio.handle_request(_req(1, "initialize"), self.root)
        self.assertEqual(resp["result"]["protocolVersion"], mstdio.PROTOCOL_VERSION)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "vibe-council")

    def test_notification_gets_no_response(self):
        self.assertIsNone(mstdio.handle_request(_req(None, "notifications/initialized"),
                                                self.root))

    def test_tools_list(self):
        resp = mstdio.handle_request(_req(2, "tools/list"), self.root)
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertEqual(names, set(ms.ENABLED_TOOLS))

    def test_tool_call_delegates_to_read_layer(self):
        resp = mstdio.handle_request(
            _req(3, "tools/call", name="list_decisions", arguments={}), self.root)
        text = resp["result"]["content"][0]["text"]
        self.assertEqual(json.loads(text), ms.list_decisions(self.root))

    def test_tool_call_show_decision_and_traversal(self):
        ok = mstdio.handle_request(
            _req(4, "tools/call", name="show_decision",
                 arguments={"id": "2026-01-01-sample"}), self.root)
        self.assertIn("# Sample decision", ok["result"]["content"][0]["text"])
        bad = mstdio.handle_request(
            _req(5, "tools/call", name="show_decision",
                 arguments={"id": "../plans/private-thing"}), self.root)
        self.assertIn("error", bad)
        self.assertNotIn("secret-ish", json.dumps(bad))

    def test_forbidden_tool_call_is_error(self):
        for n in ("write_file", "promote_decision", "git_status", "run_command"):
            resp = mstdio.handle_request(
                _req(6, "tools/call", name=n, arguments={}), self.root)
            self.assertIn("error", resp, n)

    def test_resource_read_status_and_decision(self):
        s = mstdio.handle_request(_req(7, "resources/read", uri="vibe://status"), self.root)
        self.assertIn("Current focus: testing.", s["result"]["contents"][0]["text"])
        d = mstdio.handle_request(
            _req(8, "resources/read", uri="vibe://decisions/2026-01-01-sample"), self.root)
        self.assertIn("# Sample decision", d["result"]["contents"][0]["text"])

    def test_resource_read_deferred_uri_is_error(self):
        for u in ("vibe://constraints", "vibe://release-notes", "vibe://rejected-alternatives"):
            resp = mstdio.handle_request(_req(9, "resources/read", uri=u), self.root)
            self.assertIn("error", resp, u)

    def test_unknown_method_is_error(self):
        resp = mstdio.handle_request(_req(10, "tools/destroy"), self.root)
        self.assertEqual(resp["error"]["code"], mstdio.METHOD_NOT_FOUND)

    def test_context_pack_call_writes_nothing(self):
        self.assertFalse((self.root / ".council" / "context").exists())
        before = {p for p in self.root.rglob("*")}
        mstdio.handle_request(_req(11, "tools/call", name="get_context_pack",
                                   arguments={}), self.root)
        mstdio.handle_request(_req(12, "resources/read", uri="vibe://context/latest"),
                              self.root)
        self.assertEqual({p for p in self.root.rglob("*")}, before)  # nothing written
        self.assertFalse((self.root / ".council" / "context").exists())


class TestServeStdio(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_bounded_smoke_over_streams_writes_nothing(self):
        reqs = [
            _req(1, "initialize"),
            _req(None, "notifications/initialized"),   # no response expected
            _req(2, "tools/list"),
            _req(3, "tools/call", name="get_context_pack", arguments={}),
            _req(4, "tools/call", name="write_file", arguments={}),  # forbidden
        ]
        instream = io.StringIO("\n".join(json.dumps(r) for r in reqs) + "\n")
        outstream = io.StringIO()
        before = {p for p in self.root.rglob("*")}
        rc = mstdio.serve_stdio(self.root, instream, outstream)
        self.assertEqual(rc, 0)

        responses = [json.loads(l) for l in outstream.getvalue().splitlines() if l.strip()]
        self.assertEqual([r["id"] for r in responses], [1, 2, 3, 4])  # notification: no resp
        self.assertEqual(responses[0]["result"]["protocolVersion"], mstdio.PROTOCOL_VERSION)
        self.assertIn("error", responses[3])  # write_file refused
        self.assertEqual({p for p in self.root.rglob("*")}, before)  # nothing written


class TestServeCLI(unittest.TestCase):
    def test_serve_help_exits_zero(self):
        r = run_cli(["mcp", "serve", "--help"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("stdio", (r.stdout + r.stderr).lower())

    def test_serve_without_stdio_is_usage_error(self):
        r = run_cli(["mcp", "serve"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("stdio", r.stderr.lower())


if __name__ == "__main__":
    unittest.main()
