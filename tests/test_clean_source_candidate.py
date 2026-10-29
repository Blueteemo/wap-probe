"""Test that the private release candidate is minimal and reproducible."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TESTS = {
    "test_agent_browser.py",
    "test_collector.py",
    "test_delivery_contract.py",
    "test_navigation.py",
    "test_security_regressions.py",
}
PREFIX = "wap-probe-live-discovery-r5/probe/"
EXPECTED_MEMBERS = {
    PREFIX + "wap_probe.py",
    PREFIX + "wap_wbxml.py",
    PREFIX + "fixtures/binary_portal.wmlc",
}


class PrivateCandidateTests(unittest.TestCase):
    def test_manifest_files_checksum_and_no_capture_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "candidate"
            cmd = [
                sys.executable, str(ROOT / "scripts/build_clean_source_candidate.py"),
                "--out", str(root),
            ]
            proc = subprocess.run(
                cmd, cwd=ROOT, capture_output=True,
                text=True, check=True, timeout=30)
            self.assertIn("PRIVATE_CLEAN_SOURCE_CANDIDATE ", proc.stdout)
            manifest = json.loads(
                (root / "SOURCE_CANDIDATE_MANIFEST.json").read_text("utf-8"))
            self.assertIs(manifest["publication_authorized"], False)
            self.assertIs(manifest["excluded_historical_site_captures"], True)
            self.assertEqual(set(manifest["portable_regression_files"]), EXPECTED_TESTS)
            self.assertEqual({p.name for p in (root / "tests").iterdir()},
                             EXPECTED_TESTS)
            archives = list(root.rglob("*.zip"))
            self.assertEqual(len(archives), 1)
            archive_path = archives[0]
            self.assertEqual(
                hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                manifest["reduced_archive_sha256"])
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(set(archive.namelist()), EXPECTED_MEMBERS)
                for member in archive.namelist():
                    self.assertEqual(
                        hashlib.sha256(archive.read(member)).hexdigest(),
                        manifest["reduced_archive_members"][member]["sha256"])
            names = {p.relative_to(root).as_posix() for p in root.rglob("*")
                     if p.is_file()}
            self.assertFalse(any("deepseek" in name.lower() or
                                 "online_candidates" in name.lower() or
                                 "online_international" in name.lower()
                                 for name in names))
            before = sorted(names)
            duplicate = subprocess.run(
                cmd, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertEqual(
                sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                       if p.is_file()), before)


if __name__ == "__main__":
    unittest.main()
