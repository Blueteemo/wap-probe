"""Prepare a functional, private clean-source release candidate.

This only stages files in a new local directory. It does not establish
copyright, grant a license, publish anything, or modify frozen R5.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = "WAP_Probe_WAP_Labs_Interop_R5_20261028.zip"
ORIGINAL_SHA = "cb98d2cc060cfe775a8adf99162160c7651c306a534f3770bbb7c356034b31fa"
REDUCED = "R5_Parser_Only_Candidate.zip"
PREFIX = "wap-probe-live-discovery-r5/probe/"
PORTABLE_TESTS = (
    "test_agent_browser.py",
    "test_collector.py",
    "test_delivery_contract.py",
    "test_navigation.py",
    "test_security_regressions.py",
)
KEEP = (
    PREFIX + "wap_probe.py",
    PREFIX + "wap_wbxml.py",
    PREFIX + "fixtures/binary_portal.wmlc",
)

README = """# WAP Probe - private clean-source candidate

NOT LICENSED OR AUTHORIZED FOR PUBLIC DISTRIBUTION.
This is a technical fallback for testing independent-source installation.
The owner's copyright, third-party code references, and synthetic WMLC
fixture rights still require clearance.

This candidate excludes the original frozen R5 archive, historical website
captures, nested research ZIPs, and the original 139-case research test suite.
It includes a small, independent synthetic/local-only regression test set.
It retains the two real R5 parser modules and a synthetic WMLC smoke fixture.

Requires Python 3.10+ and curl for optional public HTTP reading.

    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .
    python scripts/smoke_clean_install.py
    python -m unittest discover -s tests -v

MCP is offline by default (wap-mcp). Use --allow-network only for approved
anonymous public HTTP GETs and execute: true on each requested network call.
No WSP UDP gateway is exposed through MCP.

此目录仅用于内部构建验证，未授予公开分发许可。历史网页响应、
研究归档与完整 R5 原始测试不包含在本候选版本中。
"""

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def build(target: Path) -> dict:
    original_path = ROOT / "vendor" / "r5" / ORIGINAL
    if digest(original_path.read_bytes()) != ORIGINAL_SHA:
        raise ValueError("Frozen R5 checksum mismatch")
    target.mkdir(mode=0o700, parents=True, exist_ok=False)
    (target / "vendor" / "r5").mkdir(parents=True)
    (target / "scripts").mkdir()
    (target / "tests").mkdir()
    (target / "src" / "wap_probe").mkdir(parents=True)
    shutil.copyfile(ROOT / "pyproject.toml", target / "pyproject.toml")
    shutil.copyfile(ROOT / "scripts" / "smoke_clean_install.py",
                    target / "scripts" / "smoke_clean_install.py")
    for name in PORTABLE_TESTS:
        test_path = ROOT / "tests" / name
        if not test_path.is_file() or test_path.is_symlink():
            raise ValueError("Invalid portable regression test")
        shutil.copyfile(test_path, target / "tests" / name)
    for file in sorted((ROOT / "src" / "wap_probe").glob("*.py")):
        if not file.is_file() or file.is_symlink():
            raise ValueError("Unsafe Python source entry")
        shutil.copyfile(file, target / "src" / "wap_probe" / file.name)

    reduced_path = target / "vendor" / "r5" / REDUCED
    members = {}
    with zipfile.ZipFile(original_path) as source, zipfile.ZipFile(
        reduced_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as output:
        for name in KEEP:
            data = source.read(name)
            if not 0 < len(data) <= 128_000:
                raise ValueError("Invalid allowed R5 member")
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            output.writestr(entry, data)
            members[name] = {"bytes": len(data), "sha256": digest(data)}

    agent_path = target / "src" / "wap_probe" / "agent_browser.py"
    code = agent_path.read_text(encoding="utf-8")
    old_name = 'ARCHIVE_NAME = "' + ORIGINAL + '"'
    old_sha = 'ARCHIVE_SHA256 = "' + ORIGINAL_SHA + '"'
    if code.count(old_name) != 1 or code.count(old_sha) != 1:
        raise ValueError("Unexpected source archive pins")
    candidate_hash = digest(reduced_path.read_bytes())
    code = code.replace(old_name, 'ARCHIVE_NAME = "' + REDUCED + '"')
    code = code.replace(old_sha, 'ARCHIVE_SHA256 = "' + candidate_hash + '"')
    agent_path.write_text(code, encoding="utf-8")
    (target / "README.md").write_text(README, encoding="utf-8")

    manifest = {
        "schema": "wap-probe-private-clean-source-candidate-v1",
        "publication_authorized": False,
        "original_r5_sha256": ORIGINAL_SHA,
        "reduced_archive_sha256": candidate_hash,
        "reduced_archive_members": members,
        "excluded_historical_site_captures": True,
        "portable_regression_files": list(PORTABLE_TESTS),
        "outstanding_rights": [
            "R5 parser code and WBXML token table",
            "Synthetic WMLC fixture provenance",
            "Project-wide original source code license",
        ],
    }
    (target / "SOURCE_CANDIDATE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    with zipfile.ZipFile(reduced_path) as verify:
        if sorted(verify.namelist()) != sorted(KEEP):
            raise ValueError("Unexpected reduced archive member")
    if list(target.rglob("*.zip")) != [reduced_path]:
        raise ValueError("Unexpected archive included in clean source")
    return manifest

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.out)
    print("PRIVATE_CLEAN_SOURCE_CANDIDATE " + json.dumps({
        "archive_sha256": result["reduced_archive_sha256"],
        "archive_files": len(result["reduced_archive_members"]),
        "publication_authorized": False,
    }, sort_keys=True))

if __name__ == "__main__":
    main()
