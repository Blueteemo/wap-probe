"""Offline GET form plan policy: verify captured R5 source; never send GET."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from wap_probe.agent_browser import page_view, main as cli_main
from wap_probe.agent_mcp import BrowserServer
from wap_probe.form_plan import plan_current
from wap_probe.r5_adapter import parse_capture

R5 = Path(os.environ.get("R5_PROBE_DIR", ".r5_unpacked/wap-probe-live-discovery-r5/probe"))
HOME = "http://wap.example.org/"
SEARCH = (
    b'<wml><card id="search"><p>'
    b'<input name="q" type="text" maxlength="16"/>'
    b'<select name="genre"><option value="puzzle">Puzzle</option>'
    b'<option value="action">Action</option></select>'
    b'<anchor>Search<go method="get" href="/search.wml">'
    b'<postfield name="q" value="$(q)"/>'
    b'<postfield name="cat" value="$(genre)"/>'
    b'</go></anchor></p></card></wml>'
)


def evidence(folder: Path, body: bytes, url: str = HOME):
    folder.mkdir(parents=True)
    head = (f"HTTP/1.1 200 OK\r\nContent-Type: text/vnd.wap.wml\r\n"
            f"Content-Length: {len(body)}\r\n\r\n").encode()
    meta = {
        "url": url, "final_url": url, "profile": "wap1",
        "curl_exit_code": 0, "http_status": 200,
        "content_type": "text/vnd.wap.wml", "body_bytes": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "headers_sha256": hashlib.sha256(head).hexdigest(),
        "dns_answers": ["8.8.8.8"], "pinned_ip": "8.8.8.8", "remote_ip": "8.8.8.8",
    }
    (folder / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (folder / "headers.bin").write_bytes(head)
    (folder / "body.bin").write_bytes(body)
    exported = parse_capture(folder, probe_dir=R5)
    (folder / "r5_export.json").write_text(json.dumps(exported), encoding="utf-8")


def session(root: Path, body: bytes = SEARCH):
    folder = root / "pages" / "page-0001"
    folder.parent.mkdir(parents=True)
    evidence(folder, body)
    (root / "session.json").write_text(json.dumps({
        "schema": "wap-agent-browser-v1", "profile": "wap1",
        "pages": ["page-0001"], "cursor": 0,
        "card_positions": [0], "card_history": [],
    }), encoding="utf-8")


class GetFormPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "session"

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_plan_redacted_stable_and_no_network(self):
        session(self.root)
        self.assertEqual(page_view(self.root / "pages" / "page-0001")["links"], [])
        supplied = {"q": "猫 & dog", "genre": "puzzle"}
        before = sorted(str(p) for p in self.root.rglob("*"))
        result = plan_current(self.root, 0, supplied)
        self.assertTrue(result["ok"])
        self.assertEqual(result["query_keys"], ["q", "cat"])
        self.assertEqual(result["path"], "/search.wml")
        self.assertTrue(result["review_required"])
        self.assertFalse(result["execution_supported"])
        self.assertEqual(result["target_origin"], "http://wap.example.org")
        self.assertEqual(result["request_sha256"],
                         plan_current(self.root, 0, supplied)["request_sha256"])
        self.assertNotIn("猫", json.dumps(result, ensure_ascii=False))
        self.assertNotIn("puzzle", json.dumps(result))
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob("*")))

    def test_dangerous_and_cross_origin_actions(self):
        for path in ["/delete.wml", "/logout.wml", "/save", "/payment.wml"]:
            self._bad_action(path, "Potential state-changing")
        self._bad_action("https://elsewhere.example.org/search.wml", "rejected by public")
        self._bad_action("/secret.wml", "Sensitive form target path")
        self._bad_action("/account/private-id", "Sensitive form target path")

    def _bad_action(self, href, expected):
        raw = SEARCH.replace(b"/search.wml", href.encode("ascii"))
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "session"
            session(root, raw)
            with self.assertRaisesRegex(ValueError, expected):
                plan_current(root, 0, {"q": "hello", "genre": "puzzle"})

    def test_reject_unsupported_dynamic_or_complex_targets(self):
        for href in [b"/search.wml?q=$(q)", b"/search.wml?x=1",
                     b"/search.wml#card", b"/search.wml/$(q)",
                     b"javascript:alert(1)"]:
            with tempfile.TemporaryDirectory() as t:
                root = Path(t) / "session"
                session(root, SEARCH.replace(b"/search.wml", href))
                with self.assertRaises(ValueError):
                    plan_current(root, 0, {"q": "hello", "genre": "puzzle"})

    def test_reject_post_and_sensitive_fields(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "session"
            session(root, SEARCH.replace(b'method="get"', b'method="post"'))
            with self.assertRaisesRegex(ValueError, "Only GET"):
                plan_current(root, 0, {"q": "hello", "genre": "puzzle"})
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "session"
            session(root, SEARCH.replace(b'name="q"', b'name="password"'))
            with self.assertRaises(ValueError):
                plan_current(root, 0, {"password": "hidden", "genre": "puzzle"})

    def test_reject_missing_extra_or_invalid_variables(self):
        session(self.root)
        for vars in [
            {"q": "hello"}, {"q": "hello", "genre": "action", "other": "oops"},
            {"q": "hello", "genre": "missing"},
            {"q": "hello\nworld", "genre": "puzzle"},
            {"q": "x" * 17, "genre": "puzzle"},
            {"q": "token", "genre": 22},
        ]:
            with self.subTest(vars=vars):
                with self.assertRaises(ValueError):
                    plan_current(self.root, 0, vars)
        with self.assertRaises(ValueError):
            plan_current(self.root, True, {"q": "a", "genre": "puzzle"})

    def test_reject_setvar_or_variable_conversion(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "session"
            session(root, SEARCH.replace(b'$(q)', b'$(q:unesc)'))
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                plan_current(root, 0, {"q": "hello", "genre": "puzzle"})

    def test_cli_plan_reads_file_and_prints_no_value(self):
        session(self.root)
        values_path = Path(self.tmp.name) / "input.json"
        values_path.write_text(json.dumps({"q": "hello-user", "genre": "puzzle"}))
        outputs = []
        with patch("builtins.print", side_effect=outputs.append):
            code = cli_main(["form-plan", "--session", str(self.root),
                             "--action", "0", "--values-file", str(values_path)])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(outputs[0])["ok"])
        self.assertNotIn("hello-user", outputs[0])

    def test_mcp_plan_no_network_opt_in_needed(self):
        session(self.root)
        server = BrowserServer(Path(self.tmp.name), allow_network=False)
        server.sessions["opaque"] = self.root
        r = server.dispatch({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "wap_form_plan", "arguments": {
                "session_id": "opaque", "action": 0,
                "values": {"q": "hello", "genre": "puzzle"}}},
        })
        self.assertFalse(r["result"]["isError"])
        obj = r["result"]["structuredContent"]
        self.assertTrue(obj["ok"])
        self.assertNotIn("hello", json.dumps(obj))
        self.assertNotIn("session", obj)
        tools = server.dispatch({"jsonrpc": "2.0", "id": 5,
                                 "method": "tools/list"})["result"]["tools"]
        self.assertIn("wap_form_plan", {x["name"] for x in tools})
        self.assertNotIn("wap_form_execute", {x["name"] for x in tools})

    def test_tampered_original_body_not_plannable(self):
        session(self.root)
        p = self.root / "pages" / "page-0001" / "body.bin"
        p.write_bytes(p.read_bytes() + b"tampered")
        with self.assertRaises(ValueError):
            plan_current(self.root, 0, {"q": "a", "genre": "puzzle"})


class WMLCompatibilityMatrixTests(unittest.TestCase):
    """Offline standards-boundary corpus. An unsupported feature must fail closed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "session"

    def tearDown(self):
        self.tmp.cleanup()

    def _with(self, raw: bytes, values=None):
        session(self.root, raw)
        return plan_current(self.root, 0, values or {"q": "hello", "genre": "puzzle"})

    def _reject(self, raw: bytes, message: str = ""):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "session"
            session(root, raw)
            with self.assertRaisesRegex(ValueError, message):
                plan_current(root, 0, {"q": "hello", "genre": "puzzle"})

    def test_ambiguous_controls_with_same_name(self):
        raw = SEARCH.replace(
            b'<input name="q" type="text" maxlength="16"/>',
            b'<input name="q" type="text" maxlength="16"/>'
            b'<input name="q" type="text" maxlength="16"/>',
        )
        self._reject(raw, "Duplicate WML control variable")

    def test_event_driven_variable_assignment_not_emulated(self):
        event = (b'<onevent type="onenterforward"><refresh>'
                 b'<setvar name="q" value="do-not-evaluate"/>'
                 b'</refresh></onevent>')
        raw = SEARCH.replace(b'<card id="search">', b'<card id="search">' + event)
        self._reject(raw, "Stateful WML events")

    def test_postfield_setvar_must_not_be_interpreted(self):
        raw = SEARCH.replace(
            b'<postfield name="q" value="$(q)"/>',
            b'<postfield name="q" value="$(q)"/>'
            b'<setvar name="q" value="override"/>')
        self._reject(raw, "Stateful WML events")

    def test_input_format_mask_not_ignored(self):
        raw = SEARCH.replace(
            b'<input name="q" type="text" maxlength="16"/>',
            b'<input name="q" type="text" maxlength="16" format="*N"/>',
        )
        self._reject(raw, "Missing verified public form input")

    def test_option_onpick_is_not_silently_ignored(self):
        raw = SEARCH.replace(
            b'<option value="puzzle">Puzzle</option>',
            b'<option value="puzzle" onpick="next.wml">Puzzle</option>',
        )
        self._reject(raw, "Missing verified public form input")

    def test_duplicate_choice_values_are_ambiguous(self):
        raw = SEARCH.replace(
            b'<option value="action">Action</option>',
            b'<option value="puzzle">Action</option>',
        )
        self._reject(raw, "Missing verified public form input")

    def test_select_multiple_not_emulated_as_one_value(self):
        raw = SEARCH.replace(
            b'<select name="genre">',
            b'<select name="genre" multiple="true">',
        )
        self._reject(raw, "Missing verified public form input")

    def test_invalid_maxlength_not_treated_as_unbounded(self):
        raw = SEARCH.replace(b'maxlength="16"', b'maxlength="16bad"')
        self._reject(raw, "Missing verified public form input")

    def test_url_input_is_not_an_unchecked_text_value(self):
        raw = SEARCH.replace(
            b'<input name="q" type="text" maxlength="16"/>',
            b'<input name="q" type="url" maxlength="16"/>',
        )
        self._reject(raw, "Missing verified public form input")

    def test_non_utf8_source_requires_explicit_utf8_accept_charset(self):
        raw = SEARCH.replace(
            b'<p>', '<p>你好'.encode("gb2312"), 1)
        raw = (b'<?xml version="1.0" encoding="gb2312"?>' + raw)
        self._reject(raw, "Non-UTF-8 document requires explicit")
        accepted = raw.replace(b'method="get"', b'method="get" accept-charset="utf-8"')
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "session"
            session(root, accepted)
            # The evidence metadata is UTF-8 by default but XML declaration wins.
            got = plan_current(root, 0, {"q": "hello", "genre": "puzzle"})
            self.assertTrue(got["ok"])

    def test_unicode_query_encoding_is_bounded(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "session"
            session(root)
            values = {"q": "猫 & fish", "genre": "puzzle"}
            planned = plan_current(root, 0, values)
            self.assertTrue(planned["ok"])
            self.assertEqual(planned["query_keys"], ["q", "cat"])
            # Explicitly bound UTF-8 representation; only size/hash leave.
            self.assertGreater(planned["query_bytes"], len("q=cat&cat=puzzle"))

    def test_sensitive_actions_still_not_executable(self):
        self.assertNotIn("form-execute", __import__(
            "wap_probe.agent_browser", fromlist=["main"]).__dict__)


if __name__ == "__main__":
    unittest.main()
