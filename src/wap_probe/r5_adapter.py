"""Run the frozen R5 parser offline against captured R6 HTTP evidence.

The parser entry point is the *real*, unmodified R5 0.3.3 implementation.
No network requests, login, automatic redirects, or automatic A grades.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from wap_probe.form_inspector import inspect_forms

R5_SUPPORTED = {"text/vnd.wap.wml", "application/vnd.wap.wmlc"}
R5_SCHEMA = "r6-r5-export-v1"


def _legacy_parser(probe_dir: Path):
    probe_dir = Path(probe_dir).resolve(strict=True)
    core = probe_dir / "wap_probe.py"
    wbxml = probe_dir / "wap_wbxml.py"
    if not core.is_file() or not wbxml.is_file():
        raise ValueError("R5 parser and WBXML decoder are required")

    # Frozen R5 uses 'from wap_wbxml import ...'. Bind the exact sibling
    # module, not a similarly named module from an unrelated Python path.
    core_spec = importlib.util.spec_from_file_location("_wap_probe_r5_core", core)
    wb_spec = importlib.util.spec_from_file_location("wap_wbxml", wbxml)
    if not core_spec or not core_spec.loader or not wb_spec or not wb_spec.loader:
        raise ValueError("Invalid frozen R5 Python modules")
    saved = sys.modules.get("wap_wbxml")
    try:
        wb_module = importlib.util.module_from_spec(wb_spec)
        sys.modules["wap_wbxml"] = wb_module
        wb_spec.loader.exec_module(wb_module)
        core_module = importlib.util.module_from_spec(core_spec)
        core_spec.loader.exec_module(core_module)
        return core_module
    finally:
        if saved is None:
            sys.modules.pop("wap_wbxml", None)
        else:
            sys.modules["wap_wbxml"] = saved


def parse_r5(body: bytes, content_type: str, *, probe_dir: Path) -> dict:
    """Analyze exact captured bytes with R5 and create an R6 export."""
    if not isinstance(body, bytes) or not body or len(body) > 1_048_576:
        raise ValueError("Missing or oversized captured entity")
    if not isinstance(content_type, str):
        raise ValueError("Invalid Content-Type")
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime not in R5_SUPPORTED:
        raise ValueError("Unsupported R5/R6 MIME")
    core = _legacy_parser(probe_dir)
    if core.VERSION != "0.3.3":
        raise ValueError("Unexpected R5 parser core version")
    analysis = core.inspect_markup(body, content_type)
    if (analysis.get("valid_xml") is not True
            or analysis.get("format") not in ("wml", "wmlc")
            or not analysis.get("cards")):
        raise ValueError("R5 did not verify a WML/WMLC deck")
    if mime == "text/vnd.wap.wml" and analysis["format"] != "wml":
        raise ValueError("R5 MIME/format mismatch")
    if mime == "application/vnd.wap.wmlc" and analysis["format"] != "wmlc":
        raise ValueError("R5 MIME/format mismatch")

    # The structural preview is read-only; never create or submit requests.
    try:
        xml_body = core.decode_wmlc(body)[0] if mime == "application/vnd.wap.wmlc" else body
        parsed_forms = inspect_forms(
            xml_body, "text/vnd.wap.wml" if mime.endswith("wmlc") else content_type)
        if len(parsed_forms) != len(analysis["cards"]):
            parsed_forms = []
    except (ValueError, TypeError, UnicodeError):
        parsed_forms = []

    cards = []
    for card_index, card in enumerate(analysis["cards"]):
        links = []
        for link in card.get("links", []):
            if not isinstance(link, dict):
                raise ValueError("Malformed R5 link")
            # Even a GET link can require <postfield> or other input.
            # Such links must never become automatic second-page targets.
            # GET may be state-changing. Never treat a WML <go> action as
            # implicit safe navigation, whether it has postfields or not.
            if link.get("kind") == "go":
                continue
            if link.get("requires_inputs"):
                continue
            href, method = link.get("href"), link.get("method", "get")
            if not isinstance(href, str) or not isinstance(method, str):
                raise ValueError("Malformed R5 link fields")
            links.append({"href": href, "method": method.upper()})
        text = card.get("text", "")
        if not isinstance(text, str):
            raise ValueError("R5 card text is not a string")
        cards.append({"id": card.get("id"), "links": links,
                      "text": text[:12000],
                      "form_preview": parsed_forms[card_index] if parsed_forms else None})

    return {
        "schema": R5_SCHEMA,
        "status": "ok",
        "strict": True,
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "cards": cards,
        "parser": "frozen-r5-v0.3.3",
        "source": "R5 offline inspect_markup (not device/DTD conformance)",
    }


def parse_capture(capture_dir: Path, *, probe_dir: Path) -> dict:
    """Run R5 only after the existing R6 evidence gate accepts the capture."""
    from wap_probe.evidence_gate import verify_folder

    capture_dir = Path(capture_dir)
    evidence = verify_folder(capture_dir)
    if evidence["status"] not in ("WML_CAPTURED_NEEDS_R5", "WMLC_CAPTURED_NEEDS_R5"):
        raise ValueError("R6 evidence rejected: " + evidence["status"])
    metadata = json.loads((capture_dir / "metadata.json").read_text(encoding="utf-8"))
    return parse_r5(
        (capture_dir / "body.bin").read_bytes(),
        metadata["content_type"],
        probe_dir=probe_dir,
    )


def main():
    p = argparse.ArgumentParser(description="Generate genuine frozen-R5 export from offline capture")
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--r5-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("Output exists; refusing overwrite")
    export = parse_capture(args.capture, probe_dir=args.r5_dir)
    args.out.write_text(json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"R5 parsed {len(export['cards'])} card(s); SHA-256 {export['source_sha256']}")


if __name__ == "__main__":
    main()
