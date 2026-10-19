from collections.abc import Iterable

from ..models import Recipe
from ..schemas import ShoppingItem


def aggregate_ingredients(recipes: Iterable[Recipe]) -> list[ShoppingItem]:
    """Combine ingredients across recipes, summing quantities that share a name and unit.

    A recipe that appears more than once (e.g. planned for two dinners) is counted each time.
    """
    totals: dict[tuple[str, str], ShoppingItem] = {}
    for recipe in recipes:
        for ingredient in recipe.ingredients:
            name, unit = ingredient.name.strip(), ingredient.unit.strip()
            key = (name.lower(), unit.lower())
            item = totals.setdefault(
                key, ShoppingItem(name=name, quantity=None, unit=unit, recipes=[])
            )
            if ingredient.quantity is not None:
                item.quantity = round((item.quantity or 0) + ingredient.quantity, 2)
            if recipe.name not in item.recipes:
                item.recipes.append(recipe.name)
    return sorted(totals.values(), key=lambda item: (item.name.lower(), item.unit.lower()))
