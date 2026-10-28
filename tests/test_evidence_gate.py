import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from wap_probe.evidence_gate import sha256, verify, verify_folder


BODY = b'<?xml version="1.0"?><wml><card id="home"><p>OK</p></card></wml>'


def fixture(
    status=200, mime="text/vnd.wap.wml", body=BODY,
    extra=(), content_length=True, prefix=b"",
):
    lines = [f"HTTP/1.1 {status} Test", f"Content-Type: {mime}"]
    if content_length:
        lines.append(f"Content-Length: {len(body)}")
    lines.extend(extra)
    headers = prefix + ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")
    url = "http://wap.example.org/index.wml"
    meta = {
        "url": url, "final_url": url, "profile": "wap1",
        "curl_exit_code": 0, "http_status": status, "content_type": mime,
        "body_bytes": len(body), "body_sha256": sha256(body),
        "headers_sha256": sha256(headers),
        "dns_answers": ["8.8.8.8"],
        "pinned_ip": "8.8.8.8", "remote_ip": "8.8.8.8",
    }
    return meta, headers, body


class EvidenceGateTests(unittest.TestCase):
    def check(self, expected, **kwargs):
        self.assertEqual(verify(*fixture(**kwargs))["status"], expected)

    def test_wml(self):
        self.check("WML_CAPTURED_NEEDS_R5")

    def test_wmlc(self):
        self.check("WMLC_CAPTURED_NEEDS_R5", mime="application/vnd.wap.wmlc")

    def test_html(self):
        self.check("HTML", mime="text/html")

    def test_redirect(self):
        self.check("REDIRECT", status=302)

    def test_non_200(self):
        self.check("HTTP_NON_200", status=503)

    def test_empty_body(self):
        self.check("EMPTY_BODY", body=b"")

    def test_empty_body_has_sha256(self):
        self.assertEqual(sha256(b""), hashlib.sha256(b"").hexdigest())
        self.assertEqual(len(sha256(b"")), 64)

    def test_capture_failed(self):
        meta, headers, body = fixture()
        meta["curl_exit_code"] = 6
        self.assertEqual(verify(meta, headers, body)["status"], "CAPTURE_FAILED")

    def test_non_integer_curl_exit(self):
        meta, headers, body = fixture()
        meta["curl_exit_code"] = False
        self.assertEqual(verify(meta, headers, body)["status"], "INVALID_EVIDENCE")

    def test_short_sha(self):
        meta, headers, body = fixture()
        meta["body_sha256"] = meta["body_sha256"][:40]
        self.assertEqual(verify(meta, headers, body)["status"], "INVALID_EVIDENCE")

    def test_wrong_body_sha(self):
        meta, headers, body = fixture()
        meta["body_sha256"] = "f" * 64
        self.assertEqual(verify(meta, headers, body)["status"], "INVALID_EVIDENCE")

    def test_wrong_header_sha(self):
        meta, headers, body = fixture()
        meta["headers_sha256"] = "f" * 64
        self.assertEqual(verify(meta, headers, body)["status"], "INVALID_EVIDENCE")

    def test_wrong_body_length(self):
        meta, headers, body = fixture()
        meta["body_bytes"] += 1
        self.assertEqual(verify(meta, headers, body)["status"], "INVALID_EVIDENCE")

    def test_wrong_status(self):
        meta, headers, body = fixture()
        meta["http_status"] = 204
        self.assertEqual(verify(meta, headers, body)["status"], "INVALID_EVIDENCE")

    def test_wrong_mime(self):
        meta, headers, body = fixture()
        meta["content_type"] = "text/html"
        self.assertEqual(verify(meta, headers, body)["status"], "INVALID_EVIDENCE")

    def test_charset_mime_normalization(self):
        meta, headers, body = fixture(mime="text/vnd.wap.wml; charset=UTF-8")
        meta["content_type"] = "text/vnd.wap.wml"
        self.assertEqual(verify(meta, headers, body)["status"], "WML_CAPTURED_NEEDS_R5")

    def test_reserved_dns(self):
        meta, headers, body = fixture()
        meta["dns_answers"].append("198.18.0.1")
        self.assertEqual(verify(meta, headers, body)["status"], "INVALID_EVIDENCE")

    def test_remote_ip_mismatch(self):
        meta, headers, body = fixture()
        meta["remote_ip"] = "1.1.1.1"
        self.assertEqual(verify(meta, headers, body)["status"], "INVALID_EVIDENCE")

    def test_duplicate_mime(self):
        self.check("INVALID_EVIDENCE", extra=("Content-Type: text/html",))

    def test_content_length_duplicate(self):
        self.check("INVALID_EVIDENCE", extra=(f"Content-Length: {len(BODY)}",))

    def test_conflicting_framing(self):
        self.check("INVALID_EVIDENCE", extra=("Transfer-Encoding: chunked",))

    def test_chunked_allowed(self):
        self.check("WML_CAPTURED_NEEDS_R5", extra=("Transfer-Encoding: chunked",),
                   content_length=False)

    def test_unsupported_transfer(self):
        self.check("INVALID_EVIDENCE", extra=("Transfer-Encoding: gzip",),
                   content_length=False)

    def test_encoded_body(self):
        self.check("ENCODED_BODY", extra=("Content-Encoding: gzip",))

    def test_partial_body(self):
        self.check("PARTIAL_BODY", extra=("Content-Range: bytes 0-31/64",))

    def test_interim_100(self):
        self.check("WML_CAPTURED_NEEDS_R5",
                   prefix=b"HTTP/1.1 100 Continue\r\n\r\n")

    def test_proxy_double_final_response(self):
        self.check("INVALID_EVIDENCE",
                   prefix=b"HTTP/1.1 200 Connection established\r\n\r\n")

    def test_header_folding(self):
        self.check("INVALID_EVIDENCE", extra=(" X-Folded: value",))

    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                verify_folder(Path(d))["status"], "MISSING_OR_INVALID_FILES"
            )

    def test_valid_folder(self):
        with tempfile.TemporaryDirectory() as d:
            meta, headers, body = fixture()
            root = Path(d)
            (root / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
            (root / "headers.bin").write_bytes(headers)
            (root / "body.bin").write_bytes(body)
            self.assertEqual(
                verify_folder(root)["status"], "WML_CAPTURED_NEEDS_R5"
            )

    def test_never_auto_a(self):
        meta, headers, body = fixture()
        outcome = verify(meta, headers, body)
        self.assertEqual(outcome["A_origin"], "PENDING")
        self.assertEqual(outcome["A_navigation"], "PENDING")


if __name__ == "__main__":
    unittest.main()
