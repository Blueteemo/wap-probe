"""Experimental connectionless WSP/WDP (UDP) **read-only** lab client.

Separate from HTTP collector, MCP and normal Agent sessions. The ONLY
network destination/resource is a pinned public first-party WAP Labs test
gateway and its anonymous interop homepage, and both opt-ins are required.
No arbitrary UDP targets, authentication, POST, WMLScript, retries, redirects,
cookies, proxy discovery, or automatic card navigation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import socket
import sys
from dataclasses import dataclass

LAB_GATEWAY = ("159.89.254.0", 9200)
LAB_RESOURCE = "http://interop.wap.shrimpworks.dev/"
MAX_PDU = 8192
TIMEOUT_SECONDS = 4
MIMES = {0x08: "text/vnd.wap.wml",
         0x14: "application/vnd.wap.wmlc",
         0x03: "text/plain"}
STATUS_CLASSES = ((0x10, 0x11, 100), (0x20, 0x26, 200),
                  (0x30, 0x37, 300), (0x40, 0x51, 400),
                  (0x60, 0x65, 500))


class WspProtocolError(ValueError):
    """Unsupported, malformed, or untrusted connectionless WSP payload."""


@dataclass(frozen=True)
class WspReply:
    transaction_id: int
    status: int
    content_type: str
    body: bytes


def encode_uintvar(number: int) -> bytes:
    if type(number) is not int or not 0 <= number <= 0xFFFF_FFFF:
        raise WspProtocolError("Unsigned WSP integer out of range")
    parts = [number & 0x7F]
    number >>= 7
    while number:
        parts.insert(0, (number & 0x7F) | 0x80)
        number >>= 7
    return bytes(parts)


def decode_uintvar(data: bytes, start: int) -> tuple[int, int]:
    value = 0
    for index in range(start, min(len(data), start + 5)):
        octet = data[index]
        if value > (0xFFFF_FFFF >> 7):
            raise WspProtocolError("Overflow in WSP integer")
        value = (value << 7) | (octet & 0x7F)
        if value > 0xFFFF_FFFF:
            raise WspProtocolError("Overflow in WSP integer")
        if not octet & 0x80:
            return value, index + 1
    raise WspProtocolError("Truncated or overlong WSP integer")


def encode_get(uri: str, transaction_id: int, *, accept_wmlc: bool = True) -> bytes:
    """Pure GET PDU encoder (no transport). Fixed URI only in live_probe()."""
    if (type(transaction_id) is not int or not 0 <= transaction_id <= 255
            or not isinstance(uri, str) or not (uri.startswith("http://") or uri.startswith("/"))
            or len(uri) > 1024 or any(ord(x) < 33 or ord(x) > 126 for x in uri)
            or "@" in uri or "#" in uri or "?" in uri):
        raise WspProtocolError("Unsafe WSP GET URI or transaction id")
    raw = uri.encode("ascii")
    # 0x80 = Accept header name, 0x94 = application/vnd.wap.wmlc,
    # 0x88 = text/vnd.wap.wml; these are assigned WSP short integers.
    packet = bytes((transaction_id, 0x40)) + encode_uintvar(len(raw)) + raw
    packet += bytes((0x80, 0x94 if accept_wmlc else 0x88))
    if len(packet) > MAX_PDU:
        raise WspProtocolError("GET datagram too large")
    return packet


def decode_reply(packet: bytes, transaction_id: int) -> WspReply:
    """Decode bounded connectionless Reply with an explicit Content-Type."""
    if not isinstance(packet, bytes) or not 4 <= len(packet) <= MAX_PDU:
        raise WspProtocolError("Invalid WSP reply length")
    if type(transaction_id) is not int or not 0 <= transaction_id <= 255:
        raise WspProtocolError("Invalid expected transaction id")
    if packet[0] != transaction_id:
        raise WspProtocolError("WSP transaction ID mismatch")
    if packet[1] != 0x04:
        raise WspProtocolError("Unexpected WSP PDU (Reply required)")
    status_byte = packet[2]
    status = next((base + status_byte - lo for lo, hi, base
                   in STATUS_CLASSES if lo <= status_byte <= hi), None)
    if status is None:
        raise WspProtocolError("Unsupported WSP status")
    length, offset = decode_uintvar(packet, 3)
    if length < 1 or length > 4096 or offset + length > len(packet):
        raise WspProtocolError("Missing or truncated WSP header section")
    section = packet[offset:offset + length]
    if section[0] & 0x80:
        media = MIMES.get(section[0] & 0x7F)
        if media is None:
            raise WspProtocolError("Unsupported WSP media type")
    else:
        # Minimal text-string Content-Type. Other general WSP content-type
        # forms are deliberately unsupported until independently tested.
        end = section.find(b"\0")
        if not 1 <= end <= 80:
            raise WspProtocolError("Unsupported WSP content-type encoding")
        try:
            media = section[:end].decode("ascii").lower()
        except UnicodeError as exc:
            raise WspProtocolError("Invalid WSP content type") from exc
        if media not in MIMES.values():
            raise WspProtocolError("Unrecognized WSP content type")
    body = packet[offset + length:]
    return WspReply(transaction_id, status, media, body)


def live_probe(*, allow_network: bool, execute: bool) -> dict:
    """One bounded UDP GET to WAP Labs' documented anonymous lab resource."""
    if not (allow_network and execute):
        raise WspProtocolError("Two explicit network opt-ins required")
    tid = secrets.randbelow(256)
    wire = encode_get(LAB_RESOURCE, tid)
    # WDP over the IP bearer uses UDP; connected socket filters other peers.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(TIMEOUT_SECONDS)
        sock.connect(LAB_GATEWAY)
        sock.send(wire)
        reply, _ancillary, flags, _peer = sock.recvmsg(MAX_PDU, 0)
        if flags & getattr(socket, "MSG_TRUNC", 0):
            raise WspProtocolError("Truncated WDP datagram")
    parsed = decode_reply(reply, tid)
    if parsed.status != 200:
        raise WspProtocolError("Non-200 WSP reply; no redirects followed")
    if not parsed.body or parsed.content_type not in (
            "text/vnd.wap.wml", "application/vnd.wap.wmlc"):
        raise WspProtocolError("Not a readable WML/WMLC deck")
    from wap_probe.agent_browser import frozen_r5
    from wap_probe.r5_adapter import parse_r5
    with frozen_r5() as unpacked:
        exported = parse_r5(parsed.body, parsed.content_type, probe_dir=unpacked)
    return {
        "ok": True, "transport": "connectionless-wsp-over-udp",
        "source": "public-first-party-wap-labs-interop",
        "status": parsed.status, "mime": parsed.content_type,
        "sha256": hashlib.sha256(parsed.body).hexdigest(),
        "bytes": len(parsed.body),
        "card_count": len(exported["cards"]),
        "card_text_preview": [card["text"][:160] for card in exported["cards"][:4]],
        "no_followup": True,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Isolated read-only WSP/WDP lab probe")
    p.add_argument("--lab", action="store_true",
                   help="Only the pinned public WAP Labs interop homepage")
    p.add_argument("--allow-network", action="store_true")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args(argv)
    try:
        if not args.lab:
            raise WspProtocolError("Only --lab is implemented")
        result = live_probe(allow_network=args.allow_network, execute=args.execute)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (WspProtocolError, OSError, ValueError, TimeoutError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__},
                         ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
