import json
import tempfile
import unittest
from pathlib import Path

from wap_probe.bridge import evaluate
from wap_probe.evidence_gate import sha256


HOME_URL = "http://wap.example.org/dir/index.wml"
CHILD_URL = "http://wap.example.org/dir/next.wml"
HOME_BODY = b'<wml><card id="home"><p>Home</p></card></wml>'
CHILD_BODY = b'<wml><card id="next"><p>Next</p></card></wml>'


def write_capture(root, url, body, *, profile="wap1", mime="text/vnd.wap.wml"):
    root.mkdir(parents=True)
    headers = (
        f"HTTP/1.1 200 OK\r\nContent-Type: {mime}\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    ).encode()
    meta = {
        "url": url, "final_url": url, "profile": profile,
        "curl_exit_code": 0, "http_status": 200,
        "content_type": mime, "body_bytes": len(body),
        "body_sha256": sha256(body), "headers_sha256": sha256(headers),
        "dns_answers": ["8.8.8.8"], "pinned_ip": "8.8.8.8",
        "remote_ip": "8.8.8.8",
    }
    (root / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (root / "headers.bin").write_bytes(headers)
    (root / "body.bin").write_bytes(body)


def write_r5(path, body, links=None, **changes):
    obj = {
        "schema": "r6-r5-export-v1", "status": "ok", "strict": True,
        "source_sha256": sha256(body),
        "cards": [{"id": "home", "links": links if links is not None else [
            {"href": "next.wml", "method": "GET"}
        ]}],
    }
    obj.update(changes)
    path.write_text(json.dumps(obj), encoding="utf-8")


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home = root / "home"
        self.child = root / "child"
        self.home_r5 = root / "home.json"
        self.child_r5 = root / "child.json"
        write_capture(self.home, HOME_URL, HOME_BODY)
        write_capture(self.child, CHILD_URL, CHILD_BODY)
        write_r5(self.home_r5, HOME_BODY)
        write_r5(self.child_r5, CHILD_BODY, links=[])

    def tearDown(self):
        self.tmp.cleanup()

    def test_home_export_required(self):
        self.assertEqual(evaluate(self.home)["stage"], "HOME_R5_EXPORT_REQUIRED")

    def test_home_r5_matched(self):
        self.assertEqual(evaluate(self.home, self.home_r5)["stage"],
                         "CHILD_GET_REQUIRED")

    def test_next_get_target(self):
        task = evaluate(self.home, self.home_r5)["next_get"]
        self.assertEqual(task["url"], CHILD_URL)
        self.assertEqual(task["method"], "GET")
        self.assertIs(task["follow_redirects"], False)

    def test_two_page_matched(self):
        report = evaluate(self.home, self.home_r5, self.child, self.child_r5)
        self.assertEqual(report["stage"], "TWO_PAGE_EVIDENCE_MATCHED")
        self.assertEqual(report["A_origin"], "PENDING")
        self.assertEqual(report["A_navigation"], "PENDING")

    def test_bad_r5_sha(self):
        write_r5(self.home_r5, HOME_BODY, source_sha256="f" * 64)
        self.assertEqual(evaluate(self.home, self.home_r5)["stage"],
                         "HOME_R5_REJECTED")

    def test_not_strict(self):
        write_r5(self.home_r5, HOME_BODY, strict=False)
        self.assertEqual(evaluate(self.home, self.home_r5)["stage"],
                         "HOME_R5_REJECTED")

    def test_child_binding_wrong_url(self):
        write_capture(self.child, "http://wap.example.org/wrong.wml", CHILD_BODY)
        self.assertEqual(
            evaluate(self.home, self.home_r5, self.child, self.child_r5)["stage"],
            "CHILD_BINDING_REJECTED"
        )

    def test_child_binding_wrong_profile(self):
        write_capture(self.child, CHILD_URL, CHILD_BODY, profile="s60")
        self.assertEqual(
            evaluate(self.home, self.home_r5, self.child, self.child_r5)["stage"],
            "CHILD_BINDING_REJECTED"
        )

    def test_no_links_on_first_card(self):
        write_r5(self.home_r5, HOME_BODY, links=[])
        self.assertEqual(evaluate(self.home, self.home_r5)["stage"],
                         "HOME_R5_EVIDENCE_MATCHED")

    def test_child_r5_export_required(self):
        self.assertEqual(
            evaluate(self.home, self.home_r5, self.child)["stage"],
            "CHILD_R5_EXPORT_REQUIRED"
        )

    def test_child_bad_r5_sha(self):
        write_r5(self.child_r5, CHILD_BODY, source_sha256="b"*64)
        self.assertEqual(
            evaluate(self.home, self.home_r5, self.child, self.child_r5)["stage"],
            "CHILD_R5_REJECTED"
        )

    def test_same_capture_cannot_be_child(self):
        self.assertEqual(
            evaluate(self.home, self.home_r5, self.home, self.child_r5)["stage"],
            "CHILD_BINDING_REJECTED"
        )


if __name__ == "__main__":
    unittest.main()
