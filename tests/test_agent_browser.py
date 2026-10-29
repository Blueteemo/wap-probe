"""Offline behavior and safety tests for the agent-facing WML browser."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from wap_probe import agent_browser as b

class AgentBrowserTests(unittest.TestCase):

    def test_frozen_r5_unpacks_only_required_parser_modules(self):
        # Read-only runtime does not unpack historical website captures,
        # nested review ZIPs, Finder metadata or unrelated R5 scripts.
        with b.frozen_r5() as probe:
            names = sorted(p.name for p in probe.iterdir())
            self.assertEqual(names, ["wap_probe.py", "wap_wbxml.py"])
            self.assertTrue(all(p.is_file() for p in probe.iterdir()))
            self.assertFalse((probe.parent / "deepseek_review_original.zip").exists())

    def test_utf8(self):
        s=b'<wml><card><p>Hello World</p></card></wml>'
        self.assertIn("Hello World",b._safe_xml_text(s,"text/vnd.wap.wml"))

    def test_gb2312(self):
        s='<?xml version="1.0" encoding="GB2312"?><wml><card><p>中国书法</p></card></wml>'.encode("gb2312")
        self.assertIn("中国书法",b._safe_xml_text(s,"text/vnd.wap.wml"))

    def test_refuse_non_wml(self):
        self.assertIsNone(b._safe_xml_text(b'<html><p>Hello</p></html>',"text/vnd.wap.wml"))

    def test_no_external_entities(self):
        s=b'<!DOCTYPE wml [<!ENTITY x SYSTEM "file:///etc/passwd">]><wml><card><p>&x;</p></card></wml>'
        self.assertIsNone(b._safe_xml_text(s,"text/vnd.wap.wml"))

    def test_open_dry_run(self):
        with patch.object(b,"open_page") as f,patch("builtins.print"):
            self.assertEqual(b.main(["open","http://wap.example.org/","--out","/tmp/unused"]),2)
            f.assert_not_called()

    def test_follow_dry_run(self):
        with patch.object(b,"follow_link") as f,patch("builtins.print"):
            self.assertEqual(b.main(["follow","--session","/tmp/unused","--link","0"]),2)
            f.assert_not_called()

    def test_first_open_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"visit"
            def fake_capture(url,profile,folder): folder.mkdir()
            with patch.object(b,"page_view",return_value={"ok":False,"links":[]}):
                result=b.open_page("http://wap.example.org/",root,capture_page=fake_capture)
                self.assertEqual(result["page_count"],1)
                with self.assertRaises(FileExistsError):
                    b.open_page("http://wap.example.org/",root,capture_page=fake_capture)

    def test_follow_then_back_and_cross_origin_block(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"visit"
            (root/"pages"/"page-0001").mkdir(parents=True)
            (root/"session.json").write_text(json.dumps({"schema":"wap-agent-browser-v1","profile":"wap1","pages":["page-0001"],"cursor":0}))
            done=[]
            def fake_capture(url,profile,folder):
                done.append(url);folder.mkdir()
            v={"ok":True,"url":"http://wap.example.org/","links":[{"index":0,"url":"http://wap.example.org/detail.wml"}]}
            with patch.object(b,"page_view",return_value=v):
                self.assertEqual(b.follow_link(root,0,capture_page=fake_capture)["page_count"],2)
                self.assertEqual(b.go_back(root)["cursor"],0)
            v["links"]=[{"index":0,"url":"http://evil.example.org/"}]
            with patch.object(b,"page_view",return_value=v):
                with self.assertRaises(ValueError): b.follow_link(root,0,capture_page=fake_capture)
            self.assertEqual(done,["http://wap.example.org/detail.wml"])

    def test_limit(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/"session.json").write_text(json.dumps({"schema":"wap-agent-browser-v1","profile":"wap1","pages":[f"page-{n:04d}" for n in range(1,9)],"cursor":0}))
            with self.assertRaisesRegex(ValueError,"limit"):
                b.follow_link(p,0)
