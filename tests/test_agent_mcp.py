"""MCP stdio protocol and R5-backed WMLC readable-text regression tests."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from wap_probe.agent_browser import page_view
from wap_probe.agent_mcp import BrowserServer
from wap_probe.r5_adapter import parse_capture, parse_r5

R5_DIR = Path(os.environ.get(
    "R5_PROBE_DIR", ".r5_unpacked/wap-probe-live-discovery-r5/probe"
))


def _write_valid_capture(folder: Path, raw: bytes, mime: str) -> None:
    folder.mkdir(parents=True)
    url = "http://wap.example.org/binary.wmlc"
    header = ("HTTP/1.1 200 OK\r\nContent-Type: " + mime
              + "\r\nContent-Length: " + str(len(raw)) + "\r\n\r\n").encode()
    meta = {
        "url": url, "final_url": url, "profile": "wap1",
        "curl_exit_code": 0, "http_status": 200, "content_type": mime,
        "body_bytes": len(raw),
        "body_sha256": hashlib.sha256(raw).hexdigest(),
        "headers_sha256": hashlib.sha256(header).hexdigest(),
        "dns_answers": ["8.8.8.8"], "pinned_ip": "8.8.8.8",
        "remote_ip": "8.8.8.8",
    }
    (folder / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (folder / "headers.bin").write_bytes(header)
    (folder / "body.bin").write_bytes(raw)


class AgentWmlcTests(unittest.TestCase):
    def test_binary_wmlc_decodes_to_readable_chinese(self):
        source = (R5_DIR / "fixtures" / "binary_portal.wmlc").read_bytes()
        parsed = parse_r5(source, "application/vnd.wap.wmlc", probe_dir=R5_DIR)
        self.assertIn("查看目录", [card["text"] for card in parsed["cards"]])
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t) / "page"
            _write_valid_capture(folder, source, "application/vnd.wap.wmlc")
            record = parse_capture(folder, probe_dir=R5_DIR)
            (folder / "r5_export.json").write_text(json.dumps(record), encoding="utf-8")
            view = page_view(folder)
            self.assertTrue(view["ok"])
            self.assertTrue(view["text_available"])
            self.assertEqual(view["format"], "wmlc")
            self.assertIn("查看目录", view["text"])
            second = page_view(folder, card_index=1)
            self.assertEqual(second["active_card_index"], 1)
            self.assertIn("二进制 WAP 页面", second["text"])
            self.assertEqual(view["card_count"], second["card_count"])
            self.assertTrue(view["card_links"] or view["card_count"] >= 1)

    def test_modified_r5_export_text_not_blindly_trusted(self):
        source = (R5_DIR / "fixtures" / "binary_portal.wmlc").read_bytes()
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t) / "page"
            _write_valid_capture(folder, source, "application/vnd.wap.wmlc")
            record = parse_capture(folder, probe_dir=R5_DIR)
            record["cards"][0]["text"] = "A" * 12001
            (folder / "r5_export.json").write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid R5 card text"):
                page_view(folder)


class MCPProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = BrowserServer(Path(self.temp.name), allow_network=False)

    def tearDown(self):
        self.temp.cleanup()

    def request(self, method, params=None):
        return self.server.dispatch({"jsonrpc": "2.0", "id": 1,
                                     "method": method, "params": params or {}})

    def test_initialize(self):
        r = self.request("initialize", {"protocolVersion": "2025-11-25",
                                        "clientInfo": {"name": "test", "version": "1"}})
        self.assertEqual(r["result"]["protocolVersion"], "2025-11-25")
        self.assertIn("tools", r["result"]["capabilities"])

    def test_tools_discovery_and_ping(self):
        tools = self.request("tools/list")["result"]["tools"]
        self.assertEqual({t["name"] for t in tools},
                         {"wap_open", "wap_follow", "wap_read", "wap_back", "wap_card", "wap_form_plan"})
        self.assertEqual(self.request("ping")["result"], {})

    def test_notifications_no_response(self):
        self.assertIsNone(self.server.dispatch({"jsonrpc": "2.0",
                          "method": "notifications/initialized"}))

    def test_explicit_two_gate_network_permission(self):
        for args in [
            {"url": "http://wap.example.org/", "execute": False},
            {"url": "http://wap.example.org/", "execute": True},
        ]:
            r = self.request("tools/call", {"name": "wap_open", "arguments": args})
            self.assertTrue(r["result"]["isError"])
        self.assertEqual(self.server.sessions, {})

    def test_unknown_session_and_no_filesystem_path_access(self):
        r = self.request("tools/call", {"name": "wap_read",
                         "arguments": {"session_id": "/etc/passwd"}})
        self.assertTrue(r["result"]["isError"])

    def test_no_kwargs_extra_and_boolean_link(self):
        self.server.allow_network = True
        r = self.request("tools/call", {"name": "wap_follow",
            "arguments": {"session_id": "none", "link": True, "execute": True}})
        self.assertTrue(r["result"]["isError"])
        r = self.request("tools/call", {"name": "wap_open",
            "arguments": {"url": "http://wap.example.org/", "execute": True,
                          "password": "should-not-accept"}})
        self.assertTrue(r["result"]["isError"])

    def test_stdio_starts_and_returns_only_json_lines(self):
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-11-25"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "wap_open",
                        "arguments": {"url": "http://wap.example.org/",
                                      "execute": True}}},
        ]
        proc = subprocess.run(
            [sys.executable, "-m", "wap_probe.agent_mcp"],
            input="".join(json.dumps(x) + "\n" for x in msgs),
            text=True, capture_output=True, timeout=8,
            env={**os.environ, "PYTHONPATH": "src"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        answers = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual([x["id"] for x in answers], [1, 2, 3])
        self.assertTrue(answers[-1]["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
