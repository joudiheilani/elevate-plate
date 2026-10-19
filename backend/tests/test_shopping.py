from backend.app.models import Ingredient, Recipe
from backend.app.services.shopping import aggregate_ingredients

from .test_plan import WEEK, plan_meal


def recipe(name, *ingredients):
    return Recipe(
        name=name,
        ingredients=[Ingredient(name=n, quantity=q, unit=u) for n, q, u in ingredients],
    )


def test_aggregate_sums_matching_name_and_unit():
    items = aggregate_ingredients(
        [
            recipe("Pasta", ("Garlic", 2, "clove"), ("onion", 1, "")),
            recipe("Stir Fry", ("garlic ", 3, "clove"), ("garlic", 1, "tbsp")),
        ]
    )
    summary = [(i.name, i.quantity, i.unit, i.recipes) for i in items]
    assert summary == [
        ("Garlic", 5, "clove", ["Pasta", "Stir Fry"]),
        ("garlic", 1, "tbsp", ["Stir Fry"]),
        ("onion", 1, "", ["Pasta"]),
    ]


def test_aggregate_counts_repeated_recipes_and_handles_missing_quantity():
    oats = recipe("Oats", ("oats", 0.5, "cup"), ("salt", None, "pinch"))
    items = {i.name: i for i in aggregate_ingredients([oats, oats])}
    assert items["oats"].quantity == 1
    assert items["salt"].quantity is None
    assert items["oats"].recipes == ["Oats"]


def test_shopping_list_endpoint(client, make_recipe):
    pasta = make_recipe("Pasta", ingredients=[{"name": "spaghetti", "quantity": 1, "unit": "lb"}])
    plan_meal(client, "2026-10-13", "dinner", pasta["id"])
    plan_meal(client, "2026-10-15", "dinner", pasta["id"])
    plan_meal(client, "2026-10-25", "dinner", pasta["id"])  # next week, excluded

    data = client.get("/api/shopping-list", params={"start": WEEK}).json()
    assert data["start"] == WEEK
    assert data["end"] == "2026-10-18"
    assert data["items"] == [
        {"name": "spaghetti", "quantity": 2, "unit": "lb", "recipes": ["Pasta"]}
    ]


def test_shopping_list_empty_week(client):
    data = client.get("/api/shopping-list", params={"start": WEEK}).json()
    assert data["items"] == []
