"""Additional fail-closed regressions for R6; all fixtures are synthetic."""
import copy
import hashlib
import unittest

from wap_probe.evidence_gate import MAX_BODY_BYTES, verify
from wap_probe.navigation import evaluate_link, select_navigation

HOME = "http://wap.example.org/index.wml"
BODY = b"<wml><card id='a'/></wml>"
SHA = "a" * 64


def fixture(body=BODY, status=200, prefix=b"", extra=()):
    fields = [f"Content-Type: text/vnd.wap.wml", f"Content-Length: {len(body)}"]
    fields.extend(extra)
    header = prefix + (
        "HTTP/1.1 " + str(status) + " OK\r\n"
        + "\r\n".join(fields) + "\r\n\r\n"
    ).encode("ascii")
    digest = lambda data: hashlib.sha256(data).hexdigest()
    meta = {
        "url": HOME, "final_url": HOME,
        "profile": "wap1", "curl_exit_code": 0, "http_status": status,
        "content_type": "text/vnd.wap.wml", "body_bytes": len(body),
        "body_sha256": digest(body), "headers_sha256": digest(header),
        "dns_answers": ["8.8.8.8"], "pinned_ip": "8.8.8.8",
        "remote_ip": "8.8.8.8",
    }
    return meta, header, body


class SecurityRegressions(unittest.TestCase):
    def check(self, expected, modifier=None, **kwargs):
        meta, headers, body = fixture(**kwargs)
        if modifier:
            modifier(meta)
        self.assertEqual(verify(meta, headers, body)["status"], expected)

    def test_no_automatic_a(self):
        report = verify(*fixture())
        self.assertEqual(report["A_origin"], "PENDING")

    def test_dns_loopback(self):
        self.check("INVALID_EVIDENCE",
                   modifier=lambda m: m["dns_answers"].append("127.0.0.1"))

    def test_dns_cgnat(self):
        self.check("INVALID_EVIDENCE",
                   modifier=lambda m: m["dns_answers"].append("100.64.0.1"))

    def test_dns_documentation_ipv4(self):
        self.check("INVALID_EVIDENCE",
                   modifier=lambda m: m["dns_answers"].append("192.0.2.5"))

    def test_dns_mixed_public_private(self):
        self.check("INVALID_EVIDENCE",
                   modifier=lambda m: m["dns_answers"].append("10.0.0.1"))

    def test_final_url_mismatch(self):
        self.check("INVALID_EVIDENCE",
                   modifier=lambda m: m.update(final_url="http://evil.example.org/"))

    def test_userinfo_rejected(self):
        self.check("INVALID_EVIDENCE",
                   modifier=lambda m: m.update(
                       url="http://admin:secret@wap.example.org/index.wml",
                       final_url="http://admin:secret@wap.example.org/index.wml"))

    def test_oversize_even_with_matching_metadata(self):
        self.check("INVALID_EVIDENCE", body=b"x" * (MAX_BODY_BYTES + 1))

    def test_boolean_status_rejected(self):
        self.check("INVALID_EVIDENCE",
                   modifier=lambda m: m.update(http_status=True))

    def test_duplicate_final_headers_rejected(self):
        self.check("INVALID_EVIDENCE",
                   prefix=b"HTTP/1.1 200 Proxy\r\n\r\n")

    def test_early_hints_allowed(self):
        self.check("WML_CAPTURED_NEEDS_R5",
                   prefix=b"HTTP/1.1 103 Early Hints\r\nLink: </x>; rel=preload\r\n\r\n")

    def test_duplicate_transfer_encoding(self):
        self.check("INVALID_EVIDENCE", extra=(
            "Transfer-Encoding: chunked", "Transfer-Encoding: chunked"
        ))

    def test_script_scheme_rejected(self):
        self.assertIsNone(evaluate_link(HOME, {"href": "javascript:alert(1)"})[0])

    def test_scheme_relative_external_rejected(self):
        self.assertIsNone(evaluate_link(HOME, {"href": "//evil.example.net/page"})[0])

    def test_encoded_crlf_rejected(self):
        self.assertIsNone(evaluate_link(HOME, {"href": "next.wml%250d%250a"})[0])

    def test_encoded_wml_variable_rejected(self):
        self.assertIsNone(evaluate_link(HOME, {"href": "next.wml?x=%24%28token%29"})[0])

    def test_sensitive_query_rejected(self):
        self.assertIsNone(evaluate_link(HOME, {"href": "next.wml?authorization=abc"})[0])

    def test_fragment_in_home_rejected(self):
        result = select_navigation(
            HOME + "#card", [{"href": "next.wml"}],
            capture_status="WML_CAPTURED_NEEDS_R5",
            card_count=1, captured_body_sha256=SHA,
            parsed_body_sha256=SHA,
        )
        self.assertEqual(result["status"], "INVALID_HOME_URL")


if __name__ == "__main__":
    unittest.main()
