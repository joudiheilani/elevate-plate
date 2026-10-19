def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_create_and_get_recipe(client, make_recipe):
    created = make_recipe(
        "  Tacos  ",
        ingredients=[
            {"name": "tortillas", "quantity": 8, "unit": ""},
            {"name": "ground beef", "quantity": 1, "unit": "lb"},
        ],
        prep_minutes=20,
    )
    assert created["name"] == "Tacos"  # whitespace is stripped
    assert [i["name"] for i in created["ingredients"]] == ["tortillas", "ground beef"]

    fetched = client.get(f"/api/recipes/{created['id']}").json()
    assert fetched == created


def test_list_recipes_sorted_and_searchable(client, make_recipe):
    make_recipe("Waffles")
    make_recipe("Apple Pie")
    make_recipe("Pineapple Salsa")

    names = [r["name"] for r in client.get("/api/recipes").json()]
    assert names == ["Apple Pie", "Pineapple Salsa", "Waffles"]

    matches = [r["name"] for r in client.get("/api/recipes", params={"q": "apple"}).json()]
    assert matches == ["Apple Pie", "Pineapple Salsa"]


def test_update_recipe_replaces_ingredients(client, make_recipe):
    recipe = make_recipe()
    response = client.put(
        f"/api/recipes/{recipe['id']}",
        json={
            "name": "Fluffy Pancakes",
            "servings": 4,
            "ingredients": [{"name": "eggs", "quantity": 2}],
        },
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Fluffy Pancakes"
    assert updated["servings"] == 4
    assert [(i["name"], i["quantity"]) for i in updated["ingredients"]] == [("eggs", 2)]


def test_delete_recipe(client, make_recipe):
    recipe = make_recipe()
    assert client.delete(f"/api/recipes/{recipe['id']}").status_code == 204
    assert client.get(f"/api/recipes/{recipe['id']}").status_code == 404


def test_missing_recipe_returns_404(client):
    assert client.get("/api/recipes/999").status_code == 404
    assert client.put("/api/recipes/999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/recipes/999").status_code == 404


def test_recipe_validation(client):
    assert client.post("/api/recipes", json={"name": ""}).status_code == 422
    assert client.post("/api/recipes", json={"name": "x", "servings": 0}).status_code == 422
    bad_ingredient = {"name": "x", "ingredients": [{"name": "salt", "quantity": -1}]}
    assert client.post("/api/recipes", json=bad_ingredient).status_code == 422
