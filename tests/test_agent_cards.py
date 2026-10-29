"""Real frozen-R5 multi-card navigation, local history, and MCP tests (offline)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from wap_probe import agent_browser as a
from wap_probe.agent_mcp import BrowserServer
from wap_probe.r5_adapter import parse_capture

PROBE = Path(os.environ.get(
    "R5_PROBE_DIR", ".r5_unpacked/wap-probe-live-discovery-r5/probe"
))
HOME = "http://wap.example.org/"
BODY = (
    b'<wml><card id="start"><p>Start <a href="#second">Second card</a>'
    b' <a href="first.wml">First page</a></p></card>'
    b'<card id="second"><p>Second view <a href="detail.wml">'
    b'Detail</a></p></card></wml>'
)
DETAIL = b'<wml><card id="detail"><p>Another document</p></card></wml>'


def write_page(folder: Path, url: str, body: bytes):
    folder.mkdir(parents=True)
    headers = (f"HTTP/1.1 200 OK\r\nContent-Type: text/vnd.wap.wml\r\n"
               f"Content-Length: {len(body)}\r\n\r\n").encode()
    meta = {
        "url": url, "final_url": url, "profile": "wap1",
        "curl_exit_code": 0, "http_status": 200,
        "content_type": "text/vnd.wap.wml", "body_bytes": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "headers_sha256": hashlib.sha256(headers).hexdigest(),
        "dns_answers": ["8.8.8.8"],
        "pinned_ip": "8.8.8.8", "remote_ip": "8.8.8.8",
    }
    (folder / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (folder / "headers.bin").write_bytes(headers)
    (folder / "body.bin").write_bytes(body)
    export = parse_capture(folder, probe_dir=PROBE)
    (folder / "r5_export.json").write_text(json.dumps(export), encoding="utf-8")


class AgentCardsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "session"
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def capture(self, url, profile, folder):
        self.calls.append(url)
        data = BODY if url == HOME else DETAIL
        write_page(folder, url, data)

    def start(self):
        return a.open_page(HOME, self.root, capture_page=self.capture)

    def test_only_active_card_links_visible(self):
        first = self.start()
        self.assertTrue(first["ok"])
        self.assertEqual(first["card_count"], 2)
        self.assertEqual(first["active_card_index"], 0)
        self.assertEqual([x["id"] for x in first["cards"]], ["start", "second"])
        self.assertEqual([x["target_index"] for x in first["card_links"]], [1])
        self.assertEqual([x["url"] for x in first["links"]], [HOME + "first.wml"])
        self.assertIn("Start", first["text"])
        self.assertNotIn("Second view", first["text"])
        second = a.select_card(self.root, 1)
        self.assertEqual(second["active_card_index"], 1)
        self.assertEqual(second["card_links"], [])
        self.assertEqual([x["url"] for x in second["links"]], [HOME + "detail.wml"])
        self.assertIn("Second view", second["text"])
        self.assertEqual(len(self.calls), 1, "Card switch must not send a GET")

    def test_card_then_page_then_back_restores_selected_card(self):
        self.start()
        a.select_card(self.root, 1)
        page = a.follow_link(self.root, 0, capture_page=self.capture)
        self.assertEqual(page["page_count"], 2)
        self.assertEqual(self.calls, [HOME, HOME + "detail.wml"])
        back_to_card = a.go_back(self.root)
        self.assertEqual(back_to_card["cursor"], 0)
        self.assertEqual(back_to_card["active_card_index"], 1)
        self.assertEqual([x["url"] for x in back_to_card["links"]], [HOME + "detail.wml"])
        back_to_start = a.go_back(self.root)
        self.assertEqual(back_to_start["active_card_index"], 0)
        self.assertEqual(self.calls, [HOME, HOME + "detail.wml"])

    def test_invalid_card_no_mutation_or_network(self):
        self.start()
        old = (self.root / "session.json").read_bytes()
        for index in (True, -1, 2, 500):
            with self.assertRaises(ValueError):
                a.select_card(self.root, index)
        self.assertEqual((self.root / "session.json").read_bytes(), old)
        self.assertEqual(len(self.calls), 1)

    def test_cli_card_command_is_offline(self):
        self.start()
        with patch("builtins.print"):
            self.assertEqual(a.main(["card", "--session", str(self.root),
                                     "--index", "1"]), 0)
        self.assertEqual(a.read_page(self.root)["active_card_index"], 1)
        self.assertEqual(len(self.calls), 1)

    def test_legacy_session_without_card_state(self):
        self.start()
        f = self.root / "session.json"
        state = json.loads(f.read_text())
        state.pop("card_positions")
        state.pop("card_history")
        f.write_text(json.dumps(state))
        self.assertEqual(a.read_page(self.root)["active_card_index"], 0)
        self.assertEqual(a.select_card(self.root, 1)["active_card_index"], 1)

    def test_corrupt_card_history_is_rejected(self):
        self.start()
        f = self.root / "session.json"
        state = json.loads(f.read_text())
        state["card_history"] = [[99999, 0]]
        f.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, "Invalid card navigation state"):
            a.read_page(self.root)

    def test_mcp_card_tool_local_and_bad_index(self):
        self.start()
        server = BrowserServer(Path(self.tmp.name), allow_network=False)
        server.sessions["test-sid"] = self.root
        listed = server.dispatch({"jsonrpc": "2.0", "id": 1,
                                  "method": "tools/list"})["result"]["tools"]
        self.assertIn("wap_card", [tool["name"] for tool in listed])
        call = lambda idx: server.dispatch({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "wap_card",
                       "arguments": {"session_id": "test-sid", "index": idx}}
        })["result"]
        r = call(1)
        self.assertFalse(r["isError"])
        self.assertEqual(r["structuredContent"]["active_card_index"], 1)
        self.assertTrue(call(True)["isError"])
        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
