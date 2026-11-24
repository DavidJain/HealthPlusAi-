"""Personal-data redaction: identifiers go, ordinary questions stay intact."""

from __future__ import annotations

import pytest

from healthplus.application.query_processor import DefaultQueryProcessor
from healthplus.core.privacy import redact_personal_data


@pytest.mark.parametrize(
    ("text", "kind", "placeholder"),
    [
        ("my email is ravi.k@example.com, book me", "email", "[email]"),
        ("call me on 9876543210", "phone number", "[phone number]"),
        ("call me on +91 98765 43210", "phone number", "[phone number]"),
        ("aadhaar 1234 5678 9012 for registration", "Aadhaar number", "[ID number]"),
        ("my PAN is ABCDE1234F", "PAN", "[ID number]"),
        ("card 4111 1111 1111 1111 please", "card number", "[card number]"),
    ],
)
def test_identifiers_are_replaced(text, kind, placeholder):
    result = redact_personal_data(text)
    assert placeholder in result.text
    assert kind in result.removed
    assert result.changed


@pytest.mark.parametrize(
    "text",
    [
        "How much does an MRI brain scan cost?",
        "Is Dr. Ananya Rao in room C-204 on Monday at 10:00 AM?",
        "My father is 65, is there a senior citizen discount of 10%?",
        "Price of the Executive Health Checkup is INR 7,999?",
        "Helpline 1800-000-0000",
    ],
)
def test_ordinary_questions_are_untouched(text):
    result = redact_personal_data(text)
    assert result.text == text
    assert not result.changed


def test_query_processor_redacts_before_the_pipeline():
    cleaned = DefaultQueryProcessor().process("  book for 9876543210  please ")
    assert "9876543210" not in cleaned
    assert "[phone number]" in cleaned
