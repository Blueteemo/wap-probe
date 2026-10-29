"""Controlled loopback HTTP WMLC checks, NOT public-origin evidence.

Only binds 127.0.0.1 in an offline CI runner and never routes loopback through
the production collector, which correctly rejects non-public IP addresses.
"""
from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPHandler, HTTPRedirectHandler, Request

from wap_probe.collector import PROFILES, build_command
from wap_probe.r5_adapter import parse_r5

R5 = Path(os.environ.get("R5_PROBE_DIR",
    ".r5_unpacked/wap-probe-live-discovery-r5/probe"))
MIME = "application/vnd.wap.wmlc"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@contextmanager
def local_wmlc_server(raw: bytes):
    """One-process test fixture, never a public site or production fetch."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/deck.wmlc":
                self.send_response(200)
                self.send_header("Content-Type", MIME)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            elif self.path == "/wrong-type":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            elif self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/deck.wmlc")
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self.send_error(404)

        def log_message(self, *args):
            pass

    host = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=host.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{host.server_port}"
    finally:
        host.shutdown()
        thread.join(timeout=5)
        host.server_close()


class WmlcLoopbackTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = (R5 / "fixtures" / "binary_portal.wmlc").read_bytes()

    def test_actual_http_octets_mime_and_chinese_cards(self):
        with local_wmlc_server(self.body) as base:
            request = Request(base + "/deck.wmlc",
                              headers={"Accept": PROFILES["wmlc"]["Accept"]})
            with build_opener(HTTPHandler(), _NoRedirect()).open(
                    request, timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), MIME)
                raw = response.read()
        self.assertEqual(raw, self.body)
        report = parse_r5(raw, MIME, probe_dir=R5)
        self.assertEqual(len(report["cards"]), 2)
        self.assertEqual(report["cards"][0]["text"], "查看目录")
        self.assertIn("二进制 WAP 页面", report["cards"][1]["text"])
        self.assertIn("#", report["cards"][0]["links"][0]["href"])

    def test_wrong_mime_cannot_be_masqueraded_as_wmlc(self):
        with local_wmlc_server(self.body) as base:
            with build_opener(HTTPHandler(), _NoRedirect()).open(
                    base + "/wrong-type", timeout=5) as response:
                observed_mime = response.headers.get_content_type()
                raw = response.read()
        self.assertEqual(observed_mime, "text/html")
        with self.assertRaises(ValueError):
            parse_r5(raw, observed_mime, probe_dir=R5)

    def test_redirect_not_followed_on_loopback(self):
        with local_wmlc_server(self.body) as base:
            with self.assertRaises(HTTPError) as caught:
                build_opener(HTTPHandler(), _NoRedirect()).open(
                    base + "/redirect", timeout=5)
        self.assertEqual(caught.exception.code, 302)

    def test_truncated_binary_is_not_a_valid_document(self):
        with self.assertRaises((ValueError, IndexError, UnicodeError)):
            parse_r5(self.body[:3], MIME, probe_dir=R5)

    def test_wmlc_preference_does_not_change_existing_profiles(self):
        wmlc = PROFILES["wmlc"]["Accept"]
        self.assertEqual(PROFILES["wmlc"]["User-Agent"],
                         PROFILES["wap1"]["User-Agent"])
        self.assertLess(wmlc.index(MIME), wmlc.index("text/vnd.wap.wml"))
        self.assertTrue(PROFILES["wap1"]["Accept"].startswith("text/vnd.wap.wml"))
        self.assertIn("NokiaE63", PROFILES["s60"]["User-Agent"])

    def test_production_command_does_not_enable_unsafe_localhost(self):
        from wap_probe.collector import validate_url
        with self.assertRaises(ValueError):
            validate_url("http://127.0.0.1/")
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            command = build_command(
                "http://wap.example.org/", "wap.example.org",
                80, "8.8.8.8", "wmlc", Path(temp))
        self.assertIn("Accept: " + PROFILES["wmlc"]["Accept"], command)
        self.assertNotIn("--location", command)
        self.assertNotIn("--insecure", command)


if __name__ == "__main__":
    unittest.main()
