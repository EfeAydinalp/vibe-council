"""Local project workspaces (.council/) and the global project registry.

Stdlib-only. When `vibe` is invoked from another project, council artifacts are
stored under <project>/.council/ and the project is registered in the
vibe-council repo's data/projects.json (which is gitignored, never committed).

PR #4 will build stage/usage metadata, decision search, and cost guards on top
of these directories; this module only creates the structure and saves basic
artifacts.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# Repo root = parent of the backend package. Used for the global registry so it
# resolves correctly regardless of the caller's working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "data" / "projects.json"

WORKSPACE_DIRNAME = ".council"
SUBDIRS = ["reviews", "diffs", "decisions", "runs", "stages", "usage", "locks"]

# Config defaults (suggested). max_preset / require_allow_premium are stored for
# PR #4; this PR enforces only the premium --allow-premium guard in the CLI.
DEFAULT_CONFIG = {
    "default_preset": "balanced",
    "max_preset": "balanced",
    "require_allow_premium": True,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp_slug() -> str:
    """Filesystem-safe UTC timestamp for artifact filenames."""
    return _utc_now().replace(":", "-").replace("+", "_")


def caller_cwd() -> Path:
    """The project directory the user invoked vibe from.

    vibe.ps1 sets VIBE_CALLER_CWD before Push-Location into the repo. When run
    directly (no wrapper), fall back to the current working directory.
    """
    return Path(os.environ.get("VIBE_CALLER_CWD") or os.getcwd()).resolve()


class Workspace:
    """A project's .council/ workspace."""

    def __init__(self, project_path: Path, config: Dict[str, Any]):
        self.project_path = Path(project_path)
        self.config = config

    @property
    def council_dir(self) -> Path:
        return self.project_path / WORKSPACE_DIRNAME

    @property
    def config_path(self) -> Path:
        return self.council_dir / "config.json"

    def subdir(self, name: str) -> Path:
        return self.council_dir / name

    # ---- load / create -----------------------------------------------------
    @classmethod
    def load(cls, project_path: Path) -> Optional["Workspace"]:
        cfg_path = Path(project_path) / WORKSPACE_DIRNAME / "config.json"
        if not cfg_path.exists():
            return None
        try:
            config = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return cls(project_path, config)

    @classmethod
    def create(cls, project_path: Path, project_name: Optional[str] = None) -> "Workspace":
        """Create (or top up) the .council structure and config.json. Idempotent."""
        project_path = Path(project_path).resolve()
        council = project_path / WORKSPACE_DIRNAME
        council.mkdir(parents=True, exist_ok=True)
        for sd in SUBDIRS:
            (council / sd).mkdir(parents=True, exist_ok=True)

        existing = cls.load(project_path)
        now = _utc_now()
        if existing:
            config = existing.config
            config["last_used_at"] = now
            if project_name:
                config["project_name"] = project_name
            for k, v in DEFAULT_CONFIG.items():
                config.setdefault(k, v)
        else:
            config = {
                "project_name": project_name or project_path.name,
                "project_path": str(project_path),
                "created_at": now,
                "last_used_at": now,
                **DEFAULT_CONFIG,
            }

        ws = cls(project_path, config)
        ws._write_config()
        return ws

    def _write_config(self) -> None:
        self.council_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(self.config, indent=2), encoding="utf-8")

    def touch_used(self) -> None:
        """Update last_used_at in config and the global registry."""
        self.config["last_used_at"] = _utc_now()
        try:
            self._write_config()
        except OSError:
            pass
        register_project(self.config.get("project_name", self.project_path.name),
                         self.project_path)

    # ---- artifacts ---------------------------------------------------------
    def save_artifact(self, subdir: str, filename: str, content: str) -> Path:
        d = self.subdir(subdir)
        d.mkdir(parents=True, exist_ok=True)
        path = d / filename
        path.write_text(content, encoding="utf-8")
        return path

    def save_decision(self, record: Dict[str, Any], json_str: str, markdown: str) -> Dict[str, str]:
        d = self.subdir("decisions")
        d.mkdir(parents=True, exist_ok=True)
        slug = str(record.get("timestamp") or timestamp_slug()).replace(":", "-").replace("+", "_")
        jp = d / f"{slug}.json"
        mp = d / f"{slug}.md"
        jp.write_text(json_str, encoding="utf-8")
        mp.write_text(markdown, encoding="utf-8")
        return {"json": str(jp), "markdown": str(mp), "slug": slug}

    # ---- decision index (append-only index.jsonl) --------------------------
    @property
    def decisions_index_path(self) -> Path:
        return self.subdir("decisions") / "index.jsonl"

    def append_decision_index(self, entry: Dict[str, Any]) -> None:
        path = self.decisions_index_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_decision_index(self) -> List[Dict[str, Any]]:
        """Return index entries in file order (oldest first)."""
        path = self.decisions_index_path
        if not path.exists():
            return []
        entries = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def latest(self, subdir: str, suffixes: Optional[List[str]] = None) -> Optional[Path]:
        d = self.subdir(subdir)
        if not d.is_dir():
            return None
        files = [p for p in d.iterdir()
                 if p.is_file() and (suffixes is None or p.suffix in suffixes)]
        if not files:
            return None
        return max(files, key=lambda p: p.stat().st_mtime)


def add_gitignore_entry(project_path: Path, entry: str = ".council/") -> bool:
    """Append `entry` to the project's .gitignore if absent. Returns True if added.

    Never rewrites or removes existing content.
    """
    gi = Path(project_path) / ".gitignore"
    existing = ""
    if gi.exists():
        existing = gi.read_text(encoding="utf-8")
        lines = [ln.strip() for ln in existing.splitlines()]
        if entry in lines or entry.rstrip("/") in lines:
            return False
    sep = "" if (existing == "" or existing.endswith("\n")) else "\n"
    with open(gi, "a", encoding="utf-8") as f:
        f.write(f"{sep}{entry}\n")
    return True


# ---- global registry (data/projects.json, gitignored) ---------------------
def _read_registry() -> List[Dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        return []
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write_registry(items: List[Dict[str, Any]]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


def register_project(name: str, project_path: Path) -> None:
    items = _read_registry()
    p = str(Path(project_path).resolve())
    now = _utc_now()
    for it in items:
        if it.get("project_path") == p:
            it["project_name"] = name
            it["last_used_at"] = now
            _write_registry(items)
            return
    items.append({
        "project_name": name,
        "project_path": p,
        "created_at": now,
        "last_used_at": now,
    })
    _write_registry(items)


def list_projects() -> List[Dict[str, Any]]:
    return _read_registry()
