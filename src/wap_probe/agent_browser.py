"""Rootless Agent-facing WML reader; public HTTP(S) GET only, no WSP/WDP."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from wap_probe.bridge import read_r5_export
from wap_probe.errors import safe_error
from wap_probe.collector import capture, validate_url, PROFILES
from wap_probe.evidence_gate import verify_folder
from wap_probe.navigation import evaluate_link
from wap_probe.r5_adapter import parse_capture

ARCHIVE_NAME = "WAP_Probe_WAP_Labs_Interop_R5_20261028.zip"
ARCHIVE_SHA256 = "cb98d2cc060cfe775a8adf99162160c7651c306a534f3770bbb7c356034b31fa"
VALID_STATUSES = {"WML_CAPTURED_NEEDS_R5", "WMLC_CAPTURED_NEEDS_R5"}
MAX_PAGES = 8
MAX_LINKS = 64
MAX_TEXT = 12000
MAX_CARDS = 256
MAX_HISTORY = 64
CARD_REF = re.compile(r'#[A-Za-z_][A-Za-z0-9_.:-]{0,127}\Z')


@contextmanager
def frozen_r5():
    """Verify source SHA256 and unpack parser to ephemeral user-space directory."""
    archive = Path(__file__).resolve().parents[2] / "vendor" / "r5" / ARCHIVE_NAME
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Frozen R5 source checksum mismatch")
    with tempfile.TemporaryDirectory(prefix="wap-agent-r5-") as tmp:
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                name = item.filename
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name or len(name) > 512:
                    raise ValueError("Unsafe frozen R5 archive entry")
            z.extractall(tmp)
        yield Path(tmp) / "wap-probe-live-discovery-r5" / "probe"


def _safe_xml_text(data: bytes, content_type: str) -> str | None:
    if len(data) > 1048576 or b"<!entity" in data.lower():
        return None
    declaration = re.match(rb"\s*<\?xml[^>]{0,200}\?>", data, flags=re.I)
    match = (re.search(rb"encoding\s*=\s*['\"]([a-zA-Z0-9_-]+)['\"]",
                       declaration.group(0), flags=re.I) if declaration else None)
    mime = re.search(r"charset\s*=\s*['\"]?([a-zA-Z0-9_-]+)", content_type, flags=re.I)
    codec = ((match.group(1).decode("ascii") if match else None)
             or (mime.group(1) if mime else "utf-8")).lower()
    if codec not in {"utf-8", "utf8", "gb2312", "gbk", "big5", "iso-8859-1", "us-ascii"}:
        return None
    try:
        root = ET.fromstring(data.decode(codec, errors="strict"))
    except (UnicodeError, LookupError, ET.ParseError, ValueError):
        return None
    if root.tag.rsplit("}", 1)[-1].lower() != "wml":
        return None
    segments = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].lower() == "card":
            value = " ".join("".join(node.itertext()).split())
            if value:
                segments.append(value)
    return "\n".join(segments)[:MAX_TEXT]


def page_view(page_dir: Path, *, card_index: int = 0) -> dict:
    """Verify recorded bytes; expose only the selected WML card and its links."""
    page_dir = Path(page_dir)
    is_wsp = (page_dir / "wsp_manifest.json").exists()
    if is_wsp:
        from wap_probe.wsp_evidence import verify_imported_page
        parsed = verify_imported_page(page_dir)
        # Local R5 exports are not signed: reject tampered display text by
        # re-running frozen R5 against the exact WSP reply body at each read.
        from wap_probe.r5_adapter import parse_r5
        from wap_probe.bridge import load_json
        mime = parsed.content_type + (
            "; charset=" + parsed.charset if parsed.charset else "")
        with frozen_r5() as probe:
            rebuilt = parse_r5(parsed.body, mime, probe_dir=probe)
        if load_json(page_dir / "r5_export.json") != rebuilt:
            raise ValueError("Imported WSP R5 export no longer matches source")
        record = read_r5_export(page_dir / "r5_export.json", page_dir)
        result = {
            "url": "http://interop.wap.shrimpworks.dev/",
            "http_status": None, "wsp_status": parsed.status,
            "transport": "wsp-offline",
            "mime": parsed.content_type, "bytes": len(parsed.body),
            "sha256": hashlib.sha256(parsed.body).hexdigest(),
            "capture_status": "WSP_OFFLINE_VERIFIED",
            "source_authenticated": False, "ok": False,
            "text": None, "links": [], "card_links": [], "do_links": [],
            "cards": [],
        }
    else:
        evidence = verify_folder(page_dir)
        metadata = json.loads((page_dir / "metadata.json").read_text(encoding="utf-8"))
        result = {
            "url": metadata["url"], "http_status": metadata["http_status"],
            "mime": metadata["content_type"].split(";", 1)[0].strip().lower(),
            "bytes": metadata["body_bytes"], "sha256": metadata["body_sha256"],
            "capture_status": evidence["status"], "ok": False,
            "text": None, "links": [], "card_links": [], "do_links": [],
            "cards": [],
        }
        if evidence["status"] not in VALID_STATUSES:
            return result
        record = read_r5_export(page_dir / "r5_export.json", page_dir)
    if type(card_index) is not int or not 0 <= card_index < record["card_count"]:
        raise ValueError("Invalid card index")
    result["ok"] = True
    result["format"] = "wmlc" if result["mime"] == "application/vnd.wap.wmlc" else "wml"
    result["card_count"] = record["card_count"]
    result["active_card_index"] = card_index
    cards = record["cards"]
    result["cards"] = [
        {"index": i, "id": card["id"], "preview": card["text"][:160]}
        for i, card in enumerate(cards)
    ]
    result["text"] = cards[card_index]["text"]
    result["text_available"] = True
    result["form_preview"] = cards[card_index].get("form_preview")
    result["form_submission_supported"] = False
    ids = {card["id"]: i for i, card in enumerate(cards)
           if isinstance(card["id"], str) and card["id"]}
    for link in cards[card_index]["links"]:
        href = link.get("href")
        if (link.get("method") == "GET" and isinstance(href, str)
                and CARD_REF.fullmatch(href) and href[1:] in ids):
            if len(result["card_links"]) < MAX_LINKS:
                result["card_links"].append({
                    "index": len(result["card_links"]),
                    "id": href[1:], "target_index": ids[href[1:]],
                })
            continue
        if is_wsp:
            # Offline imported WSP evidence cannot initiate any follow-up GET.
            continue
        url, reason = evaluate_link(metadata["url"], link)
        if url is not None and len(result["links"]) < MAX_LINKS:
            result["links"].append({
                "index": len(result["links"]), "url": url,
                "method": "GET", "card_id": cards[card_index]["id"],
            })
    for action in ([] if is_wsp else cards[card_index].get("do_navigation", [])):
        target, reason = evaluate_link(metadata["url"], action)
        if target is not None and len(result["do_links"]) < 16:
            result["do_links"].append({
                "index": len(result["do_links"]), "url": target,
                "source": "do_go", "explicit_execute_required": True,
                "method": "GET", "submitted_fields": 0,
            })
    return result


def _session_path(root: Path) -> Path:
    return root / "session.json"


def _load_session(root: Path) -> dict:
    state = json.loads(_session_path(root).read_text(encoding="utf-8"))
    if (state.get("schema") != "wap-agent-browser-v1"
            or not isinstance(state.get("pages"), list)
            or not 1 <= len(state["pages"]) <= MAX_PAGES
            or type(state.get("cursor")) is not int
            or not 0 <= state["cursor"] < len(state["pages"])
            or state.get("profile") not in PROFILES
            or state.get("transport") not in (None, "wsp-offline")
            or (state.get("transport") == "wsp-offline" and (
                len(state["pages"]) != 1 or state["cursor"] != 0
                or state.get("profile") != "wmlc"))):
        raise ValueError("Invalid browser session")
    positions = state.setdefault("card_positions", [0] * len(state["pages"]))
    history = state.setdefault("card_history", [])
    if (not isinstance(positions, list) or len(positions) != len(state["pages"])
            or any(type(n) is not int or not 0 <= n < MAX_CARDS for n in positions)
            or not isinstance(history, list) or len(history) > MAX_HISTORY
            or any(not isinstance(x, list) or len(x) != 2
                   or type(x[0]) is not int or type(x[1]) is not int
                   or not 0 <= x[0] < len(state["pages"])
                   or not 0 <= x[1] < MAX_CARDS for x in history)):
        raise ValueError("Invalid card navigation state")
    return state


def _current_page(root: Path, state: dict) -> Path:
    name = state["pages"][state["cursor"]]
    if not isinstance(name, str) or not re.fullmatch(r"page-[0-9]{4}", name):
        raise ValueError("Invalid page reference")
    return root / "pages" / name


def _view(root: Path, state: dict) -> dict:
    return {"session": str(root), "cursor": state["cursor"],
            "page_count": len(state["pages"]),
            **page_view(_current_page(root, state),
                        card_index=state["card_positions"][state["cursor"]])}


def _remember(state: dict) -> None:
    history = state["card_history"]
    history.append([state["cursor"], state["card_positions"][state["cursor"]]])
    if len(history) > MAX_HISTORY:
        del history[0]


def _append_page(root: Path, state: dict, page_dir: Path) -> dict:
    if state["pages"]:
        _remember(state)
    state["pages"].append(page_dir.name)
    state["card_positions"].append(0)
    state["cursor"] = len(state["pages"]) - 1
    _session_path(root).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return _view(root, state)


def _capture_page(url: str, profile: str, folder: Path) -> dict:
    metadata = capture(url, profile, folder)
    if metadata["classification"] in VALID_STATUSES:
        with frozen_r5() as probe:
            export = parse_capture(folder, probe_dir=probe)
        (folder / "r5_export.json").write_text(
            json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def open_page(url: str, root: Path, profile: str = "wap1", *, capture_page=_capture_page) -> dict:
    validate_url(url)
    if profile not in PROFILES:
        raise ValueError("Unknown profile")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    (root / "pages").mkdir()
    page = root / "pages" / "page-0001"
    capture_page(url, profile, page)
    state = {"schema": "wap-agent-browser-v1", "profile": profile,
             "pages": [], "cursor": 0, "card_positions": [],
             "card_history": []}
    return _append_page(root, state, page)


def follow_link(root: Path, index: int, *, capture_page=_capture_page) -> dict:
    """Fetch exactly one safe same-origin GET selected from parsed R5 links."""
    root = Path(root)
    state = _load_session(root)
    if state.get("transport") == "wsp-offline":
        raise ValueError("Imported WSP evidence cannot follow network links")
    if len(state["pages"]) >= MAX_PAGES:
        raise ValueError("Session page limit reached")
    current = _view(root, state)
    if not current["ok"]:
        raise ValueError("Current page is not parsed WML")
    if type(index) is not int or not 0 <= index < len(current["links"]):
        raise ValueError("Invalid link index")
    target = current["links"][index]["url"]
    checked, status = evaluate_link(current["url"], {"href": target, "method": "GET"})
    if status != "OK" or checked != target:
        raise ValueError("Unsafe navigation target")
    page = root / "pages" / f"page-{len(state['pages'])+1:04d}"
    capture_page(target, state["profile"], page)
    return _append_page(root, state, page)


def follow_do(root: Path, index: int, *, capture_page=_capture_page) -> dict:
    """Explicitly follow one verified no-input <do><go> GET, never a form."""
    root = Path(root)
    state = _load_session(root)
    if state.get("transport") == "wsp-offline":
        raise ValueError("Imported WSP evidence cannot follow network links")
    if len(state["pages"]) >= MAX_PAGES:
        raise ValueError("Session page limit reached")
    current = _view(root, state)
    if not current["ok"]:
        raise ValueError("Current page is not verified WML")
    if type(index) is not int or not 0 <= index < len(current["do_links"]):
        raise ValueError("Invalid do/go index")
    link = current["do_links"][index]
    target = link["url"]
    checked, reason = evaluate_link(current["url"], {"href": target, "method": "GET"})
    if reason != "OK" or checked != target:
        raise ValueError("Unsafe do/go navigation target")
    page = root / "pages" / f"page-{len(state['pages'])+1:04d}"
    capture_page(target, state["profile"], page)
    return _append_page(root, state, page)


def read_page(root: Path) -> dict:
    root = Path(root)
    return _view(root, _load_session(root))


def select_card(root: Path, index: int) -> dict:
    """View any card from the verified local deck without making a GET."""
    root = Path(root)
    state = _load_session(root)
    current = _view(root, state)
    if not current["ok"]:
        raise ValueError("Current page is not parsed WML")
    if type(index) is not int or not 0 <= index < current["card_count"]:
        raise ValueError("Invalid card index")
    if index == state["card_positions"][state["cursor"]]:
        return current
    _remember(state)
    state["card_positions"][state["cursor"]] = index
    _session_path(root).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return _view(root, state)


def go_back(root: Path) -> dict:
    root = Path(root)
    state = _load_session(root)
    if state["card_history"]:
        page_index, card_index = state["card_history"].pop()
        state["cursor"] = page_index
        state["card_positions"][page_index] = card_index
    elif state["cursor"] > 0:  # Backward compatibility with old sessions.
        state["cursor"] -= 1
    else:
        raise ValueError("No previous page or card")
    _session_path(root).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return _view(root, state)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Opt-in rootless JSON WML reader for Agents")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("open", help="One public HTTP(S) GET into a new session")
    p.add_argument("url")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--profile", choices=tuple(PROFILES), default="wap1")
    p.add_argument("--execute", action="store_true", help="Required to fetch")
    p = sub.add_parser("import-wsp", help="Offline import of verified lab WSP evidence")
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("follow", help="Follow one same-origin public GET link")
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--link", type=int, required=True)
    p.add_argument("--execute", action="store_true", help="Required to fetch")
    p = sub.add_parser("card", help="Select a card in the current deck offline")
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--index", type=int, required=True)
    p = sub.add_parser("form-plan", help="Safely preview one GET form request offline")
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--action", type=int, required=True)
    p.add_argument("--values-file", type=Path, required=True,
                   help="Local JSON object of non-secret form values")
    p = sub.add_parser("go", help="Opt-in one no-input WML do/go GET")
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--index", type=int, required=True)
    p.add_argument("--execute", action="store_true", help="Required for network GET")
    for command in ("read", "back"):
        sub.add_parser(command).add_argument("--session", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("open", "follow", "go") and not args.execute:
            raise ValueError("Network opt-in required: --execute")
        if args.command == "open":
            result = open_page(args.url, args.out, args.profile)
        elif args.command == "import-wsp":
            from wap_probe.wsp_evidence import import_record
            result = import_record(args.evidence, args.out)
        elif args.command == "follow":
            result = follow_link(args.session, args.link)
        elif args.command == "go":
            result = follow_do(args.session, args.index)
        elif args.command == "read":
            result = read_page(args.session)
        elif args.command == "card":
            result = select_card(args.session, args.index)
        elif args.command == "form-plan":
            from wap_probe.form_plan import plan_current
            supplied = json.loads(args.values_file.read_text(encoding="utf-8"))
            result = plan_current(args.session, args.action, supplied)
        else:
            result = go_back(args.session)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0 if result["ok"] else 1
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, **safe_error(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
