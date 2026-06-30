"""Minimal read-only MCP **stdio transport** (v0.4, PR #59).

Speaks the MCP stdio protocol — newline-delimited **JSON-RPC 2.0** over stdin/stdout
— for the read-only surface already implemented and tested in
:mod:`backend.mcp_server` (status, curated decisions, context pack, context health).
**No new dependency:** this is a small stdlib JSON-RPC server, not the `mcp` SDK, so
the normal `vibe` CLI keeps working without any MCP runtime. Importing this module
starts nothing.

It is a thin **transport adapter**: every method delegates to the pure
`mcp_server` read/dispatch layer. It therefore inherits that layer's guarantees —
read-only, path-traversal guarded, no `.council/` writes, and no forbidden/deferred
tool reachable. It opens no socket/HTTP port, starts no daemon, runs no
shell/git/provider/model calls, and writes nothing.

Methods implemented: ``initialize``, ``notifications/initialized`` (no-op), ``ping``,
``tools/list``, ``tools/call``, ``resources/list``, ``resources/read``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, TextIO

from . import mcp_server
from . import mcp_contract

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "vibe-council"

# JSON-RPC error codes (subset)
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Minimal input schemas for the enabled tools (all read-only).
_TOOL_SCHEMAS: Dict[str, dict] = {
    "get_project_status": {"type": "object", "properties": {}},
    "list_decisions": {"type": "object", "properties": {}},
    "show_decision": {"type": "object",
                      "properties": {"id": {"type": "string"}},
                      "required": ["id"]},
    "get_context_pack": {"type": "object", "properties": {}},
    "check_context_health": {"type": "object", "properties": {}},
}


# --------------------------------------------------------------------------- #
# Registry (derived from the tested read layer + contract; no new surface)
# --------------------------------------------------------------------------- #

def tools_list() -> List[dict]:
    """The enabled read-only tools, as MCP tool descriptors."""
    descr = {t.name: t.description for t in mcp_contract.READ_ONLY_TOOLS}
    out: List[dict] = []
    for name in mcp_server.ENABLED_TOOLS:
        out.append({
            "name": name,
            "description": descr.get(name, ""),
            "inputSchema": _TOOL_SCHEMAS.get(name, {"type": "object", "properties": {}}),
        })
    return out


def resources_list() -> List[dict]:
    """The enabled read-only resources, as MCP resource descriptors. The
    templated ``vibe://decisions/{id}`` is advertised as a concrete-only note."""
    descr = {r.uri: r.description for r in mcp_contract.READ_ONLY_RESOURCES}
    out: List[dict] = []
    for uri in mcp_server.ENABLED_RESOURCES:
        out.append({
            "uri": uri,
            "name": uri,
            "description": descr.get(uri, ""),
            "mimeType": "text/markdown",
        })
    return out


# --------------------------------------------------------------------------- #
# Handlers (delegate to the pure read layer; read-only, no writes)
# --------------------------------------------------------------------------- #

def _text_content(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def _tool_call(name: str, arguments: dict, root: Path) -> dict:
    """Run an enabled read-only tool and return MCP tool-result content. Unknown,
    forbidden, or deferred tools are refused by ``mcp_server.dispatch``."""
    kwargs = {}
    if name == "show_decision":
        kwargs["id"] = str((arguments or {}).get("id") or "")
    result = mcp_server.dispatch(name, root, **kwargs)
    if isinstance(result, str):
        return _text_content(result)
    return _text_content(json.dumps(result, ensure_ascii=False, indent=2))


def _resource_read(uri: str, root: Path) -> dict:
    """Read an enabled resource by URI (read-only)."""
    if uri == "vibe://status":
        text = mcp_server.get_project_status(root)
    elif uri == "vibe://decisions":
        text = json.dumps(mcp_server.list_decisions(root), ensure_ascii=False, indent=2)
    elif uri == "vibe://context/latest":
        text = mcp_server.get_context_pack(root)["text"]
    elif uri.startswith("vibe://decisions/") and uri != "vibe://decisions":
        ident = uri[len("vibe://decisions/"):]
        text = mcp_server.show_decision(root, ident)["text"]
    else:
        raise mcp_server.ReadError(f"resource not available: {uri}")
    return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]}


# --------------------------------------------------------------------------- #
# JSON-RPC dispatch
# --------------------------------------------------------------------------- #

def _ok(req_id, result) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id, code, message) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_request(msg: dict, root: Path) -> Optional[dict]:
    """Handle one JSON-RPC message. Returns a response dict, or ``None`` for
    notifications (no id). Never writes; never raises out — read-layer errors
    become JSON-RPC errors with safe messages."""
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    # notifications (no id) — e.g. notifications/initialized — get no response
    if req_id is None:
        return None

    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": {"name": SERVER_NAME, "version": "0.4-read-only"},
            "instructions": "Read-only project memory. No write/action tools.",
        })
    if method == "ping":
        return _ok(req_id, {})
    if method == "tools/list":
        return _ok(req_id, {"tools": tools_list()})
    if method == "resources/list":
        return _ok(req_id, {"resources": resources_list()})
    if method == "tools/call":
        name = params.get("name")
        try:
            return _ok(req_id, _tool_call(name, params.get("arguments") or {}, root))
        except mcp_server.ReadError as e:
            return _err(req_id, INVALID_PARAMS, str(e))
    if method == "resources/read":
        uri = params.get("uri") or ""
        try:
            return _ok(req_id, _resource_read(uri, root))
        except mcp_server.ReadError as e:
            return _err(req_id, INVALID_PARAMS, str(e))

    return _err(req_id, METHOD_NOT_FOUND, f"method not found: {method}")


def serve_stdio(root: Path, instream: TextIO, outstream: TextIO) -> int:
    """Bounded read-only MCP stdio loop: read newline-delimited JSON-RPC requests
    from ``instream``, write responses to ``outstream``, until EOF. Read-only and
    deterministic; writes no files; opens no socket. Returns 0 at EOF."""
    for line in instream:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            outstream.write(json.dumps(_err(None, PARSE_ERROR, "parse error")) + "\n")
            outstream.flush()
            continue
        resp = handle_request(msg, root)
        if resp is not None:
            outstream.write(json.dumps(resp, ensure_ascii=False) + "\n")
            outstream.flush()
    return 0
