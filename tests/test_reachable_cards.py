import unittest
from wap_probe.navigation import select_reachable_navigation

HOME="http://wap.example.org/index.wml"
SHA="a"*64

def select(cards,**args):
    kw=dict(capture_status="WML_CAPTURED_NEEDS_R5",card_count=len(cards),
            captured_body_sha256=SHA,parsed_body_sha256=SHA)
    kw.update(args)
    return select_reachable_navigation(HOME,cards,**kw)

class ReachableCardTests(unittest.TestCase):
    def test_fragment_to_second_card(self):
        r=select([{"id":"home","links":[{"href":"#news"}]},
                  {"id":"news","links":[{"href":"posts.wml"}]}])
        self.assertEqual(r["target_url"],"http://wap.example.org/posts.wml")
        self.assertEqual(r["fragment_path"],["news"])
        self.assertEqual(r["source_card_index"],1)
        self.assertEqual(r["A_navigation"],"PENDING")
    def test_unreachable_card_not_used(self):
        r=select([{"id":"home","links":[]},
                  {"id":"news","links":[{"href":"posts.wml"}]}])
        self.assertEqual(r["status"],"NO_SAFE_SECOND_PAGE")
    def test_cycle_does_not_loop(self):
        r=select([{"id":"home","links":[{"href":"#news"}]},
                  {"id":"news","links":[{"href":"#home"}]}])
        self.assertEqual(r["status"],"NO_SAFE_SECOND_PAGE")
    def test_duplicate_id_fail_closed(self):
        r=select([{"id":"home","links":[]},{"id":"home","links":[{"href":"next.wml"}]}])
        self.assertEqual(r["status"],"DUPLICATE_CARD_ID")
    def test_post_fragment_blocked(self):
        r=select([{"id":"home","links":[{"href":"#news","method":"POST"}]},
                  {"id":"news","links":[{"href":"next.wml"}]}])
        self.assertEqual(r["status"],"NO_SAFE_SECOND_PAGE")
    def test_fragment_only_never_a_pass(self):
        r=select([{"id":"home","links":[{"href":"#news"}]},
                  {"id":"news","links":[]}])
        self.assertEqual(r["A_navigation"],"PENDING")

    def test_real_r5_portal_fragment(self):
        import os
        from pathlib import Path
        from wap_probe.r5_adapter import parse_r5
        probe_dir = Path(os.environ.get("R5_PROBE_DIR", ".r5_unpacked/wap-probe-live-discovery-r5/probe"))
        body = (probe_dir / "fixtures" / "portal.wml").read_bytes()
        record = parse_r5(body, "text/vnd.wap.wml", probe_dir=probe_dir)
        hash_value = record["source_sha256"]
        outcome = select_reachable_navigation(
            HOME, record["cards"],
            capture_status="WML_CAPTURED_NEEDS_R5",
            card_count=len(record["cards"]),
            captured_body_sha256=hash_value, parsed_body_sha256=hash_value)
        self.assertEqual(outcome["status"], "READY_FOR_GET")
        self.assertEqual(outcome["target_url"], "http://wap.example.org/posts.wml")
        self.assertEqual(outcome["fragment_path"], ["news"])
