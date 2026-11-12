# -*- coding: utf-8 -*-
"""Proxy flag: sessions must go through the configured proxy and credentials must never be logged."""
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import web


class RecordingProxy(BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        RecordingProxy.seen.append((self.path, self.headers.get("Proxy-Authorization")))
        body = b"<html><body>via proxy</body></html>"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class TestProxy(unittest.TestCase):
    def tearDown(self):
        web.configure_proxy(None)

    def test_no_proxy_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(web.PROXY_ENV, None)
            self.assertIsNone(web.configure_proxy(None))
        self.assertEqual(web.new_session().proxies, {})

    def test_env_fallback_and_flag_priority(self):
        with mock.patch.dict(os.environ, {web.PROXY_ENV: "http://envhost:1111"}):
            self.assertEqual(web.configure_proxy(None), "http://envhost:1111")
            self.assertEqual(web.configure_proxy("http://flaghost:2222"), "http://flaghost:2222")

    def test_description_hides_credentials(self):
        d = web.configure_proxy("http://tok%40en:1@10.0.0.1:8080")
        self.assertEqual(d, "http://10.0.0.1:8080")
        self.assertNotIn("tok", d)

    def test_rejects_malformed_url(self):
        for bad in ("10.0.0.1:8080", "ftp://h:1", "http://"):
            with self.assertRaises(ValueError, msg=bad):
                web.configure_proxy(bad)

    def test_session_uses_proxy_even_if_env_proxy_is_set(self):
        srv = HTTPServer(("127.0.0.1", 0), RecordingProxy)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            RecordingProxy.seen.clear()
            web.configure_proxy(f"http://user:pw@127.0.0.1:{srv.server_port}")
            with mock.patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9"}):
                soup = web.fetch_soup(web.new_session(), "http://example.invalid/page", retries=1)
            self.assertIn("via proxy", soup.text)
            self.assertEqual(RecordingProxy.seen[0][0], "http://example.invalid/page")
            self.assertTrue(RecordingProxy.seen[0][1].startswith("Basic "))
        finally:
            srv.shutdown()
            srv.server_close()


class FakeRun:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.r = mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

    def __call__(self, *a, **k):
        return self.r


class TestUrbanJp(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.object(web, "URBAN_SCRIPT_DIR", os.path.dirname(os.path.abspath(__file__)))
        self.patch.start()
        os.makedirs(os.path.join(web.URBAN_SCRIPT_DIR, "node_modules"), exist_ok=True)

    def tearDown(self):
        self.patch.stop()
        os.rmdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "node_modules"))
        web.configure_proxy(None)

    def test_returns_single_url(self):
        url = web.fetch_urban_jp(run=FakeRun(stdout="http://tok:1@1.2.3.4:8081\n"))
        self.assertEqual(url, "http://tok:1@1.2.3.4:8081")

    def test_failure_message_comes_from_stderr(self):
        run = FakeRun(returncode=1, stdout="", stderr="urban proxy: skipped p-jp1: timed out\nurban proxy failed: no working JP server")
        with self.assertRaisesRegex(ValueError, "no working JP server"):
            web.fetch_urban_jp(run=run)

    def test_rejects_unexpected_output(self):
        with self.assertRaises(ValueError):
            web.fetch_urban_jp(run=FakeRun(stdout="a b"))

    def test_configure_uses_urban_jp_and_hides_credentials(self):
        with mock.patch.object(web, "fetch_urban_jp", return_value="http://secret:1@1.2.3.4:8081"):
            d = web.configure_proxy("urban-jp")
        self.assertEqual(d, "http://1.2.3.4:8081")
        self.assertEqual(web.new_session().proxies["https"], "http://secret:1@1.2.3.4:8081")

    def test_missing_dependencies_message(self):
        with mock.patch.object(web, "URBAN_SCRIPT_DIR", "/nonexistent"):
            with self.assertRaisesRegex(ValueError, "npm install"):
                web.fetch_urban_jp()


if __name__ == "__main__":
    unittest.main()
