"""Separate, hash-bound WSP lab record and offline-only Agent importer.

Never creates fake HTTP/curl evidence. The manifest is an integrity assertion
about saved bytes, NOT cryptographic proof of the external gateway's identity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from wap_probe.wsp_readonly import (
    LAB_GATEWAY, LAB_RESOURCE, MAX_PDU, WspProtocolError,
    decode_reply, encode_get,
)

SCHEMA = "wap-probe-wsp-lab-evidence-v1"
SESSION_SCHEMA = "wap-agent-browser-v1"
HEX = re.compile(r"[a-f0-9]{64}\Z")
MAX_JSON = 4096


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_limited(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Unsafe or oversized WSP evidence file")
    data = path.read_bytes()
    if not data or len(data) > limit:
        raise ValueError("Missing or oversized WSP evidence file")
    return data


def write_record(folder: Path, request: bytes, response: bytes) -> None:
    """Write only a valid, allowlisted, single-GET response; never overwrite."""
    validate_packets(request, response)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": SCHEMA,
        "gateway": f"{LAB_GATEWAY[0]}:{LAB_GATEWAY[1]}",
        "resource": LAB_RESOURCE,
        "request_sha256": _sha(request),
        "reply_sha256": _sha(response),
        "request_bytes": len(request),
        "reply_bytes": len(response),
        "transport": "connectionless-wsp-over-udp",
        "authenticated": False,
    }
    (folder / "request.wsp").write_bytes(request)
    (folder / "reply.wsp").write_bytes(response)
    (folder / "wsp_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def validate_packets(request: bytes, response: bytes):
    """Return independently decoded Reply, enforcing the single lab request."""
    if (not isinstance(request, bytes) or not isinstance(response, bytes)
            or not 1 <= len(request) <= MAX_PDU
            or not 1 <= len(response) <= MAX_PDU):
        raise ValueError("Invalid WSP datagram lengths")
    if request != encode_get(LAB_RESOURCE, request[0]):
        raise ValueError("WSP request not the allowlisted exact GET")
    parsed = decode_reply(response, request[0])
    if (parsed.status != 200 or parsed.content_type not in (
            "text/vnd.wap.wml", "application/vnd.wap.wmlc")
            or not parsed.body or len(parsed.body) > MAX_PDU):
        raise ValueError("WSP reply is not a successful WML deck")
    return parsed


def verify_record(folder: Path):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("WSP evidence directory invalid")
    raw = _read_limited(folder / "wsp_manifest.json", MAX_JSON)
    manifest = json.loads(raw.decode("utf-8"))
    if not isinstance(manifest, dict) or (
        set(manifest) != {"schema", "gateway", "resource", "request_sha256",
                         "reply_sha256", "request_bytes", "reply_bytes",
                         "transport", "authenticated"}
    ):
        raise ValueError("Invalid WSP evidence manifest")
    if (manifest["schema"] != SCHEMA
            or manifest["gateway"] != f"{LAB_GATEWAY[0]}:{LAB_GATEWAY[1]}"
            or manifest["resource"] != LAB_RESOURCE
            or manifest["transport"] != "connectionless-wsp-over-udp"
            or manifest["authenticated"] is not False):
        raise ValueError("Untrusted WSP source metadata")
    request = _read_limited(folder / "request.wsp", MAX_PDU)
    response = _read_limited(folder / "reply.wsp", MAX_PDU)
    for name, packet in (("request", request), ("reply", response)):
        declared = manifest[name + "_sha256"]
        length = manifest[name + "_bytes"]
        if (not isinstance(declared, str) or not HEX.fullmatch(declared)
                or type(length) is not int or length != len(packet)
                or declared != _sha(packet)):
            raise ValueError("WSP evidence checksum or length mismatch")
    return validate_packets(request, response)


def verify_imported_page(page: Path):
    """Revalidate source PDU bytes and derived body every time a card is read."""
    parsed = verify_record(page)
    entity = _read_limited(Path(page) / "body.bin", MAX_PDU)
    if entity != parsed.body:
        raise ValueError("Imported WSP source body mismatch")
    return parsed


def import_record(folder: Path, destination: Path) -> dict:
    """Create an offline Agent session from verified WSP evidence; zero network."""
    parsed = verify_record(folder)
    from wap_probe.agent_browser import frozen_r5, read_page
    from wap_probe.r5_adapter import parse_r5

    mime = parsed.content_type + (
        "; charset=" + parsed.charset if parsed.charset else "")
    with frozen_r5() as probe:
        export = parse_r5(parsed.body, mime, probe_dir=probe)

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    pages = destination / "pages"
    pages.mkdir()
    page = pages / "page-0001"
    page.mkdir()
    for name in ("request.wsp", "reply.wsp", "wsp_manifest.json"):
        (page / name).write_bytes((Path(folder) / name).read_bytes())
    (page / "body.bin").write_bytes(parsed.body)
    (page / "r5_export.json").write_text(
        json.dumps(export, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    state = {
        "schema": SESSION_SCHEMA, "profile": "wmlc",
        "transport": "wsp-offline", "pages": ["page-0001"],
        "cursor": 0, "card_positions": [0], "card_history": [],
    }
    (destination / "session.json").write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return read_page(destination)
