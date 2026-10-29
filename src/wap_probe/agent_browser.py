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


def page_view(page_dir: Path) -> dict:
    """Recheck recorded evidence and return bounded text/safe links."""
    page_dir = Path(page_dir)
    evidence = verify_folder(page_dir)
    metadata = json.loads((page_dir / "metadata.json").read_text(encoding="utf-8"))
    result = {
        "url": metadata["url"], "http_status": metadata["http_status"],
        "mime": metadata["content_type"].split(";", 1)[0].strip().lower(),
        "bytes": metadata["body_bytes"], "sha256": metadata["body_sha256"],
        "capture_status": evidence["status"], "ok": False,
        "text": None, "links": [],
    }
    if evidence["status"] not in VALID_STATUSES:
        return result
    record = read_r5_export(page_dir / "r5_export.json", page_dir)
    result["ok"] = True
    result["format"] = "wmlc" if result["mime"] == "application/vnd.wap.wmlc" else "wml"
    if result["format"] == "wml":
        result["text"] = _safe_xml_text((page_dir / "body.bin").read_bytes(),
                                        metadata["content_type"])
    else:
        # R5 already decoded the original WBXML; its export is bound to the
        # exact raw SHA-256, and the same export is validated above.
        result["text"] = "\n".join(
            card["text"] for card in record["cards"] if card["text"]
        )[:MAX_TEXT]
    result["text_available"] = result["text"] is not None
    result["card_count"] = record["card_count"]
    for card in record["cards"]:
        for link in card["links"]:
            if len(result["links"]) >= MAX_LINKS:
                break
            url, reason = evaluate_link(metadata["url"], link)
            if url is not None:
                result["links"].append({
                    "index": len(result["links"]), "url": url,
                    "method": "GET", "card_id": card.get("id"),
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
            or state.get("profile") not in PROFILES):
        raise ValueError("Invalid browser session")
    return state


def _current_page(root: Path, state: dict) -> Path:
    name = state["pages"][state["cursor"]]
    if not isinstance(name, str) or not re.fullmatch(r"page-[0-9]{4}", name):
        raise ValueError("Invalid page reference")
    return root / "pages" / name


def _append_page(root: Path, state: dict, page_dir: Path) -> dict:
    state["pages"].append(page_dir.name)
    state["cursor"] = len(state["pages"]) - 1
    _session_path(root).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return {"session": str(root), "cursor": state["cursor"],
            "page_count": len(state["pages"]), **page_view(page_dir)}


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
             "pages": [], "cursor": 0}
    return _append_page(root, state, page)


def follow_link(root: Path, index: int, *, capture_page=_capture_page) -> dict:
    """Fetch exactly one safe same-origin GET selected from parsed R5 links."""
    root = Path(root)
    state = _load_session(root)
    if len(state["pages"]) >= MAX_PAGES:
        raise ValueError("Session page limit reached")
    current = page_view(_current_page(root, state))
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


def read_page(root: Path) -> dict:
    root = Path(root)
    state = _load_session(root)
    return {"session": str(root), "cursor": state["cursor"],
            "page_count": len(state["pages"]), **page_view(_current_page(root, state))}


def go_back(root: Path) -> dict:
    root = Path(root)
    state = _load_session(root)
    if state["cursor"] == 0:
        raise ValueError("No previous page")
    state["cursor"] -= 1
    _session_path(root).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return read_page(root)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Opt-in rootless JSON WML reader for Agents")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("open", help="One public HTTP(S) GET into a new session")
    p.add_argument("url")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--profile", choices=tuple(PROFILES), default="wap1")
    p.add_argument("--execute", action="store_true", help="Required to fetch")
    p = sub.add_parser("follow", help="Follow one same-origin public GET link")
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--link", type=int, required=True)
    p.add_argument("--execute", action="store_true", help="Required to fetch")
    for command in ("read", "back"):
        sub.add_parser(command).add_argument("--session", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("open", "follow") and not args.execute:
            raise ValueError("Network opt-in required: --execute")
        if args.command == "open":
            result = open_page(args.url, args.out, args.profile)
        elif args.command == "follow":
            result = follow_link(args.session, args.link)
        elif args.command == "read":
            result = read_page(args.session)
        else:
            result = go_back(args.session)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0 if result["ok"] else 1
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__,
                          "message": str(exc)[:200]}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
