"""Structural tests for the cross-platform install wrappers.

Stdlib-only (`unittest`), no extra dependencies, and **OS-agnostic**: these are
file-content assertions, so they pass on Windows CI too without executing the
shell scripts. Behavioral (run-the-script) coverage lives in CI on Ubuntu/macOS.

They guard against the most likely regressions:
- a wrapper going missing or losing its shebang,
- the POSIX launcher being copy-pasted from vibe.ps1 with a hardcoded Windows path,
- the env-handling contract (VIBE_CALLER_CWD / VIBE_COUNCIL_HOME / backend.cli)
  silently drifting.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class TestWrappersExist(unittest.TestCase):
    def test_vibe_sh_exists_with_shebang(self):
        p = SCRIPTS / "vibe.sh"
        self.assertTrue(p.is_file(), f"missing {p}")
        self.assertTrue(read(p).startswith("#!"), "vibe.sh must start with a shebang")

    def test_install_vibe_sh_exists_with_shebang(self):
        p = SCRIPTS / "install-vibe.sh"
        self.assertTrue(p.is_file(), f"missing {p}")
        self.assertTrue(read(p).startswith("#!"), "install-vibe.sh must start with a shebang")

    def test_windows_wrappers_still_present(self):
        # Cross-platform support must not have removed the Windows path.
        for name in ("vibe.ps1", "vibe.cmd", "install-vibe.ps1"):
            self.assertTrue((SCRIPTS / name).is_file(), f"missing scripts/{name}")


class TestLauncherEnvHandling(unittest.TestCase):
    def setUp(self):
        self.text = read(SCRIPTS / "vibe.sh")

    def test_references_env_contract(self):
        for token in ("VIBE_CALLER_CWD", "VIBE_COUNCIL_HOME", "VIBE_PYTHON"):
            self.assertIn(token, self.text, f"vibe.sh should handle {token}")

    def test_invokes_backend_cli(self):
        self.assertIn("backend.cli", self.text)

    def test_no_hardcoded_windows_path(self):
        # Guards against a Windows-style absolute path leaking into the POSIX launcher.
        self.assertNotIn("C:\\", self.text)
        self.assertNotIn("C:/", self.text)

    def test_preflight_dependency_check(self):
        # A clear message instead of a raw ModuleNotFoundError.
        self.assertIn("import backend.cli", self.text)


class TestInstallerBehaviorContract(unittest.TestCase):
    def setUp(self):
        self.text = read(SCRIPTS / "install-vibe.sh")

    def test_user_local_bin_default(self):
        self.assertIn(".local/bin", self.text)

    def test_mentions_path(self):
        self.assertIn("PATH", self.text)

    def test_supports_dry_run_and_force(self):
        for flag in ("--dry-run", "--force", "--bin-dir"):
            self.assertIn(flag, self.text)

    def test_no_sudo_invocation(self):
        # User-local install must never shell out to sudo. "sudo" may appear in a
        # comment ("never requires sudo"); only flag it in executable lines.
        code_lines = [ln for ln in self.text.splitlines()
                      if ln.strip() and not ln.lstrip().startswith("#")]
        offenders = [ln for ln in code_lines if "sudo" in ln]
        self.assertEqual(offenders, [], f"sudo used in: {offenders}")


if __name__ == "__main__":
    unittest.main()
