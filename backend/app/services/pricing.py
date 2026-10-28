"""Cost estimates for ingredients, recipes and shopping lists."""

import math

from ..data.prices import DEFAULT_PRICE, PRICES, Price
from ..models import Recipe
from .matching import keyword_pattern, normalize

# Longest names first, so "sweet potato" wins over "potato".
_KEYS_BY_LENGTH = sorted(PRICES, key=len, reverse=True)


def lookup_price(name: str) -> tuple[Price, bool]:
    """Return (price, known). Unknown ingredients get a default estimate."""
    key = normalize(name)
    if key in PRICES:
        return PRICES[key], True
    for candidate in _KEYS_BY_LENGTH:
        if keyword_pattern(candidate).search(key):
            return PRICES[candidate], True
    return DEFAULT_PRICE, False


def _same_unit(price: Price, unit: str) -> bool:
    return normalize(price.unit) == normalize(unit)


def purchase_cost(name: str, quantity: float | None, unit: str) -> tuple[float, bool]:
    """What it costs to buy enough of an item, in whole packages. Returns (cost, known)."""
    price, known = lookup_price(name)
    packages = 1
    if quantity is not None and _same_unit(price, unit):
        if quantity <= 0:
            return 0.0, known
        packages = max(1, math.ceil(quantity / price.size - 1e-9))
    return round(packages * price.cost, 2), known


def usage_cost(name: str, quantity: float | None, unit: str) -> float:
    """The share of a package a recipe uses up. Used to compare recipes fairly."""
    price, _ = lookup_price(name)
    if quantity is not None and _same_unit(price, unit):
        return quantity / price.size * price.cost
    # Unknown amount or unit: assume a quarter of a package.
    return price.cost * 0.25


def recipe_cost(recipe: Recipe) -> float:
    """Estimated cost of cooking the whole recipe once."""
    return round(sum(usage_cost(i.name, i.quantity, i.unit) for i in recipe.ingredients), 2)


def cost_per_serving(recipe: Recipe) -> float:
    return round(recipe_cost(recipe) / max(recipe.servings or 1, 1), 2)
