"""$/L calculation tests — covers the brief's exact example."""
import pytest
from decimal import Decimal

from app.services.normalize import (
    parse_comparable_dol_per_litre,
    price_per_litre,
)


def test_60_per_700ml():
    # brief example: $60 / 0.7L = $85.71/L
    ppl = price_per_litre(Decimal("60.00"), 700)
    assert ppl == Decimal("85.71")


def test_80_per_1000ml():
    assert price_per_litre(Decimal("80.00"), 1000) == Decimal("80.00")


def test_101_per_1136ml():
    # page captured: $101 / 1.136L ~= $88.91/L
    ppl = price_per_litre(Decimal("101"), 1136)
    assert ppl == Decimal("88.91")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("$97.14/ 1L", Decimal("97.14")),
        ("$88.91/ 1L", Decimal("88.91")),
        ("$20.45/ 1L", Decimal("20.45")),
        ("$100.00/ 1L", Decimal("100.00")),
        ("$1.36/ 100ml", Decimal("13.60")),
        ("$2.08/ 100g", None),  # not a volume
    ],
)
def test_parse_comparable_dol_per_litre(text, expected):
    assert parse_comparable_dol_per_litre(text) == expected


@pytest.mark.parametrize(
    "price,volume,expected",
    [
        (None, 700, None),
        (Decimal("60.00"), None, None),
        (Decimal("60.00"), 0, None),
    ],
)
def test_price_per_litre_no_volume(price, volume, expected):
    assert price_per_litre(price, volume) is expected