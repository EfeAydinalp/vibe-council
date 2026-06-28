"""Privacy/portability guard: no hardcoded local developer paths in public files.

Stdlib-only (`unittest`), OS-agnostic file-content assertions. These guard against a
specific regression: a maintainer's local absolute path (e.g.
``C:\\Users\\<name>\\Desktop\\llm-council``) leaking into the launcher or the docs,
which is both a privacy leak and a portability bug.

The PowerShell launcher must derive the repo root from its own location instead of
hardcoding any user path. Behavioral (run-the-script) coverage of ``vibe.ps1`` lives in
CI / manual checks; here we only assert on file contents so the suite stays portable.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VIBE_PS1 = REPO_ROOT / "scripts" / "vibe.ps1"

# Any per-user home path is a leak, regardless of the specific username. We capture
# the username segment so placeholders (``<you>``) and bare-prefix mentions in
# redaction checklists (``C:\Users\`` followed by a backtick) don't false-positive.
WINDOWS_USER_PATH = re.compile(r"C:\\Users\\([A-Za-z0-9_.-]+)", re.IGNORECASE)
POSIX_USER_PATH = re.compile(r"/(?:Users|home)/(?!<)([A-Za-z0-9_.-]+)")

# Generic placeholder names that are fine to ship in docs.
PLACEHOLDER_NAMES = {"dev", "you", "user", "me", "name", "runner", "username"}


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def public_text_files():
    """Public, human-facing files that must not embed a developer-local path."""
    files = [REPO_ROOT / "README.md", VIBE_PS1]
    files += sorted((REPO_ROOT / "docs").rglob("*.md"))
    return [p for p in files if p.is_file()]


class TestNoHardcodedDevPaths(unittest.TestCase):
    def test_no_windows_user_path_in_public_files(self):
        offenders = []
        for p in public_text_files():
            for i, line in enumerate(read(p).splitlines(), 1):
                for m in WINDOWS_USER_PATH.finditer(line):
                    if m.group(1).lower() not in PLACEHOLDER_NAMES:
                        offenders.append(
                            f"{p.relative_to(REPO_ROOT)}:{i}: {line.strip()}"
                        )
        self.assertEqual(
            offenders, [],
            "hardcoded C:\\Users\\<name> path(s) found:\n" + "\n".join(offenders),
        )

    def test_no_posix_user_home_path_in_public_files(self):
        # Generic placeholders like /home/dev/... or /path/to/... are fine; a real
        # per-user home (/Users/<name>, /home/<name>) is not.
        offenders = []
        for p in public_text_files():
            for i, line in enumerate(read(p).splitlines(), 1):
                for m in POSIX_USER_PATH.finditer(line):
                    if m.group(1).lower() not in PLACEHOLDER_NAMES:
                        offenders.append(
                            f"{p.relative_to(REPO_ROOT)}:{i}: {line.strip()}"
                        )
        self.assertEqual(
            offenders, [],
            "hardcoded POSIX home path(s) found:\n" + "\n".join(offenders),
        )


class TestLauncherDerivesRepoRoot(unittest.TestCase):
    def setUp(self):
        self.text = read(VIBE_PS1)

    def test_no_hardcoded_user_path(self):
        self.assertIsNone(
            WINDOWS_USER_PATH.search(self.text),
            "vibe.ps1 must not hardcode a C:\\Users\\<name> path",
        )

    def test_respects_env_override(self):
        self.assertIn("VIBE_COUNCIL_HOME", self.text)

    def test_derives_root_from_script_location(self):
        # Falls back to the script's own directory, not a baked-in path.
        self.assertIn("MyInvocation", self.text)
        self.assertIn("Split-Path", self.text)

    def test_preserves_launcher_contract(self):
        for token in ("VIBE_CALLER_CWD", "backend.cli", "Push-Location", "Pop-Location"):
            self.assertIn(token, self.text, f"vibe.ps1 should still reference {token}")


if __name__ == "__main__":
    unittest.main()
