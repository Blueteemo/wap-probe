"""Read-only form inspection, frozen R5 integration and no-submit safeguards."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from wap_probe.form_inspector import inspect_forms
from wap_probe.r5_adapter import parse_r5, parse_capture
from wap_probe.agent_browser import page_view

R5 = Path(os.environ.get(
    "R5_PROBE_DIR", ".r5_unpacked/wap-probe-live-discovery-r5/probe"
))
BASE = "http://wap.example.org/"
FORM = b'''<?xml version="1.0" encoding="utf-8"?>
<wml>
<card id="home"><p>Choose a category
<input name="q" title="Search" type="text" value="$(previous)" maxlength="48"/>
<input name="password" type="password" value="SECRET_SENTINEL"/>
<select name="genre" title="Genres" multiple="true">
<option value="abc">Action</option><option value="xyz">Puzzle</option>
</select>
<anchor>Submit search<go href="/search.wml?q=$(q)" method="get">
<postfield name="q" value="$(q)"/></go></anchor>
<do type="accept"><go href="/remove.wml?token=TOPSECRET" method="post">
<postfield name="csrf_token" value="TOPSECRET"/></go></do>
<a href="public.wml">Safe browse</a>
</p></card>
<card id="second"><p>Second card</p></card>
</wml>'''


def make_capture(root, raw, mime="text/vnd.wap.wml"):
    root.mkdir()
    headers = (f"HTTP/1.1 200 OK\r\nContent-Type: {mime}\r\n"
               f"Content-Length: {len(raw)}\r\n\r\n").encode()
    meta = {"url": BASE, "final_url": BASE, "profile": "wap1",
            "curl_exit_code": 0, "http_status": 200, "content_type": mime,
            "body_bytes": len(raw),
            "body_sha256": hashlib.sha256(raw).hexdigest(),
            "headers_sha256": hashlib.sha256(headers).hexdigest(),
            "dns_answers": ["8.8.8.8"],
            "pinned_ip": "8.8.8.8", "remote_ip": "8.8.8.8"}
    (root / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (root / "headers.bin").write_bytes(headers)
    (root / "body.bin").write_bytes(raw)
    record = parse_capture(root, probe_dir=R5)
    (root / "r5_export.json").write_text(json.dumps(record), encoding="utf-8")


class FormInspectorTests(unittest.TestCase):
    def test_field_types_options_and_actions(self):
        cards = inspect_forms(FORM)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["field_count"], 3)
        self.assertEqual(cards[0]["action_count"], 2)
        fields = cards[0]["fields"]
        self.assertEqual(fields[0]["name"], "q")
        self.assertTrue(fields[0]["dynamic_default"])
        self.assertEqual(fields[0]["maxlength"], 48)
        self.assertEqual(fields[1]["name"], "[redacted]")
        self.assertTrue(fields[1]["sensitive"])
        self.assertEqual(fields[2]["option_count"], 2)
        self.assertEqual([o["label"] for o in fields[2]["options"]],
                         ["Action", "Puzzle"])
        self.assertTrue(fields[2]["multiple"])
        actions = cards[0]["actions"]
        self.assertEqual([x["method"] for x in actions], ["GET", "POST"])
        self.assertTrue(actions[0]["dynamic_href"])
        self.assertTrue(actions[0]["has_query"])
        self.assertFalse(any(x["submission_available"] for x in actions))
        data = json.dumps(cards)
        self.assertNotIn("SECRET_SENTINEL", data)
        self.assertNotIn("TOPSECRET", data)
        self.assertNotIn("csrf_token", data)

    def test_gb2312(self):
        raw = ('<?xml version="1.0" encoding="GB2312"?>'
               '<wml><card id="a"><p><input name="query" title="搜索"/>'
               '<select name="cat"><option value="a">游戏</option></select>'
               '</p></card></wml>').encode("gb2312")
        result = inspect_forms(raw)
        self.assertEqual(result[0]["fields"][0]["title"], "搜索")
        self.assertEqual(result[0]["fields"][1]["options"][0]["label"], "游戏")

    def test_bad_entities_or_non_wml_rejected(self):
        with self.assertRaises(ValueError):
            inspect_forms(b'<!DOCTYPE wml [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
                          b'<wml><card><p>&x;</p></card></wml>')
        with self.assertRaises(ValueError):
            inspect_forms(b"<html></html>")

    def test_max_controls_and_value_redaction(self):
        body = b"<wml><card>" + b'<input name="x" value="TOKEN"/>' * 60 + b"</card></wml>"
        result = inspect_forms(body)[0]
        self.assertEqual(result["field_count"], 60)
        self.assertEqual(len(result["fields"]), 48)
        self.assertTrue(result["truncated"])
        self.assertNotIn("TOKEN", json.dumps(result))


class R5FormsIntegrationTests(unittest.TestCase):
    def test_forms_visible_only_on_active_card(self):
        with tempfile.TemporaryDirectory() as t:
            home = Path(t) / "home"
            make_capture(home, FORM)
            first = page_view(home)
            self.assertTrue(first["ok"])
            self.assertEqual(first["form_preview"]["field_count"], 3)
            self.assertEqual(first["form_preview"]["action_count"], 2)
            self.assertFalse(first["form_submission_supported"])
            self.assertNotIn("TOPSECRET", json.dumps(first["form_preview"]))
            self.assertEqual(first["links"][0]["url"], BASE + "public.wml")
            self.assertNotIn("remove.wml", json.dumps(first["links"]))
            second = page_view(home, card_index=1)
            self.assertEqual(second["form_preview"]["field_count"], 0)
            self.assertEqual(second["form_preview"]["action_count"], 0)

    def test_get_go_is_not_normal_agent_navigation(self):
        raw = (b'<wml><card id="a"><p>'
               b'<anchor>Delete<go href="/delete.wml" method="get"/></anchor>'
               b'<a href="safe.wml">Continue</a></p></card></wml>')
        result = parse_r5(raw, "text/vnd.wap.wml", probe_dir=R5)
        urls = [x["href"] for x in result["cards"][0]["links"]]
        self.assertNotIn("/delete.wml", urls)
        self.assertIn("safe.wml", urls)
        self.assertEqual(result["cards"][0]["form_preview"]["action_count"], 1)

    def test_wmlc_preview_uses_frozen_decoder(self):
        body = (R5 / "fixtures" / "binary_portal.wmlc").read_bytes()
        result = parse_r5(body, "application/vnd.wap.wmlc", probe_dir=R5)
        self.assertEqual(len(result["cards"]), 2)
        self.assertIsNotNone(result["cards"][0]["form_preview"])
        self.assertTrue(result["cards"][0]["form_preview"]["read_only"])

    def test_legacy_export_without_forms_still_works(self):
        with tempfile.TemporaryDirectory() as t:
            home = Path(t) / "home"
            make_capture(home, FORM)
            path = home / "r5_export.json"
            data = json.loads(path.read_text())
            for card in data["cards"]:
                card.pop("form_preview", None)
            path.write_text(json.dumps(data))
            view = page_view(home)
            self.assertTrue(view["ok"])
            self.assertIsNone(view["form_preview"])


if __name__ == "__main__":
    unittest.main()
