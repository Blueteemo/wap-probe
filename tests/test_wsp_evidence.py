"""WSP evidence import: offline card reading without HTTP/curl spoofing."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import threading
import unittest
from unittest.mock import patch

from wap_probe import agent_browser as agent
from wap_probe import wsp_evidence as ev
from wap_probe import wsp_readonly as wsp

R5 = Path(os.environ.get(
    "R5_PROBE_DIR", ".r5_unpacked/wap-probe-live-discovery-r5/probe"))
BIN = R5 / "fixtures" / "binary_portal.wmlc"


class WspEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.record = self.work / "record"
        self.session = self.work / "session"
        self.body = BIN.read_bytes()
        self.request = wsp.encode_get(wsp.LAB_RESOURCE, 42)
        self.reply = bytes((42, 4, 0x20, 1, 0x94)) + self.body

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        ev.write_record(self.record, self.request, self.reply)

    def import_it(self):
        return ev.import_record(self.record, self.session)

    @unittest.skipUnless(os.name == "posix", "POSIX directory mode")
    def test_operator_wsp_record_and_imported_session_are_private(self):
        self.write()
        self.import_it()
        self.assertEqual(stat.S_IMODE(self.record.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.session.stat().st_mode), 0o700)

    def test_import_and_multicard_read_are_strictly_offline(self):
        self.write()
        with patch("socket.socket") as sock, patch.object(agent, "capture") as capture:
            view = self.import_it()
            self.assertTrue(view["ok"])
            self.assertEqual(view["transport"], "wsp-offline")
            self.assertEqual(view["capture_status"], "WSP_OFFLINE_VERIFIED")
            self.assertFalse(view["source_authenticated"])
            self.assertIsNone(view["http_status"])
            self.assertEqual(view["wsp_status"], 200)
            self.assertEqual(view["card_count"], 2)
            self.assertEqual(view["links"], [])
            self.assertEqual(view["do_links"], [])
            self.assertIn("查看目录", view["text"])
            child = agent.select_card(self.session, 1)
            self.assertIn("二进制 WAP 页面", child["text"])
            back = agent.go_back(self.session)
            self.assertEqual(back["active_card_index"], 0)
            self.assertEqual(back["card_count"], 2)
            sock.assert_not_called()
            capture.assert_not_called()
        self.assertFalse((self.session / "pages/page-0001/headers.bin").exists())
        self.assertFalse((self.session / "pages/page-0001/metadata.json").exists())

    def test_cli_import_and_read_require_no_execute_flag(self):
        self.write()
        output = []
        with patch("builtins.print", side_effect=output.append), patch("socket.socket") as sock:
            result = agent.main(["import-wsp", "--evidence", str(self.record),
                                 "--out", str(self.session)])
            self.assertEqual(result, 0)
            self.assertTrue(json.loads(output[0])["ok"])
            self.assertEqual(agent.main(["read", "--session",
                                         str(self.session)]), 0)
            sock.assert_not_called()

    def test_import_never_overwrites_existing_session_or_record(self):
        self.write()
        self.import_it()
        with self.assertRaises(FileExistsError):
            self.import_it()
        with self.assertRaises(FileExistsError):
            self.write()

    def test_tampered_original_or_manifest_rejected(self):
        for filename in ("request.wsp", "reply.wsp"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "record"
                ev.write_record(root, self.request, self.reply)
                path = root / filename
                path.write_bytes(path.read_bytes() + b"extra")
                with self.assertRaises(ValueError):
                    ev.verify_record(root)
        self.write()
        m = self.record / "wsp_manifest.json"
        data = json.loads(m.read_text())
        data["authenticated"] = True
        m.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.import_it()
        self.assertFalse(self.session.exists())

    def test_wrong_get_target_and_reply_tid_rejected(self):
        invalid_request = wsp.encode_get("http://another.example.org/", 42)
        with self.assertRaises(ValueError):
            ev.write_record(self.record, invalid_request, self.reply)
        self.assertFalse(self.record.exists())
        invalid_reply = bytes((43, 4, 0x20, 1, 0x94)) + self.body
        with self.assertRaises(wsp.WspProtocolError):
            ev.write_record(self.record, self.request, invalid_reply)

    def test_imported_source_or_export_modified_rejected(self):
        self.write()
        self.import_it()
        page = self.session / "pages/page-0001"
        body = page / "body.bin"
        body.write_bytes(body.read_bytes() + b"x")
        with self.assertRaises(ValueError):
            agent.read_page(self.session)
        body.write_bytes(self.body)
        exported = page / "r5_export.json"
        data = json.loads(exported.read_text())
        data["cards"][0]["text"] = "forged Agent text"
        exported.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "R5 export"):
            agent.read_page(self.session)

    def test_imported_packet_manifest_rechecked_every_read(self):
        self.write()
        self.import_it()
        p = self.session / "pages/page-0001/reply.wsp"
        p.write_bytes(p.read_bytes()[:-1])
        with self.assertRaises(ValueError):
            agent.select_card(self.session, 1)

    def test_no_network_follow_or_form_plan_for_import(self):
        self.write()
        self.import_it()
        with patch.object(agent, "capture") as capture:
            with self.assertRaisesRegex(ValueError, "cannot follow network"):
                agent.follow_link(self.session, 0)
            with self.assertRaisesRegex(ValueError, "cannot follow network"):
                agent.follow_do(self.session, 0)
            from wap_probe.form_plan import plan_current
            with self.assertRaisesRegex(ValueError, "does not support form planning"):
                plan_current(self.session, 0, {})
            capture.assert_not_called()

    def test_invalid_r5_deck_is_not_importable(self):
        body = b"<html>not a WML page</html>"
        reply = bytes((42, 4, 0x20, 1, 0x94)) + body
        ev.write_record(self.record, self.request, reply)
        with self.assertRaises(ValueError):
            self.import_it()
        self.assertFalse(self.session.exists())

    def test_loopback_udp_can_save_verifiable_record_then_import(self):
        peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        peer.bind(("127.0.0.1", 0))
        peer.settimeout(3)
        local_gateway = ("127.0.0.1", peer.getsockname()[1])
        seen = []
        errors = []
        def serve():
            try:
                received, address = peer.recvfrom(wsp.MAX_PDU)
                seen.append(received)
                answer = bytes((received[0], 4, 0x20, 1, 0x94)) + self.body
                peer.sendto(answer, address)
            except Exception as e:
                errors.append(e)
            finally:
                peer.close()
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        with patch.object(wsp, "LAB_GATEWAY", local_gateway), patch.object(ev, "LAB_GATEWAY", local_gateway):
            response = wsp.live_probe(allow_network=True, execute=True,
                                      evidence_out=self.record)
            self.assertEqual(response["card_count"], 2)
            self.assertTrue(ev.verify_record(self.record))
            view = self.import_it()
            self.assertTrue(view["ok"])
        thread.join(3)
        self.assertFalse(errors)
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
