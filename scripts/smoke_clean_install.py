"""Zero-public-network smoke check for a clean editable install (Python 3.10+).

Must be launched using the *installed* virtual environment's Python and PATH.
All page content is synthetic or read from the pinned local frozen R5 archive;
this is NOT a substitute for prior separately documented public-site runs.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import wap_probe
from wap_probe.agent_browser import ARCHIVE_NAME, ARCHIVE_SHA256, frozen_r5
from wap_probe.r5_adapter import parse_r5
from wap_probe.wsp_evidence import write_record
from wap_probe.wsp_readonly import LAB_RESOURCE, encode_get

REPO = Path(__file__).resolve().parents[1]


def call(tool, *args, input=None):
    executable = shutil.which(tool)
    assert executable, f"{tool} is not installed in PATH"
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [executable, *args], input=input, text=True, capture_output=True,
        timeout=20, env=env,
    )
    assert proc.returncode == 0, (
        f"{tool} failed with return code {proc.returncode}; "
        "check the command and its local prerequisites"
    )
    return proc.stdout


def json_call(tool, *args):
    return json.loads(call(tool, *args))


def http_fixture(folder: Path):
    """Produce explicitly synthetic HTTP evidence without any external GET."""
    body = (b'<wml><card id="home"><p>Offline smoke'
            b' <a href="#next">Card 2</a></p></card>'
            b'<card id="next"><p>Second local card</p></card></wml>')
    url = "http://wap.example.org/"
    headers = (
        b"HTTP/1.1 200 OK\r\nContent-Type: text/vnd.wap.wml\r\n"
        + b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n"
    )
    page = folder / "pages" / "page-0001"
    page.mkdir(parents=True)
    page.joinpath("body.bin").write_bytes(body)
    page.joinpath("headers.bin").write_bytes(headers)
    meta = {
        "url": url, "final_url": url, "profile": "wap1",
        "curl_exit_code": 0, "http_status": 200, "content_type": "text/vnd.wap.wml",
        "body_bytes": len(body), "body_sha256": hashlib.sha256(body).hexdigest(),
        "headers_sha256": hashlib.sha256(headers).hexdigest(),
        "dns_answers": ["8.8.8.8"], "pinned_ip": "8.8.8.8",
        "remote_ip": "8.8.8.8",
    }
    page.joinpath("metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    with frozen_r5() as probe:
        parsed = parse_r5(body, "text/vnd.wap.wml", probe_dir=probe)
    page.joinpath("r5_export.json").write_text(json.dumps(parsed), encoding="utf-8")
    state = {
        "schema": "wap-agent-browser-v1", "profile": "wap1",
        "pages": ["page-0001"], "cursor": 0,
        "card_positions": [0], "card_history": [],
    }
    folder.joinpath("session.json").write_text(json.dumps(state), encoding="utf-8")


def main():
    assert sys.version_info >= (3, 10)
    assert wap_probe.__version__ == "1.0.0"
    assert Path(wap_probe.__file__).resolve().is_relative_to(REPO)
    assert not os.environ.get("PYTHONPATH"), "run with no PYTHONPATH override"
    archive = REPO / "vendor" / "r5" / ARCHIVE_NAME
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA256
    for cmd in ("wap-agent", "wap-mcp", "wap-wsp-lab"):
        assert "usage:" in call(cmd, "--help").lower()

    with tempfile.TemporaryDirectory(prefix="wap-probe-clean-install-") as temp:
        root = Path(temp)
        http = root / "synthetic-http-session"
        http_fixture(http)
        first = json_call("wap-agent", "read", "--session", str(http))
        assert first["ok"] and first["format"] == "wml"
        assert first["card_count"] == 2 and "Offline smoke" in first["text"]
        second = json_call("wap-agent", "card", "--session", str(http), "--index", "1")
        assert "Second local card" in second["text"]
        assert json_call("wap-agent", "back", "--session", str(http))["active_card_index"] == 0

        with zipfile.ZipFile(archive) as z:
            fixture = next(name for name in z.namelist()
                           if name.endswith("/fixtures/binary_portal.wmlc"))
            wmlc = z.read(fixture)
        wire = encode_get(LAB_RESOURCE, 42)
        reply = bytes((42, 4, 0x20, 1, 0x94)) + wmlc
        evidence = root / "synthetic-wsp-evidence"
        write_record(evidence, wire, reply)
        imported = root / "wsp-agent-session"
        read = json_call("wap-agent", "import-wsp", "--evidence", str(evidence),
                         "--out", str(imported))
        assert read["ok"] and read["transport"] == "wsp-offline"
        assert read["http_status"] is None and read["wsp_status"] == 200
        assert read["card_count"] == 2 and read["links"] == []
        card = json_call("wap-agent", "card", "--session", str(imported),
                         "--index", "1")
        assert "二进制 WAP 页面" in card["text"]
        assert json_call("wap-agent", "back", "--session", str(imported))["active_card_index"] == 0

        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-11-25"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "wap_import_wsp", "arguments": {}}},
        ]
        output = call("wap-mcp", "--wsp-evidence", str(evidence),
                      input="".join(json.dumps(req) + "\n" for req in requests))
        responses = [json.loads(line) for line in output.splitlines()]
        assert [entry["id"] for entry in responses] == [1, 2, 3]
        assert responses[0]["result"]["serverInfo"]["version"] == "1.0.0"
        names = {t["name"] for t in responses[1]["result"]["tools"]}
        assert len(names) == 8 and "wap_import_wsp" in names
        mcp_view = responses[2]["result"]["structuredContent"]
        assert mcp_view["ok"] and mcp_view["card_count"] == 2
        assert mcp_view["links"] == [] and mcp_view["transport"] == "wsp-offline"
        assert str(root) not in output and "request.wsp" not in output
    print(f"CLEAN_EDITABLE_INSTALL_OK python={sys.version_info.major}.{sys.version_info.minor} "
          "cli=http,wsp mcp=wsp-offline no_public_network=true")


if __name__ == "__main__":
    main()
