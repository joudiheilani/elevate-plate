from .test_plan import WEEK, plan_meal


def add_pantry(client, name, quantity=None, unit=""):
    response = client.post("/api/pantry", json={"name": name, "quantity": quantity, "unit": unit})
    assert response.status_code == 201, response.text
    return response.json()


def shopping_items(client):
    items = client.get("/api/shopping-list", params={"start": WEEK}).json()["items"]
    return {item["name"]: item for item in items}


def test_pantry_crud(client):
    item = add_pantry(client, "Rolled oats", 2, "cup")
    assert client.get("/api/pantry").json() == [item]

    updated = client.put(
        f"/api/pantry/{item['id']}", json={"name": "Rolled oats", "quantity": 1, "unit": "cup"}
    ).json()
    assert updated["quantity"] == 1

    assert client.delete(f"/api/pantry/{item['id']}").status_code == 204
    assert client.get("/api/pantry").json() == []
    assert client.delete(f"/api/pantry/{item['id']}").status_code == 404


def test_adding_same_item_sums_quantities(client):
    add_pantry(client, "milk", 1, "cup")
    merged = add_pantry(client, "Milk", 0.5, "cups")
    assert merged["quantity"] == 1.5
    assert len(client.get("/api/pantry").json()) == 1


def test_shopping_list_subtracts_pantry(client, make_recipe):
    oatmeal = make_recipe(
        "Oatmeal",
        ingredients=[
            {"name": "rolled oats", "quantity": 1, "unit": "cup"},
            {"name": "milk", "quantity": 2, "unit": "cup"},
            {"name": "honey", "quantity": 1, "unit": "tbsp"},
            {"name": "blueberries", "quantity": 0.5, "unit": "cup"},
            {"name": "cinnamon", "quantity": None, "unit": ""},
        ],
    )
    plan_meal(client, "2026-10-13", "breakfast", oatmeal["id"])
    add_pantry(client, "Rolled Oats", 3, "cups")  # covers it
    add_pantry(client, "milk", 0.5, "cup")  # not enough
    add_pantry(client, "honey", 1, "jar")  # different unit
    add_pantry(client, "cinnamon")  # "have some"

    items = shopping_items(client)
    assert (items["rolled oats"]["status"], items["rolled oats"]["to_buy"]) == ("have", 0)
    assert (items["milk"]["status"], items["milk"]["to_buy"]) == ("partial", 1.5)
    assert (items["honey"]["status"], items["honey"]["pantry_unit"]) == ("check", "jar")
    assert (items["blueberries"]["status"], items["blueberries"]["to_buy"]) == ("buy", 0.5)
    assert items["cinnamon"]["status"] == "have"


def test_meal_ideas_rank_by_pantry_and_skip_restricted(client, make_recipe):
    make_recipe("Toast", ingredients=[{"name": "bread"}, {"name": "butter"}])
    make_recipe("Rice Bowl", ingredients=[{"name": "rice"}, {"name": "beans"}, {"name": "salsa"}])
    make_recipe("Fried Rice", ingredients=[{"name": "rice"}, {"name": "egg"}])
    add_pantry(client, "rice")
    add_pantry(client, "eggs")
    client.post("/api/restrictions", json={"name": "Dairy", "kind": "allergy"})

    ideas = client.get("/api/recipes/ideas").json()
    assert [idea["recipe"]["name"] for idea in ideas] == ["Fried Rice", "Rice Bowl"]
    assert ideas[0]["have"] == ["rice", "egg"]
    assert ideas[0]["missing"] == []
    assert ideas[1]["missing"] == ["beans", "salsa"]
