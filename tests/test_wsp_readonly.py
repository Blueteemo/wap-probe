"""Rootless, offline-pinned WSP/WDP conformance and loopback UDP tests.

The only UDP socket in these tests binds 127.0.0.1. Live WAP Labs probing
is NOT part of CI. Existing HTTP capture and MCP remain independent.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import threading
import unittest
from unittest.mock import patch

from wap_probe import wsp_readonly as wsp

REFERENCE = Path("tests/fixtures/lowband_wsp_reference.json")
R5 = Path(os.environ.get("R5_PROBE_DIR",
              ".r5_unpacked/wap-probe-live-discovery-r5/probe"))


class WspConnectionlessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(REFERENCE.read_text(encoding="utf-8"))

    def test_pinned_independent_get_bytes(self):
        item = self.doc["get"]
        self.assertEqual(item["kind"], "get")
        self.assertEqual(
            wsp.encode_get(item["uri"], item["transactionId"], accept_wmlc=False),
            bytes(item["encoded"]))
        self.assertEqual(
            wsp.encode_get("http://interop.wap.shrimpworks.dev/", 4)[-2:],
            b"\x80\x94")

    def test_pinned_reply_bytes_and_status_codes(self):
        for item in self.doc["replies"]:
            with self.subTest(item=item["name"]):
                reply = wsp.decode_reply(bytes(item["encoded"]), item["transactionId"])
                self.assertEqual(reply.status, item["statusCode"])
                self.assertEqual(reply.content_type, item["contentType"])
                self.assertEqual(reply.body, bytes(item["body"]))
        for status_byte, expected in self.doc["statuses"]:
            with self.subTest(status=status_byte):
                reply = wsp.decode_reply(
                    bytes((42, 4, status_byte, 1, 0x94)) + b"x", 42)
                self.assertEqual(reply.status, expected)

    def test_uintvar_roundtrips_and_malformed(self):
        for value in (0, 1, 127, 128, 16383, 16384, 0xFFFFFFFF):
            with self.subTest(value=value):
                encoded = wsp.encode_uintvar(value)
                self.assertLessEqual(len(encoded), 5)
                self.assertEqual(wsp.decode_uintvar(encoded, 0), (value, len(encoded)))
        for val in (True, -1, 0x100000000):
            with self.assertRaises(wsp.WspProtocolError):
                wsp.encode_uintvar(val)
        for raw in (b"", b"\x80", b"\x80\x80\x80\x80\x80",
                    b"\xff\xff\xff\xff\x7f"):
            with self.assertRaises(wsp.WspProtocolError):
                wsp.decode_uintvar(raw, 0)

    def test_reject_untrusted_wsp_reply_pdus(self):
        good = b"\x2a\x04\x20\x01\x94hello"
        corrupted = (
            b"", good[:1], b"\x2b" + good[1:], b"\x2a\x40" + good[2:],
            good[:3], good[:4], b"\x2a\x04\x20\x02\x94",
            b"\x2a\x04\xff\x01\x94x", b"\x2a\x04\x20\x01\xffx",
            b"\x2a\x04\x20\x01\x00x",
            b"\x2a\x04\x20\x05\x94bad",
        )
        for raw in corrupted:
            with self.subTest(payload=raw.hex()):
                with self.assertRaises(wsp.WspProtocolError):
                    wsp.decode_reply(raw, 42)
        with self.assertRaises(wsp.WspProtocolError):
            wsp.decode_reply(good + b"x" * (wsp.MAX_PDU + 1), 42)

    def test_textual_mime_and_wrong_content_type(self):
        raw = b"\x2a\x04\x20" + b"\x15" + b"application/vnd.wap.wmlc\x00"
        with self.assertRaises(wsp.WspProtocolError):
            wsp.decode_reply(raw, 42)
        header = b"text/vnd.wap.wml\x00"
        message = bytes((42, 4, 0x20, len(header))) + header + b"<wml/>"
        self.assertEqual(wsp.decode_reply(message, 42).content_type,
                         "text/vnd.wap.wml")

    def test_unsafe_get_inputs_rejected(self):
        for uri in ("ftp://evil.example/", "http://u:p@example.org/",
                    "http://example.org/?action=delete", "http://example.org/#x",
                    "http://example.org/space here", "http://example.org/你好",
                    "http://example.org/\x00"):
            with self.subTest(uri=uri), self.assertRaises(wsp.WspProtocolError):
                wsp.encode_get(uri, 1)
        for tid in (-1, 256, True):
            with self.assertRaises(wsp.WspProtocolError):
                wsp.encode_get("/test", tid)

    def test_no_network_without_both_opt_ins(self):
        for kwargs in ({"allow_network": False, "execute": False},
                       {"allow_network": False, "execute": True},
                       {"allow_network": True, "execute": False}):
            with patch("wap_probe.wsp_readonly.socket.socket") as forbidden:
                with self.assertRaises(wsp.WspProtocolError):
                    wsp.live_probe(**kwargs)
                forbidden.assert_not_called()

    def test_cli_has_no_network_by_default(self):
        with patch("wap_probe.wsp_readonly.socket.socket") as forbidden:
            with patch("builtins.print"):
                self.assertEqual(wsp.main(["--lab"]), 2)
            forbidden.assert_not_called()

    def _udp_peer(self, responder):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", 0))
        sock.settimeout(2)
        problems = []
        seen = []
        def worker():
            try:
                data, endpoint = sock.recvfrom(wsp.MAX_PDU)
                seen.append(data)
                answer = responder(data)
                if answer is not None:
                    sock.sendto(answer, endpoint)
            except Exception as error:
                problems.append(error)
            finally:
                sock.close()
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return ("127.0.0.1", sock.getsockname()[1]), thread, problems, seen

    def test_real_loopback_udp_wsp_wmlc_chinese_decode(self):
        binary = (R5 / "fixtures" / "binary_portal.wmlc").read_bytes()
        def respond(data):
            self.assertEqual(data[1], 0x40)
            self.assertIn(b"http://interop.wap.shrimpworks.dev/", data)
            self.assertEqual(data[-2:], b"\x80\x94")
            return bytes((data[0], 4, 0x20, 1, 0x94)) + binary
        address, thread, problems, seen = self._udp_peer(respond)
        with patch.object(wsp, "LAB_GATEWAY", address):
            response = wsp.live_probe(allow_network=True, execute=True)
        thread.join(3)
        self.assertFalse(problems)
        self.assertEqual(len(seen), 1, "exactly one GET datagram")
        self.assertTrue(response["ok"])
        self.assertEqual(response["mime"], "application/vnd.wap.wmlc")
        self.assertEqual(response["card_count"], 2)
        self.assertIn("查看目录", response["card_text_preview"])
        self.assertTrue(response["no_followup"])
        self.assertNotIn("raw_reply", response)

    def test_wrong_tid_over_udp_does_not_accept_reply(self):
        def wrong(data):
            return bytes(((data[0] + 1) % 256, 4, 0x20, 1, 0x94)) + b"irrelevant"
        address, thread, problems, seen = self._udp_peer(wrong)
        with patch.object(wsp, "LAB_GATEWAY", address):
            with self.assertRaisesRegex(wsp.WspProtocolError, "transaction ID"):
                wsp.live_probe(allow_network=True, execute=True)
        thread.join(3)
        self.assertFalse(problems)
        self.assertEqual(len(seen), 1)

    def test_udp_timeout_is_bounded_and_no_retries(self):
        address, thread, problems, seen = self._udp_peer(lambda _: None)
        with patch.object(wsp, "LAB_GATEWAY", address):
            with patch.object(wsp, "TIMEOUT_SECONDS", 0.15):
                with self.assertRaises(socket.timeout):
                    wsp.live_probe(allow_network=True, execute=True)
        thread.join(3)
        self.assertFalse(problems)
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
