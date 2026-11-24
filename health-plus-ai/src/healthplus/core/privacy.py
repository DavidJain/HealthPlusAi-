"""Personal-data redaction for user questions.

Questions are sent to a third-party LLM provider (free OpenRouter models may
log prompts) and kept in conversation memory, so personal identifiers are
replaced with placeholders BEFORE a question goes anywhere. The assistant
never needs them: it answers from hospital documents, not patient records.

Patterns are deliberately conservative (whole tokens with clear shapes) so
ordinary questions — prices, room numbers like C-204, times, ages — pass
through untouched.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# Order matters: more specific shapes first, so e.g. a card number is not
# half-consumed by the phone pattern.
_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "email",
        "[email]",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "card number",
        "[card number]",
        # 13-19 digits, optionally grouped by spaces or dashes.
        re.compile(r"\b(?:\d[ -]?){12,18}\d\b"),
    ),
    (
        "Aadhaar number",
        "[ID number]",
        # 12 digits, commonly written 4-4-4.
        re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
    ),
    (
        "PAN",
        "[ID number]",
        re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    ),
    (
        "phone number",
        "[phone number]",
        # Indian mobiles (optionally +91 / 0 prefix) and other 10-digit numbers.
        re.compile(r"(?<![\w+])(?:\+?91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}\b"),
    ),
]


class RedactionResult(NamedTuple):
    text: str
    removed: list[str]  # human-readable kinds of data removed, deduplicated

    @property
    def changed(self) -> bool:
        return bool(self.removed)


def redact_personal_data(text: str) -> RedactionResult:
    """Replace personal identifiers in `text` with neutral placeholders."""
    removed: list[str] = []
    for kind, placeholder, pattern in _PATTERNS:
        text, count = pattern.subn(placeholder, text)
        if count and kind not in removed:
            removed.append(kind)
    return RedactionResult(text=text, removed=removed)
