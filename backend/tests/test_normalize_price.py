"""Price parsing tests."""
import pytest
from decimal import Decimal

from app.services.normalize import parse_price


@pytest.mark.parametrize(
    "text,expected",
    [
        ("$80.00", Decimal("80.00")),
        ("$1,234.50", Decimal("1234.50")),
        ("A$80", Decimal("80")),
        ("$ 60.00", Decimal("60.00")),
        (Decimal("60.00"), Decimal("60.00")),
        (60, Decimal("60.00")),
        # The numeric case (80.0 / 80) is also supported because
        # the brief mentions retailers returning JSON numerics; we
        # handle them via the int/float/Decimal branch.
        (80.0, Decimal("80.00")),
    ],
)
def test_parse_price_happy(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text", [None, "", "free", "n/a", "abc"])
def test_parse_price_no_match(text):
    # We do NOT match bare-digit strings without a currency sign —
    # that would be unsafe for volume strings like "700ml".
    assert parse_price(text) is None