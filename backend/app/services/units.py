"""Unit normalisation and conversion for recipe quantities.

Weights convert to grams and volumes to millilitres, so "200 g" of beef can be priced
against a "per lb" package. Weight and volume can't be converted into each other without
knowing the food's density, so those comparisons return None and callers fall back to
a rough estimate. Count-like units (pieces, cloves, slices, cans...) only match
themselves.
"""

from .matching import normalize

WEIGHT_GRAMS = {"g": 1.0, "kg": 1000.0, "oz": 28.3495, "lb": 453.592}
VOLUME_ML = {
    "ml": 1.0,
    "l": 1000.0,
    "tsp": 4.92892,
    "tbsp": 14.7868,
    "fl oz": 29.5735,
    "cup": 236.588,
    "pint": 473.176,
    "quart": 946.353,
    "gallon": 3785.41,
}

ALIASES = {
    # weight
    "gram": "g",
    "grams": "g",
    "gr": "g",
    "kilogram": "kg",
    "kilo": "kg",
    "kgs": "kg",
    "ounce": "oz",
    "ounces": "oz",
    "pound": "lb",
    "pounds": "lb",
    "lbs": "lb",
    # volume
    "millilitre": "ml",
    "milliliter": "ml",
    "litre": "l",
    "liter": "l",
    "ltr": "l",
    "teaspoon": "tsp",
    "tsps": "tsp",
    "tablespoon": "tbsp",
    "tbs": "tbsp",
    "tbl": "tbsp",
    "tbls": "tbsp",
    "tblsp": "tbsp",
    "tbsps": "tbsp",
    "tb": "tbsp",
    "cups": "cup",
    "c": "cup",
    "floz": "fl oz",
    "fluid ounce": "fl oz",
    "pt": "pint",
    "qt": "quart",
    "gal": "gallon",
    # counts
    "piece": "",
    "pieces": "",
    "pc": "",
    "pcs": "",
    "each": "",
    "whole": "",
    "large": "",
    "medium": "",
    "small": "",
    "item": "",
}


def canonical_unit(unit: str) -> str:
    """'Tablespoons' -> 'tbsp', 'lbs' -> 'lb', 'pieces' -> '' (a count)."""
    text = " ".join(unit.lower().replace(".", "").split())
    if text in ALIASES:
        return ALIASES[text]
    if text in WEIGHT_GRAMS or text in VOLUME_ML:
        return text
    single = normalize(text)
    return ALIASES.get(single, single)


def convert(quantity: float, from_unit: str, to_unit: str) -> float | None:
    """Convert between compatible units, or None if they measure different things."""
    a, b = canonical_unit(from_unit), canonical_unit(to_unit)
    if a == b:
        return quantity
    for table in (WEIGHT_GRAMS, VOLUME_ML):
        if a in table and b in table:
            return quantity * table[a] / table[b]
    return None


def _dimension(unit: str) -> str | None:
    if unit in WEIGHT_GRAMS:
        return "weight"
    if unit in VOLUME_ML:
        return "volume"
    if unit == "":
        return "count"
    return None


def convert_food(
    quantity: float,
    from_unit: str,
    to_unit: str,
    g_per_cup: float | None = None,
    g_each: float | None = None,
) -> float | None:
    """Like convert(), but can cross weight/volume/count using a food's density or
    piece weight, e.g. 1 cup of oats (90 g/cup) into ounces, or 3 carrots into pounds.
    """
    direct = convert(quantity, from_unit, to_unit)
    if direct is not None:
        return direct
    a, b = canonical_unit(from_unit), canonical_unit(to_unit)
    dim_a, dim_b = _dimension(a), _dimension(b)

    # Express the amount in grams, if we can.
    if dim_a == "weight":
        grams = quantity * WEIGHT_GRAMS[a]
    elif dim_a == "volume" and g_per_cup:
        grams = quantity * VOLUME_ML[a] / VOLUME_ML["cup"] * g_per_cup
    elif dim_a == "count" and g_each:
        grams = quantity * g_each
    else:
        return None

    # Then grams into the target unit.
    if dim_b == "weight":
        return grams / WEIGHT_GRAMS[b]
    if dim_b == "volume" and g_per_cup:
        return grams / g_per_cup * VOLUME_ML["cup"] / VOLUME_ML[b]
    if dim_b == "count" and g_each:
        return grams / g_each
    return None
