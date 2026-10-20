"""Matching ingredient names against the pantry and against allergies/dislikes."""

import re
from collections.abc import Iterable
from functools import lru_cache

from ..models import FoodRestriction, Recipe
from ..schemas import Conflict

# Allergy/diet groups expand to the ingredients they usually cover, so "Dairy" also
# catches "parmesan" and "greek yogurt". Any other term matches only itself.
_TREE_NUTS = (
    "almond",
    "walnut",
    "cashew",
    "pecan",
    "pistachio",
    "hazelnut",
    "macadamia",
    "pine nut",
    "nut",
)
FOOD_GROUPS: dict[str, tuple[str, ...]] = {
    "dairy": (
        "milk",
        "cheese",
        "butter",
        "cream",
        "yogurt",
        "yoghurt",
        "parmesan",
        "mozzarella",
        "cheddar",
        "feta",
        "ricotta",
        "ghee",
        "whey",
    ),
    "gluten": (
        "wheat",
        "flour",
        "bread",
        "breadcrumb",
        "pasta",
        "spaghetti",
        "noodle",
        "tortilla",
        "barley",
        "rye",
        "couscous",
        "cracker",
        "bagel",
        "bun",
        "seitan",
        "soy sauce",
    ),
    "nut": _TREE_NUTS,
    "tree nut": _TREE_NUTS,
    "peanut": ("peanut",),
    "egg": ("egg", "mayonnaise", "mayo", "meringue"),
    "shellfish": (
        "shrimp",
        "prawn",
        "crab",
        "lobster",
        "clam",
        "mussel",
        "oyster",
        "scallop",
    ),
    "fish": (
        "fish",
        "salmon",
        "tuna",
        "cod",
        "tilapia",
        "trout",
        "halibut",
        "anchovy",
        "anchovie",
        "sardine",
    ),
    "soy": ("soy", "tofu", "edamame", "tempeh", "miso"),
    "meat": (
        "beef",
        "chicken",
        "pork",
        "lamb",
        "bacon",
        "ham",
        "sausage",
        "turkey",
        "steak",
        "salami",
        "prosciutto",
    ),
}

# Phrases that contain a group keyword but don't belong to the group.
GROUP_EXCEPTIONS: dict[str, tuple[str, ...]] = {
    "dairy": (
        "peanut butter",
        "almond butter",
        "cashew butter",
        "coconut milk",
        "coconut cream",
        "almond milk",
        "oat milk",
        "soy milk",
        "rice milk",
    ),
}


def singularize(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("oes", "ches", "shes", "xes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us")):
        return word[:-1]
    return word


def normalize(text: str) -> str:
    """Lowercase, collapse spaces, singularize the last word: "Rolled  Oats" -> "rolled oat"."""
    words = text.lower().split()
    if not words:
        return ""
    words[-1] = singularize(words[-1])
    return " ".join(words)


@lru_cache(maxsize=512)
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(keyword)}(?:e?s)?\b")


def find_conflicts(recipe: Recipe, restrictions: Iterable[FoodRestriction]) -> list[Conflict]:
    conflicts = []
    for restriction in restrictions:
        term = normalize(restriction.name)
        patterns = [_keyword_pattern(k) for k in FOOD_GROUPS.get(term, (term,))]
        exceptions = GROUP_EXCEPTIONS.get(term, ())
        for ingredient in recipe.ingredients:
            text = ingredient.name.lower()
            for phrase in exceptions:
                text = text.replace(phrase, " ")
            if any(pattern.search(text) for pattern in patterns):
                conflicts.append(
                    Conflict(
                        restriction=restriction.name,
                        kind=restriction.kind,
                        ingredient=ingredient.name,
                    )
                )
    return conflicts


def pantry_coverage(recipe: Recipe, pantry_names: set[str]) -> tuple[list[str], list[str]]:
    """Split a recipe's ingredients into (already in pantry, missing)."""
    have, missing = [], []
    for ingredient in recipe.ingredients:
        (have if normalize(ingredient.name) in pantry_names else missing).append(ingredient.name)
    return have, missing
