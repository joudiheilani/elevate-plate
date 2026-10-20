import pytest

from backend.app.models import FoodRestriction, Ingredient, Recipe
from backend.app.services.matching import find_conflicts, normalize


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Rolled  Oats", "rolled oat"),
        ("tomatoes", "tomato"),
        ("Blueberries", "blueberry"),
        ("glass", "glass"),
        ("hummus", "hummus"),
        ("cups", "cup"),
        ("", ""),
    ],
)
def test_normalize(text, expected):
    assert normalize(text) == expected


def recipe_with(*ingredient_names):
    return Recipe(name="Test", ingredients=[Ingredient(name=n, unit="") for n in ingredient_names])


def conflicts_for(recipe, *restrictions):
    rules = [FoodRestriction(name=name, kind=kind) for name, kind in restrictions]
    return [(c.restriction, c.ingredient) for c in find_conflicts(recipe, rules)]


def test_group_matches_member_ingredients():
    recipe = recipe_with("whole milk", "parmesan cheese", "rolled oats")
    assert conflicts_for(recipe, ("Dairy", "allergy")) == [
        ("Dairy", "whole milk"),
        ("Dairy", "parmesan cheese"),
    ]


def test_group_exceptions_are_not_flagged():
    recipe = recipe_with("peanut butter", "coconut milk")
    assert conflicts_for(recipe, ("dairy", "allergy")) == []
    assert conflicts_for(recipe, ("peanuts", "allergy")) == [("peanuts", "peanut butter")]


def test_custom_term_matches_plurals_but_not_partial_words():
    recipe = recipe_with("mushrooms", "eggplant", "2 eggs")
    assert conflicts_for(recipe, ("Mushroom", "dislike")) == [("Mushroom", "mushrooms")]
    assert conflicts_for(recipe, ("Eggs", "allergy")) == [("Eggs", "2 eggs")]


def test_tree_nuts_do_not_match_coconut_or_nutmeg():
    recipe = recipe_with("coconut flakes", "nutmeg", "walnuts")
    assert conflicts_for(recipe, ("Nuts", "allergy")) == [("Nuts", "walnuts")]
