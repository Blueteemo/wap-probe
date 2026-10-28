"""Real R5 -> R6 offline integration; synthetic HTTP bytes, no network."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from wap_probe.bridge import evaluate
from wap_probe.evidence_gate import sha256
from wap_probe.r5_adapter import parse_capture

R5_PROBE = Path(os.environ.get(
    "R5_PROBE_DIR", ".r5_unpacked/wap-probe-live-discovery-r5/probe"
))
HOME_URL = "http://wap.example.org/dir/index.wml"
CHILD_URL = "http://wap.example.org/dir/next.wml"
HOME_BODY = b'<wml><card id="home"><p><a href="next.wml">Next</a></p></card></wml>'
CHILD_BODY = b'<wml><card id="child"><p>Second card</p></card></wml>'


def write_capture(folder, url, body, *, profile="wap1"):
    folder.mkdir()
    headers = (f"HTTP/1.1 200 OK\r\nContent-Type: text/vnd.wap.wml\r\n"
               f"Content-Length: {len(body)}\r\n\r\n").encode("ascii")
    metadata = {
        "url": url, "final_url": url, "profile": profile,
        "curl_exit_code": 0, "http_status": 200,
        "content_type": "text/vnd.wap.wml", "body_bytes": len(body),
        "body_sha256": sha256(body), "headers_sha256": sha256(headers),
        "dns_answers": ["8.8.8.8"],
        "pinned_ip": "8.8.8.8", "remote_ip": "8.8.8.8",
    }
    (folder / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (folder / "headers.bin").write_bytes(headers)
    (folder / "body.bin").write_bytes(body)


class RealR5R6IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.home, self.child = root / "home", root / "child"
        self.home_export = root / "home_r5.json"
        self.child_export = root / "child_r5.json"
        write_capture(self.home, HOME_URL, HOME_BODY)
        write_capture(self.child, CHILD_URL, CHILD_BODY)
        self.home_export.write_text(
            json.dumps(parse_capture(self.home, probe_dir=R5_PROBE)),
            encoding="utf-8",
        )
        self.child_export.write_text(
            json.dumps(parse_capture(self.child, probe_dir=R5_PROBE)),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_real_r5_bytes_then_two_page_bridge(self):
        report = evaluate(self.home, self.home_export, self.child, self.child_export)
        self.assertEqual(report["stage"], "TWO_PAGE_EVIDENCE_MATCHED")
        self.assertEqual(report["A_origin"], "PENDING")
        self.assertEqual(report["A_navigation"], "PENDING")

    def test_second_page_get_bound_to_real_r5_link(self):
        result = evaluate(self.home, self.home_export)
        self.assertEqual(result["stage"], "CHILD_GET_REQUIRED")
        self.assertEqual(result["next_get"]["url"], CHILD_URL)
        self.assertFalse(result["next_get"]["follow_redirects"])

    def test_r5_cannot_rescue_tampered_capture(self):
        (self.home / "body.bin").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "R6 evidence rejected"):
            parse_capture(self.home, probe_dir=R5_PROBE)


if __name__ == "__main__":
    unittest.main()
