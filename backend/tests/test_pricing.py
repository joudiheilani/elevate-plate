import pytest

from backend.app.data.catalog import CATALOG
from backend.app.data.prices import PRICES, UNKNOWN_PACKAGE_COST, UNKNOWN_USAGE_COST
from backend.app.models import Ingredient, Recipe
from backend.app.services.pricing import (
    cost_breakdown,
    cost_per_serving,
    lookup_price,
    purchase_cost,
)
from backend.app.services.units import canonical_unit, convert, convert_food


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("Rolled Oats", "rolled oat"),
        ("coconut milk", "coconut milk"),  # not plain "milk"
        ("sweet potatoes", "sweet potato"),  # not plain "potato"
        ("canned chickpeas", "chickpea"),
        ("cherry tomatoes", "tomato"),
        ("tortillas", "tortilla"),
    ],
)
def test_lookup_price_prefers_most_specific_match(name, key):
    assert lookup_price(name) is PRICES[key]


def test_unknown_items_have_no_price():
    assert lookup_price("dragon fruit") is None


@pytest.mark.parametrize(
    ("unit", "canonical"),
    [("Tablespoons", "tbsp"), ("tbls", "tbsp"), ("lbs", "lb"), ("grams", "g"), ("pieces", "")],
)
def test_canonical_units(unit, canonical):
    assert canonical_unit(unit) == canonical


def test_convert_within_weight_and_volume_only():
    assert convert(16, "oz", "lb") == pytest.approx(1, rel=1e-4)
    assert convert(3, "tsp", "tbsp") == pytest.approx(1, rel=1e-4)
    assert convert(1, "cup", "lb") is None  # needs a density


def test_convert_food_uses_density_and_piece_weight():
    assert convert_food(1, "cup", "oz", g_per_cup=90) == pytest.approx(90 / 28.3495)
    assert convert_food(4, "", "lb", g_each=113.4) == pytest.approx(1, rel=1e-3)
    assert convert_food(1, "cup", "lb") is None


def test_purchase_cost_rounds_up_to_whole_packages():
    assert purchase_cost("rice", 1.5, "cup") == (2.24, True)  # one 2 lb bag
    assert purchase_cost("rice", 3, "lb") == (4.48, True)  # two bags
    assert purchase_cost("eggs", 13, "") == (4.54, True)  # two dozen
    assert purchase_cost("eggs", 0, "") == (0.0, True)
    assert purchase_cost("ground beef", 500, "g") == (13.58, True)  # 1.1 lb -> two 1 lb packs


def test_unknown_items_are_a_flat_guess_not_multiplied_by_quantity():
    assert purchase_cost("dragon fruit", 8, "") == (UNKNOWN_PACKAGE_COST, False)
    line = cost_breakdown(_recipe(("dragon fruit", 8, "")))[0]
    assert (line.cost, line.priced, line.source) == (UNKNOWN_USAGE_COST, False, "Guess")


def test_breakfast_burrito_is_priced_sensibly():
    """Regression: '8 tater tots' used to count as 8 unknown packages ($32/serving)."""
    burrito = _recipe(
        ("eggs", 2, ""),
        ("tater tots", 8, ""),
        ("cheese slice", 1, ""),
        ("avocado", 1, ""),
        ("tortilla", 1, ""),
        servings=1,
    )
    assert 2 < cost_per_serving(burrito) < 5


def test_breakdown_reports_sources():
    lines = cost_breakdown(_recipe(("eggs", 2, ""), ("tofu", 7, "oz")))
    assert lines[0].source.startswith("BLS average price")
    assert lines[1].source == "Estimate"
    assert lines[1].cost == 1.25  # half a 14 oz block


def test_every_catalog_ingredient_has_a_price():
    """Keeps the catalog and price table in sync, so budgets aren't silently guessed."""
    unpriced = {
        name for recipe in CATALOG for name, _, _ in recipe.ingredients if not lookup_price(name)
    }
    assert unpriced == set()


def test_catalog_costs_per_serving_are_reasonable():
    for recipe in CATALOG:
        assert 0.3 < cost_per_serving(recipe.to_model()) < 8, recipe.name


def _recipe(*ingredients, servings=2):
    return Recipe(
        name="Test",
        servings=servings,
        ingredients=[Ingredient(name=n, quantity=q, unit=u) for n, q, u in ingredients],
    )
