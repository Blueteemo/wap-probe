"""Offline bridge between captured evidence and a normalized R5 export.

R5 parser execution is NOT implemented here. The export is not independently
authenticated; therefore even a valid two-page report never auto-assigns A PASS.
"""
import argparse
import hashlib
import json
from pathlib import Path

from wap_probe.evidence_gate import verify_folder
from wap_probe.navigation import WML_STATUSES, select_navigation

EXPORT_SCHEMA = "r6-r5-export-v1"


def load_json(path):
    path = Path(path)
    if path.stat().st_size > 2_097_152:
        raise ValueError("Oversized JSON file")
    return json.loads(path.read_text(encoding="utf-8"))


def read_r5_export(export_path, capture_dir):
    record = load_json(export_path)
    body = (Path(capture_dir) / "body.bin").read_bytes()
    actual_sha = hashlib.sha256(body).hexdigest()
    if not isinstance(record, dict):
        raise ValueError("Expected an R5 export object")
    if (
        record.get("schema") != EXPORT_SCHEMA
        or record.get("status") != "ok"
        or record.get("strict") is not True
        or record.get("source_sha256") != actual_sha
    ):
        raise ValueError("Invalid R5 export or source provenance")
    cards = record.get("cards")
    if not isinstance(cards, list) or not 1 <= len(cards) <= 256:
        raise ValueError("Invalid card collection")
    for card in cards:
        if not isinstance(card, dict):
            raise ValueError("Invalid card")
    # Only use visible/initial card's links; other cards may not be reachable.
    raw_links = cards[0].get("links", [])
    if not isinstance(raw_links, list) or len(raw_links) > 1024:
        raise ValueError("Invalid link collection")
    links = []
    for item in raw_links:
        if not isinstance(item, dict):
            raise ValueError("Invalid link")
        if not isinstance(item.get("href"), str):
            raise ValueError("Invalid href")
        method = item.get("method", "GET")
        if not isinstance(method, str):
            raise ValueError("Invalid method")
        links.append({"href": item["href"], "method": method})
    return {"source_sha256": actual_sha, "card_count": len(cards), "links": links}


def report_stage(stage, **fields):
    return {"stage": stage, "A_origin": "PENDING", "A_navigation": "PENDING", **fields}


def evaluate(home_dir, home_r5_path=None, child_dir=None, child_r5_path=None):
    home_dir = Path(home_dir)
    home_evidence = verify_folder(home_dir)
    report = report_stage("HOME_CAPTURE_REJECTED", home_evidence=home_evidence)
    if home_evidence["status"] not in WML_STATUSES:
        return report
    if home_r5_path is None:
        report["stage"] = "HOME_R5_EXPORT_REQUIRED"
        return report
    try:
        home_meta = load_json(home_dir / "metadata.json")
        home_r5 = read_r5_export(home_r5_path, home_dir)
        profile = home_meta["profile"]
        if not isinstance(profile, str) or not 1 <= len(profile) <= 64:
            raise ValueError("Invalid profile")
        navigation = select_navigation(
            home_meta["url"],
            home_r5["links"],
            capture_status=home_evidence["status"],
            card_count=home_r5["card_count"],
            captured_body_sha256=home_meta["body_sha256"],
            parsed_body_sha256=home_r5["source_sha256"],
        )
        if navigation["status"] in ("HOME_NOT_VERIFIED", "INVALID_HOME_URL"):
            raise ValueError("Unsafe or unverified home")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        report["stage"] = "HOME_R5_REJECTED"
        report["reason"] = str(exc)
        return report
    report["stage"] = "HOME_R5_EVIDENCE_MATCHED"
    report["home_r5"] = {
        "card_count": home_r5["card_count"],
        "source_sha256": home_r5["source_sha256"],
    }
    report["navigation_selection"] = navigation
    if navigation["status"] != "READY_FOR_GET":
        return report
    target = navigation["target_url"]
    report["next_get"] = {
        "url": target, "profile": profile,
        "method": "GET", "follow_redirects": False,
        "source_link_index": navigation["source_link_index"],
    }
    if child_dir is None:
        report["stage"] = "CHILD_GET_REQUIRED"
        return report
    child_dir = Path(child_dir)
    if child_dir.resolve() == home_dir.resolve():
        report["stage"] = "CHILD_BINDING_REJECTED"
        report["reason"] = "Child must be a distinct capture"
        return report
    child_evidence = verify_folder(child_dir)
    report["child_evidence"] = child_evidence
    if child_evidence["status"] not in WML_STATUSES:
        report["stage"] = "CHILD_CAPTURE_REJECTED"
        return report
    try:
        child_meta = load_json(child_dir / "metadata.json")
        if child_meta["url"] != target or child_meta["profile"] != profile:
            raise ValueError("Child capture target or profile mismatch")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        report["stage"] = "CHILD_BINDING_REJECTED"
        report["reason"] = str(exc)
        return report
    if child_r5_path is None:
        report["stage"] = "CHILD_R5_EXPORT_REQUIRED"
        return report
    try:
        child_r5 = read_r5_export(child_r5_path, child_dir)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        report["stage"] = "CHILD_R5_REJECTED"
        report["reason"] = str(exc)
        return report
    report["stage"] = "TWO_PAGE_EVIDENCE_MATCHED"
    report["child_r5"] = {
        "card_count": child_r5["card_count"],
        "source_sha256": child_r5["source_sha256"],
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Inspect offline R5/R6 evidence")
    parser.add_argument("--home", required=True)
    parser.add_argument("--home-r5")
    parser.add_argument("--child")
    parser.add_argument("--child-r5")
    parser.add_argument("--out")
    args = parser.parse_args()
    if args.child_r5 and not args.child:
        parser.error("--child-r5 requires --child")
    result = evaluate(args.home, args.home_r5, args.child, args.child_r5)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
