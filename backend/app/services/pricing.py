"""Cost estimates for ingredients, recipes and shopping lists.

See data/prices.py for where each price comes from.
"""

import math

from ..data.prices import PRICES, UNKNOWN_PACKAGE_COST, UNKNOWN_USAGE_COST, Price
from ..models import Recipe
from ..schemas import CostLine
from .matching import keyword_pattern, normalize
from .units import convert_food

# Longest names first, so "sweet potato" wins over "potato".
_KEYS_BY_LENGTH = sorted(PRICES, key=len, reverse=True)
# When the units can't be compared (e.g. "2 cups" of something sold by the pound),
# assume a recipe uses this share of the package.
_UNCOMPARABLE_SHARE = 0.25


def lookup_price(name: str) -> Price | None:
    """The price-table entry for an ingredient, or None if it isn't listed."""
    key = normalize(name)
    if key in PRICES:
        return PRICES[key]
    for candidate in _KEYS_BY_LENGTH:
        if keyword_pattern(candidate).search(key):
            return PRICES[candidate]
    return None


def _to_package_unit(price: Price, quantity: float, unit: str) -> float | None:
    return convert_food(quantity, unit, price.unit, price.g_per_cup, price.g_each)


def purchase_cost(name: str, quantity: float | None, unit: str) -> tuple[float, bool]:
    """What it costs to buy enough of an item, in whole packages. Returns (cost, known)."""
    price = lookup_price(name)
    if price is None:
        return UNKNOWN_PACKAGE_COST, False
    packages = 1
    if quantity is not None:
        if quantity <= 0:
            return 0.0, True
        amount = _to_package_unit(price, quantity, unit)
        if amount is not None:
            packages = max(1, math.ceil(amount / price.size - 1e-9))
    return round(packages * price.cost, 2), True


def usage_line(name: str, quantity: float | None, unit: str) -> CostLine:
    """The share of a package one recipe line uses, with where the price came from."""
    price = lookup_price(name)
    if price is None:
        return CostLine(ingredient=name, cost=UNKNOWN_USAGE_COST, priced=False, source="Guess")
    amount = None if quantity is None else _to_package_unit(price, quantity, unit)
    if amount is not None:
        cost = amount / price.size * price.cost
    else:
        # Unknown amount, or units that can't be compared (weight vs volume).
        cost = price.cost * _UNCOMPARABLE_SHARE
    return CostLine(ingredient=name, cost=round(cost, 2), priced=True, source=price.source)


def cost_breakdown(recipe: Recipe) -> list[CostLine]:
    return [usage_line(i.name, i.quantity, i.unit) for i in recipe.ingredients]


def usage_cost(name: str, quantity: float | None, unit: str) -> float:
    return usage_line(name, quantity, unit).cost


def recipe_cost(recipe: Recipe) -> float:
    """Estimated cost of cooking the whole recipe once."""
    return round(sum(line.cost for line in cost_breakdown(recipe)), 2)


def cost_per_serving(recipe: Recipe) -> float:
    return round(recipe_cost(recipe) / max(recipe.servings or 1, 1), 2)
