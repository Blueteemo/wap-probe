"""Offline, fail-closed verification of captured WAP HTTP evidence.

The evidence gate never makes network requests and never grants A grades.
Curl must be configured separately to use GET, pinned public DNS and no redirects.
"""
import argparse
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

MAX_BODY_BYTES = 1_048_576
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
HEADER_NAME_RE = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
STATUS_LINE_RE = re.compile(rb"HTTP/[0-9]+(?:\.[0-9]+)?[ \t]+([0-9]{3})(?:[ \t].*)?\Z")
DNS_LABEL_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


def sha256(data):
    """Return the normal SHA-256 even for zero-length input."""
    return hashlib.sha256(data).hexdigest()


def verdict(status):
    return {
        "status": status,
        "A_origin": "PENDING",
        "A_navigation": "PENDING",
    }


def _hostname(url):
    if not isinstance(url, str) or any(ord(ch) <= 32 or ord(ch) == 127 for ch in url):
        raise ValueError("Unsafe URL")
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Unsupported URL")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise ValueError("Credentials or fragment not allowed")
    default_port = 443 if parsed.scheme == "https" else 80
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Nonstandard port not allowed")
    host = parsed.hostname.lower()
    if len(host) > 253 or "." not in host or not all(
        DNS_LABEL_RE.fullmatch(label) for label in host.split(".")
    ):
        raise ValueError("Invalid DNS hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("Literal IP not allowed")
    return host


def final_response_headers(raw):
    """Decode curl -D output, allowing only interim HTTP 1xx responses."""
    if not isinstance(raw, bytes) or not raw.endswith(b"\r\n\r\n"):
        raise ValueError("Headers must have CRLF terminator")
    blocks = raw[:-4].split(b"\r\n\r\n")
    if not 1 <= len(blocks) <= 6:
        raise ValueError("Unexpected number of header blocks")
    responses = []
    for block in blocks:
        lines = block.split(b"\r\n")
        match = STATUS_LINE_RE.fullmatch(lines[0])
        if not match:
            raise ValueError("Invalid HTTP status line")
        status = int(match.group(1))
        fields = {}
        for line in lines[1:]:
            if line.startswith((b" ", b"\t")):
                raise ValueError("Obsolete folded header")
            if b":" not in line:
                raise ValueError("Malformed header")
            name, value = line.split(b":", 1)
            if not HEADER_NAME_RE.fullmatch(name):
                raise ValueError("Unsafe header name")
            if any(ch < 32 and ch != 9 or ch == 127 for ch in value):
                raise ValueError("Control character in header value")
            key = name.decode("ascii").lower()
            fields.setdefault(key, []).append(value.strip().decode("latin-1"))
        responses.append((status, fields))
    for status, _ in responses[:-1]:
        if not 100 <= status < 200 or status == 101:
            raise ValueError("Only interim responses may precede final response")
    status, fields = responses[-1]
    if status < 200:
        raise ValueError("No final response")
    return status, fields


def _single_header(headers, name):
    values = headers.get(name, [])
    if len(values) > 1:
        raise ValueError("Duplicate " + name)
    return values[0] if values else ""


def _mime(value):
    if not isinstance(value, str):
        raise ValueError("Content-Type is not a string")
    return value.split(";", 1)[0].strip().lower()


def verify(meta, raw_headers, body):
    """Validate captured bytes against metadata; never infer R5 parsing success."""
    if not isinstance(meta, dict) or not isinstance(raw_headers, bytes) or not isinstance(body, bytes):
        return verdict("INVALID_EVIDENCE")
    if type(meta.get("curl_exit_code")) is not int:
        return verdict("INVALID_EVIDENCE")
    if meta["curl_exit_code"] != 0:
        return verdict("CAPTURE_FAILED")
    try:
        if not raw_headers or len(body) > MAX_BODY_BYTES:
            raise ValueError("Missing headers or oversized body")
        if type(meta["body_bytes"]) is not int or meta["body_bytes"] != len(body):
            raise ValueError("Body byte count mismatch")
        for key, data in (("body_sha256", body), ("headers_sha256", raw_headers)):
            actual = meta[key]
            if not isinstance(actual, str) or not SHA256_RE.fullmatch(actual):
                raise ValueError("Invalid SHA-256 format")
            if actual != sha256(data):
                raise ValueError("SHA-256 mismatch")
        _hostname(meta["url"])
        if meta["url"] != meta["final_url"]:
            raise ValueError("Unexpected redirect")
        dns_values = meta["dns_answers"]
        if not isinstance(dns_values, list) or not dns_values:
            raise ValueError("Missing DNS evidence")
        dns = [ipaddress.ip_address(value) for value in dns_values]
        pinned = ipaddress.ip_address(meta["pinned_ip"])
        remote = ipaddress.ip_address(meta["remote_ip"])
        if not all(ip.is_global for ip in dns + [pinned, remote]):
            raise ValueError("Nonpublic IP")
        if pinned != remote or pinned not in dns:
            raise ValueError("Pinned IP mismatch")
        status, headers = final_response_headers(raw_headers)
        if type(meta["http_status"]) is not int or status != meta["http_status"]:
            raise ValueError("Status mismatch")
        actual_type = _single_header(headers, "content-type")
        mime = _mime(actual_type)
        if mime != _mime(meta["content_type"]):
            raise ValueError("MIME mismatch")
        length = _single_header(headers, "content-length")
        transfer = _single_header(headers, "transfer-encoding")
        encoding = _single_header(headers, "content-encoding")
        if length and transfer:
            raise ValueError("Conflicting HTTP framing")
        if transfer and transfer.lower().strip() != "chunked":
            raise ValueError("Unsupported Transfer-Encoding")
        if length:
            if not re.fullmatch(r"[0-9]+", length.strip()):
                raise ValueError("Malformed Content-Length")
            if int(length) != len(body):
                raise ValueError("Content-Length mismatch")
    except (KeyError, TypeError, ValueError, IndexError, UnicodeError):
        return verdict("INVALID_EVIDENCE")
    if 300 <= status < 400:
        return verdict("REDIRECT")
    if status != 200:
        return verdict("HTTP_NON_200")
    if not body:
        return verdict("EMPTY_BODY")
    if "content-range" in headers:
        return verdict("PARTIAL_BODY")
    if encoding and encoding.lower().strip() != "identity":
        return verdict("ENCODED_BODY")
    if mime == "text/vnd.wap.wml":
        return verdict("WML_CAPTURED_NEEDS_R5")
    if mime == "application/vnd.wap.wmlc":
        return verdict("WMLC_CAPTURED_NEEDS_R5")
    if "html" in mime:
        return verdict("HTML")
    return verdict("OTHER")


def verify_folder(folder):
    folder = Path(folder)
    try:
        meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        headers = (folder / "headers.bin").read_bytes()
        body = (folder / "body.bin").read_bytes()
        return verify(meta, headers, body)
    except (OSError, ValueError, TypeError, UnicodeError):
        return verdict("MISSING_OR_INVALID_FILES")


def main():
    parser = argparse.ArgumentParser(description="Offline R6 HTTP evidence gate")
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    if not args.evidence_dir.is_dir():
        parser.error("Evidence directory not found")
    report = {
        folder.name: verify_folder(folder)
        for folder in sorted(args.evidence_dir.iterdir())
        if folder.is_dir()
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
