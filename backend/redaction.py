"""Minimal, stdlib-only redaction guard for public docs.

Pattern-based scanner that flags risky content (API keys, private keys, secret
assignments, local user paths, concrete raw `.council/` artifact paths, Obsidian
workspace state) plus advisory warnings (the private commercial-plan filename,
cost/pricing details, raw-output markers).

This is **defense-in-depth, not a guarantee** (see `docs/redaction-policy.md`):
a pattern scanner can miss secrets and human review remains required. It exists
so generated/promoted docs can be checked before they are committed or shared.

Design notes:
- Per-line regex scanning -> deterministic, fast, exact line/column.
- Two severities: ``critical`` (a real leak; fails by default) and ``warning``
  (advisory; only fails under ``--strict``).
- Secret/path matches are **masked** in output so the scanner never reprints a
  full secret or username.
- Concrete `.council/` artifacts are matched only when **date-prefixed**
  (e.g. ``.council/reviews/2026-06-29T...``), so the many benign convention
  mentions (``.council/decisions/``, ``index.jsonl``) do not false-positive.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional

CRITICAL = "critical"
WARNING = "warning"

# Directories never walked on a default scan (or when expanding a passed dir).
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", ".council", "data", "node_modules", "__pycache__",
    ".obsidian", "dist", "build", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
    ".tox", ".eggs",
}

# Extensions scanned when expanding a directory (explicit single files are read
# regardless of extension).
TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".rst", ".json", ".jsonl", ".yaml", ".yml",
    ".toml", ".cfg", ".ini", ".env", ".py", ".sh", ".ps1", ".cmd",
}

# Top-level markdown files included in a default scan, if present.
ROOT_MARKDOWN = ("README.md", "CLAUDE.md", "AGENTS.md", "CHANGELOG.md", "RULES.md")

_MAX_BYTES = 5_000_000  # skip absurdly large files

# Placeholder user-names that are safe in a path (not a real per-user leak).
_PLACEHOLDER_NAMES = {
    "dev", "you", "user", "me", "name", "runner", "username", "example",
    "youruser", "your-user", "someone", "demo",
}

# A "secret-shaped" value: an sk-prefixed token or a long base64/hex-ish blob.
# Deliberately strict so placeholders like ``<key>``, ``...``, ``your-key`` do
# not match (they contain ``<`` / ``.`` / too few chars).
_SECRET_VAL = r"(?:sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9+/_-]{16,})"
_SECRET_VAL_SHORT = r"(?:sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9+/_-]{12,})"


class Rule(NamedTuple):
    id: str
    severity: str
    regex: "re.Pattern[str]"
    message: str
    redact: str  # "secret" | "path" | "none"


class Finding(NamedTuple):
    path: str
    line: int
    col: int
    rule_id: str
    severity: str
    message: str
    match: str  # already masked / safe for display


RULES: List[Rule] = [
    # --- critical -------------------------------------------------------- #
    Rule("openrouter-key", CRITICAL,
         re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}"),
         "OpenRouter API key", "secret"),
    Rule("private-key-block", CRITICAL,
         re.compile(r"BEGIN\s+[A-Z0-9]+(?:\s+[A-Z0-9]+)*\s+PRIVATE\s+KEY"),
         "Private key block marker", "secret"),
    Rule("api-key-assignment", CRITICAL,
         re.compile(r"\b[A-Z][A-Z0-9_]*API_KEY\s*=\s*['\"]?(?P<val>" + _SECRET_VAL + r")"),
         "API key assignment with a secret-shaped value", "secret"),
    Rule("secret-assignment", CRITICAL,
         re.compile(r"\b\w*(?:SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE_KEY)\w*\s*=\s*"
                    r"['\"]?(?P<val>" + _SECRET_VAL_SHORT + r")"),
         "Secret/token/password assignment with a secret-shaped value", "secret"),
    Rule("windows-user-path", CRITICAL,
         re.compile(r"C:\\Users\\(?P<name>[A-Za-z0-9_.\-]+)"),
         "Windows per-user local path", "path"),
    Rule("unix-user-path", CRITICAL,
         re.compile(r"/(?:Users|home)/(?P<name>[A-Za-z0-9_.\-]+)"),
         "Unix per-user local path", "path"),
    Rule("council-artifact-path", CRITICAL,
         re.compile(r"\.council[\\/](?:reviews|decisions|context|runs|stages|usage|diffs)"
                    r"[\\/](?P<art>\d{4}-\d{2}-\d{2}[^\s)\]]*)"),
         "Concrete raw .council/ artifact path (date-stamped)", "none"),
    Rule("obsidian-workspace", CRITICAL,
         re.compile(r"\.obsidian[\\/]workspace"),
         "Obsidian workspace/config state path", "none"),
    # --- warning (advisory; fails only under --strict) ------------------- #
    Rule("private-plan-filename", WARNING,
         re.compile(r"commercialization-and-hosted-platform-feasibility"),
         "Reference to the private commercial feasibility plan filename", "none"),
    # A *concrete* local/private profile artifact filename (v0.7.1 hardening). The
    # local `.council/profile.*` store is machine-local and must never be committed.
    # WARNING (not CRITICAL) — legitimate design-doc references to the concrete name
    # exist, matching the `private-plan-filename` precedent; operational/policy text
    # should prefer the glob form `.council/profile.*`, which this rule deliberately
    # does NOT match (the discriminator). Promotion path: when a real
    # `.council/profile.*` store ships, a concrete reference in public docs becomes a
    # live-artifact leak — promote this rule to CRITICAL then and glob-form the docs.
    Rule("local-profile-path", WARNING,
         re.compile(r"\.council[\\/]profile\.(?:json|md|toml|ya?ml)"),
         "Reference to a local/private profile artifact "
         "(never commit; `.council/profile.*` is machine-local)", "none"),
    Rule("cost-pricing", WARNING,
         re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s*/\s*(?:mo|month|seat|yr|year|user)"
                    r"|\bper\s+seat\b|\bmonthly\s+infra\b|\bcost\s+table\b"),
         "Possible cost/pricing detail (review if private)", "none"),
    Rule("raw-output-marker", WARNING,
         re.compile(r"\[usage\]\s+Reported\s+tokens|Provider-reported\s+cost\s*\("
                    r"|\[saved\]\s+\S*\.council[\\/]"),
         "Possible raw council output marker", "none"),
]


def _is_placeholder_name(name: str) -> bool:
    return name.lower() in _PLACEHOLDER_NAMES


def _mask_secret(s: str) -> str:
    """Mask a secret-like value: keep a short prefix, hide the rest."""
    s = s.strip("'\"")
    keep = min(4, len(s))
    return s[:keep] + "***[" + str(len(s)) + " chars]"


def _mask_path_name(match: "re.Match[str]") -> str:
    """Replace the captured per-user name with ***, keep the rest visible."""
    name = match.group("name")
    return match.group(0).replace(name, "***", 1)


def _display(rule: Rule, match: "re.Match[str]") -> str:
    if rule.redact == "secret":
        val = match.groupdict().get("val") or match.group(0)
        return _mask_secret(val)
    if rule.redact == "path":
        return _mask_path_name(match)
    text = match.group(0)
    return text if len(text) <= 80 else text[:77] + "..."


def scan_text(text: str, path: str = "<text>") -> List[Finding]:
    """Scan in-memory text; return findings (deterministic order)."""
    findings: List[Finding] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for rule in RULES:
            for m in rule.regex.finditer(line):
                if rule.redact == "path" and _is_placeholder_name(m.group("name")):
                    continue
                findings.append(Finding(
                    path=path, line=lineno, col=m.start() + 1,
                    rule_id=rule.id, severity=rule.severity,
                    message=rule.message, match=_display(rule, m),
                ))
    return findings


def scan_file(path: Path) -> List[Finding]:
    """Scan a single file; unreadable/oversized files yield no findings."""
    try:
        if path.stat().st_size > _MAX_BYTES:
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return []
    return scan_text(text, str(path))


def _walk_dir(root: Path) -> Iterable[Path]:
    """Yield text files under root, skipping EXCLUDE_DIRS."""
    import os
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in TEXT_SUFFIXES:
                yield p


def _git_tracked_docs(root: Path) -> Optional[List[Path]]:
    """Tracked docs/*.md + tracked top-level markdown, via git. None on failure."""
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "docs", "*.md"],
            capture_output=True, text=True, encoding="utf-8", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    files = [f for f in r.stdout.split("\0") if f]
    out: List[Path] = []
    for f in files:
        p = (root / f)
        # tracked set already excludes gitignored .council/, data/, .venv/, etc.
        if p.suffix.lower() in TEXT_SUFFIXES and p.is_file():
            out.append(p)
    return out or None


def default_targets(root: Path) -> List[Path]:
    """Public docs likely to be committed: tracked docs (via git) if available,
    else a filesystem walk of docs/ + top-level markdown (EXCLUDE_DIRS skipped)."""
    tracked = _git_tracked_docs(root)
    if tracked is not None:
        return sorted(set(tracked))
    targets: List[Path] = []
    docs = root / "docs"
    if docs.is_dir():
        targets.extend(_walk_dir(docs))
    for name in ROOT_MARKDOWN:
        p = root / name
        if p.is_file():
            targets.append(p)
    return sorted(set(targets))


def collect_targets(paths: Iterable[str], root: Path) -> List[Path]:
    """Resolve explicit paths (files as-is, dirs walked) or fall back to the
    default public-docs set when no paths are given."""
    paths = list(paths)
    if not paths:
        return default_targets(root)
    out: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(_walk_dir(p))
        elif p.is_file():
            out.append(p)
    # de-dup, stable order
    seen, ordered = set(), []
    for p in out:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            ordered.append(p)
    return ordered


def scan_paths(paths: Iterable[str], root: Path) -> List[Finding]:
    findings: List[Finding] = []
    for f in collect_targets(paths, root):
        findings.extend(scan_file(f))
    return findings


def has_blocking(findings: Iterable[Finding], strict: bool = False) -> bool:
    """True if any finding should fail the run: criticals always; warnings only
    under strict."""
    for f in findings:
        if f.severity == CRITICAL or (strict and f.severity == WARNING):
            return True
    return False
