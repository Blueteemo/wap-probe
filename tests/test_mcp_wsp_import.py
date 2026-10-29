"""MCP can open only operator-selected local WSP evidence, without network."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from wap_probe.agent_mcp import BrowserServer, main
from wap_probe.wsp_evidence import write_record
from wap_probe.wsp_readonly import LAB_RESOURCE, encode_get

R5 = Path(os.environ.get(
    "R5_PROBE_DIR", ".r5_unpacked/wap-probe-live-discovery-r5/probe"))


class WspMcpOfflineImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.evidence = self.work / "operator-chosen-evidence"
        self.body = (R5 / "fixtures" / "binary_portal.wmlc").read_bytes()
        request = encode_get(LAB_RESOURCE, 42)
        reply = bytes((42, 4, 0x20, 1, 0x94)) + self.body
        write_record(self.evidence, request, reply)
        self.server = BrowserServer(self.work / "mcp-temp",
                                    allow_network=False,
                                    wsp_evidence=self.evidence)

    def tearDown(self):
        self.temp.cleanup()

    def rpc(self, name, arguments=None):
        return self.server.dispatch({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        })["result"]

    def test_read_only_import_then_card_and_back_without_network(self):
        with patch("socket.socket") as socket_factory:
            first = self.rpc("wap_import_wsp")
            self.assertFalse(first["isError"])
            view = first["structuredContent"]
            sid = view["session_id"]
            self.assertNotIn("session", view)
            self.assertEqual(view["transport"], "wsp-offline")
            self.assertEqual(view["card_count"], 2)
            self.assertEqual(view["links"], [])
            self.assertEqual(view["do_links"], [])
            self.assertFalse(view["source_authenticated"])
            self.assertIn("查看目录", view["text"])
            read = self.rpc("wap_read", {"session_id": sid})
            self.assertFalse(read["isError"])
            card = self.rpc("wap_card", {"session_id": sid, "index": 1})
            self.assertFalse(card["isError"])
            self.assertIn("二进制 WAP 页面", card["structuredContent"]["text"])
            back = self.rpc("wap_back", {"session_id": sid})
            self.assertFalse(back["isError"])
            self.assertEqual(back["structuredContent"]["active_card_index"], 0)
            socket_factory.assert_not_called()
        wire = json.dumps(first, ensure_ascii=False)
        self.assertNotIn(str(self.work), wire)
        self.assertNotIn("request.wsp", wire)
        self.assertNotIn("reply.wsp", wire)

    def test_import_idempotent_same_opaque_session(self):
        first = self.rpc("wap_import_wsp")["structuredContent"]
        second = self.rpc("wap_import_wsp")["structuredContent"]
        self.assertEqual(first["session_id"], second["session_id"])
        self.assertEqual(len(self.server.sessions), 1)

    def test_missing_operator_configuration_rejected(self):
        server = BrowserServer(self.work / "unconfigured", allow_network=False)
        result = server.dispatch({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "wap_import_wsp", "arguments": {}},
        })["result"]
        self.assertTrue(result["isError"])
        self.assertFalse(server.sessions)

    def test_tool_client_cannot_select_paths_or_udp_targets(self):
        for args in (
            {"path": "/etc/passwd"},
            {"evidence": str(self.evidence)},
            {"gateway": "127.0.0.1:9200"},
            {"execute": True},
        ):
            with self.subTest(args=args):
                result = self.rpc("wap_import_wsp", args)
                self.assertTrue(result["isError"])
                self.assertEqual(self.server.sessions, {})
        tool = next(tool for tool in self.server.dispatch({
            "jsonrpc": "2.0", "id": 6, "method": "tools/list",
        })["result"]["tools"] if tool["name"] == "wap_import_wsp")
        self.assertEqual(tool["inputSchema"]["properties"], {})
        self.assertEqual(tool["inputSchema"]["required"], [])

    def test_network_permission_does_not_enable_wsp_followup(self):
        self.server.allow_network = True
        sid = self.rpc("wap_import_wsp")["structuredContent"]["session_id"]
        with patch("socket.socket") as socket_factory, patch(
            "wap_probe.agent_browser.capture"
        ) as capture:
            for name, args in [
                ("wap_follow", {"session_id": sid, "link": 0, "execute": True}),
                ("wap_go", {"session_id": sid, "index": 0, "execute": True}),
                ("wap_form_plan", {"session_id": sid, "action": 0, "values": {}}),
            ]:
                with self.subTest(name=name):
                    result = self.rpc(name, args)
                    self.assertTrue(result["isError"])
            socket_factory.assert_not_called()
            capture.assert_not_called()
        # Regardless of the MCP network flag, the imported Agent session
        # does not contain any ordinary/followable link.
        self.assertEqual(self.rpc("wap_read", {"session_id": sid})
                         ["structuredContent"]["links"], [])

    def test_tampering_with_source_is_rejected_on_each_read(self):
        sid = self.rpc("wap_import_wsp")["structuredContent"]["session_id"]
        root = self.server.sessions[sid]
        reply = root / "pages" / "page-0001" / "reply.wsp"
        reply.write_bytes(reply.read_bytes() + b"tamper")
        out = self.rpc("wap_read", {"session_id": sid})
        self.assertTrue(out["isError"])
        self.assertEqual(len(self.server.sessions), 1)

    def test_changed_operator_record_is_not_silently_reimported(self):
        sid = self.rpc("wap_import_wsp")["structuredContent"]["session_id"]
        original = self.evidence / "reply.wsp"
        original.write_bytes(original.read_bytes() + b"tamper")
        again = self.rpc("wap_import_wsp")
        self.assertFalse(again["isError"])
        self.assertEqual(again["structuredContent"]["session_id"], sid)
        # The current session contains an integrity-checked immutable copy.
        self.assertTrue(self.rpc("wap_read", {"session_id": sid})
                        ["structuredContent"]["ok"])

    def test_mcp_startup_flag_only_configures_host_selected_path(self):
        chosen = []
        with patch("wap_probe.agent_mcp.serve", side_effect=chosen.append):
            status = main(["--wsp-evidence", str(self.evidence)])
        self.assertEqual(status, 0)
        self.assertEqual(chosen[0].wsp_evidence, self.evidence)
        self.assertFalse(chosen[0].allow_network)


if __name__ == "__main__":
    unittest.main()
