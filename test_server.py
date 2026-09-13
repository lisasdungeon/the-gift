"""Tests for server.py's request handling: traversal guard, hidden-path
blocking, redirects, conditional requests, and the concurrency cap.

Run with: python3 -m unittest test_server
"""

import os

# Keep the concurrency-cap test cheap — it opens this many real sockets.
os.environ.setdefault("GIFT_MAX_CONCURRENT", "3")

import http.client
import socket
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

    def test_etag_conditional_304(self):
        resp, _ = self.request("GET", "/README.md")
        etag = resp.getheader("ETag")
        self.assertTrue(etag)
        resp2, body2 = self.request("GET", "/README.md", headers={"If-None-Match": etag})
        self.assertEqual(resp2.status, 304)
        self.assertEqual(body2, b"")

    def test_concurrency_cap_returns_503(self):
        hogs = []
        try:
            for _ in range(gift.MAX_CONCURRENT):
                hogs.append(socket.create_connection(("127.0.0.1", self.port), timeout=5))
            time.sleep(0.3)  # let process_request() claim every slot
            resp, _ = self.request("GET", "/healthz")
            self.assertEqual(resp.status, 503)
        finally:
            for s in hogs:
                s.close()


if __name__ == "__main__":
    unittest.main()
