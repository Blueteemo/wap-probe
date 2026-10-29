"""Opt-in, direct-origin HTTP capture for WAP Probe R6.

No network activity on import or without --execute. No redirects, proxies,
credentials, cookies, POST, insecure TLS, or privileged ports. Every network
request pins a public DNS answer in curl. Capture ≠ A-level verification.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

MAX_BODY_BYTES = 1_048_576
MAX_URL_LEN = 2048
LABEL_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
SENSITIVE_KEYS = {"token", "sid", "session", "sessionid", "session_id", "auth",
                  "authorization", "api_key", "password", "passwd", "pwd",
                  "secret", "csrf", "cookie"}
CANDIDATES = (
    "http://tx.com.cn/",
    "http://qq.ip138.com/train/search_train.wml",
    "http://wap.yuyangzhou.name/",
    "http://wap.ee1234.com/",
    "http://wap.517ming.com/",
    "http://wap.shufaji.com/",
    "http://wap.uc123.com/",
    "http://www.cctv.com/wap/index.wml",
)
PROFILES = {
    "wap1": {
        "User-Agent": "Nokia7110/1.0 (04.88)",
        "Accept": "text/vnd.wap.wml,application/vnd.wap.wmlc;q=0.9,*/*;q=0.1",
    },
    "wmlc": {
        "User-Agent": "Nokia7110/1.0 (04.88)",
        "Accept": ("application/vnd.wap.wmlc,"
                   "text/vnd.wap.wml;q=0.7,*/*;q=0.1"),
    },
    "s60": {
        "User-Agent": ("NokiaE63-1/100.21.110 (SymbianOS/9.2; U; Series60/3.1; "
                       "Profile/MIDP-2.0 Configuration/CLDC-1.1)"),
        "Accept": ("application/vnd.wap.xhtml+xml,application/xhtml+xml;q=0.9,"
                   "text/html;q=0.8,text/vnd.wap.wml;q=0.6,*/*;q=0.1"),
    },
}
COMMON_HEADERS = (
    "Accept-Language: zh-cn,zh;q=0.9,en;q=0.5",
    "Accept-Encoding: identity",
)


def _unsafe(value: str) -> bool:
    """Fail closed on control characters, escaped controls and WML variables."""
    for _ in range(5):
        if any(ord(c) <= 32 or ord(c) == 127 for c in value):
            return True
        if "\\" in value or "$(" in value:
            return True
        value = unquote(value)
    return False


def validate_url(url: str) -> tuple[str, str, int]:
    if not isinstance(url, str) or not url or len(url) > MAX_URL_LEN or _unsafe(url):
        raise ValueError("Unsafe or oversized URL")
    p = urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Only explicit HTTP(S) DNS hostnames are supported")
    if p.username is not None or p.password is not None or p.fragment:
        raise ValueError("No credentials or fragment")
    host = p.hostname.lower()
    if len(host) > 253 or "." not in host or not all(
        LABEL_RE.fullmatch(part) for part in host.split(".")
    ):
        raise ValueError("Invalid hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP literals are forbidden")
    port = 80 if p.scheme == "http" else 443
    if p.port not in (None, port):
        raise ValueError("Only default ports allowed")
    if "{" in url or "}" in url or "#" in url:
        raise ValueError("Unsafe curl URL constructs")
    path_segments = [unquote(x).lower() for x in p.path.split("/")]
    if any(x in (".", "..") for x in path_segments):
        raise ValueError("Dot-segments are not allowed")
    for pair in p.query.split("&"):
        name = unquote(pair.split("=", 1)[0]).lower()
        if name in SENSITIVE_KEYS:
            raise ValueError("Sensitive query parameter")
    return p.scheme, host, port


def public_dns(host: str, *, resolver=socket.getaddrinfo) -> list[str]:
    records = resolver(host, None, type=socket.SOCK_STREAM)
    values = sorted({
        str(ipaddress.ip_address(item[4][0].split("%")[0]))
        for item in records
    }, key=lambda item: (":" in item, item))
    if not values or not all(ipaddress.ip_address(value).is_global for value in values):
        raise ValueError("DNS returned non-global or no addresses")
    return values


def anonymous_jsessionid(raw_headers: bytes) -> str:
    """Extract one host-only anonymous JSESSIONID from the home response.

    Strictly limited to a 32-hex session ID. No other cookie is consumed.
    """
    if not isinstance(raw_headers, bytes) or len(raw_headers) > 65536:
        raise ValueError("Invalid home response headers")
    candidates = []
    for line in raw_headers.splitlines():
        if not line.lower().startswith(b"set-cookie:"):
            continue
        fields = line.split(b":", 1)[1].strip().split(b";")
        name, sep, value = fields[0].strip().partition(b"=")
        if name.strip().lower() != b"jsessionid":
            continue
        if not sep or not re.fullmatch(rb"[A-Fa-f0-9]{32}", value):
            raise ValueError("Malformed anonymous JSESSIONID")
        attributes = {
            item.strip().partition(b"=")[0].lower() for item in fields[1:]
        }
        if b"domain" in attributes:
            raise ValueError("JSESSIONID must be host-only")
        candidates.append(value.decode("ascii"))
    if len(candidates) != 1:
        raise ValueError("Missing or ambiguous anonymous JSESSIONID")
    return candidates[0]


def _secure_cookie_file(folder: Path, session: str) -> Path:
    if not re.fullmatch(r"[A-Fa-f0-9]{32}", session):
        raise ValueError("Invalid anonymous session token")
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="ascii", prefix=".anon_session_",
        suffix=".cookie", dir=folder, delete=False
    ) as handle:
        handle.write("# Netscape HTTP Cookie File\n")
        handle.write(
            "tx.com.cn\tFALSE\t/\tTRUE\t0\tJSESSIONID\t" + session + "\n"
        )
        return Path(handle.name)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_command(url: str, hostname: str, port: int, ip: str,
                  profile: str, folder: Path, *, cookie_file=None) -> list[str]:
    if profile not in PROFILES:
        raise ValueError("Unknown device profile")
    pinned = f"[{ip}]" if ":" in ip else ip
    command = [
        "curl", "-q", "--silent", "--show-error",
        "--noproxy", "*", "--proxy", "",
        "--request", "GET", "--http1.1",
        "--proto", "=http,https",
        "--max-redirs", "0", "--connect-timeout", "8",
        "--max-time", "20", "--max-filesize", str(MAX_BODY_BYTES),
        "--resolve", f"{hostname}:{port}:{pinned}",
        "--dump-header", str(folder / "headers.bin"),
        "--output", str(folder / "body.bin"),
        "--write-out", "%{http_code}\\n%{url_effective}\\n%{remote_ip}\\n%{content_type}\\n",
    ]
    if cookie_file is not None:
        command += ["--cookie", str(cookie_file)]
    for key, value in PROFILES[profile].items():
        command += ["--header", f"{key}: {value}"]
    for line in COMMON_HEADERS:
        command += ["--header", line]
    command += ["--", url]
    return command


def capture(url: str, profile: str, folder: Path, *,
            resolver=socket.getaddrinfo, runner=subprocess.run,
            session_cookie=None) -> dict:
    """Create a self-contained evidence folder, even on network failure.

    Subprocess and resolver can be injected for fully offline regression tests.
    """
    if profile not in PROFILES:
        raise ValueError("Unknown device profile")
    scheme, host, port = validate_url(url)
    if session_cookie is not None:
        if scheme != "https" or host != "tx.com.cn":
            raise ValueError("Anonymous session replay requires HTTPS tx.com.cn")
        if not isinstance(session_cookie, str) or not re.fullmatch(
            r"[a-fA-F0-9]{32}", session_cookie
        ):
            raise ValueError("Invalid anonymous session")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    header_path, body_path = folder / "headers.bin", folder / "body.bin"
    header_path.write_bytes(b"")
    body_path.write_bytes(b"")
    (folder / "stderr.txt").write_text("", encoding="utf-8")
    (folder / "curl_writeout.txt").write_text("", encoding="utf-8")
    metadata = {
        "schema": "wap-probe-r6-capture-v1", "url": url, "profile": profile,
        "scheme": scheme, "started_utc": utc(), "finished_utc": None,
        "dns_answers": [], "pinned_ip": None, "remote_ip": None,
        "curl_exit_code": -1, "http_status": 0, "final_url": url,
        "content_type": "", "body_bytes": 0,
        "body_sha256": sha256(b""), "headers_sha256": sha256(b""),
        "classification": "NOT_STARTED",
        "A_origin": "PENDING", "A_navigation": "PENDING",
        "anonymous_cookie_sent": ["JSESSIONID"] if session_cookie else [],
    }
    cookie_file = None
    try:
        answers = public_dns(host, resolver=resolver)
        pinned = answers[0]
        metadata["dns_answers"] = answers
        metadata["pinned_ip"] = pinned
        if shutil.which("curl") is None and runner is subprocess.run:
            raise RuntimeError("curl executable not installed")
        if session_cookie is not None:
            cookie_file = _secure_cookie_file(folder, session_cookie)
        command = build_command(
            url, host, port, pinned, profile, folder, cookie_file=cookie_file
        )
        completed = runner(command, capture_output=True, check=False, timeout=25)
        metadata["curl_exit_code"] = int(completed.returncode)
        (folder / "stderr.txt").write_bytes(completed.stderr[:16_384])
        (folder / "curl_writeout.txt").write_bytes(completed.stdout[:16_384])
        fields = completed.stdout.decode("utf-8", "replace").splitlines()
        if len(fields) >= 4:
            try:
                metadata["http_status"] = int(fields[0])
            except ValueError:
                pass
            metadata["final_url"] = fields[1]
            metadata["remote_ip"] = fields[2]
            metadata["content_type"] = fields[3]
        metadata["classification"] = "CAPTURE_FAILED"
        if completed.returncode == 0:
            from wap_probe.evidence_gate import verify
            raw_headers = header_path.read_bytes()
            body = body_path.read_bytes()
            # The persisted hashes/count below must be computed first.
            metadata["body_bytes"] = len(body)
            metadata["body_sha256"] = sha256(body)
            metadata["headers_sha256"] = sha256(raw_headers)
            metadata["classification"] = verify(metadata, raw_headers, body)["status"]
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        (folder / "stderr.txt").write_text(
            str(exc)[:4096] + "\n", encoding="utf-8"
        )
        metadata["classification"] = "DNS_OR_SAFETY_OR_TOOL_ERROR"
    finally:
        if cookie_file is not None:
            cookie_file.unlink(missing_ok=True)
        body = body_path.read_bytes()
        headers = header_path.read_bytes()
        metadata["body_bytes"] = len(body)
        metadata["body_sha256"] = sha256(body)
        metadata["headers_sha256"] = sha256(headers)
        metadata["finished_utc"] = utc()
        (folder / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return metadata


def matrix() -> list[tuple[str, str]]:
    jobs = []
    for url in CANDIDATES:
        p = urlsplit(url)
        for scheme in ("http", "https"):
            target = p._replace(scheme=scheme).geturl()
            for profile in ("wap1", "s60"):
                jobs.append((target, profile))
    return jobs


def main(argv=None):
    parser = argparse.ArgumentParser(description="Opt-in WAP origin capture (GET only)")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--url", help="Single public HTTP(S) URL")
    target.add_argument("--matrix", action="store_true", help="32 candidate tasks")
    parser.add_argument("--profile", choices=tuple(PROFILES), default="wap1")
    parser.add_argument("--out", type=Path, default=Path("evidence/r6"))
    parser.add_argument("--execute", action="store_true", help="Explicit network opt-in")
    parser.add_argument("--limit", type=int, default=32)
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args(argv)
    if args.limit < 1 or args.limit > 32 or not 1 <= args.delay <= 3600:
        parser.error("Limit must be 1..32; delay must be 1..3600 seconds")
    jobs = matrix() if args.matrix else [(args.url, args.profile)]
    for url, profile in jobs:
        validate_url(url)
        print(f"{url} [{profile}]", file=sys.stderr)
    print(f"Planned {min(len(jobs), args.limit)} capture(s); execute={args.execute}")
    if not args.execute:
        return 0
    if args.out.exists() and any(args.out.iterdir()):
        parser.error("Output directory must be new/empty; refusing overwrite")
    args.out.mkdir(parents=True, exist_ok=True)
    results = {}
    for index, (url, profile) in enumerate(jobs[:args.limit], 1):
        if index > 1:
            time.sleep(args.delay)
        folder = args.out / f"{index:03d}_{profile}"
        r = capture(url, profile, folder)
        results[folder.name] = {
            "url": url, "profile": profile, "status": r["classification"]
        }
        print(f"[{index}/{min(len(jobs),args.limit)}] {r['classification']} - {url}")
    (args.out / "summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
