"""Safe, stable user-facing errors for local Agent CLI and MCP clients.

Never echo OSError filenames, untrusted input, remote page text or submitted
form values to the Agent through exception strings.
"""
from __future__ import annotations

MESSAGES = {
    "FileNotFoundError": "Required local file or evidence was not found",
    "PermissionError": "Access to local evidence was denied",
    "FileExistsError": "Destination exists; choose an unused location",
    "IsADirectoryError": "Expected a file, but found a directory",
    "NotADirectoryError": "Expected a directory, but found a file",
    "TimeoutError": "Operation timed out without an automatic retry",
    "KeyError": "Required field was missing from the request or evidence",
    "TypeError": "Invalid input type or evidence structure",
    "ValueError": "Input, permission scope or evidence validation was rejected",
    "UnicodeError": "Text encoding or local evidence is invalid",
    "JSONDecodeError": "Invalid JSON in local evidence or request",
    "OSError": "Local file or network operation failed",
}


def safe_error(exc: BaseException) -> dict[str, str]:
    """Only expose an allowlisted exception class and generic explanation."""
    name = type(exc).__name__
    if name not in MESSAGES:
        # Do not leak arbitrary exception class names from external code.
        name = "OSError" if isinstance(exc, OSError) else "ValueError"
    return {"error": name, "message": MESSAGES[name]}
