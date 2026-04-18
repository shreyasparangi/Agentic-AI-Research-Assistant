"""
Progress Streaming Utilities
============================
Shared helpers for emitting clean, UI-safe progress messages from LangGraph nodes.
"""

import re
from typing import Any

ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
EMOJI_SYMBOL_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\u2600-\u27BF"
    "\u200D"
    "\uFE0F"
    "]+",
    flags=re.UNICODE,
)
NON_ASCII_RE = re.compile(r"[^\x09\x0A\x0D\x20-\x7E]")
CONTROL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]")
WHITESPACE_RE = re.compile(r"[ \t]+")


def sanitize_status(message: str) -> str:
    """
    Strip terminal color codes, emojis, Unicode symbols, and control characters.
    Returns clean ASCII text suitable for enterprise UI progress messages.
    """
    cleaned = ANSI_ESCAPE_RE.sub("", str(message))
    cleaned = EMOJI_SYMBOL_RE.sub("", cleaned)
    cleaned = CONTROL_RE.sub("", cleaned)
    cleaned = NON_ASCII_RE.sub("", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def emit_progress(state: dict[str, Any], message: str) -> None:
    """Push a sanitized progress message into the active stream queue, if present."""
    progress_queue = state.get("progress_queue")
    if progress_queue is None:
        return

    cleaned = sanitize_status(message)
    if cleaned:
        progress_queue.put_nowait(cleaned)
