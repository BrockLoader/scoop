"""Pure normalization logic — no I/O.

Centralized here so unit tests can hammer it without retailer mocks.
"""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Optional


# ---------- text normalization ----------

# All apostrophe-like characters to a single ASCII apostrophe
_APOST = re.compile(r"[\u2018\u2019\u02BC\u02BB\uFF07\u2032']")
# Anything that's not a letter, digit, or space gets dropped
_NON_ALNUM = re.compile(r"[^a-z0-9\s]+")
_WS = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    """Lowercase, NFKD-normalize, drop apostrophes and punctuation,
    collapse whitespace. Returns '' if input is None/empty after strip."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = _APOST.sub("", s)
    s = s.lower()
    s = _NON_ALNUM.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


# Known brand aliases — extend as new products are encountered.
# Both the spaced form (apostrophe-dropped) and the squished form
# map to the canonical "jack daniels" key.
_BRAND_ALIASES = {
    "jack daniels": "jack daniels",
    "jack daniel s": "jack daniels",
    "jackdaniels": "jack daniels",
    "jackdaniel s": "jack daniels",
}


def normalize_brand(brand: str) -> str:
    """Normalize a brand and apply alias mapping.

    Brand normalization must handle apostrophe-collapsed forms like
    "Jack Daniel's" → "jack daniel s" → "jack daniels". We look up
    the alias both for the spaced form and the squished form.
    """
    n = normalize_text(brand)
    if n in _BRAND_ALIASES:
        return _BRAND_ALIASES[n]
    squished = n.replace(" ", "")
    if squished in _BRAND_ALIASES:
        return _BRAND_ALIASES[squished]
    return n


def normalize_query(query: str) -> str:
    return normalize_text(query)


# ---------- volume parsing ----------

_VOL_PATTERNS = [
    # 1.136L / 1,136ml / 1136 ml / 700mL
    (re.compile(r"(?P<n>\d+(?:[.,]\d+)?)\s*(?P<u>l|litre|litres|liter|liters)\b"), "l"),
    (re.compile(r"(?P<n>\d+(?:[.,]\d+)?)\s*(?P<u>ml|millilitre|millilitres|milliliter|milliliters)\b"), "ml"),
    (re.compile(r"(?P<n>\d+(?:[.,]\d+)?)\s*(?P<u>cl|centilitre|centilitres)\b"), "cl"),
    # Pack sizes: 4 pack, 6pk, 24 pack
    (re.compile(r"(?P<n>\d+)\s*(?:pack|pk|x|ct|count)\b"), "pack"),
]


def parse_volume_ml(text: str) -> Optional[int]:
    """Parse a volume label to millilitres. Returns None if nothing found.

    Examples:
        "700ml" -> 700
        "1 L" -> 1000
        "1.136L" -> 1136
        "1.136 L" -> 1136
        "1 Litre" -> 1000
        "70cl" -> 700
        "4 pack" -> None  (pack is not a volume — caller decides)
    """
    if not text:
        return None
    t = text.lower().replace("\u00a0", " ")

    for pat, unit in _VOL_PATTERNS:
        m = pat.search(t)
        if not m:
            continue
        if unit == "pack":
            continue  # we don't infer volume from pack count
        raw = m.group("n").replace(",", "")
        try:
            n = float(raw)
        except (ValueError, InvalidOperation):
            continue
        if unit == "l":
            return int(round(n * 1000))
        if unit == "ml":
            return int(round(n))
        if unit == "cl":
            return int(round(n * 10))
    return None


# ---------- price parsing ----------

_PRICE_PATTERNS = [
    # $80.00, $1,234.50, A$80
    re.compile(r"\$\s*(?P<n>\d{1,3}(?:[,]\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"),
    re.compile(r"a\$\s*(?P<n>\d{1,3}(?:[,]\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)", re.IGNORECASE),
]


def parse_price(text) -> Optional[Decimal]:
    """Parse a price string like '$80.00' or '80.00' or 80 (number) to Decimal."""
    if text is None:
        return None
    if isinstance(text, (int, float, Decimal)):
        try:
            return Decimal(str(text)).quantize(Decimal("0.01"))
        except InvalidOperation:
            return None
    s = str(text).strip()
    for pat in _PRICE_PATTERNS:
        m = pat.search(s)
        if m:
            raw = m.group("n").replace(",", "")
            try:
                return Decimal(raw).quantize(Decimal("0.01"))
            except InvalidOperation:
                continue
    return None


# ---------- $/L calculation ----------

def price_per_litre(price: Decimal, volume_ml: Optional[int]) -> Optional[Decimal]:
    """Return price-per-litre as Decimal rounded to 2dp, or None if no volume."""
    if price is None or volume_ml is None or volume_ml <= 0:
        return None
    litres = Decimal(volume_ml) / Decimal(1000)
    ppl = price / litres
    return ppl.quantize(Decimal("0.01"))


# ---------- price-per-litre from "comparable" strings ----------

_COMPARABLE_PRICE = re.compile(
    r"\$?\s*(?P<n>\d+(?:\.\d+)?)\s*/\s*(?P<u>1l|100ml|100\s*ml|litre|ml)\b",
    re.IGNORECASE,
)


def parse_comparable_dol_per_litre(text: str) -> Optional[Decimal]:
    """Parse a Coles-style '$85.71/ 1L' string to $/L Decimal.

    Returns None if the string doesn't match the expected shape.
    """
    if not text:
        return None
    m = _COMPARABLE_PRICE.search(text)
    if not m:
        return None
    raw = m.group("n")
    unit = m.group("u").lower().replace(" ", "")
    try:
        n = Decimal(raw)
    except InvalidOperation:
        return None
    if unit in ("1l", "litre"):
        return n.quantize(Decimal("0.01"))
    if unit == "ml":
        return (n * 1000).quantize(Decimal("0.01"))
    if unit == "100ml":
        return (n * 10).quantize(Decimal("0.01"))
    return None