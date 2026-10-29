"""Compare pinned independent Lowband WBXML corpus with unchanged R5 decoder.

No network, no dynamic Rust dependency, no implicit assertions of conformance.
Print compact evidence useful for an explicit compatibility-gate decision.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

from wap_probe.r5_adapter import _legacy_parser, parse_r5

REFERENCE = Path("tests/fixtures/lowband_wml13_reference.json")
R5 = Path(os.environ.get("R5_PROBE_DIR", ".r5_unpacked/wap-probe-live-discovery-r5/probe"))


def main():
    doc = json.loads(REFERENCE.read_text(encoding="utf-8"))
    core = _legacy_parser(R5)
    print("REFERENCE",
          doc["provenance"]["repo"],
          doc["provenance"]["commit"],
          "entries=" + str(len(doc["fixtures"])))
    for item in doc["fixtures"]:
        raw = bytes.fromhex(item["hex"])
        expected = item["expected_xml"] is not None
        outcome = "accepted"
        actual = ""
        try:
            actual, _ = core.decode_wmlc(raw)
            actual = actual.decode("utf-8") if isinstance(actual, bytes) else actual
            ET.fromstring(actual)
        except (ValueError, IndexError, UnicodeError, ET.ParseError, TypeError,
                NotImplementedError) as exc:
            outcome = "rejected"
            actual = ""
            name = type(exc).__name__
        verdict = "matched_rejection" if not expected and outcome == "rejected" else (
                  "unexpected_accept" if not expected else
                  "decoder_reject" if outcome == "rejected" else
                  "same_xml" if ET.canonicalize(actual) == ET.canonicalize(
                      item["expected_xml"]) else "different_xml")
        if expected and outcome == "accepted":
            left = ET.fromstring(actual)
            right = ET.fromstring(item["expected_xml"])
            left_tags = [e.tag for e in left.iter()]
            right_tags = [e.tag for e in right.iter()]
            left_text = [" ".join("".join(e.itertext()).split()) for e in left.iter() if e.tag == "card"]
            right_text = [" ".join("".join(e.itertext()).split()) for e in right.iter() if e.tag == "card"]
            print("WMLC_COMPARE", item["id"],
                  "same_tags=" + str(left_tags == right_tags),
                  "same_card_text=" + str(left_text == right_text),
                  "r5_card_text=" + repr(left_text[:2])[:250],
                  "ref_card_text=" + repr(right_text[:2])[:250],
                  "r5_card_attrs=" + repr([e.attrib for e in left.iter() if e.tag == "card"][:2])[:200],
                  "ref_card_attrs=" + repr([e.attrib for e in right.iter() if e.tag == "card"][:2])[:200])
        # A valid WBXML document can still be an ineligible browser deck
        # (e.g. a self-closing <wml/> with no card).
        browser = "skipped"
        if outcome == "accepted":
            try:
                cards = parse_r5(raw, "application/vnd.wap.wmlc", probe_dir=R5)["cards"]
                browser = "cards-" + str(len(cards))
            except (ValueError, IndexError, UnicodeError, TypeError,
                    NotImplementedError, KeyError, ET.ParseError) as exc:
                browser = "rejected-" + type(exc).__name__
        print("WMLC_REFERENCE", item["id"],
              "rust_expected=" + ("valid" if expected else "invalid"),
              "r5_decode=" + outcome,
              "xml=" + verdict,
              "agent_adapter=" + browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
