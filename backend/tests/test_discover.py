import pytest

from backend.app.services import mealdb

PANCAKES = {
    "idMeal": "52854",
    "strMeal": "Pancakes",
    "strCategory": "Dessert",
    "strArea": "American",
    "strMealThumb": "https://www.themealdb.com/images/media/meals/rwuyqx1511383174.jpg",
    "strSource": "https://example.com/pancakes",
    "strInstructions": "Whisk everything.\r\n\r\n\r\nFry in a hot pan.",
    "strIngredient1": "Flour",
    "strMeasure1": "100g ",
    "strIngredient2": "Eggs",
    "strMeasure2": "2 large",
    "strIngredient3": "Milk",
    "strMeasure3": "300ml ",
    "strIngredient4": "Blueberries",
    "strMeasure4": "to serve",
    "strIngredient5": "",
    "strMeasure5": "",
}


@pytest.fixture
def fake_mealdb(monkeypatch):
    """Replace network calls to TheMealDB with canned responses."""
    calls = []

    def fake_fetch(path, params):
        calls.append((path, params))
        if path == "search.php":
            return {"meals": [PANCAKES] if "pancake" in params["s"].lower() else None}
        if path == "lookup.php":
            return {"meals": [PANCAKES] if params["i"] == "52854" else None}
        raise AssertionError(path)

    monkeypatch.setattr(mealdb, "fetch", fake_fetch)
    return calls


@pytest.mark.parametrize(
    ("measure", "expected"),
    [
        ("100g ", (100, "g")),
        ("1 1/2 cups ", (1.5, "cup")),
        ("1/2 tsp", (0.5, "tsp")),
        ("2 tblsp ", (2, "tbsp")),
        ("2 Lbs", (2, "lb")),
        ("1.5kg", (1.5, "kg")),
        ("3 Cloves Crushed", (3, "clove")),
        ("1 tin", (1, "can")),
        ("2 large", (2, "")),
        ("1 chopped", (1, "")),
        ("½ cup", (0.5, "cup")),
        ("to serve", (None, "")),
        ("", (None, "")),
        (None, (None, "")),
    ],
)
def test_parse_measure(measure, expected):
    assert mealdb.parse_measure(measure) == expected


def test_search_returns_priced_previews(client, fake_mealdb):
    results = client.get("/api/discover", params={"q": "pancakes"}).json()
    assert len(results) == 1
    pancakes = results[0]
    assert pancakes["name"] == "Pancakes"
    assert pancakes["mealdb_url"] == "https://www.themealdb.com/meal/52854"
    assert [(i["name"], i["quantity"], i["unit"]) for i in pancakes["ingredients"]] == [
        ("flour", 100, "g"),
        ("eggs", 2, ""),
        ("milk", 300, "ml"),
        ("blueberries", None, ""),
    ]
    assert 0 < pancakes["cost_per_serving"] < 2
    assert pancakes["in_library"] is False


def test_search_flags_conflicts(client, fake_mealdb):
    client.post("/api/restrictions", json={"name": "Dairy", "kind": "allergy"})
    pancakes = client.get("/api/discover", params={"q": "pancakes"}).json()[0]
    assert pancakes["conflicts"][0]["ingredient"] == "milk"


def test_search_validation_and_empty(client, fake_mealdb):
    assert client.get("/api/discover", params={"q": "a"}).status_code == 422
    assert client.get("/api/discover", params={"q": "zzz"}).json() == []


def test_import_saves_recipe_with_credit(client, fake_mealdb):
    response = client.post("/api/discover/52854/import")
    assert response.status_code == 201
    recipe = response.json()
    assert recipe["name"] == "Pancakes"
    assert "From TheMealDB: https://www.themealdb.com/meal/52854" in recipe["description"]
    assert "original recipe: https://example.com/pancakes" in recipe["description"]
    assert recipe["instructions"] == "Whisk everything.\n\nFry in a hot pan."
    assert len(recipe["ingredients"]) == 4

    # Shows as in the library, and can't be imported twice.
    assert client.get("/api/discover", params={"q": "pancakes"}).json()[0]["in_library"]
    assert client.post("/api/discover/52854/import").status_code == 409


def test_import_errors(client, fake_mealdb):
    assert client.post("/api/discover/99999/import").status_code == 404
    assert client.post("/api/discover/abc/import").status_code == 422


def test_upstream_failure_is_a_clear_502(client, monkeypatch):
    def broken(path, params):
        raise mealdb.MealDBError("Couldn't reach TheMealDB right now. Please try again.")

    monkeypatch.setattr(mealdb, "fetch", broken)
    response = client.get("/api/discover", params={"q": "curry"})
    assert response.status_code == 502
    assert "TheMealDB" in response.json()["detail"]
