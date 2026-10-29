"""Select safe same-origin WML GET links for a *future* second capture.

Pure offline selection. No network and no A-navigation claims.
"""
import ipaddress
import re
from urllib.parse import parse_qsl, unquote, urldefrag, urljoin, urlsplit, urlunsplit

WML_STATUSES = {"WML_CAPTURED_NEEDS_R5", "WMLC_CAPTURED_NEEDS_R5"}
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
LABEL_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
SENSITIVE_KEYS = {
    "password", "passwd", "pwd", "token", "access_token", "auth",
    "authorization", "session", "sessionid", "session_id",
    "sid", "cookie", "csrf", "secret", "api_key",
}


# Auth/account pages are not valid candidates for public second-page evidence.
# This is a conservative path/query filter; no login/cookie flow is followed.
AUTH_PATH_STEMS = {
    "login", "logout", "logon", "signin", "signout", "signup",
    "sign-in", "sign-out", "sign-up",
    "register", "registration", "authenticate", "auth", "fltin_t",
}
AUTH_QUERY_ACTIONS = {
    "login", "logout", "logon", "signin", "signout", "signup",
    "sign-in", "sign-out", "sign-up",
    "register", "registration", "authenticate", "password",
}


def _decoded_lower(text):
    for _ in range(5):
        changed = unquote(text)
        if changed == text:
            break
        text = changed
    return text.lower()


def _auth_destination(path, query):
    for segment in _decoded_lower(path).split("/"):
        stem = segment.split(".", 1)[0]
        if segment in AUTH_PATH_STEMS or stem in AUTH_PATH_STEMS:
            return True
    for key, value in parse_qsl(query, keep_blank_values=True, max_num_fields=64):
        name = _decoded_lower(key)
        intent = _decoded_lower(value)
        if name in ("type", "action", "mode", "op", "operation", "step") and intent in AUTH_QUERY_ACTIONS:
            return True
    return False



# Exclude scripts, downloads, and obvious state-changing GET actions.
NON_DOCUMENT_SUFFIXES = (
    ".wmls", ".wmlsc", ".js", ".css", ".jar", ".jad", ".sis", ".sisx",
    ".zip", ".rar", ".7z", ".apk", ".exe", ".cab",
    ".mp3", ".mid", ".midi", ".wav", ".mp4", ".3gp",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
)
MUTATION_STEMS = {"delete", "remove", "destroy", "save", "update", "submit",
                  "send", "pay", "payment", "checkout", "purchase", "cancel",
                  "unsubscribe", "withdraw", "transfer", "reset", "confirm",
                  "activate", "deactivate", "enable", "disable", "execute"}

def _mutation_destination(path, query):
    for segment in _decoded_lower(path).split("/"):
        stem = segment.split(".", 1)[0]
        if segment in MUTATION_STEMS or stem in MUTATION_STEMS:
            return True
    for key, value in parse_qsl(query, keep_blank_values=True, max_num_fields=64):
        if (_decoded_lower(key) in ("action", "mode", "type", "op", "operation", "cmd", "do")
                and _decoded_lower(value) in MUTATION_STEMS):
            return True
    return False


def validate_preferred_path(path):
    """Conservative literal path used ONLY to match a real parsed R5 link."""
    if not isinstance(path, str) or not re.fullmatch(
        r"/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*(?:\.[A-Za-z0-9]+)?", path
    ):
        raise ValueError("Preferred path must be a simple absolute URL path")
    return path


def origin(url):
    p = urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.fragment:
        raise ValueError("Invalid scheme, host or fragment")
    if p.username is not None or p.password is not None:
        raise ValueError("URL credentials")
    host = p.hostname.lower()
    if len(host) > 253 or "." not in host or not all(LABEL_RE.fullmatch(x) for x in host.split(".")):
        raise ValueError("Invalid hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP literal")
    default_port = 443 if p.scheme == "https" else 80
    if p.port is not None and p.port != default_port:
        raise ValueError("Unsupported port")
    return p.scheme, host, default_port


def unsafe_text(value):
    for _ in range(4):
        if any(ord(ch) <= 32 or ord(ch) == 127 for ch in value):
            return True
        if "\\" in value or "$(" in value:
            return True
        value = unquote(value)
    return False


def evaluate_link(home_url, link):
    if not isinstance(link, dict):
        return None, "INVALID_LINK"
    method = link.get("method", "GET")
    if not isinstance(method, str) or method.upper() != "GET":
        return None, "NON_GET"
    href = link.get("href")
    if not isinstance(href, str) or not href:
        return None, "EMPTY_HREF"
    if len(href) > 2048 or unsafe_text(href):
        return None, "UNSAFE_HREF"
    try:
        base_origin = origin(home_url)
        resolved = urljoin(home_url, href)
        target, _fragment = urldefrag(resolved)
        if len(target) > 2048 or unsafe_text(target):
            return None, "UNSAFE_TARGET"
        if origin(target) != base_origin:
            return None, "CROSS_ORIGIN"
        p = urlsplit(target)
        if _auth_destination(p.path, p.query):
            return None, "AUTH_FLOW"
        if _mutation_destination(p.path, p.query):
            return None, "MUTATION_FLOW"
        if _decoded_lower(p.path).endswith(NON_DOCUMENT_SUFFIXES):
            return None, "NON_WML_RESOURCE"
        normalized = urlunsplit((p.scheme, p.hostname.lower(), p.path or "/", p.query, ""))
        home = urlsplit(urldefrag(home_url)[0])
        home_normalized = urlunsplit(
            (home.scheme, home.hostname.lower(), home.path or "/", home.query, "")
        )
        if normalized == home_normalized:
            return None, "SAME_RESOURCE"
        for key, _ in parse_qsl(p.query, keep_blank_values=True, max_num_fields=64):
            if key.lower() in SENSITIVE_KEYS:
                return None, "SENSITIVE_QUERY"
        return normalized, "OK"
    except (ValueError, TypeError, AttributeError):
        return None, "INVALID_URL"


