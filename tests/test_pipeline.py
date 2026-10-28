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


    def test_anonymous_session_only_replays_home_cookie_to_https_child(self):
        valid = "0123456789abcdef0123456789ABCDEF"
        calls = []
        def fake_capture(url, profile, folder, **kwargs):
            calls.append((url, kwargs.get("session_cookie")))
            Path(folder).mkdir()
            if len(calls) == 1:
                (Path(folder)/"headers.bin").write_bytes(
                    ("HTTP/1.1 200 OK\r\n"
                     "Set-Cookie: JSESSIONID=" + valid
                     + "; Path=/; HttpOnly\r\n\r\n").encode())
            return {"classification": "WML_CAPTURED_NEEDS_R5"}
        def fake_bridge(home, home_r5, child=None, child_r5=None, **kwargs):
            if child is None:
                return {"stage": "CHILD_GET_REQUIRED", "next_get": {
                    "url": "https://tx.com.cn/zone/cs/category.do?z=900000011",
                    "method": "GET", "profile": "wap1",
                    "follow_redirects": False}}
            return {"stage": "TWO_PAGE_EVIDENCE_MATCHED"}
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(pipeline, "_export", side_effect=lambda p, q: p/"r5_export.json"):
                with mock.patch.object(pipeline, "evaluate", side_effect=fake_bridge):
                    report = pipeline.run_job(
                        "https://tx.com.cn/", "wap1", Path(root)/"sample",
                        Path(root), capture_fn=fake_capture,
                        preferred_path="/zone/cs/category.do", anonymous_session=True)
            persisted = (Path(root)/"sample"/"run_report.json").read_text()
        self.assertEqual(report["stage"], "TWO_PAGE_EVIDENCE_MATCHED")
        self.assertEqual(report["anonymous_session_mode"], "jsessionid_https_only")
        self.assertEqual(calls[0], ("https://tx.com.cn/", None))
        self.assertEqual(calls[1][1], valid)
        self.assertEqual(len(calls), 2)
        self.assertNotIn(valid, persisted)

    def test_anonymous_session_ignores_other_cookie_names(self):
        valid = "0123456789abcdef0123456789ABCDEF"
        seen = []
        def fake_capture(url, profile, folder, **kwargs):
            seen.append(kwargs.get("session_cookie"))
            Path(folder).mkdir()
            if len(seen) == 1:
                (Path(folder)/"headers.bin").write_bytes(
                    ("HTTP/1.1 200 OK\r\nSet-Cookie: access=admin; Path=/\r\n"
                     "Set-Cookie: JSESSIONID=" + valid +
                     "; Path=/; HttpOnly\r\n\r\n").encode())
            return {"classification": "WML_CAPTURED_NEEDS_R5"}
        def fake_bridge(home, home_r5, child=None, child_r5=None, **kw):
            if child is None:
                return {"stage": "CHILD_GET_REQUIRED", "next_get": {
                    "url": "https://tx.com.cn/zone/cs/category.do",
                    "method": "GET", "profile": "wap1",
                    "follow_redirects": False}}
            return {"stage": "TWO_PAGE_EVIDENCE_MATCHED"}
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(pipeline, "_export", side_effect=lambda p, q: p/"r5_export.json"):
                with mock.patch.object(pipeline, "evaluate", side_effect=fake_bridge):
                    report = pipeline.run_job(
                        "https://tx.com.cn/", "wap1", Path(root)/"sample",
                        Path(root), capture_fn=fake_capture,
                        preferred_path="/zone/cs/category.do", anonymous_session=True)
        self.assertEqual(report["stage"], "TWO_PAGE_EVIDENCE_MATCHED")
        self.assertEqual(seen, [None, valid])

    def test_anonymous_session_fails_closed_on_missing_cookie(self):
        count = []
        def fake_capture(url, profile, folder, **kwargs):
            count.append(url)
            Path(folder).mkdir()
            (Path(folder)/"headers.bin").write_bytes(
                b"HTTP/1.1 200 OK\r\n\r\n")
            return {"classification": "WML_CAPTURED_NEEDS_R5"}
        def fake_bridge(home, home_r5, child=None, child_r5=None, **kw):
            return {"stage": "CHILD_GET_REQUIRED", "next_get": {
                "url": "https://tx.com.cn/zone/cs/category.do",
                "method": "GET", "profile": "wap1", "follow_redirects": False}}
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(pipeline, "_export", side_effect=lambda p, q: p/"r5_export.json"):
                with mock.patch.object(pipeline, "evaluate", side_effect=fake_bridge):
                    report = pipeline.run_job(
                        "https://tx.com.cn/", "wap1", Path(root)/"sample",
                        Path(root), capture_fn=fake_capture,
                        preferred_path="/zone/cs/category.do", anonymous_session=True)
        self.assertEqual(report["stage"], "PIPELINE_FAILED")
        self.assertEqual(len(count), 1)

    def test_anonymous_session_cannot_change_scheme_site_or_path(self):
        with tempfile.TemporaryDirectory() as root:
            for index, (url, path) in enumerate((
                ("http://tx.com.cn/", "/zone/cs/category.do"),
                ("https://example.org/", "/zone/cs/category.do"),
                ("https://tx.com.cn/", "/read/cs/goodBook.do"),
            )):
                with self.subTest(url=url, path=path):
                    with self.assertRaises(ValueError):
                        pipeline.run_job(
                            url, "wap1", Path(root)/str(index), Path(root),
                            preferred_path=path, anonymous_session=True)
            self.assertEqual(list(Path(root).iterdir()), [])

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
