def test_profile_defaults_and_update(client):
    profile = client.get("/api/profile").json()
    assert profile == {
        "weekly_budget": 75,
        "people": 2,
        "max_minutes": 30,
        "diet": "any",
        "meals": ["breakfast", "lunch", "dinner"],
        "mode": "auto",
        "assume_staples": True,
        "macro_goals": {"calories": None, "protein_g": None, "carbs_g": None, "fat_g": None},
    }

    updated = {
        **profile,
        "weekly_budget": 50,
        "max_minutes": None,
        "diet": "vegetarian",
        "macro_goals": {"calories": 2000, "protein_g": 120, "carbs_g": None, "fat_g": None},
    }
    assert client.put("/api/profile", json=updated).json() == updated
    assert client.get("/api/profile").json() == updated


def test_profile_validation(client):
    profile = client.get("/api/profile").json()
    assert client.put("/api/profile", json={**profile, "meals": []}).status_code == 422
    assert client.put("/api/profile", json={**profile, "diet": "keto"}).status_code == 422
    assert client.put("/api/profile", json={**profile, "mode": "hybrid"}).status_code == 200
    assert client.put("/api/profile", json={**profile, "mode": "chaos"}).status_code == 422
    assert client.put("/api/profile", json={**profile, "people": 0}).status_code == 422


def test_diet_flags_recipes_and_costs_are_reported(client, make_recipe):
    make_recipe("Burger", ingredients=[{"name": "ground beef", "quantity": 1, "unit": "lb"}])
    profile = client.get("/api/profile").json()
    client.put("/api/profile", json={**profile, "diet": "vegetarian"})

    burger = client.get("/api/recipes").json()[0]
    assert burger["conflicts"] == [
        {"restriction": "Meat", "kind": "diet", "ingredient": "ground beef"}
    ]
    assert burger["cost_per_serving"] == 3.4  # BLS $6.79/lb ground beef, serves 2
