from .test_generator import generate
from .test_plan import WEEK


def mark_out(client, meal_type="dinner", day=WEEK, **fields):
    response = client.put("/api/dining-out", json={"day": day, "meal_type": meal_type, **fields})
    assert response.status_code == 200, response.text
    return response.json()


def test_mark_update_and_clear(client):
    entry = mark_out(client, note="Pizza night", cost=30)
    assert entry["note"] == "Pizza night"
    again = mark_out(client, note="Sushi", cost=45)  # same slot: updated, not duplicated
    assert again["id"] == entry["id"]
    assert client.get(f"/api/dining-out?start={WEEK}").json() == [again]

    assert client.delete(f"/api/dining-out/{entry['id']}").status_code == 204
    assert client.get(f"/api/dining-out?start={WEEK}").json() == []


def test_slot_is_either_a_recipe_or_dining_out(client, make_recipe):
    recipe_id = make_recipe()["id"]
    client.put("/api/plan", json={"day": WEEK, "meal_type": "dinner", "recipe_id": recipe_id})
    mark_out(client)
    assert client.get(f"/api/plan?start={WEEK}").json() == []

    client.put("/api/plan", json={"day": WEEK, "meal_type": "dinner", "recipe_id": recipe_id})
    assert client.get(f"/api/dining-out?start={WEEK}").json() == []
    assert len(client.get(f"/api/plan?start={WEEK}").json()) == 1


def test_other_users_cannot_touch_it(client, sign_up):
    entry = mark_out(client)
    bob = sign_up("bob@example.com")
    assert bob.get(f"/api/dining-out?start={WEEK}").json() == []
    assert bob.delete(f"/api/dining-out/{entry['id']}").status_code == 404


def test_shopping_list_reports_dining_spend(client):
    mark_out(client, cost=30)
    mark_out(client, meal_type="lunch", cost=12.5)
    mark_out(client, meal_type="breakfast")  # no cost given
    shopping = client.get(f"/api/shopping-list?start={WEEK}").json()
    assert shopping["dining_out_total"] == 42.5


def test_generator_skips_dining_out_and_keeps_it_out_of_the_grocery_budget(client):
    mark_out(client, cost=40)
    plan = generate(client, weekly_budget=120)
    slots = {(m["day"], m["meal_type"]) for m in plan["meals"]}
    assert len(plan["meals"]) == 20
    assert (WEEK, "dinner") not in slots
    assert plan["dining_out_total"] == 40
    assert plan["dining_out"][0]["meal_type"] == "dinner"
    assert any("eating out" in note for note in plan["notes"])
    # Eating out is reported but doesn't shrink the grocery budget.
    assert plan["budget"] == 120
    assert plan["within_budget"] == (plan["estimated_total"] <= 120)
    assert any("not part of your grocery budget" in note for note in plan["notes"])


def test_dining_out_slots_kept_in_auto_mode_apply(client):
    mark_out(client)
    plan = generate(client)
    meals = [
        {"day": m["day"], "meal_type": m["meal_type"], "recipe_name": m["recipe"]["name"]}
        for m in plan["meals"]
    ]
    assert client.post("/api/generator/apply", json={"meals": meals}).status_code == 200
    assert len(client.get(f"/api/dining-out?start={WEEK}").json()) == 1
