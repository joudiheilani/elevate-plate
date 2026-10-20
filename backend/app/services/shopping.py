from collections import defaultdict
from collections.abc import Iterable

from ..models import PantryItem, Recipe
from ..schemas import ShoppingItem
from .matching import normalize


def aggregate_ingredients(recipes: Iterable[Recipe]) -> list[ShoppingItem]:
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
