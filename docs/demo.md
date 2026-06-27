# Recording a safe vibe-council demo

This is a **guide for recording a terminal demo** of vibe-council — not a recorded
asset. As of this writing **no demo cast/GIF has been recorded yet**; doing so spends
real API credits and risks leaking secrets/paths, so it is a separately-approved
follow-up. When that recording happens, follow this guide so the published asset is
**safe** (no keys, no `.env`, no local usernames/paths, no raw `.council/` outputs).

> **Current best-available artifact:** a **sanitized text transcript** of the workflow
> is committed at [`demo-transcript.md`](demo-transcript.md) (captured on a Windows dev
> box where asciinema isn't available). It's honestly labeled as a transcript, **not** a
> recording. The real asciinema cast / GIF described below remains the approved
> follow-up — produce it on **Linux / WSL / a container / Codespaces**, where asciinema
> runs.

> **TL;DR:** Record an [asciinema](https://asciinema.org/) cast (text, tiny,
> copy-pasteable) from a **neutral throwaway directory** with a **generic prompt**,
> **history disabled**, and a **dedicated low-quota API key**. Rehearse on
> `--preset cheap`; do the real take on `balanced`. **Watch it back and scan the
> `.cast` for `sk-or-v1-`, your username, and home paths before publishing.**

## Minimal safe checklist (do these 8, every time)

If you read nothing else, do these — the rest of the doc is the reasoning behind them:

1. **Create a fresh, dedicated, low-quota OpenRouter key right before recording** (not
   your everyday key). Set an OpenRouter spending cap on it.
2. **Record from a neutral throwaway dir** that doesn't embed your username — e.g.
   `mkdir -p /tmp/vibe-demo-$(uuidgen | cut -d- -f1)` (POSIX) or `C:\Temp\vibe-demo`
   (Windows). Not `~/...` (it expands to `/home/<you>`).
3. **Use a generic shell prompt** (no `user@host`) and **disable history for the
   session** (`set +o history`). `clear` the screen before you hit record.
4. **Do a 10-second toolchain test first** — `asciinema rec /tmp/t.cast`, type `echo
   hi`, `exit`, `asciinema play /tmp/t.cast` — to confirm recording works *before*
   spending any credits.
5. **Rehearse the flow on `--preset cheap`**; only the final take uses `balanced`.
   Add `--max-cost 0.50` so a misbehaving run can't drain the key.
6. **Never put a key/`.env`/raw `.council/` file on screen.** vibe doesn't print the
   key; your shell or a copy/paste might.
7. **Scan the finished `.cast` for secrets** (see [below](#after-recording--verify-before-publishing)).
8. **Rotate (or delete) the demo key immediately after** — and **if a key was ever
   visible in the recording at all, delete the recording and treat that key as
   exposed**, no exceptions.

---

## Why asciinema first (GIF optional, later)

- **asciinema** records the terminal as **selectable text**, not pixels. The cast
  file is tiny, the player lets a reader copy commands out, and — crucially — the
  text `.cast` is **directly editable** so you can scrub a leaked path or token after
  the fact. It also doesn't capture window chrome (title bars, other apps).
- **GIF** is a *secondary, optional* artifact for surfaces that can't embed a player
  (an inline README thumbnail, social posts). It's heavier and lossy. Generate it
  **from the cast** later with [`agg`](https://github.com/asciinema/agg) rather than
  screen-recording separately — one source of truth, already redacted.

Written against **asciinema 2.x** (`asciinema --version`). Newer versions are fine;
the `rec` / `cat` / file-editing workflow below is stable across them.

---

## The demo scenario

A short happy-path loop using a **committed example plan** (`examples/plans/feature-plan.md`),
so every command is real and runnable. Mirrors the README [Quick demo](../README.md#quick-demo).

```sh
# 1. Install / verify — prove the tool is wired up.
vibe --version
vibe status
vibe presets

# 2. Review a real example plan. No --yes the first time, so viewers see the
#    approval prompt and that this spends credits.
vibe review --preset balanced --file examples/plans/feature-plan.md --usage

# 3. Make an edit, then review the git diff.
vibe diff --preset balanced --yes --usage

# 4. Record the decision (single model — the cheapest step).
vibe extract --preset balanced --file examples/plans/feature-plan.md --save --yes --usage

# 5. Read it back out of decision memory (no model call, no key needed).
vibe decisions context "demo"
```

Tips for a clean take:

- **Rehearse on `--preset cheap`** (pennies) to get the timing and screen layout
  right; only switch to `balanced` for the final recording. **As of 2026-06**, a
  `balanced` review step ran **≈ $0.15–0.30** via OpenRouter (ballpark, provider- and
  size-dependent — check current pricing before recording); the full loop above runs a
  couple of those, so budget roughly **under ~$1** for one clean take. Pass
  **`--max-cost 0.50`** on each step (and/or `--max-tokens N`) so a misbehaving or
  re-taken run can't drain the key.
- **Keep it short** (target **< 90s**). Model calls have real latency — trim the long
  wait gaps when editing the cast, or narrate that the wait is normal.
- **Before recording, sanity-check the input** — open `examples/plans/feature-plan.md`
  and confirm it contains nothing confidential. It's a committed sample, but make the
  check a habit so a future custom demo input never leaks business details.

Record with:

```sh
asciinema rec demo.cast      # Ctrl-D (or `exit`) to stop
asciinema play demo.cast     # watch it back before doing anything else
```

---

## Redaction checklist (do this every time)

A terminal recording captures **everything on screen**. Before you hit record:

- **API keys** — never `cat .env`, never `echo $OPENROUTER_API_KEY`, never start
  recording with a key in your scrollback. vibe never prints the key itself, but your
  **shell history** might echo it back — disable history for the session
  (`set +o history` / a temp shell profile) and `clear` the screen first.
- **`.env`** — don't open, print, or `ls -la` it on camera.
- **Local usernames / paths** — `vibe status` prints the **absolute project path**
  (e.g. `C:\Users\<you>\...`). Record from a directory that **doesn't embed your
  username**: `/tmp/vibe-demo-$(uuidgen | cut -d- -f1)` (POSIX) or `C:\Temp\vibe-demo`
  (Windows), not `~/demo` (it expands to `/home/<you>`). Set a **generic shell prompt**
  with no `user@host`. (A future `vibe status --no-paths` flag would remove this step —
  see the [release checklist](release-checklist.md#future-automation-not-in-v010).)
- **`.council/` raw outputs** — it's fine to *show that artifacts were saved* (the
  stderr `[saved] ...` lines). Do **not** open and scroll a full raw review/decision
  file on camera — those contain your full prompts and model outputs.
- **Provider request details** — don't enable `--save-stages` on camera and then open
  a stage file; don't show verbose HTTP/debug logs that could include request bodies.
- **Copy/paste flashes** — pasting commands from a browser or editor can briefly flash
  **URLs, tokens, or internal paths** on screen. Type them, or paste from a plain
  scratch file you've vetted.
- **Window chrome** — close other tabs/windows; pixel recorders capture the title bar.
  asciinema sidesteps this entirely (text-only) — another reason to prefer it.

### After recording — verify before publishing

1. **Watch the whole cast/GIF once** (`asciinema play demo.cast`).
2. **Scan the text** for anything sensitive. With an asciinema `.cast` you can grep the
   file directly:

   ```sh
   grep -nEi "sk-or-v1-|/Users/|/home/|C:\\\\Users|$USER" demo.cast
   ```

   Note: `sk-or-v1-` is **OpenRouter-specific** — if you ever test mid-recording with
   another provider, that pattern won't catch its key. A keyword grep also misses
   secrets split across frames or buried in escape sequences/error bodies. For anything
   you publish, run a real secrets scanner over the file as the primary control —
   [`gitleaks`](https://github.com/gitleaks/gitleaks) or
   [`trufflehog`](https://github.com/trufflesecurity/trufflehog) — not just `grep`.

   Any hit → **edit the `.cast`** (it's JSON-lines text; `sed`/your editor work) to
   replace the offending span with a redacted placeholder, then re-verify.
3. **If a key was visible in the recording *at all* — even for one frame, even if you
   plan to edit it out — delete the recording and treat that key as exposed.** Don't
   ship an edited cast that ever contained a live key.
4. **Use a dedicated, fresh, low-quota key created right before recording, and rotate
   it immediately after** (or sooner if you abort). That way the demo key is only ever
   valid for a short, low-blast-radius window.

---

## What NOT to show

- The contents of `.env` or any real API key.
- Full raw `.council/` review/decision/stage files.
- Your real home directory, username, or machine name.
- Provider request/response bodies or debug HTTP logs.
- Anything from an unrelated project window.

---

## Where a future demo asset should live

When a recording is approved and made:

- Put the asset under **`docs/assets/`** (e.g. `docs/assets/demo.cast`, and an
  optional `docs/assets/demo.gif` derived from it).
- Keep it **small** — trim dead time, cap GIF dimensions. Aim for a cast/GIF **under
  a few MB** (≈ 2 MB is a good ceiling); large binaries bloat the repo and slow page
  loads.
- Link it from the README **Demo** section and from this guide.
- Re-validate / re-record when the CLI surface or the example files it depends on
  change (the committed `examples/plans/*` are guarded by `tests/test_examples_docs.py`,
  so a missing input is caught — but command output still drifts).

> `docs/assets/` does **not exist yet** and is intentionally empty of binaries until a
> recording is approved. This PR ships the guide only.

---

## Reminder: never commit secrets or local runtime artifacts

Recording the demo creates local artifacts under `.council/` (and a registry under
`data/`). **Never commit:**

- `.env` — your `OPENROUTER_API_KEY`.
- `.council/` — reviews, diffs, decisions, runs, stages, usage, locks (your prompts
  and the models' outputs).
- `data/` — the workspace registry and any `data/decisions/` / `data/cli_runs/`.

The repo `.gitignore` already covers all of these. See
[Privacy & local-first](../README.md#privacy--local-first) and the
[release checklist](release-checklist.md) for the full pre-publish safety pass.
