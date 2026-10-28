"""Offline-by-default one-shot WML/WMLC origin + second-page workflow.

Requires explicit --execute to perform GET; never grants A-level PASS.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from wap_probe.collector import capture, matrix, validate_url, PROFILES
from wap_probe.bridge import evaluate
from wap_probe.r5_adapter import parse_capture

WML_STATUSES = {"WML_CAPTURED_NEEDS_R5", "WMLC_CAPTURED_NEEDS_R5"}


def _save(folder: Path, report: dict) -> dict:
    (folder / "run_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def _export(capture_dir: Path, probe_dir: Path) -> Path:
    record = parse_capture(capture_dir, probe_dir=probe_dir)
    path = capture_dir / "r5_export.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


def run_job(url: str, profile: str, folder: Path, probe_dir: Path, *,
            capture_fn=capture, before_second_get=None) -> dict:
    """Opt-in caller supplies capture_fn; never directly opens a socket here."""
    validate_url(url)
    if profile not in PROFILES:
        raise ValueError("Invalid profile")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    report = {
        "url": url, "profile": profile, "stage": "STARTED",
        "A_origin": "PENDING", "A_navigation": "PENDING",
        "home_capture": None, "child_capture": None,
    }
    home = folder / "home"
    try:
        home_meta = capture_fn(url, profile, home)
        report["home_capture"] = home_meta["classification"]
        if home_meta["classification"] not in WML_STATUSES:
            report["stage"] = "HOME_NOT_WML_EVIDENCE"
            return _save(folder, report)
        home_r5 = _export(home, probe_dir)
        plan = evaluate(home, home_r5)
        report["home_bridge"] = plan
        if plan["stage"] != "CHILD_GET_REQUIRED":
            report["stage"] = plan["stage"]
            return _save(folder, report)
        next_request = plan["next_get"]
        next_url = next_request["url"]
        if (next_request.get("method") != "GET"
                or next_request.get("profile") != profile
                or next_request.get("follow_redirects") is not False):
            raise ValueError("Unsafe navigation task")
        validate_url(next_url)
        if before_second_get is not None:
            before_second_get()
        child = folder / "child"
        child_meta = capture_fn(next_url, profile, child)
        report["child_capture"] = child_meta["classification"]
        if child_meta["classification"] not in WML_STATUSES:
            report["stage"] = "CHILD_NOT_WML_EVIDENCE"
            return _save(folder, report)
        child_r5 = _export(child, probe_dir)
        result = evaluate(home, home_r5, child, child_r5)
        report["bridge"] = result
        report["stage"] = result["stage"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        report["stage"] = "PIPELINE_FAILED"
        report["error"] = f"{type(exc).__name__}: {str(exc)[:1024]}"
    return _save(folder, report)


def main(argv=None):
    p = argparse.ArgumentParser(description="Controlled, read-only origin WAP verification")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--url")
    mode.add_argument("--matrix", action="store_true")
    p.add_argument("--profile", choices=tuple(PROFILES), default="wap1")
    p.add_argument("--r5-dir", type=Path, default=Path(".r5_unpacked/wap-probe-live-discovery-r5/probe"))
    p.add_argument("--out", type=Path, default=Path("evidence/live"))
    p.add_argument("--execute", action="store_true", help="Explicitly perform network GET")
    p.add_argument("--limit", type=int, default=32)
    p.add_argument("--delay", type=float, default=2.0)
    a = p.parse_args(argv)
    if a.limit < 1 or a.limit > 32 or not 1 <= a.delay <= 3600:
        p.error("Limit 1..32 and delay 1..3600 required")
    jobs = matrix() if a.matrix else [(a.url, a.profile)]
    jobs = jobs[:a.limit]
    for u, _ in jobs:
        validate_url(u)
    print(json.dumps({"execute": a.execute, "jobs": len(jobs),
                      "urls": [u for u, _ in jobs]}, indent=2))
    if not a.execute:
        return 0
    if not (a.r5_dir / "wap_probe.py").is_file():
        p.error("The frozen R5 parser is not unpacked")
    if a.out.exists():
        p.error("Output root already exists; provide a fresh directory")
    a.out.mkdir(parents=True)
    results = []
    last_request = False

    def throttle():
        nonlocal last_request
        if last_request:
            time.sleep(a.delay)
        last_request = True

    # The first capture uses its own call; every subsequent request (including
    # navigation) has a >= delay gap.
    def paced_capture(url, profile, folder):
        throttle()
        return capture(url, profile, folder)

    for idx, (url, profile) in enumerate(jobs, 1):
        report = run_job(url, profile, a.out / f"{idx:03d}_{profile}",
                         a.r5_dir, capture_fn=paced_capture)
        results.append({"url": url, "profile": profile, "stage": report["stage"]})
        print(f"{idx}/{len(jobs)} {profile} {url} -> {report['stage']}")
    (a.out / "summary.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
