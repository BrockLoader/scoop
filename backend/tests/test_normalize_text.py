"""Product name normalization tests — apostrophe variants, fuzzy cases."""
import pytest

from app.services.normalize import normalize_text, normalize_brand, normalize_query


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Jack Daniel's", "jack daniels"),
        ("Jack Daniels", "jack daniels"),
        ("Jack Daniel\u2019s", "jack daniels"),  # curly apostrophe
        ("Jack Daniel\u2018s", "jack daniels"),  # single curly
        ("jack daniels tennessee whiskey", "jack daniels tennessee whiskey"),
        ("  JACK   DANIELS  ", "jack daniels"),
        ("Jack Daniel's Tennessee Whiskey", "jack daniels tennessee whiskey"),
        # The product name collapses "Daniel's" to "daniels" because the
        # apostrophe is dropped without inserting a placeholder. Brand
        # aliasing is applied separately via `normalize_brand()`.
        ("Jack Daniel's Old No. 7", "jack daniels old no 7"),
    ],
)
def test_normalize_text(raw, expected):
    assert normalize_text(raw) == expected


def test_brand_alias_round_trip():
    a = normalize_brand("Jack Daniel's")
    b = normalize_brand("Jack Daniels")
    assert a == "jack daniels"
    assert b == a


def test_normalize_query_empty():
    assert normalize_query("") == ""
    assert normalize_query(None) == ""