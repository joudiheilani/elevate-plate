import pytest

from backend.app.data.catalog import CATALOG
from backend.app.data.prices import DEFAULT_PRICE
from backend.app.services.pricing import cost_per_serving, lookup_price, purchase_cost


@pytest.mark.parametrize(
    ("name", "expected_cost"),
    [
        ("Rolled Oats", 4.50),
        ("coconut milk", 2.50),  # not plain "milk"
        ("sweet potatoes", 1.25),  # not plain "potato"
        ("canned chickpeas", 1.20),
        ("cherry tomatoes", 0.80),
    ],
)
def test_lookup_price_prefers_most_specific_match(name, expected_cost):
    price, known = lookup_price(name)
    assert known
    assert price.cost == expected_cost


def test_unknown_items_use_default_price():
    assert lookup_price("dragon fruit") == (DEFAULT_PRICE, False)


def test_purchase_cost_rounds_up_to_whole_packages():
    assert purchase_cost("rice", 1.5, "cup") == (5.00, True)  # one bag
    assert purchase_cost("rice", 25, "cups") == (10.00, True)  # two bags
    assert purchase_cost("eggs", 13, "") == (7.00, True)  # two dozen
    assert purchase_cost("eggs", 0, "") == (0.0, True)
    assert purchase_cost("milk", 2, "liters") == (4.00, True)  # unit mismatch: one package


def test_every_catalog_ingredient_has_a_price():
    """Keeps the catalog and price table in sync, so budgets aren't silently guessed."""
    unpriced = {
        name for recipe in CATALOG for name, _, _ in recipe.ingredients if not lookup_price(name)[1]
    }
    assert unpriced == set()


def test_cost_per_serving_is_reasonable():
    for recipe in CATALOG:
        assert 0.2 < cost_per_serving(recipe.to_model()) < 15, recipe.name
