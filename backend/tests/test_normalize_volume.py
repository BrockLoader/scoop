"""Volume parsing tests — every shape from the brief plus edge cases."""
import pytest

from app.services.normalize import parse_volume_ml


@pytest.mark.parametrize(
    "text,expected",
    [
        ("700ml", 700),
        ("700 mL", 700),
        ("700 ML", 700),
        ("700mL", 700),
        ("1L", 1000),
        ("1 L", 1000),
        ("1 Litre", 1000),
        ("1 Litre.", 1000),
        ("1.136L", 1136),
        ("1.136 L", 1136),
        ("1136ml", 1136),
        ("1,136 ml", 1136),
        ("70cl", 700),
        ("70 cl", 700),
        ("Bottle 700ml", 700),
        ("JACK DANIELS WHISKEY 700ML:EA", 700),
        ("JACK DANIELS OLD NO.7 TENNESSEE WHISKEY 1136ML:EA", 1136),
    ],
)
def test_parse_volume_ml_happy(text, expected):
    assert parse_volume_ml(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        None,
        "4 pack",
        "no volume here",
        "abc",
    ],
)
def test_parse_volume_ml_no_match(text):
    assert parse_volume_ml(text) is None