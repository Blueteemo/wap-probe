"""Read-only structural preview of verified WML decks.

No variable substitution, URL construction, form submission, or script execution.
All displayed values are bounded, and sensitive defaults are NEVER returned.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

MAX_XML = 1_048_576
MAX_NODES = 4096
MAX_CARDS = 256
MAX_FIELDS = 48
MAX_ACTIONS = 32
MAX_OPTIONS = 32
PRIVATE = re.compile(
    r"(?:passw|passwd|pwd|secret|token|cookie|session|csrf|auth|apikey|api_key|"
    r"credential|private|pin|otp|account|access.key)", re.I
)
DECLARED_ENCODING = re.compile(
    rb"encoding\s*=\s*['\"]([a-zA-Z0-9_-]{1,32})['\"]", re.I
)
MIME_ENCODING = re.compile(
    r"charset\s*=\s*['\"]?([a-zA-Z0-9_-]{1,32})", re.I
)
CODECS = {"utf-8", "utf8", "gb2312", "gbk", "big5", "iso-8859-1", "us-ascii"}


def _tag(node) -> str:
    return node.tag.rsplit("}", 1)[-1].lower() if isinstance(node.tag, str) else ""


def _label(value, size=96) -> str:
    return " ".join(value.split())[:size] if isinstance(value, str) else ""


def _name(value) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return "[redacted]" if PRIVATE.search(value) else _label(value, 64)


def _field(node) -> dict:
    t = _tag(node)
    typ = _label(node.get("type", "text"), 20).lower() if t == "input" else "select"
    name = node.get("name", "")
    sensitive = typ == "password" or bool(PRIVATE.search(name))
    out = {
        "kind": t, "name": _name(name), "type": typ,
        "title": _label(node.get("title", "")),
        "sensitive": sensitive, "has_default": node.get("value") is not None,
        "dynamic_default": "$(" in node.get("value", ""),
    }
    if t == "input":
        maximum = node.get("maxlength", "")
        out["maxlength"] = (int(maximum) if maximum.isdigit()
                            and 0 <= int(maximum) <= 65535 else None)
    else:
        out["multiple"] = node.get("multiple", "false").lower() in ("true", "yes", "1")
        choices = []
        for option in node.iter():
            if _tag(option) != "option":
                continue
            if len(choices) >= MAX_OPTIONS:
                break
            choices.append({
                "label": _label("".join(option.itertext()), 128),
                "has_value": option.get("value") is not None,
                "selected_by_default": option.get("onpick") is not None
                or option.get("selected", "").lower() in ("true", "yes", "1"),
            })
        out["option_count"] = sum(1 for o in node.iter() if _tag(o) == "option")
        out["options"] = choices
        out["options_truncated"] = out["option_count"] > MAX_OPTIONS
    return out


def _action(node) -> dict:
    method = _label(node.get("method", "get"), 16).upper()
    href = node.get("href", "")
    dynamic = "$(" in href
    parsed = urlsplit(href) if isinstance(href, str) else None
    destination = "dynamic" if dynamic else ("absolute" if parsed and parsed.scheme
                   else "fragment" if isinstance(href, str) and href.startswith("#")
                   else "relative" if href else "missing")
    postfields = [
        {"name": _name(p.get("name", "")),
         "has_value": p.get("value") is not None,
         "dynamic_value": "$(" in p.get("value", "")}
        for p in node.iter() if _tag(p) == "postfield"
    ][:MAX_FIELDS]
    return {
        "method": method, "destination_kind": destination,
        "has_path": bool(parsed and parsed.path),
        "has_query": bool(parsed and parsed.query),
        "dynamic_href": dynamic,
        "postfield_count": sum(1 for p in node.iter() if _tag(p) == "postfield"),
        "postfields": postfields,
        "submission_available": False,
        "reason": "READ_ONLY_NO_FORM_SUBMISSIONS",
    }


def inspect_forms(raw: bytes, content_type: str = "text/vnd.wap.wml", *,
                  include_action_hrefs: bool = False) -> list[dict]:
    """Return per-card control/action metadata; safe for untrusted XML.

    The caller must separately verify that this raw body came from an accepted
    evidence capture and passed the frozen R5 parser. XML/WMLC decoding is not
    a substitute for R5 verification.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_XML:
        raise ValueError("Invalid form-source size")
    if b"<!entity" in raw.lower():
        raise ValueError("Custom XML entities are not accepted")
    declaration = re.match(rb"\s*<\?xml[^>]{0,200}\?>", raw, flags=re.I)
    match = DECLARED_ENCODING.search(declaration.group(0)) if declaration else None
    mime = MIME_ENCODING.search(content_type) if isinstance(content_type, str) else None
    codec = (match.group(1).decode("ascii") if match else
             mime.group(1) if mime else "utf-8").lower()
    if codec not in CODECS:
        raise ValueError("Unsupported XML charset")
    try:
        root = ET.fromstring(raw.decode(codec, "strict"))
    except (UnicodeError, ET.ParseError, LookupError) as exc:
        raise ValueError("Unusable XML/WML for form preview") from exc
    if _tag(root) != "wml":
        raise ValueError("Not a WML deck")
    if sum(1 for _ in root.iter()) > MAX_NODES:
        raise ValueError("Too many XML nodes for form preview")
    cards = [node for node in root if _tag(node) == "card"]
    if not 1 <= len(cards) <= MAX_CARDS:
        raise ValueError("Unsupported WML card count")
    result = []
    for card in cards:
        fields, actions = [], []
        for node in card.iter():
            tag = _tag(node)
            if tag in ("input", "select") and len(fields) < MAX_FIELDS:
                fields.append(_field(node))
            if tag == "go" and len(actions) < MAX_ACTIONS:
                actions.append(_action(node))
        count_fields = sum(1 for n in card.iter() if _tag(n) in ("input", "select"))
        count_actions = sum(1 for n in card.iter() if _tag(n) == "go")
        result.append({
            "fields": fields, "actions": actions,
            "field_count": count_fields, "action_count": count_actions,
            "truncated": count_fields > MAX_FIELDS or count_actions > MAX_ACTIONS,
            "read_only": True,
            **({"_action_hrefs": [
                node.get("href") for node in card.iter()
                if _tag(node) == "go" and isinstance(node.get("href"), str)
            ]} if include_action_hrefs else {}),
        })
    return result
