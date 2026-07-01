# Claude Code / MCP setup — read-only vibe-council server (v0.4)

## 1. Purpose

Let Claude Code (or any local MCP client) read vibe-council's **curated project memory** — project
status, curated decisions, and the generated context pack + health — over a **read-only** MCP stdio
server. The agent can *read* why past decisions were made; it **cannot** write files, promote
decisions, run commands, or touch git. You remain the only writer.

## 2. Requirements

- vibe-council installed with the global `vibe` launcher (or run `python -m backend.cli` from the
  repo). No extra dependency: the MCP transport is a small stdlib JSON-RPC-over-stdio server (**no
  `mcp` SDK required**).
- Run the server **from the project whose memory you want** (it reads that repo's
  `docs/decisions/` and `docs/context/project/STATUS.md`).

## 3. Commands

```sh
vibe mcp contract                    # print the read-only resources/tools + forbidden tools
vibe mcp inspect --context --health  # read-only smoke: status + decisions + context pack/health
                                     #   (built in memory — writes no .council/ files)
vibe mcp serve --stdio               # start the read-only MCP stdio server (runs until EOF)
```

`serve --stdio` speaks newline-delimited **JSON-RPC 2.0** over stdin/stdout. It opens no HTTP port,
starts no daemon, and exits when its stdin closes (EOF).

## 4. MCP client configuration (generic stdio pattern)

> **Generic MCP stdio client pattern.** The JSON below is the common `mcpServers` shape used by
> many MCP clients; it is **not** presented as verified Claude Code config syntax. Confirm the exact
> field names and file location against your client's own MCP documentation before relying on it.

```jsonc
{
  "mcpServers": {
    "vibe-council": {
      "command": "vibe",
      "args": ["mcp", "serve", "--stdio"]
    }
  }
}
```

If the `vibe` launcher isn't on the client's PATH, use the module form and set the working directory
to the target repo:

```jsonc
{
  "mcpServers": {
    "vibe-council": {
      "command": "python",
      "args": ["-m", "backend.cli", "mcp", "serve", "--stdio"]
    }
  }
}
```

The server reads the repo it is launched in — point the client's working directory at the project
whose memory you want exposed.

## 5. What the server exposes (read-only)

Resources:

- `vibe://status` — project status snapshot (`STATUS.md`)
- `vibe://decisions` — curated decision index
- `vibe://decisions/{id}` — a single curated decision (by id/stem)
- `vibe://context/latest` — the generated context pack (built in memory)

Tools:

- `get_project_status`
- `list_decisions`
- `show_decision`
- `get_context_pack`
- `check_context_health`

## 6. What it does NOT expose

- **No write tools** — no `promote_decision`, `write_file`, `edit_file`, `delete_file`.
- **No git/shell tools** — no `git_commit`/`git_push`/`git_status`, no `run_command`, no `deploy`,
  no `send_email`.
- **No provider/model calls** and no network beyond the local stdio protocol.
- **No decision promotion** through MCP (promotion stays a human-reviewed CLI step).
- **No raw `.council/`** reviews/drafts, **no private/untracked plans**, and no secrets, `.env`,
  `.venv/`, `data/`, raw outputs, local absolute paths, cloned repos, or `.obsidian/`.

Verify the boundary any time with `vibe mcp contract` (lists the forbidden tools) — a call to any
forbidden tool over the transport returns a JSON-RPC error (`tool not available`).

## 7. Troubleshooting

- **`vibe: command not found`** — the launcher isn't installed/on PATH. Use the `python -m
  backend.cli mcp serve --stdio` form, or run the installer (`scripts/install-vibe.*`).
- **Wrong repo / empty results** — the server reads the *current* project. Start it (or set the
  client's working directory) inside the repo whose `docs/decisions/` + `STATUS.md` you want.
- **Context health below 21/21** — the curated docs are missing a signal; run `vibe context check`
  to see which check fails, then fix the curated docs (this is deterministic, not an LLM eval).
- **Generated pack files vs in-memory MCP reads** — `get_context_pack`/`check_context_health` build
  the pack **in memory** and write nothing. `.council/context/pack-latest.md` is only written by the
  CLI `vibe context build`; MCP reads never create or modify it.
- **Windows path quoting** — quote paths with spaces in the client config; prefer forward slashes or
  escaped backslashes in JSON.
- **Server "exits" immediately** — the stdio server runs until stdin EOF; that's expected when not
  driven by a client. An MCP client keeps the pipe open for the session.

## 8. Safety checklist

- [ ] `vibe mcp contract` lists the read-only surface and the forbidden tools.
- [ ] Forbidden tools are absent (a `tools/call` for e.g. `write_file` returns an error).
- [ ] MCP reads cause **no `.council/` writes** (`pack-latest.md` / `claude-code-context.md`
      unchanged after context reads).
- [ ] `vibe mcp inspect --health` (or `check_context_health`) reports **21/21**.
- [ ] Served content contains no secrets, private/untracked plans, or local absolute paths.
