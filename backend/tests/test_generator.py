from backend.app.data.catalog import CATALOG_BY_NAME

from .test_plan import WEEK


def generate(client, **overrides):
    payload = {
        "start": WEEK,
        "weekly_budget": 120,
        "people": 2,
        "max_minutes": None,
        "diet": "any",
        "meals": ["breakfast", "lunch", "dinner"],
        "seed": 7,
        **overrides,
    }
    response = client.post("/api/generator", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_generates_full_week_within_budget(client):
    plan = generate(client)
    assert len(plan["meals"]) == 21
    assert plan["within_budget"] is True
    assert plan["estimated_total"] <= 120
    assert plan["estimated_total"] == round(sum(i["est_cost"] for i in plan["groceries"]), 2)
    days = {meal["day"] for meal in plan["meals"]}
    assert len(days) == 7


def test_respects_cooking_time(client):
    plan = generate(client, max_minutes=20)
    assert all(meal["recipe"]["prep_minutes"] <= 20 for meal in plan["meals"])
    assert plan["average_minutes"] <= 20


def test_respects_diet_and_allergies(client):
    client.post("/api/restrictions", json={"name": "Peanuts", "kind": "allergy"})
    plan = generate(client, diet="vegan")
    names = {meal["recipe"]["name"] for meal in plan["meals"]}
    ingredients = {i["name"] for meal in plan["meals"] for i in meal["recipe"]["ingredients"]}
    assert names  # vegan options exist for every meal
    assert "Peanut Butter Banana Toast" not in names
    for animal_product in ("eggs", "milk", "greek yogurt", "cheddar cheese", "honey", "shrimp"):
        assert animal_product not in ingredients


def test_tight_budget_lowers_cost(client):
    roomy = generate(client, weekly_budget=300)
    tight = generate(client, weekly_budget=60)
    assert tight["estimated_total"] < roomy["estimated_total"]


def test_impossible_budget_explains_itself(client):
    plan = generate(client, weekly_budget=10)
    assert plan["within_budget"] is False
    assert any("above your $10.00 budget" in note for note in plan["notes"])


def test_missing_meal_types_are_reported(client):
    plan = generate(client, max_minutes=5, meals=["breakfast", "dinner"])
    assert {meal["meal_type"] for meal in plan["meals"]} == {"breakfast"}
    assert any("No dinner recipes" in note for note in plan["notes"])


def test_same_seed_same_plan_and_new_seed_reshuffles(client):
    first = [m["recipe"]["name"] for m in generate(client, seed=1)["meals"]]
    again = [m["recipe"]["name"] for m in generate(client, seed=1)["meals"]]
    other = [m["recipe"]["name"] for m in generate(client, seed=2)["meals"]]
    assert first == again
    assert first != other


def test_pantry_items_are_not_bought(client):
    client.post("/api/pantry", json={"name": "rice"})
    plan = generate(client, meals=["dinner"])
    rice = [g for g in plan["groceries"] if g["name"] == "rice"]
    if rice:  # only relevant when a rice dish was picked
        assert rice[0]["status"] == "have"
        assert rice[0]["est_cost"] == 0


def test_apply_saves_recipes_and_plan(client, make_recipe):
    make_recipe("Overnight Oats")  # already in the library: reused, not duplicated
    meals = [
        {"day": "2026-10-12", "meal_type": "breakfast", "recipe_name": "Overnight Oats"},
        {"day": "2026-10-12", "meal_type": "dinner", "recipe_name": "Black Bean Tacos"},
        {"day": "2026-10-13", "meal_type": "dinner", "recipe_name": "black bean tacos"},
    ]
    result = client.post("/api/generator/apply", json={"meals": meals}).json()
    assert result == {"recipes_added": 1, "meals_planned": 3}

    library = {r["name"] for r in client.get("/api/recipes").json()}
    assert library == {"Overnight Oats", "Black Bean Tacos"}
    tacos = next(r for r in client.get("/api/recipes").json() if r["name"] == "Black Bean Tacos")
    assert len(tacos["ingredients"]) == len(CATALOG_BY_NAME["black bean tacos"].ingredients)

    week = client.get("/api/plan", params={"start": WEEK}).json()
    assert [(e["day"], e["meal_type"], e["recipe"]["name"]) for e in week] == [
        ("2026-10-12", "breakfast", "Overnight Oats"),
        ("2026-10-12", "dinner", "Black Bean Tacos"),
        ("2026-10-13", "dinner", "Black Bean Tacos"),
    ]


def test_apply_rejects_unknown_recipe(client):
    meals = [{"day": "2026-10-12", "meal_type": "lunch", "recipe_name": "Mystery Stew"}]
    assert client.post("/api/generator/apply", json={"meals": meals}).status_code == 404


def test_applied_plan_costs_the_same_on_the_shopping_list(client):
    """The generator's estimate and the shopping list must agree once a plan is applied."""
    plan = generate(client, people=2, weekly_budget=90)  # profile default is also 2 people
    meals = [
        {"day": m["day"], "meal_type": m["meal_type"], "recipe_name": m["recipe"]["name"]}
        for m in plan["meals"]
    ]
    client.post("/api/generator/apply", json={"meals": meals})

    shopping = client.get("/api/shopping-list", params={"start": WEEK}).json()
    assert shopping["estimated_total"] == plan["estimated_total"]


def test_fill_gaps_keeps_planned_meals_and_fills_the_rest(client, make_recipe):
    mine = make_recipe(
        "Grandma's Lasagna",
        servings=4,
        ingredients=[{"name": "pasta", "quantity": 1, "unit": "lb"}],
        prep_minutes=90,  # longer than the time limit, but it's the user's choice
    )
    for day in ("2026-10-12", "2026-10-14"):
        client.put("/api/plan", json={"day": day, "meal_type": "dinner", "recipe_id": mine["id"]})

    plan = generate(client, fill_gaps=True, max_minutes=30, meals=["lunch", "dinner"])
    dinners = {m["day"]: m for m in plan["meals"] if m["meal_type"] == "dinner"}
    assert len(plan["meals"]) == 14
    assert dinners["2026-10-12"]["recipe"]["name"] == "Grandma's Lasagna"
    assert dinners["2026-10-12"]["locked"] is True
    assert dinners["2026-10-13"]["locked"] is False
    assert sum(m["locked"] for m in plan["meals"]) == 2
    assert all(m["recipe"]["prep_minutes"] <= 30 for m in plan["meals"] if not m["locked"])
    assert any("Kept your 2 planned meals and filled 12 open slots" in n for n in plan["notes"])
    # The user's meals are part of the grocery list and budget.
    assert (
        "Grandma's Lasagna" in next(g for g in plan["groceries"] if g["name"] == "pasta")["recipes"]
    )


def test_fill_gaps_is_off_by_default(client, make_recipe):
    mine = make_recipe("Toast")
    client.put(
        "/api/plan", json={"day": "2026-10-12", "meal_type": "breakfast", "recipe_id": mine["id"]}
    )
    plan = generate(client, meals=["breakfast"])
    assert not any(m["locked"] for m in plan["meals"])
    assert len(plan["meals"]) == 7


def test_fill_gaps_with_full_week(client, make_recipe):
    mine = make_recipe("Toast")
    for offset in range(7):
        client.put(
            "/api/plan",
            json={
                "day": f"2026-10-{12 + offset}",
                "meal_type": "breakfast",
                "recipe_id": mine["id"],
            },
        )
    plan = generate(client, fill_gaps=True, meals=["breakfast"])
    assert all(m["locked"] for m in plan["meals"])
    assert any("already fill every slot" in n for n in plan["notes"])
