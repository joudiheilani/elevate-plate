import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from ..data.prices import STAPLES
from ..models import PantryItem, Recipe
from ..schemas import ShoppingItem
from .matching import normalize
from .pricing import purchase_cost

# Units bought in whole pieces: round 1.5 eggs up to 2.
COUNT_UNITS = {"", "can", "clove", "head", "bunch", "slice"}


@dataclass(frozen=True)
class Line:
    name: str
    quantity: float | None
    unit: str


@dataclass(frozen=True)
class Portion:
    """A recipe's ingredients scaled to the number of people eating it."""

    name: str
    ingredients: tuple[Line, ...]


def portion(recipe: Recipe, people: int) -> Portion:
    factor = people / max(recipe.servings or 1, 1)
    return Portion(
        recipe.name,
        tuple(
            Line(i.name, None if i.quantity is None else i.quantity * factor, i.unit)
            for i in recipe.ingredients
        ),
    )


def staple_items() -> list[PantryItem]:
    """Unsaved pantry entries for basics assumed to be at home (oil, spices...)."""
    return [PantryItem(name=name, quantity=None, unit="") for name in sorted(STAPLES)]


def round_up_counts(items: list[ShoppingItem]) -> list[ShoppingItem]:
    for item in items:
        if item.quantity is not None and normalize(item.unit) in COUNT_UNITS:
            item.quantity = float(math.ceil(item.quantity - 1e-9))
    return items


def price_items(items: list[ShoppingItem]) -> float:
    """Fill in each item's estimated cost (whole packages) and return the total."""
    total = 0.0
    for item in items:
        if item.status == "have":
            item.est_cost, item.price_known = 0.0, True
        else:
            item.est_cost, item.price_known = purchase_cost(item.name, item.to_buy, item.unit)
        total += item.est_cost
    return round(total, 2)


def aggregate_ingredients(recipes: Iterable[Recipe | Portion]) -> list[ShoppingItem]:
    """Combine ingredients across recipes, summing quantities that share a name and unit.

    A recipe that appears more than once (e.g. planned for two dinners) is counted each time.
    """
    totals: dict[tuple[str, str], ShoppingItem] = {}
    for recipe in recipes:
        for ingredient in recipe.ingredients:
            name, unit = ingredient.name.strip(), ingredient.unit.strip()
            key = (normalize(name), normalize(unit))
            item = totals.setdefault(
                key, ShoppingItem(name=name, quantity=None, unit=unit, recipes=[])
            )
            if ingredient.quantity is not None:
                item.quantity = round((item.quantity or 0) + ingredient.quantity, 2)
            if recipe.name not in item.recipes:
                item.recipes.append(recipe.name)
    return sorted(totals.values(), key=lambda item: (item.name.lower(), item.unit.lower()))


def apply_pantry(items: list[ShoppingItem], pantry: Iterable[PantryItem]) -> list[ShoppingItem]:
    """Work out how much of each item still needs buying, given what's in the pantry."""
    by_name: dict[str, list[PantryItem]] = defaultdict(list)
    for pantry_item in pantry:
        by_name[normalize(pantry_item.name)].append(pantry_item)

    for item in items:
        matches = by_name.get(normalize(item.name), [])
        item.to_buy = item.quantity
        if not matches:
            item.status = "buy"
            continue

        same_unit = next((p for p in matches if normalize(p.unit) == normalize(item.unit)), None)
        stocked = same_unit or matches[0]
        item.pantry_quantity, item.pantry_unit = stocked.quantity, stocked.unit

        if stocked.quantity is None or item.quantity is None:
            # "Have some" (no amount recorded) or the recipe needs no specific amount.
            item.status, item.to_buy = "have", 0
        elif same_unit is None:
            item.status = "check"
        else:
            shortfall = round(item.quantity - stocked.quantity, 2)
            item.status, item.to_buy = ("have", 0) if shortfall <= 0 else ("partial", shortfall)
    return items
