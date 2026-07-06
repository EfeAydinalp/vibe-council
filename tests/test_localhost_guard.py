"""Localhost-only guard for the app's server surface (v0.8.0 PR 3).

This is the council's **mandatory phase guardrail** (v0.8.x plan §5 / §6 PR 3): it locks
the invariant that the only server the app runs — the Workbench panel — binds **loopback
only**, and that **no other module** constructs a listening socket/server. It adds NO
production behavior; the panel already enforces localhost-only (make_server input
allowlist + a post-bind re-check). These tests pin that so it cannot silently drift into
LAN/hosted exposure.

Deterministic and offline: the runtime check binds to an ephemeral loopback port and
closes immediately (no `serve_forever`); the static check reads source text only.

Scope/limits: this is a **code-drift tripwire**, not a runtime sandbox. It catches a new
listening surface being *added to the source* (the realistic regression) and pins the
panel's own loopback enforcement; it does not defend against a hostile process or a
listener conjured through indirection the source scan can't see. Widening `ALLOWLIST` or
`LISTENER_TOKENS` should be treated as a security-relevant change, reviewed, not a routine
edit to make a red test green.
"""

import socket
import unittest
from pathlib import Path

from backend import workbench_panel as wp

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"

# Addresses a bound server socket may actually listen on.
LOOPBACK = ("127.0.0.1", "::1")

# Non-loopback hosts that must never be accepted / bound.
NON_LOCAL_HOSTS = ("0.0.0.0", "::", "192.168.1.50", "10.0.0.5", "172.16.0.9",
                   "203.0.113.7", "example.com", "")


class TestPanelBindsLoopbackOnly(unittest.TestCase):
    """The Workbench panel is the app's only server; it binds loopback only."""

    def _root(self):
        import shutil
        import tempfile
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(d, ignore_errors=True))
        return Path(d)

    def test_default_host_is_loopback(self):
        httpd = wp.make_server(self._root(), port=0)
        try:
            self.assertIn(wp.effective_bind_host(httpd), LOOPBACK)
        finally:
            httpd.server_close()

    def test_make_server_rejects_non_local_hosts(self):
        root = self._root()
        for host in NON_LOCAL_HOSTS:
            with self.assertRaises(ValueError, msg=f"accepted non-local host {host!r}"):
                wp.make_server(root, host=host, port=0)

    def test_socket_bind_calls_are_all_loopback(self):
        # Runtime guard (plan's primary mechanism): record every socket bind that happens
        # while the panel server is created, and assert each is a loopback address.
        recorded = []
        orig_bind = socket.socket.bind

        def spy_bind(self, address):
            recorded.append(address)
            return orig_bind(self, address)

        socket.socket.bind = spy_bind
        try:
            httpd = wp.make_server(self._root(), port=0)
            httpd.server_close()
        finally:
            socket.socket.bind = orig_bind

        self.assertTrue(recorded, "no socket bind was observed")
        for address in recorded:
            host = address[0]
            self.assertIn(host, LOOPBACK,
                          f"panel bound a non-loopback address: {address!r}")

    def test_host_header_validation_accepts_only_loopback(self):
        for good in ("127.0.0.1", "127.0.0.1:8765", "localhost", "localhost:8765",
                     "[::1]:8765"):
            self.assertTrue(wp.host_header_is_local(good), good)
        for bad in ("0.0.0.0:8765", "192.168.1.50:8765", "10.0.0.5", "evil.example.com",
                    "attacker.test:8765", None, ""):
            self.assertFalse(wp.host_header_is_local(bad), repr(bad))

    def test_serve_uses_loopback_host(self):
        # The blocking serve() entry point binds 127.0.0.1 (asserted via make_server, which
        # serve() calls with host="127.0.0.1"); pin the constant it relies on.
        self.assertIn("127.0.0.1", wp._LOCAL_HOSTS)
        self.assertEqual(wp._LOOPBACK_ADDRS, ("127.0.0.1", "::1"))


class TestNoSecondListener(unittest.TestCase):
    """No module outside the panel constructs a listening socket/server. If this fails,
    a new network-listening surface has appeared — that is a security finding to surface,
    not to silence by editing the allowlist without review."""

    # The ONLY module permitted to construct a listening server.
    ALLOWLIST = {"workbench_panel.py"}

    # Source tokens that indicate constructing/serving a network listener.
    LISTENER_TOKENS = (
        "HTTPServer(", "ThreadingHTTPServer(", "socketserver", ".serve_forever(",
        ".listen(", "from http.server import", "import http.server",
    )

    def test_only_panel_constructs_a_listener(self):
        offenders = {}
        for py in sorted(BACKEND.glob("*.py")):
            if py.name in self.ALLOWLIST:
                continue
            text = py.read_text(encoding="utf-8", errors="replace")
            hits = [tok for tok in self.LISTENER_TOKENS if tok in text]
            if hits:
                offenders[py.name] = hits
        self.assertEqual(offenders, {},
                         "a module outside the panel appears to construct a network "
                         f"listener (SECURITY: review before allowlisting): {offenders}")

    def test_socket_bind_only_in_panel(self):
        # A raw ``socket.bind(``/``.bind((`` outside the panel would be a second bind
        # surface; assert there is none.
        offenders = []
        for py in sorted(BACKEND.glob("*.py")):
            if py.name in self.ALLOWLIST:
                continue
            text = py.read_text(encoding="utf-8", errors="replace")
            if "socket.bind(" in text or ".bind((" in text:
                offenders.append(py.name)
        self.assertEqual(offenders, [],
                         f"raw socket bind found outside the panel: {offenders}")


if __name__ == "__main__":
    unittest.main()
