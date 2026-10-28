"""Offline tests that run the real, frozen R5 parser rather than a stub."""
import os
import tempfile
import unittest
from pathlib import Path

from wap_probe.r5_adapter import parse_r5

R5_PROBE = Path(
    os.environ.get(
        "R5_PROBE_DIR",
        ".r5_unpacked/wap-probe-live-discovery-r5/probe",
    )
)
FIXTURES = R5_PROBE / "fixtures"


class RealR5ParserAdapterTests(unittest.TestCase):
    def test_wml_cards(self):
        r = parse_r5((FIXTURES / "portal.wml").read_bytes(),
                     "text/vnd.wap.wml", probe_dir=R5_PROBE)
        self.assertEqual(r["schema"], "r6-r5-export-v1")
        self.assertEqual(r["parser"], "frozen-r5-v0.3.3")
        self.assertEqual(len(r["cards"]), 2)
        self.assertEqual(r["cards"][0]["links"][0]["href"], "#news")
        self.assertEqual(r["cards"][1]["links"][0]["href"], "posts.wml")

    def test_wmlc_binary(self):
        body = (FIXTURES / "binary_portal.wmlc").read_bytes()
        r = parse_r5(body, "application/vnd.wap.wmlc", probe_dir=R5_PROBE)
        self.assertGreaterEqual(len(r["cards"]), 1)
        self.assertTrue(r["strict"])

    def test_broken_wml_rejected(self):
        with self.assertRaisesRegex(ValueError, "did not verify"):
            parse_r5(b"<wml><card>", "text/vnd.wap.wml", probe_dir=R5_PROBE)

    def test_html_mime_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            parse_r5(b"<html></html>", "text/html", probe_dir=R5_PROBE)

    def test_html_body_with_wml_mime_rejected(self):
        with self.assertRaisesRegex(ValueError, "did not verify"):
            parse_r5(b"<html></html>", "text/vnd.wap.wml", probe_dir=R5_PROBE)

    def test_missing_real_parser_not_stubbed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "required"):
                parse_r5(b"<wml><card id='x'/></wml>",
                         "text/vnd.wap.wml", probe_dir=Path(folder))

    def test_get_with_postfield_never_becomes_safe_navigation(self):
        body = (b'<wml><card id="h"><p><anchor>Submit'
                b'<go href="next.wml" method="get">'
                b'<postfield name="q" value="1"/></go>'
                b'</anchor></p></card></wml>')
        result = parse_r5(body, "text/vnd.wap.wml", probe_dir=R5_PROBE)
        self.assertEqual(result["cards"][0]["links"], [])

    def test_post_not_exposed_for_get(self):
        body = (b'<wml><card id="h"><p><anchor>Submit'
                b'<go href="post.wml" method="post"/>'
                b'</anchor></p></card></wml>')
        result = parse_r5(body, "text/vnd.wap.wml", probe_dir=R5_PROBE)
        self.assertEqual(result["cards"][0]["links"], [])


if __name__ == "__main__":
    unittest.main()
