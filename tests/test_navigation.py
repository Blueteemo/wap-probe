import unittest

from wap_probe.navigation import (evaluate_link, select_navigation,
    select_reachable_navigation, validate_preferred_path)

HOME = "http://wap.example.org/dir/index.wml"
SHA = "a" * 64


def choose(links, **changes):
    args = {
        "capture_status": "WML_CAPTURED_NEEDS_R5",
        "card_count": 2, "captured_body_sha256": SHA,
        "parsed_body_sha256": SHA,
    }
    args.update(changes)
    return select_navigation(HOME, links, **args)


class NavigationTests(unittest.TestCase):
    def test_relative(self):
        self.assertEqual(
            choose([{"href": "next.wml"}])["target_url"],
            "http://wap.example.org/dir/next.wml"
        )

    def test_root_relative(self):
        self.assertEqual(
            choose([{"href": "/next.wml"}])["target_url"],
            "http://wap.example.org/next.wml"
        )

    def test_absolute_same_origin(self):
        self.assertEqual(
            choose([{"href": "http://wap.example.org/next.wml"}])["status"],
            "READY_FOR_GET"
        )

    def test_fragment_only(self):
        self.assertEqual(choose([{"href": "#next"}])["status"],
                         "NO_SAFE_SECOND_PAGE")

    def test_other_page_with_fragment(self):
        self.assertEqual(
            choose([{"href": "next.wml#two"}])["target_url"],
            "http://wap.example.org/dir/next.wml"
        )

    def test_post_refused(self):
        self.assertEqual(
            choose([{"href": "submit.wml", "method": "POST"}])["status"],
            "NO_SAFE_SECOND_PAGE"
        )

    def test_other_domain(self):
        self.assertEqual(
            choose([{"href": "http://evil.example.net/"}])["status"],
            "NO_SAFE_SECOND_PAGE"
        )

    def test_scheme_upgrade(self):
        self.assertEqual(
            choose([{"href": "https://wap.example.org/next.wml"}])["status"],
            "NO_SAFE_SECOND_PAGE"
        )

    def test_other_port(self):
        self.assertEqual(
            choose([{"href": "http://wap.example.org:8080/next.wml"}])["status"],
            "NO_SAFE_SECOND_PAGE"
        )

    def test_explicit_default_port_normalized(self):
        self.assertEqual(
            choose([{"href": "http://wap.example.org:80/next.wml"}])["target_url"],
            "http://wap.example.org/next.wml"
        )

    def test_ip_literal(self):
        self.assertEqual(
            choose([{"href": "http://8.8.8.8/next.wml"}])["status"],
            "NO_SAFE_SECOND_PAGE"
        )

    def test_mailto(self):
        self.assertEqual(
            choose([{"href": "mailto:a@example.org"}])["status"],
            "NO_SAFE_SECOND_PAGE"
        )

    def test_wml_variable(self):
        self.assertEqual(
            choose([{"href": "next.wml?user=$(name)"}])["status"],
            "NO_SAFE_SECOND_PAGE"
        )

    def test_crlf_escape(self):
        self.assertEqual(
            choose([{"href": "next.wml%0d%0a"}])["status"],
            "NO_SAFE_SECOND_PAGE"
        )

    def test_sensitive_query(self):
        self.assertEqual(
            choose([{"href": "next.wml?sid=123"}])["status"],
            "NO_SAFE_SECOND_PAGE"
        )

    def test_login_destination_from_real_tx_capture(self):
        target, reason = evaluate_link(
            "https://tx.com.cn/",
            {"href": "/in/fltin_t.jsp?z=900000019&type=login", "method": "GET"},
        )
        self.assertIsNone(target)
        self.assertEqual(reason, "AUTH_FLOW")

    def test_login_redirect_destination_rejected(self):
        target, reason = evaluate_link(
            "https://tx.com.cn/",
            {"href": "/in/login.do?kid=&type=passwdforward", "method": "GET"},
        )
        self.assertIsNone(target)
        self.assertEqual(reason, "AUTH_FLOW")

    def test_encoded_auth_path_rejected(self):
        target, reason = evaluate_link(
            HOME, {"href": "/account/%2573ignin?next=posts.wml"}
        )
        self.assertIsNone(target)
        self.assertEqual(reason, "AUTH_FLOW")

    def test_auth_query_action_rejected(self):
        target, reason = evaluate_link(
            HOME, {"href": "/entry.wml?action=sign-in"}
        )
        self.assertIsNone(target)
        self.assertEqual(reason, "AUTH_FLOW")

    def test_login_skipped_before_public_content(self):
        result = choose([
            {"href": "/in/fltin_t.jsp?type=login"},
            {"href": "/love/index.do?z=900000018&from=txindex"}
        ])
        self.assertEqual(result["status"], "READY_FOR_GET")
        self.assertEqual(result["source_link_index"], 1)
        self.assertEqual(result["skipped"][0]["reason"], "AUTH_FLOW")

    def test_public_content_not_overblocked(self):
        target, reason = evaluate_link(
            "https://tx.com.cn/",
            {"href": "/love/index.do?z=900000018&from=txindex"}
        )
        self.assertEqual(reason, "OK")
        self.assertEqual(target, "https://tx.com.cn/love/index.do?z=900000018&from=txindex")

    def test_prefer_tx_category_from_real_home_links(self):
        links = [
            {"href": "/in/fltin_t.jsp?type=login"},
            {"href": "/love/index.do?z=1&from=txindex"},
            {"href": "/zone/cs/category.do?&z=900000014&from=txindex"},
            {"href": "/editor/cs/official.do?&id=1232&from=txindex"},
        ]
        r = select_reachable_navigation(
            "https://tx.com.cn/", [{"id": None, "links": links}],
            capture_status="WML_CAPTURED_NEEDS_R5",
            card_count=1, captured_body_sha256=SHA,
            parsed_body_sha256=SHA, preferred_path="/zone/cs/category.do"
        )
        self.assertEqual(r["status"], "READY_FOR_GET")
        self.assertEqual(r["source_link_index"], 2)
        self.assertEqual(r["target_url"],
            "https://tx.com.cn/zone/cs/category.do?&z=900000014&from=txindex")
        self.assertEqual(r["skipped"][1]["reason"], "OTHER_PUBLIC_LINK")

    def test_preferred_missing_cannot_fall_back_to_first_link(self):
        r = select_reachable_navigation(
            HOME, [{"id": "home", "links": [{"href": "other.wml"}]}],
            capture_status="WML_CAPTURED_NEEDS_R5", card_count=1,
            captured_body_sha256=SHA, parsed_body_sha256=SHA,
            preferred_path="/dir/category.do")
        self.assertEqual(r["status"], "PREFERRED_LINK_NOT_FOUND")
        self.assertIsNone(r["target_url"])

    def test_preferred_path_rejects_url_query_and_traversal(self):
        for value in ("https://evil.example/", "//evil.example/", "/../admin",
                      "/read/cs/category.do?token=abc", "/some%2fpath", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_preferred_path(value)

    def test_preferred_only_matches_eligible_get_same_origin(self):
        r = select_reachable_navigation(
            HOME, [{"id": "home", "links": [
                {"href": "https://wap.example.org/dir/category.do"},
                {"href": "category.do", "method": "POST"}]}],
            capture_status="WML_CAPTURED_NEEDS_R5", card_count=1,
            captured_body_sha256=SHA, parsed_body_sha256=SHA,
            preferred_path="/dir/category.do")
        self.assertEqual(r["status"], "PREFERRED_LINK_NOT_FOUND")

    def test_preferred_link_reachable_through_fragment(self):
        cards = [{"id": "home", "links": [{"href": "#posts"}]},
                 {"id": "posts", "links": [
                     {"href": "other.wml"}, {"href": "category.do"}]}]
        r = select_reachable_navigation(
            HOME, cards, capture_status="WML_CAPTURED_NEEDS_R5",
            card_count=2, captured_body_sha256=SHA,
            parsed_body_sha256=SHA, preferred_path="/dir/category.do")
        self.assertEqual(r["status"], "READY_FOR_GET")
        self.assertEqual(r["fragment_path"], ["posts"])
        self.assertEqual(r["source_link_index"], 1)

    def test_query_only_navigation(self):
        self.assertEqual(choose([{"href": "?page=2"}])["status"],
                         "READY_FOR_GET")

    def test_first_safe(self):
        self.assertEqual(
            choose([{"href": "#two"}, {"href": "next.wml"}])["source_link_index"], 1
        )

    def test_no_cards(self):
        self.assertEqual(
            choose([{"href": "next.wml"}], card_count=0)["status"],
            "HOME_NOT_VERIFIED"
        )

    def test_hash_mismatch(self):
        self.assertEqual(
            choose([{"href": "next.wml"}], parsed_body_sha256="b"*64)["status"],
            "HOME_NOT_VERIFIED"
        )

    def test_bad_capture(self):
        self.assertEqual(
            choose([{"href": "next.wml"}], capture_status="HTML")["status"],
            "HOME_NOT_VERIFIED"
        )

    def test_no_a_pass(self):
        self.assertEqual(
            choose([{"href": "next.wml"}])["A_navigation"], "PENDING"
        )


if __name__ == "__main__":
    unittest.main()
