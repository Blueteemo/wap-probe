"""Pinned independent Lowband WBXML/WML 1.3 cross-decoder regressions.

We test WML Agent-relevant semantics (card count/text, token tag hierarchy,
explicit attributes) rather than incorrectly claiming DTD-expanded XML parity.
Lowband adds WML DTD defaults; the frozen R5 decoder intentionally does not.
See tests/fixtures/LOWBAND_LICENSE.txt for provenance and license.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from wap_probe.r5_adapter import _legacy_parser, parse_r5

R5 = Path(os.environ.get("R5_PROBE_DIR",
              ".r5_unpacked/wap-probe-live-discovery-r5/probe"))
SOURCE = Path("tests/fixtures/lowband_wml13_reference.json")

# These are WML 1.3 DTD defaults added by independent Rust Lowband, while
# R5 returns an explicit-attribute view. Do not erase arbitrary differences.
WML_DTD_DEFAULTS = {
    "card": {"newcontext": "false", "ordered": "true"},
    "p": {"align": "left"},
    "input": {"type": "text"},
    "img": {"vspace": "0", "hspace": "0", "align": "bottom"},
    "go": {"sendreferer": "false", "method": "get",
           "enctype": "application/x-www-form-urlencoded"},
    "do": {"optional": "false"},
    "meta": {"forua": "false"},
}


def canonical_semantic_tree(element: ET.Element):
    """Normalize only explicit, known WML DTD default attribute values."""
    defaults = WML_DTD_DEFAULTS.get(element.tag, {})
    attributes = {
        k: v for k, v in element.attrib.items()
        if not (k in defaults and v == defaults[k])
    }
    return (
        element.tag,
        tuple(sorted(attributes.items())),
        element.text or "",
        tuple(canonical_semantic_tree(child) for child in element),
        element.tail or "",
    )


class IndependentLowbandWbxmlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.core = _legacy_parser(R5)

    def test_pinned_provenance_and_counts(self):
        info = self.corpus["provenance"]
        self.assertEqual(info["repo"], "dills122/wap-labs")
        self.assertEqual(info["commit"],
                         "9cd7ab97dc6752fc1616feb3505a58603f6a45df")
        self.assertEqual(info["license"], "MIT")
        self.assertEqual(info["original_corpus_count"], 42)
        self.assertEqual(len(self.corpus["fixtures"]), 23)
        self.assertEqual(sum(x["expected_xml"] is not None for x in
                             self.corpus["fixtures"]), 12)
        self.assertEqual(sum(x["expected_error"] is not None for x in
                             self.corpus["fixtures"]), 11)
        self.assertTrue(Path("tests/fixtures/LOWBAND_LICENSE.txt").is_file())

    def test_independent_positive_documents_match_agent_semantics(self):
        samples = [x for x in self.corpus["fixtures"]
                   if x["expected_xml"] is not None]
        for sample in samples:
            with self.subTest(sample=sample["id"]):
                binary = bytes.fromhex(sample["hex"])
                decoded, _meta = self.core.decode_wmlc(binary)
                actual = ET.fromstring(decoded)
                expected = ET.fromstring(sample["expected_xml"])
                self.assertEqual(canonical_semantic_tree(actual),
                                 canonical_semantic_tree(expected),
                                 "Unexpected WBXML tag, text, or non-default attribute difference")
                parsed = parse_r5(binary, "application/vnd.wap.wmlc",
                                  probe_dir=R5)
                actual_cards = [e for e in actual.iter() if e.tag == "card"]
                self.assertEqual(len(parsed["cards"]), len(actual_cards))
                for got, xml_card in zip(parsed["cards"], actual_cards):
                    # R5's card text excludes WML presentation-only metadata.
                    normalized = " ".join("".join(xml_card.itertext()).split())
                    self.assertEqual(got["text"], normalized[:12000])
                self.assertTrue(parsed["source_sha256"])
                self.assertEqual(parsed["parser"], "frozen-r5-v0.3.3")

    def test_independent_negative_documents_rejected(self):
        samples = [x for x in self.corpus["fixtures"]
                   if x["expected_error"] is not None]
        for sample in samples:
            with self.subTest(sample=sample["id"]):
                binary = bytes.fromhex(sample["hex"])
                with self.assertRaises((ValueError, IndexError, TypeError,
                                        UnicodeError, NotImplementedError)):
                    self.core.decode_wmlc(binary)
                with self.assertRaises((ValueError, IndexError, TypeError,
                                        UnicodeError, NotImplementedError)):
                    parse_r5(binary, "application/vnd.wap.wmlc", probe_dir=R5)


if __name__ == "__main__":
    unittest.main()
