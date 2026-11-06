import pytest

from backend.app.models import Ingredient, Recipe
from backend.app.services.nutrition import estimate, lookup_food, recipe_nutrition

from .test_plan import WEEK


def recipe(*ingredients, servings=1, **macros):
    return Recipe(
        name="Test",
        servings=servings,
        ingredients=[Ingredient(name=n, quantity=q, unit=u) for n, q, u in ingredients],
        **macros,
    )


def test_estimates_from_ingredients_per_serving():
    # 2 eggs (100 g) = 143 kcal, 12.6 g protein; 1 tbsp olive oil (~13.5 g) = ~120 kcal.
    n = estimate(recipe(("eggs", 2, ""), ("olive oil", 1, "tbsp"), servings=1))
    assert n.calories == pytest.approx(143 + 119.5, abs=1)
    assert n.protein_g == pytest.approx(12.6, abs=0.1)
    assert n.fat_g == pytest.approx(9.5 + 13.5, abs=0.2)
    assert n.source == "estimated"
    assert n.missing == []

    halved = estimate(recipe(("eggs", 2, ""), ("olive oil", 1, "tbsp"), servings=2))
    assert halved.calories == pytest.approx(n.calories / 2, abs=1)


def test_converts_weights_counts_and_cans():
    pound = estimate(recipe(("chicken breast", 1, "lb")))
    assert pound.protein_g == pytest.approx(22.5 * 4.536, abs=0.2)
    can = estimate(recipe(("black beans", 1, "can")))
    assert can.calories == pytest.approx(132 * 2.55, abs=1)


def test_spices_are_negligible_and_unknowns_are_listed():
    n = estimate(recipe(("salt", 1, "tsp"), ("garlic powder", 1, "tsp"), ("dragon fruit", 1, "")))
    assert n.calories == 0
    assert n.missing == ["dragon fruit"]
    # Unmeasured amounts can't be estimated either.
    assert estimate(recipe(("cheddar cheese", None, ""))).missing == ["cheddar cheese"]


def test_longest_name_wins():
    assert lookup_food("peanut butter").fat == 50
    assert lookup_food("sweet potatoes").kcal == 86
    assert lookup_food("chopped red onion").kcal == 40


def test_entered_macros_win_and_blanks_are_estimated():
    r = recipe(("eggs", 2, ""), calories=500, protein_g=30)
    n = recipe_nutrition(r)
    assert n.source == "entered"
    assert (n.calories, n.protein_g) == (500, 30)
    assert n.fat_g == pytest.approx(9.5, abs=0.1)  # left blank, so estimated


def test_recipe_api_returns_and_saves_macros(make_recipe, client):
    estimated = make_recipe("Eggs", [{"name": "eggs", "quantity": 4, "unit": ""}])
    assert estimated["nutrition"]["source"] == "estimated"
    assert estimated["nutrition"]["calories"] == pytest.approx(143, abs=1)  # 2 servings
    assert estimated["calories"] is None

    mine = make_recipe("Takeout Bowl", [], calories=650, protein_g=40, carbs_g=70, fat_g=20)
    assert mine["nutrition"] == {
        "calories": 650,
        "protein_g": 40,
        "carbs_g": 70,
        "fat_g": 20,
        "source": "entered",
        "note": "Entered by you",
        "missing": [],
    }

    # Clearing the numbers goes back to the estimate.
    payload = {"name": "Takeout Bowl", "servings": 2, "ingredients": [], "calories": None}
    updated = client.put(f"/api/recipes/{mine['id']}", json=payload).json()
    assert updated["calories"] is None
    assert updated["nutrition"]["source"] == "estimated"

    bad = client.post("/api/recipes", json={"name": "X", "calories": -5})
    assert bad.status_code == 422


def test_plan_entries_include_macros(make_recipe, client):
    recipe_id = make_recipe("Eggs", [{"name": "eggs", "quantity": 4, "unit": ""}])["id"]
    client.put("/api/plan", json={"day": WEEK, "meal_type": "breakfast", "recipe_id": recipe_id})
    plan = client.get(f"/api/plan?start={WEEK}").json()
    assert plan[0]["recipe"]["nutrition"]["calories"] == pytest.approx(143, abs=1)


