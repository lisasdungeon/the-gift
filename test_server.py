"""Tests for server.py's request handling: traversal guard, hidden-path
blocking, redirects, conditional requests, and the concurrency cap.

Run with: python3 -m unittest test_server
"""

import os

# Keep the concurrency-cap test cheap — it opens this many real sockets.
os.environ.setdefault("GIFT_MAX_CONCURRENT", "3")

import http.client
import tempfile
import threading
import time
import unittest
from pathlib import Path

import server as gift


class GiftServerTestCase(unittest.TestCase):
    """Exercises the handler against a tiny fixture tree, not the real
    1.8GB library — keeps the suite fast and independent of repo content."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        (root / "README.md").write_text("# The Gift (test fixture)\n")
        (root / "LICENSE").write_text("MIT (test fixture)\n")
        (root / "Bibles").mkdir()
        (root / "Bibles" / "sample.txt").write_text("in the beginning\n")
        (root / "deploy").mkdir()
        (root / "deploy" / "deploy.sh").write_text("#!/bin/sh\necho hi\n")
        (root / ".git").mkdir()
        (root / ".git" / "config").write_text("[core]\n")

        cls._orig_root = gift.ROOT
        gift.ROOT = root

        cls.httpd = gift.BoundedThreadingHTTPServer(("127.0.0.1", 0), gift.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)
        gift.ROOT = cls._orig_root
        cls.tmp.cleanup()

    def request(self, method, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, headers=headers or {})
            resp = conn.getresponse()
            body = resp.read()
            return resp, body
        finally:
            conn.close()

    def test_healthz(self):
        resp, body = self.request("GET", "/healthz")
        self.assertEqual(resp.status, 200)
        self.assertIn(b'"ok": true', body)

    def test_landing_page(self):
        resp, body = self.request("GET", "/")
        self.assertEqual(resp.status, 200)
        self.assertIn(b"<h1>The Gift</h1>", body)

    def test_public_file_served(self):
        resp, body = self.request("GET", "/README.md")
        self.assertEqual(resp.status, 200)
        self.assertTrue(body)

    def test_traversal_dotdot_blocked(self):
        # http.client sends the path as given, unlike curl it does not
        # collapse ../ client-side, so this actually exercises the guard.
        resp, _ = self.request("GET", "/../../../../etc/passwd")
        self.assertEqual(resp.status, 404)

    def test_traversal_encoded_dots_blocked(self):
        resp, _ = self.request("GET", "/%2e%2e/%2e%2e/%2e%2e/etc/passwd")
        self.assertEqual(resp.status, 404)

    def test_hidden_dotgit_file_blocked(self):
        resp, _ = self.request("GET", "/.git/config")
        self.assertEqual(resp.status, 404)

    def test_hidden_deploy_file_blocked(self):
        resp, _ = self.request("GET", "/deploy/deploy.sh")
        self.assertEqual(resp.status, 404)

    def test_hidden_dir_listing_blocked(self):
        resp, _ = self.request("GET", "/deploy/")
        self.assertEqual(resp.status, 404)

    def test_directory_redirects_to_trailing_slash(self):
        resp, _ = self.request("GET", "/Bibles")
        self.assertEqual(resp.status, 301)
        self.assertTrue(resp.getheader("Location", "").endswith("/Bibles/"))

    def test_directory_listing_served(self):
        resp, body = self.request("GET", "/Bibles/")
        self.assertEqual(resp.status, 200)
        self.assertIn(b"<table>", body)

    def test_extensionless_license_served_as_text(self):
        resp, body = self.request("GET", "/LICENSE")
        self.assertEqual(resp.status, 200)
        self.assertTrue(resp.getheader("Content-Type", "").startswith("text/plain"))
        self.assertIn(b"MIT", body)

    def test_etag_conditional_304(self):
        resp, _ = self.request("GET", "/README.md")
        etag = resp.getheader("ETag")
        self.assertTrue(etag)
        resp2, body2 = self.request("GET", "/README.md", headers={"If-None-Match": etag})
        self.assertEqual(resp2.status, 304)
        self.assertEqual(body2, b"")

    def test_favicon_served(self):
        resp, body = self.request("GET", "/favicon.ico")
        self.assertEqual(resp.status, 200)
        self.assertTrue(resp.getheader("Content-Type", "").startswith("image/svg+xml"))
        self.assertIn(b"<svg", body)

    def test_landing_page_has_favicon_link(self):
        resp, body = self.request("GET", "/")
        self.assertEqual(resp.status, 200)
        self.assertIn(b'rel="icon"', body)

    def test_concurrency_cap_returns_503(self):
        """Fill every serving slot with real in-flight requests; a further
        request gets 503, while a connection opened while the server is full
        (no request sent yet) is still served once capacity frees up."""
        blocked = threading.Event()

        def gate(self):
            blocked.wait(timeout=10)  # request stays in flight until released
            return orig_serve(self)

        # park each request inside the handler's serve step so it holds a slot
        orig_serve = gift.Handler._serve
        gift.Handler._serve = gate
        try:
            conns = []
            idle = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            try:
                for _ in range(gift.MAX_CONCURRENT):
                    c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
                    c.request("GET", "/")
                    conns.append(c)
                time.sleep(0.3)  # let them parse and claim every slot
                resp, _ = self.request("GET", "/healthz")
                self.assertEqual(resp.status, 503)

                blocked.set()  # release the parked requests
                for c in conns:
                    r = c.getresponse()
                    self.assertEqual(r.status, 200)
                    r.read()

                # the connection opened while full was never bounced — its
                # request is served normally now that slots are free
                idle.request("GET", "/healthz")
                r2 = idle.getresponse()
                self.assertEqual(r2.status, 200)
                r2.read()
            finally:
                idle.close()
                for c in conns:
                    c.close()
        finally:
            gift.Handler._serve = orig_serve

    def test_keepalive_requests_all_served(self):
        """Several requests over one connection all get served (no per-
        connection slot held between requests)."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            for i in range(3):
                conn.request("GET", "/healthz")
                resp = conn.getresponse()
                body = resp.read()
                self.assertEqual(resp.status, 200)
                self.assertIn(b'"ok": true', body)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
