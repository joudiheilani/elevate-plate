WEEK = "2026-10-12"  # a Monday


def plan_meal(client, day, meal_type, recipe_id):
    return client.put(
        "/api/plan", json={"day": day, "meal_type": meal_type, "recipe_id": recipe_id}
    )


def test_plan_meal_and_get_week(client, make_recipe):
    recipe = make_recipe("Omelette")
    response = plan_meal(client, "2026-10-13", "breakfast", recipe["id"])
    assert response.status_code == 200
    assert response.json()["recipe"]["name"] == "Omelette"

    week = client.get("/api/plan", params={"start": WEEK}).json()
    assert [(e["day"], e["meal_type"]) for e in week] == [("2026-10-13", "breakfast")]


def test_week_excludes_other_weeks(client, make_recipe):
    recipe = make_recipe()
    plan_meal(client, "2026-10-11", "dinner", recipe["id"])  # day before
    plan_meal(client, "2026-10-18", "dinner", recipe["id"])  # last day of week
    plan_meal(client, "2026-10-19", "dinner", recipe["id"])  # day after

    week = client.get("/api/plan", params={"start": WEEK}).json()
    assert [e["day"] for e in week] == ["2026-10-18"]


def test_planning_same_slot_replaces_recipe(client, make_recipe):
    first = make_recipe("Soup")
    second = make_recipe("Salad")
    plan_meal(client, "2026-10-14", "lunch", first["id"])
    plan_meal(client, "2026-10-14", "lunch", second["id"])

    week = client.get("/api/plan", params={"start": WEEK}).json()
    assert len(week) == 1
    assert week[0]["recipe"]["name"] == "Salad"


def test_clear_meal(client, make_recipe):
    entry = plan_meal(client, "2026-10-14", "dinner", make_recipe()["id"]).json()
    assert client.delete(f"/api/plan/{entry['id']}").status_code == 204
    assert client.get("/api/plan", params={"start": WEEK}).json() == []
    assert client.delete(f"/api/plan/{entry['id']}").status_code == 404


def test_deleting_recipe_removes_it_from_plan(client, make_recipe):
    recipe = make_recipe()
    plan_meal(client, "2026-10-14", "dinner", recipe["id"])
    client.delete(f"/api/recipes/{recipe['id']}")
    assert client.get("/api/plan", params={"start": WEEK}).json() == []


def test_plan_validation(client, make_recipe):
    recipe = make_recipe()
    assert plan_meal(client, "2026-10-14", "dinner", 999).status_code == 404
    assert plan_meal(client, "2026-10-14", "midnight snack", recipe["id"]).status_code == 422
    assert plan_meal(client, "not-a-date", "dinner", recipe["id"]).status_code == 422
