def add_restriction(client, name, kind="allergy"):
    return client.post("/api/restrictions", json={"name": name, "kind": kind})


def test_restriction_crud(client):
    peanuts = add_restriction(client, "Peanuts").json()
    olives = add_restriction(client, "olives", "dislike").json()
    assert client.get("/api/restrictions").json() == [peanuts, olives]

    assert client.delete(f"/api/restrictions/{peanuts['id']}").status_code == 204
    assert client.get("/api/restrictions").json() == [olives]
    assert client.delete(f"/api/restrictions/{peanuts['id']}").status_code == 404


def test_duplicate_restriction_rejected(client):
    add_restriction(client, "Dairy")
    response = add_restriction(client, "dairy", "dislike")
    assert response.status_code == 409
    assert "already" in response.json()["detail"]


def test_restriction_validation(client):
    assert add_restriction(client, "").status_code == 422
    assert add_restriction(client, "Gluten", "hate").status_code == 422


def test_recipes_report_conflicts_and_can_be_filtered(client, make_recipe):
    make_recipe("Cheese Toast", ingredients=[{"name": "bread"}, {"name": "cheddar cheese"}])
    make_recipe("Fruit Salad", ingredients=[{"name": "apple"}, {"name": "banana"}])
    add_restriction(client, "Dairy")
    add_restriction(client, "banana", "dislike")

    recipes = {r["name"]: r for r in client.get("/api/recipes").json()}
    assert recipes["Cheese Toast"]["conflicts"] == [
        {"restriction": "Dairy", "kind": "allergy", "ingredient": "cheddar cheese"}
    ]
    assert recipes["Fruit Salad"]["conflicts"][0]["kind"] == "dislike"

    assert client.get("/api/recipes", params={"safe_only": True}).json() == []
