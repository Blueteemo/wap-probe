import unittest

from wap_probe.navigation import evaluate_link, select_navigation

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
