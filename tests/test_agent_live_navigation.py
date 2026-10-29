"""Frozen R5 -> Agent legacy WML <do><go> compatibility; no unsafe auto-follow."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from wap_probe import agent_browser
from wap_probe.agent_mcp import BrowserServer
from wap_probe.navigation import evaluate_link
from test_agent_cards import write_page

HOME = "http://wap.example.org/"
BODY = (b'<wml><card id="home"><p>Mobile index'
        b'<a href="ordinary.wml">Ordinary</a>'
        b'<do type="options"><go href="m_service/default.wml" method="get"/></do>'
        b'<do type="help"><go href="scripts/menu.wmls#run"/></do>'
        b'<do type="accept"><go href="delete.wml"/></do>'
        b'<do type="options"><go href="search.wml">'
        b'<postfield name="q" value="$(q)"/></go></do>'
        b'<do type="prev"><prev/></do>'
        b'</p></card></wml>')
CHILD = b'<wml><card id="child"><p>Useful child page</p></card></wml>'


class LegacyDoNavigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "visit"
        self.requests = []

    def tearDown(self):
        self.tmp.cleanup()

    def capture(self, url, profile, folder):
        self.requests.append(url)
        write_page(folder, url, BODY if url == HOME else CHILD)

    def test_script_and_postfields_never_enter_readable_navigation(self):
        page = agent_browser.open_page(HOME, self.root, capture_page=self.capture)
        self.assertTrue(page["ok"])
        self.assertEqual([x["url"] for x in page["links"]], [HOME + "ordinary.wml"])
        self.assertEqual([x["url"] for x in page["do_links"]],
                         [HOME + "m_service/default.wml"])
        self.assertEqual(page["do_links"][0]["source"], "do_go")
        self.assertTrue(page["do_links"][0]["explicit_execute_required"])
        self.assertEqual(page["do_links"][0]["submitted_fields"], 0)
        self.assertFalse(page["form_submission_supported"])
        self.assertNotIn("delete.wml", json.dumps(page["do_links"]))
        self.assertNotIn("scripts/menu", json.dumps(page["do_links"]))
        self.assertNotIn("search.wml", json.dumps(page["do_links"]))
        self.assertEqual(self.requests, [HOME])

    def test_explicit_follow_do_makes_exactly_one_additional_get(self):
        agent_browser.open_page(HOME, self.root, capture_page=self.capture)
        child = agent_browser.follow_do(self.root, 0, capture_page=self.capture)
        self.assertEqual(self.requests, [HOME, HOME + "m_service/default.wml"])
        self.assertEqual(child["page_count"], 2)
        self.assertIn("Useful child page", child["text"])
        back = agent_browser.go_back(self.root)
        self.assertEqual(back["cursor"], 0)
        self.assertEqual(len(back["do_links"]), 1)

    def test_invalid_do_index_does_not_fetch(self):
        agent_browser.open_page(HOME, self.root, capture_page=self.capture)
        for index in (-1, 1, True, 100):
            with self.assertRaises(ValueError):
                agent_browser.follow_do(self.root, index, capture_page=self.capture)
        self.assertEqual(self.requests, [HOME])

    def test_cli_requires_explicit_execute(self):
        with patch.object(agent_browser, "follow_do") as spy, patch("builtins.print"):
            status = agent_browser.main(["go", "--session", str(self.root), "--index", "0"])
        self.assertEqual(status, 2)
        spy.assert_not_called()

    def test_mcp_requires_server_and_tool_opt_in(self):
        agent_browser.open_page(HOME, self.root, capture_page=self.capture)
        server = BrowserServer(Path(self.tmp.name), allow_network=False)
        server.sessions["opaque"] = self.root
        names = [x["name"] for x in server.dispatch(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        )["result"]["tools"]]
        self.assertIn("wap_go", names)
        for execute in (False, True):
            reply = server.dispatch({
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "wap_go", "arguments": {
                    "session_id": "opaque", "index": 0, "execute": execute}}
            })["result"]
            self.assertTrue(reply["isError"])
        self.assertEqual(self.requests, [HOME])

    def test_wml_script_and_binary_resource_links_rejected(self):
        for suffix in ("file.wmls", "file.wmlsc", "game.jar", "pic.png", "movie.3gp"):
            target, reason = evaluate_link(HOME, {"href": suffix})
            self.assertIsNone(target)
            self.assertEqual(reason, "NON_WML_RESOURCE")

    def test_mutating_get_action_and_query_blocked(self):
        for url in ("delete.wml", "/remove/item.wml", "info.wml?action=delete"):
            target, reason = evaluate_link(HOME, {"href": url})
            self.assertIsNone(target)
            self.assertEqual(reason, "MUTATION_FLOW")

    def test_no_input_do_go_is_not_a_form_submission(self):
        page = agent_browser.open_page(HOME, self.root, capture_page=self.capture)
        actions = page["form_preview"]["actions"]
        self.assertGreaterEqual(len(actions), 4)
        self.assertTrue(all(x["submission_available"] is False for x in actions))
        # The new route is an *explicit* GET, never a postfield-bearing form.
        self.assertEqual(page["do_links"][0]["method"], "GET")


if __name__ == "__main__":
    unittest.main()