def select_navigation(
    home_url, links, *, capture_status, card_count,
    captured_body_sha256, parsed_body_sha256,
):
    output = {"A_navigation": "PENDING", "target_url": None}
    if (
        capture_status not in WML_STATUSES
        or type(card_count) is not int or card_count < 1
        or not isinstance(captured_body_sha256, str)
        or not SHA256_RE.fullmatch(captured_body_sha256)
        or captured_body_sha256 != parsed_body_sha256
    ):
        return {**output, "status": "HOME_NOT_VERIFIED"}
    try:
        origin(home_url)
    except (TypeError, ValueError, AttributeError):
        return {**output, "status": "INVALID_HOME_URL"}
    if not isinstance(links, list):
        return {**output, "status": "INVALID_LINK_LIST"}
    skipped = []
    for index, link in enumerate(links[:32]):
        target, reason = evaluate_link(home_url, link)
        if target is not None:
            return {
                "status": "READY_FOR_GET",
                "A_navigation": "PENDING",
                "target_url": target,
                "method": "GET",
                "source_link_index": index,
                "skipped": skipped,
            }
        skipped.append({"index": index, "reason": reason})
    return {**output, "status": "NO_SAFE_SECOND_PAGE", "skipped": skipped}


def select_reachable_navigation(
    home_url, cards, *, capture_status, card_count,
    captured_body_sha256, parsed_body_sha256, preferred_path=None,
):
    """BFS across explicit #card links, then select one safe external GET.

    This only creates a request plan. A fragment traversal is not a new HTTP
    response and cannot count as A-navigation by itself.
    """
    from collections import deque
    base = select_navigation(
        home_url, [],
        capture_status=capture_status,
        card_count=card_count,
        captured_body_sha256=captured_body_sha256,
        parsed_body_sha256=parsed_body_sha256,
    )
    if base["status"] != "NO_SAFE_SECOND_PAGE":
        return base
    if preferred_path is not None:
        try:
            validate_preferred_path(preferred_path)
        except ValueError:
            return {**base, "status": "INVALID_PREFERRED_PATH"}
    if not isinstance(cards, list) or not cards or len(cards) > 256:
        return {**base, "status": "INVALID_CARDS"}
    index = {}
    for i, card in enumerate(cards):
        if not isinstance(card, dict) or not isinstance(card.get("links", []), list):
            return {**base, "status": "INVALID_CARDS"}
        identifier = card.get("id")
        if identifier is not None and not isinstance(identifier, str):
            return {**base, "status": "INVALID_CARDS"}
        if identifier:
            if identifier in index:
                return {**base, "status": "DUPLICATE_CARD_ID"}
            index[identifier] = i
    queue = deque([(0, [])])
    seen = {0}
    skipped = []
    while queue:
        card_index, path = queue.popleft()
        card = cards[card_index]
        for link_index, link in enumerate(card.get("links", [])[:32]):
            target, reason = evaluate_link(home_url, link)
            if target is not None and preferred_path is not None:
                if urlsplit(target).path != preferred_path:
                    target, reason = None, "OTHER_PUBLIC_LINK"
            if target is not None:
                return {
                    "status": "READY_FOR_GET",
                    "A_navigation": "PENDING",
                    "target_url": target,
                    "method": "GET",
                    "source_card_index": card_index,
                    "source_card_id": card.get("id"),
                    "source_link_index": link_index,
                    "fragment_path": path,
                    "skipped": skipped[:64],
                }
            # A card-local fragment may make a different card visible.
            # Only a *literal* #id, with a valid GET, may advance BFS.
            href = link.get("href") if isinstance(link, dict) else None
            if (
                reason == "SAME_RESOURCE" and isinstance(href, str)
                and href.startswith("#")
                and re.fullmatch(r"#[A-Za-z_][A-Za-z0-9_.:-]{0,127}", href)
            ):
                child_index = index.get(href[1:])
                if child_index is not None and child_index not in seen:
                    seen.add(child_index)
                    queue.append((child_index, path + [href[1:]]))
            if len(skipped) < 64:
                skipped.append({"card_index": card_index,
                                "link_index": link_index, "reason": reason})
    return {
        **base,
        "status": "PREFERRED_LINK_NOT_FOUND" if preferred_path is not None
                  else "NO_SAFE_SECOND_PAGE",
        "skipped": skipped,
    }
