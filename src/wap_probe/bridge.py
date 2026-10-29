"""Offline bridge between captured evidence and a normalized R5 export.

R5 parser execution is NOT implemented here. The export is not independently
authenticated; therefore even a valid two-page report never auto-assigns A PASS.
"""
import argparse
import hashlib
import json
from pathlib import Path

from wap_probe.evidence_gate import verify_folder
from wap_probe.navigation import WML_STATUSES, select_reachable_navigation

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
    validated_cards = []
    total_links = 0
    for card in cards:
        raw_links = card.get("links", [])
        if not isinstance(raw_links, list):
            raise ValueError("Invalid card link collection")
        parsed_links = []
        for item in raw_links:
            if not isinstance(item, dict) or not isinstance(item.get("href"), str):
                raise ValueError("Invalid link")
            method = item.get("method", "GET")
            if not isinstance(method, str):
                raise ValueError("Invalid method")
            parsed_links.append({"href": item["href"], "method": method})
            total_links += 1
            if total_links > 1024:
                raise ValueError("Too many links")
        card_text = card.get("text", "")
        if not isinstance(card_text, str) or len(card_text) > 12000:
            raise ValueError("Invalid R5 card text")
        form = card.get("form_preview")
        if form is not None:
            if (not isinstance(form, dict)
                    or form.get("read_only") is not True
                    or not isinstance(form.get("fields"), list)
                    or not isinstance(form.get("actions"), list)
                    or len(form["fields"]) > 48
                    or len(form["actions"]) > 32
                    or type(form.get("field_count")) is not int
                    or type(form.get("action_count")) is not int
                    or form["field_count"] < len(form["fields"])
                    or form["action_count"] < len(form["actions"])
                    or type(form.get("truncated")) is not bool):
                raise ValueError("Invalid R5 form preview")
            for field in form["fields"]:
                if not isinstance(field, dict) or field.get("kind") not in ("input", "select"):
                    raise ValueError("Invalid R5 form field")
            for action in form["actions"]:
                if (not isinstance(action, dict)
                        or action.get("submission_available") is not False):
                    raise ValueError("Invalid R5 form action")
        do_raw = card.get("do_navigation", [])
        if not isinstance(do_raw, list) or len(do_raw) > 16:
            raise ValueError("Invalid R5 no-input do/go collection")
        validated_do = []
        for action in do_raw:
            if (not isinstance(action, dict) or not isinstance(action.get("href"), str)
                    or not 0 < len(action["href"]) <= 2048
                    or action.get("method") != "GET"):
                raise ValueError("Invalid R5 do/go action")
            validated_do.append({"href": action["href"], "method": "GET"})
        validated_cards.append({"id": card.get("id"), "links": parsed_links,
                                "text": card_text, "form_preview": form,
                                "do_navigation": validated_do})
    return {"source_sha256": actual_sha, "card_count": len(cards),
            "cards": validated_cards, "links": validated_cards[0]["links"]}


def report_stage(stage, **fields):
    return {"stage": stage, "A_origin": "PENDING", "A_navigation": "PENDING", **fields}


def evaluate(home_dir, home_r5_path=None, child_dir=None, child_r5_path=None,
             *, preferred_path=None):
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
        navigation = select_reachable_navigation(
            home_meta["url"],
            home_r5["cards"],
            capture_status=home_evidence["status"],
            card_count=home_r5["card_count"],
            captured_body_sha256=home_meta["body_sha256"],
            parsed_body_sha256=home_r5["source_sha256"],
            preferred_path=preferred_path,
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
        "source_card_index": navigation.get("source_card_index", 0),
        "source_card_id": navigation.get("source_card_id"),
        "fragment_path": navigation.get("fragment_path", []),
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
