"""Conservative, read-only publication audit of the *entire Git history*.

No external network, no source bodies or matching credentials printed.
This is an automated triage, NOT a legal opinion or a license grant.
Requires a full git checkout (actions/checkout fetch-depth: 0).
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "vendor/r5/WAP_Probe_WAP_Labs_Interop_R5_20261028.zip"
LICENSE_FILENAMES = {"license", "license.txt", "license.md", "copying",
                     "copying.txt", "notice", "notice.txt", "unlicense"}
SENSITIVE = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"(?:ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{35,}"),
    "cloud_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "slack_token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,}"),
    "credential_assignment": re.compile(
        rb"(?i)(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)\s*[:=]\s*['\"](?!(?:<|example|test|dummy|fake|redacted|none))[A-Za-z0-9_+/=-]{24,}['\"]"
    ),
}


def _git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def _safe_label(s: str) -> str:
    # No arbitrary filename strings from previous commits are printed.
    return Path(s).name[:85]


def _scan_bytes(data: bytes, label: str, findings: set[tuple[str, str]]):
    for kind, pattern in SENSITIVE.items():
        if pattern.search(data):
            findings.add((label, kind))


def _scan_archive(data: bytes, base: str, *, depth: int,
                  license_paths: set[str], candidate_sources: list[int],
                  findings: set[tuple[str, str]]):
    if depth > 2:
        return
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for member in z.infolist():
            if member.is_dir() or member.file_size > 3_000_000:
                continue
            name = member.filename
            candidate_sources[0] += int(name.endswith((".py", ".js", ".c", ".h", ".rs", ".java")))
            base_name = name.replace("\\", "/").rsplit("/", 1)[-1].lower()
            if base_name in LICENSE_FILENAMES or base_name.startswith("license."):
                license_paths.add(base + ":" + name)
            if member.file_size > 1_000_000:
                continue
            raw = z.read(member)
            _scan_bytes(raw, base + ":" + _safe_label(name), findings)
            if name.lower().endswith(".zip"):
                try:
                    _scan_archive(raw, base + ":" + _safe_label(name),
                                  depth=depth + 1, license_paths=license_paths,
                                  candidate_sources=candidate_sources,
                                  findings=findings)
                except zipfile.BadZipFile:
                    pass


def main() -> None:
    root_license = sorted(p.name for p in ROOT.iterdir()
                          if p.is_file() and (
                              p.name.lower() in LICENSE_FILENAMES or
                              p.name.lower().startswith("license.")))
    source_count = [0]
    license_paths: set[str] = set()
    suspicious: set[tuple[str, str]] = set()
    _scan_archive(ARCHIVE.read_bytes(), "frozen-r5.zip", depth=0,
                  license_paths=license_paths, candidate_sources=source_count,
                  findings=suspicious)
    objects = _git("rev-list", "--objects", "--all").decode("utf-8", "replace").splitlines()
    blobs = 0
    archived_paths = set()
    for line in objects:
        sha, _, path = line.partition(" ")
        if not path:
            continue
        if path.endswith(".zip"):
            archived_paths.add(_safe_label(path))
        if not path.endswith((".py", ".md", ".txt", ".json", ".yml", ".yaml",
                              ".toml", ".cfg", ".ini", ".sh", ".env")):
            continue
        size = int(_git("cat-file", "-s", sha))
        if size > 500_000:
            continue
        blobs += 1
        raw = _git("cat-file", "-p", sha)
        _scan_bytes(raw, "git-history:" + _safe_label(path), suspicious)

    outcome = {
        "scope": "all locally available Git history + current R5 ZIP and nested ZIPs",
        "root_license_files": root_license,
        "r5_archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        "r5_potential_source_file_count": source_count[0],
        "r5_internal_license_filenames": sorted(license_paths)[:30],
        "historical_archive_basenames": sorted(archived_paths)[:30],
        "history_text_blobs_scanned": blobs,
        "potential_credential_pattern_categories": sorted({kind for _, kind in suspicious}),
        "potential_credential_match_locations": sorted(
            set(label for label, _ in suspicious))[:30],
        "automated_publication_decision": "REVIEW_REQUIRED",
        "reason": "No automated scan proves reuse and redistribution rights for frozen historical source or all Git history",
    }
    print("PUBLICATION_AUDIT " + json.dumps(outcome, ensure_ascii=False, sort_keys=True))
    # Do not fail the ordinary offline reader CI solely because licensing
    # review remains incomplete. Visibility changes require manual review.
    if suspicious:
        print("PUBLICATION_AUDIT_NOTE Potential credential patterns need human review; no matched value was printed.")


if __name__ == "__main__":
    main()
