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
        {
            "name": "spaghetti",
            "quantity": 2,
            "unit": "lb",
            "recipes": ["Pasta"],
            "status": "buy",
            "to_buy": 2,
            "pantry_quantity": None,
            "pantry_unit": None,
            "source": "plan",
            "custom_id": None,
            "est_cost": 3.0,  # two 1 lb boxes at $1.50
            "price_known": True,
        }
    ]
    assert data["estimated_total"] == 3.0
    assert data["budget"] == 75  # default weekly budget


def test_custom_groceries_join_the_shopping_list(client):
    milk = client.post(
        "/api/groceries", json={"name": "oat milk", "quantity": 1, "unit": "carton", "price": 4.25}
    ).json()
    client.post("/api/groceries", json={"name": "dragon fruit"})  # no price, unknown item

    data = client.get("/api/shopping-list", params={"start": WEEK}).json()
    items = {item["name"]: item for item in data["items"]}
    assert items["oat milk"]["source"] == "custom"
    assert items["oat milk"]["custom_id"] == milk["id"]
    assert items["oat milk"]["est_cost"] == 4.25
    assert items["dragon fruit"]["price_known"] is False  # default estimate used
    assert data["estimated_total"] == 4.25 + items["dragon fruit"]["est_cost"]

    assert client.delete(f"/api/groceries/{milk['id']}").status_code == 204
    assert client.delete(f"/api/groceries/{milk['id']}").status_code == 404
    assert len(client.get("/api/groceries").json()) == 1


def test_shopping_list_empty_week(client):
    data = client.get("/api/shopping-list", params={"start": WEEK}).json()
    assert data["items"] == []


def test_shopping_list_scales_to_household_and_skips_staples(client, make_recipe):
    soup = make_recipe(
        "Soup",
        servings=4,
        ingredients=[
            {"name": "lentils", "quantity": 2, "unit": "cup"},
            {"name": "carrots", "quantity": 3, "unit": ""},
            {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
        ],
    )
    plan_meal(client, "2026-10-13", "dinner", soup["id"])  # profile default: 2 people

    def items():
        data = client.get("/api/shopping-list", params={"start": WEEK}).json()
        return {item["name"]: item for item in data["items"]}

    assert items()["lentils"]["quantity"] == 1  # half the recipe
    assert items()["carrots"]["quantity"] == 2  # 1.5 carrots, rounded up to whole ones
    assert items()["olive oil"]["status"] == "have"  # a basic, assumed at home

    profile = client.get("/api/profile").json()
    client.put("/api/profile", json={**profile, "people": 4, "assume_staples": False})
    assert items()["lentils"]["quantity"] == 2
    assert items()["olive oil"]["status"] == "buy"
