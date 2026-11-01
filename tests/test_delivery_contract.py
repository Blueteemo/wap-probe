"""Stable release/CLI/MCP contract and exception-redaction regression tests."""
from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import wap_probe
from wap_probe.agent_browser import main as agent_main
from wap_probe.agent_mcp import BrowserServer, TOOL_DOC
from wap_probe.errors import safe_error
from wap_probe.wsp_readonly import main as lab_main

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "1.0.0"


class DeliveryContractTests(unittest.TestCase):
    def test_versioned_entrypoints_and_mcp_server_info_are_consistent(self):
        meta = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        version = re.search(r'^version\s*=\s*"([^"]+)"', meta, re.M)
        self.assertIsNotNone(version)
        self.assertEqual(version.group(1), RELEASE)
        self.assertEqual(wap_probe.__version__, RELEASE)
        for script in ("wap-agent", "wap-mcp", "wap-wsp-lab"):
            self.assertRegex(meta, rf"(?m)^{re.escape(script)} = ")
        with tempfile.TemporaryDirectory() as temp:
            server = BrowserServer(Path(temp))
            result = server.dispatch({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
            })
        self.assertEqual(result["result"]["serverInfo"]["version"], RELEASE)

    def test_tool_metadata_has_exact_and_validated_required_properties(self):
        with tempfile.TemporaryDirectory() as temp:
            server = BrowserServer(Path(temp))
            result = server.dispatch({
                "jsonrpc": "2.0", "id": 2, "method": "tools/list",
            })
        tools = result["result"]["tools"]
        self.assertEqual(len(tools), 8)
        self.assertEqual({x["name"] for x in tools}, set(TOOL_DOC))
        for item in tools:
            with self.subTest(tool=item["name"]):
                schema = item["inputSchema"]
                self.assertEqual(schema["type"], "object")
                self.assertIs(schema["additionalProperties"], False)
                self.assertTrue(set(schema["required"]) <= set(schema["properties"]))
                self.assertEqual(len(item["name"].split()), 1)
        importer = next(x for x in tools if x["name"] == "wap_import_wsp")
        self.assertEqual(importer["inputSchema"]["required"], [])
        self.assertEqual(importer["inputSchema"]["properties"], {})

    def test_safe_errors_never_echo_secret_paths_or_supplied_values(self):
        secret = "/private/home/user/TOKEN_DO_NOT_PRINT"
        cases = (
            FileNotFoundError(2, "no such file", secret),
            PermissionError(13, "denied", secret),
            FileExistsError(17, "exists", secret),
            ValueError("url contains " + secret),
            TypeError("form values contain " + secret),
            KeyError(secret),
            OSError(99, "connection failed", secret),
        )
        for exc in cases:
            with self.subTest(exc=type(exc).__name__):
                data = safe_error(exc)
                self.assertEqual(set(data), {"error", "message"})
                self.assertNotIn(secret, json.dumps(data))
                self.assertTrue(data["message"])
        self.assertEqual(safe_error(FileNotFoundError("x"))["error"],
                         "FileNotFoundError")

    def test_mcp_missing_operator_evidence_errors_are_redacted(self):
        with tempfile.TemporaryDirectory() as root:
            private_path = Path(root) / "TOP_SECRET_UNIQUE_PATH"
            server = BrowserServer(Path(root) / "sessions", wsp_evidence=private_path)
            request = {
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "wap_import_wsp", "arguments": {}},
            }
            output = server.dispatch(request)
            self.assertTrue(output["result"]["isError"])
            wire = json.dumps(output)
            self.assertNotIn(str(private_path), wire)
            self.assertNotIn("TOP_SECRET_UNIQUE_PATH", wire)
            self.assertEqual(server.sessions, {})

    def test_cli_nonexistent_local_source_errors_are_redacted(self):
        with tempfile.TemporaryDirectory() as root:
            secret = str(Path(root) / "PRIVATE_LOCAL_PATH_123")
            lines = []
            with patch("builtins.print", side_effect=lines.append):
                code = agent_main(["read", "--session", secret])
            self.assertEqual(code, 2)
            result = json.loads(lines[0])
            self.assertFalse(result["ok"])
            self.assertNotIn(secret, lines[0])
            self.assertNotIn("PRIVATE_LOCAL_PATH_123", lines[0])

    def test_wsp_cli_does_not_open_sockets_without_two_permissions(self):
        outputs = []
        with patch("socket.socket") as socket_factory:
            with patch("builtins.print", side_effect=outputs.append):
                self.assertEqual(lab_main(["--lab"]), 2)
            socket_factory.assert_not_called()
        self.assertFalse(json.loads(outputs[0])["ok"])


if __name__ == "__main__":
    unittest.main()