def test_generated_meals_include_macros(client):
    from .test_generator import generate

    plan = generate(client)
    assert all(meal["recipe"]["nutrition"]["calories"] > 0 for meal in plan["meals"])
    daily = plan["daily_nutrition"]
    total = sum(meal["recipe"]["nutrition"]["calories"] for meal in plan["meals"])
    assert daily["calories"] == pytest.approx(total / 7, abs=1)


def _avg_error(plan, goal_name):
    target = plan["daily_target"][goal_name]
    return abs(plan["daily_nutrition"][goal_name] - target) / target


def test_macro_goals_steer_the_plan(client):
    from .test_generator import generate

    budget = {"weekly_budget": 400, "max_minutes": None}
    high = generate(client, macro_goals={"calories": 2600, "protein_g": 150}, **budget)
    low = generate(client, macro_goals={"calories": 1400, "protein_g": 60}, **budget)
    assert high["daily_target"]["calories"] == 2600  # all three meals at home
    assert high["daily_nutrition"]["calories"] > low["daily_nutrition"]["calories"] + 400
    assert high["daily_nutrition"]["protein_g"] > low["daily_nutrition"]["protein_g"] + 30
    for plan in (high, low):
        assert _avg_error(plan, "calories") < 0.2


def test_macro_target_covers_only_meals_at_home(client):
    from .test_dining_out import mark_out
    from .test_generator import generate

    mark_out(client, meal_type="dinner")
    plan = generate(client, meals=["lunch", "dinner"], macro_goals={"calories": 2000})
    # Breakfast isn't planned (25%) and one of 7 dinners is out (40% / 7).
    assert plan["daily_target"]["calories"] == round(2000 * (0.75 - 0.4 / 7))


def test_no_goals_means_no_target(client):
    from .test_generator import generate

    plan = generate(client)
    assert plan["daily_target"] is None


def test_goal_validation(client):
    from .test_generator import WEEK

    response = client.post(
        "/api/generator",
        json={
            "start": WEEK,
            "weekly_budget": 100,
            "meals": ["dinner"],
            "macro_goals": {"calories": 50},
        },
    )
    assert response.status_code == 422


def test_portions_are_saved_and_bought_for(client):
    from .test_generator import generate

    plan = generate(client, weekly_budget=400, macro_goals={"calories": 2800})
    big = [m for m in plan["meals"] if m["portions"] > 1]
    assert big, "a 2800 kcal goal needs some bigger portions"
    meal = big[0]
    assert meal["nutrition"]["calories"] == pytest.approx(
        meal["recipe"]["nutrition"]["calories"] * meal["portions"], abs=1
    )

    body = {
        "meals": [
            {
                "day": meal["day"],
                "meal_type": meal["meal_type"],
                "recipe_name": meal["recipe"]["name"],
                "portions": meal["portions"],
            }
        ]
    }
    assert client.post("/api/generator/apply", json=body).status_code == 200
    entry = client.get(f"/api/plan?start={WEEK}").json()[0]
    assert entry["portions"] == meal["portions"]

    # The shopping list buys for the bigger portion.
    single = {**body["meals"][0], "portions": 1}
    first = client.get(f"/api/shopping-list?start={WEEK}").json()["items"]
    client.post("/api/generator/apply", json={"meals": [single]})
    second = client.get(f"/api/shopping-list?start={WEEK}").json()["items"]
    amounts = {i["name"]: i["quantity"] for i in second if i["quantity"]}
    assert any(i["quantity"] > amounts.get(i["name"], 0) for i in first if i["quantity"])

    # Picking a recipe by hand resets it to one serving.
    recipe_id = entry["recipe"]["id"]
    client.put(
        "/api/plan",
        json={"day": meal["day"], "meal_type": meal["meal_type"], "recipe_id": recipe_id},
    )
    assert client.get(f"/api/plan?start={WEEK}").json()[0]["portions"] == 1
