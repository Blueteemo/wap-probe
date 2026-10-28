import tempfile
import unittest
from pathlib import Path
from unittest import mock
from wap_probe import pipeline

class PipelineTests(unittest.TestCase):
    def test_dryrun_does_not_capture(self):
        with mock.patch.object(pipeline,"capture") as c:
            self.assertEqual(pipeline.main(["--url","http://tx.com.cn/"]),0)
            c.assert_not_called()

    def test_full_two_page_executes_only_two_get_calls(self):
        urls=[]
        def fake_capture(url,profile,folder):
            urls.append(url)
            Path(folder).mkdir()
            return {"classification":"WML_CAPTURED_NEEDS_R5"}
        def fake_bridge(home, home_r5, child=None, child_r5=None):
            if child is None:
                return {"stage": "CHILD_GET_REQUIRED", "next_get": {
                    "url": "http://tx.com.cn/next.wml", "method": "GET",
                    "profile": "wap1", "follow_redirects": False}}
            return {"stage": "TWO_PAGE_EVIDENCE_MATCHED", "A_navigation": "PENDING"}
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(pipeline, "_export", side_effect=lambda p, q: p/"r5_export.json"):
                with mock.patch.object(pipeline, "evaluate", side_effect=fake_bridge):
                    r=pipeline.run_job("http://tx.com.cn/","wap1",Path(d)/"run",
                                       Path(d),capture_fn=fake_capture)
            self.assertEqual(r["stage"],"TWO_PAGE_EVIDENCE_MATCHED")
            self.assertEqual(urls,["http://tx.com.cn/","http://tx.com.cn/next.wml"])
            self.assertEqual(r["A_origin"],"PENDING")
            self.assertEqual(r["A_navigation"],"PENDING")

    def test_preference_reused_in_child_binding_and_report(self):
        urls, seen = [], []
        def fake_capture(url, profile, folder):
            urls.append(url)
            Path(folder).mkdir()
            return {"classification": "WML_CAPTURED_NEEDS_R5"}
        def fake_bridge(home, home_r5, child=None, child_r5=None, **kw):
            seen.append(kw.get("preferred_path"))
            if child is None:
                return {"stage": "CHILD_GET_REQUIRED", "next_get": {
                    "url": "http://tx.com.cn/zone/cs/category.do",
                    "method": "GET", "profile": "wap1",
                    "follow_redirects": False}}
            return {"stage": "TWO_PAGE_EVIDENCE_MATCHED"}
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(pipeline, "_export",
                                   side_effect=lambda p, q: p / "r5_export.json"):
                with mock.patch.object(pipeline, "evaluate", side_effect=fake_bridge):
                    report = pipeline.run_job(
                        "http://tx.com.cn/", "wap1", Path(d) / "sample", Path(d),
                        capture_fn=fake_capture,
                        preferred_path="/zone/cs/category.do")
        self.assertEqual(report["stage"], "TWO_PAGE_EVIDENCE_MATCHED")
        self.assertEqual(report["preferred_path"], "/zone/cs/category.do")
        self.assertEqual(seen, ["/zone/cs/category.do", "/zone/cs/category.do"])
        self.assertEqual(len(urls), 2)

    def test_html_home_stops_after_one_get(self):
        urls=[]
        def fake_capture(url,profile,folder):
            urls.append(url)
            Path(folder).mkdir()
            return {"classification":"HTML"}
        with tempfile.TemporaryDirectory() as d:
            r=pipeline.run_job("http://tx.com.cn/","wap1",Path(d)/"run",
                               Path(d),capture_fn=fake_capture)
            self.assertEqual(r["stage"],"HOME_NOT_WML_EVIDENCE")
            self.assertEqual(len(urls),1)
