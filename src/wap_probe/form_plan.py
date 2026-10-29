"""Offline-only, conservative WML GET form request planning.

A plan is NOT an authorization to execute a server-side action. No function
in this module performs network requests or persists supplied field values.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode, urljoin, urlsplit, quote

from wap_probe.collector import validate_url
from wap_probe.navigation import evaluate_link
from wap_probe.form_inspector import (
    CODECS, DECLARED_ENCODING, MIME_ENCODING, PRIVATE, MAX_XML,
    inspect_forms, _tag,
)

import xml.etree.ElementTree as ET

FIELD_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,31}\Z")
VAR_REF = re.compile(r"\$\(([A-Za-z_][A-Za-z0-9_]{0,31})\)\Z")
DANGEROUS = re.compile(
    r"(?:^|[._/-])(?:delete|remove|logout|login|signout|register|submit|"
    r"save|update|reset|purchase|checkout|payment|pay|cancel|unsubscribe|"
    r"send|transfer|withdraw|destroy|post|execute|confirm|edit|activate|"
    r"deactivate)(?:$|[._/-])", re.I,
)
MAX_INPUT = 128
MAX_VALUES = 8
MAX_TARGET = 1024


def _source_cards(raw: bytes, content_type: str) -> list:
    """Decode restricted XML and enforce the same document limits as preview."""
    inspect_forms(raw, content_type)
    declaration = re.match(rb"\s*<\?xml[^>]{0,200}\?>", raw, flags=re.I)
    declared = DECLARED_ENCODING.search(declaration.group(0)) if declaration else None
    mime = MIME_ENCODING.search(content_type)
    codec = (declared.group(1).decode("ascii") if declared else
             mime.group(1) if mime else "utf-8").lower()
    if codec not in CODECS:
        raise ValueError("Unsupported form charset")
    root = ET.fromstring(raw.decode(codec, errors="strict"))
    return [node for node in root if _tag(node) == "card"]


def _validate_values(values: object) -> dict[str, str]:
    if not isinstance(values, dict) or len(values) > MAX_VALUES:
        raise ValueError("Invalid number of form variables")
    for key, value in values.items():
        if (not isinstance(key, str) or not FIELD_NAME.fullmatch(key)
                or PRIVATE.search(key)):
            raise ValueError("Unsafe form variable name")
        if (not isinstance(value, str) or len(value) > MAX_INPUT
                or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)):
            raise ValueError("Invalid form value")
    return values


def _resolve_plan(source_url: str, card, action_index: int,
                  values: dict[str, str]) -> dict:
    actions = [node for node in card.iter() if _tag(node) == "go"]
    if (type(action_index) is not int or not 0 <= action_index < len(actions)
            or action_index >= 32):
        raise ValueError("Invalid form action index")
    go = actions[action_index]
    if go.get("method", "get").lower() != "get":
        raise ValueError("Only GET actions are eligible for planning")
    if go.get("sendreferer", "false").lower() not in ("false", "0"):
        raise ValueError("Referrer-sending actions are unsupported")
    if go.get("enctype", "application/x-www-form-urlencoded").lower() != "application/x-www-form-urlencoded":
        raise ValueError("Unsupported GET form encoding")
    if go.get("accept-charset", "utf-8").lower() not in ("utf-8", "utf8"):
        raise ValueError("Unsupported form accept-charset")
    if any(_tag(child) != "postfield" for child in go):
        raise ValueError("Task contains unhandled or state-changing WML elements")
    href = go.get("href")
    if (not isinstance(href, str) or not href or len(href) > MAX_TARGET
            or "$" in href or "?" in href or "#" in href):
        raise ValueError("Dynamic or complex form targets are not supported")
    # Disallow embedded URL credentials, alternate schemes and query strings.
    target = urljoin(source_url, href)
    validate_url(target)
    parsed = urlsplit(target)
    if DANGEROUS.search(parsed.path):
        raise ValueError("Potential state-changing GET endpoint")
    if parsed.query or parsed.fragment:
        raise ValueError("GET endpoint must be a literal path")
    control_map = {}
    for node in card.iter():
        if _tag(node) not in ("input", "select"):
            continue
        name = node.get("name", "")
        if (not FIELD_NAME.fullmatch(name) or PRIVATE.search(name)
                or name in control_map or
                (_tag(node) == "input" and node.get("type", "text").lower() not in ("text", "url"))):
            continue
        if _tag(node) == "select":
            if node.get("multiple", "false").lower() not in ("false", "no", "0"):
                continue
            opts = [opt.get("value") for opt in node.iter() if _tag(opt) == "option"]
            if len(opts) > 32 or any(o is None for o in opts):
                continue
            control_map[name] = ("select", set(opts))
        else:
            maximum = node.get("maxlength", "")
            maxlen = int(maximum) if maximum.isdigit() else MAX_INPUT
            control_map[name] = ("input", min(maxlen, MAX_INPUT))

    fields = [node for node in go if _tag(node) == "postfield"]
    if not 1 <= len(fields) <= MAX_VALUES:
        raise ValueError("Require 1..8 explicit GET postfields")
    pairs = []
    used = set()
    for field in fields:
        name = field.get("name")
        expression = field.get("value", "")
        match = VAR_REF.fullmatch(expression)
        if (not name or not FIELD_NAME.fullmatch(name) or PRIVATE.search(name)
                or name in used or not match):
            raise ValueError("Unsupported or sensitive GET postfield")
        variable = match.group(1)
        if variable not in control_map or variable not in values:
            raise ValueError("Missing verified public form input")
        kind, constraint = control_map[variable]
        value = values[variable]
        if (kind == "select" and value not in constraint) or (
                kind == "input" and len(value) > constraint):
            raise ValueError("Form value fails control validation")
        pairs.append((name, value))
        used.add(name)
    expected_vars = {VAR_REF.fullmatch(f.get("value", "")).group(1) for f in fields}
    if set(values) != expected_vars:
        raise ValueError("Unexpected unused form variables")
    query = urlencode(pairs, encoding="utf-8")
    full_url = target + "?" + query
    validate_url(full_url)
    resolved, reason = evaluate_link(source_url, {"href": full_url, "method": "GET"})
    if reason != "OK" or resolved != full_url or len(full_url) > MAX_TARGET:
        raise ValueError("GET target rejected by public same-origin policy")
    # Never disclose submitted field *values* to an Agent or CLI stdout.
    # The digest allows precise future auditing, but is not an execution token.
    return {
        "ok": True, "kind": "wml-get-form-plan-v1",
        "method": "GET", "request_sha256": hashlib.sha256(full_url.encode()).hexdigest(),
        "target_origin": parsed.scheme + "://" + parsed.netloc,
        "path": parsed.path, "query_keys": [name for name, _ in pairs],
        "query_bytes": len(query.encode()), "field_count": len(pairs),
        "review_required": True, "execution_supported": False,
        "risk": "GET_MAY_HAVE_SERVER_SIDE_EFFECTS",
        "reason": "Preview only; no network request was made",
    }


def plan_current(root: Path, action_index: int, values: object) -> dict:
    """Build a redacted plan only from the currently verified WML/WMLC card."""
    from wap_probe.agent_browser import (
        _load_session, _current_page, _view, frozen_r5,
    )
    from wap_probe.r5_adapter import _legacy_parser

    values = _validate_values(values)
    root = Path(root)
    state = _load_session(root)
    current = _view(root, state)  # validates capture + source-bound R5 export
    preview = current.get("form_preview")
    if not current.get("ok") or not isinstance(preview, dict):
        raise ValueError("No verified WML form preview available")
    if preview.get("truncated") or preview.get("action_count", 0) > 32:
        raise ValueError("Truncated or oversized form cannot be planned")
    folder = _current_page(root, state)
    raw = (folder / "body.bin").read_bytes()
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if hashlib.sha256(raw).hexdigest() != current["sha256"]:
        raise ValueError("Captured body changed")
    mime = metadata["content_type"]
    if current["format"] == "wmlc":
        with frozen_r5() as probe:
            raw, _ = _legacy_parser(probe).decode_wmlc(raw)
        mime = "text/vnd.wap.wml; charset=utf-8"
    cards = _source_cards(raw, mime)
    idx = current["active_card_index"]
    if len(cards) != current["card_count"]:
        raise ValueError("Source and R5 card count disagree")
    if len([node for node in cards[idx].iter() if _tag(node) == "go"]) != preview["action_count"]:
        raise ValueError("Source and R5 form action count disagree")
    result = _resolve_plan(current["url"], cards[idx], action_index, values)
    result["source_sha256"] = current["sha256"]
    result["active_card_index"] = idx
    result["action_index"] = action_index
    return result
