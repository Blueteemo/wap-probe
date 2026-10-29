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

PROVENANCE = "# Third-party references and code provenance (internal candidate)\n\n**This is a factual provenance record, not a LICENSE, copyright assignment,\npermission to publish, or claim of independent legal clearance.**\n\n## Frozen parser and synthetic WMLC fixture\n\nThe private original R5 ZIP, pinned by SHA-256 in the candidate manifest,\ncontains probe/RESEARCH_LOG.md. The 2026-10-28 v0.3 research notes expressly\ndescribe implementing wap_wbxml.py as a \"strict subset decoder\" using WAP\nWBXML/WML semantics, OMA identifiers, and Android kXML WML token tables.\nThose notes also record construction of an 86-byte binary WMLC test sample\nwith two cards and an in-page #next link. The candidate contains that\n86-byte sample and only two R5 Python parser files, each byte-for-byte\nretained from the frozen archive.\n\nThese original research notes document a project-origin narrative; they are\nnot an independent third-party similarity audit or a legal rights grant.\nThe owner must verify that model-assisted contributions and subsequent\nmodifications are theirs to authorize.\n\n## Standards and implementation references\n\n- WAP Forum WBXML specification:\n  https://www.w3.org/1999/06/NOTE-wbxml-19990624/\n- WAP Forum WML token specification:\n  https://www.wapforum.org/what/technical/spec-wml-19990616.pdf\n- Android historical kXML2 Wml.java (token-table reference):\n  https://android.googlesource.com/platform/dalvik.git/+/f6c387128427e121477c1b32ad35cdcaa5101ba3/libcore/xml/src/main/java/org/kxml2/wap/wml/Wml.java\n- kXML2 source licensing:\n  https://github.com/kobjects/kxml2/blob/master/license.txt\n  kXML2's related Wbxml.java states copyright (c) 2002, 2003\n  Stefan Haustein and contains a permissive notice with attribution\n  obligations where code or substantial protected expression is reused:\n  https://android.googlesource.com/platform/dalvik.git/+/f6c387128427e121477c1b32ad35cdcaa5101ba3/libcore/xml/src/main/java/org/kxml2/wap/Wbxml.java\n\nProtocol-defined numeric token assignments alone do not establish that\nthe project's decoder implementation is copied from kXML2. Conversely,\nthis documentation does not prove independent expression or rule out\nattribution obligations. Before public release, confirm whether any\nprotected source/table expression was incorporated and preserve the full\napplicable upstream notice when required.\n\n## External interoperability materials excluded from this candidate\n\n- WAP Labs / wapcurl: separately installed tooling in original R5 work,\n  not shipped as a Rust or other source-code dependency.\n- libwbxml: separately invoked reference tool, not bundled here.\n- WAP Labs Lowband independent reference corpus: belongs to the full\n  private repository with its own retained license, not this candidate.\n- Third-party website captures, historic source-response snapshots and\n  DeepSeek nested review files: not shipped.\n\n## Release gate\n\nNo top-level project license has yet been chosen or granted by the owner.\nDo not treat this provenance file, any upstream reference, passing tests,\nor the presence of a binary fixture as permission to publish.\n"

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

See THIRD_PARTY_REFERENCES.md for the origin of the R5 parser and fixture,
and for unresolved attribution and release-permission questions.

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
            if name.endswith("/fixtures/binary_portal.wmlc") and len(data) != 86:
                raise ValueError("Synthetic R5 sample differs from original research log")
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
    (target / "THIRD_PARTY_REFERENCES.md").write_text(PROVENANCE, encoding="utf-8")

    manifest = {
        "schema": "wap-probe-private-clean-source-candidate-v1",
        "publication_authorized": False,
        "original_r5_sha256": ORIGINAL_SHA,
        "reduced_archive_sha256": candidate_hash,
        "reduced_archive_members": members,
        "excluded_historical_site_captures": True,
        "provenance_review_document": "THIRD_PARTY_REFERENCES.md",
        "sample_original_r5_research_log": "probe/RESEARCH_LOG.md",
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
