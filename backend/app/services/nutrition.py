"""Macro estimates (calories, protein, carbs, fat) for recipes.

A recipe's own numbers win when the user typed them in; otherwise each ingredient is
converted to grams and looked up in data/nutrition.py. Ingredients we can't look up or
measure are listed in `missing`, so the app can say the estimate leaves them out.
"""

from ..data.nutrition import FOODS, NEGLIGIBLE, SOURCE, Food
from ..models import Recipe
from ..schemas import Nutrition
from .matching import keyword_pattern, normalize
from .units import VOLUME_ML, WEIGHT_GRAMS, canonical_unit

# Longest names first, so "peanut butter" wins over "butter" and "garlic powder"
# (negligible) over "garlic".
_KEYS_BY_LENGTH = sorted({*FOODS, *NEGLIGIBLE}, key=len, reverse=True)
_NEGLIGIBLE = object()


def lookup_food(name: str) -> Food | object | None:
    """The nutrition entry for an ingredient, _NEGLIGIBLE for spices and water, or None."""
    key = normalize(name)
    if key in NEGLIGIBLE:
        return _NEGLIGIBLE
    if key in FOODS:
        return FOODS[key]
    for candidate in _KEYS_BY_LENGTH:
        if keyword_pattern(candidate).search(key):
            return _NEGLIGIBLE if candidate in NEGLIGIBLE else FOODS[candidate]
    return None


def grams(food: Food, quantity: float, unit: str) -> float | None:
    """How many grams `quantity unit` of a food weighs, or None if we can't tell."""
    unit = canonical_unit(unit)
    if unit in WEIGHT_GRAMS:
        return quantity * WEIGHT_GRAMS[unit]
    if unit in VOLUME_ML:
        if food.g_per_cup is None:
            return None
        return quantity * VOLUME_ML[unit] / VOLUME_ML["cup"] * food.g_per_cup
    if unit in food.per_unit:
        return quantity * food.per_unit[unit]
    if unit == "" and food.g_each is not None:
        return quantity * food.g_each
    return None


def estimate(recipe: Recipe) -> Nutrition:
    """Per-serving macros worked out from the ingredient list."""
    totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    missing = []
    for ingredient in recipe.ingredients:
        food = lookup_food(ingredient.name)
        if food is _NEGLIGIBLE:
            continue
        weight = None
        if food is not None and ingredient.quantity is not None:
            weight = grams(food, ingredient.quantity, ingredient.unit)
        if weight is None:
            missing.append(ingredient.name)
            continue
        share = weight / 100
        totals["calories"] += food.kcal * share
        totals["protein_g"] += food.protein * share
        totals["carbs_g"] += food.carbs * share
        totals["fat_g"] += food.fat * share

    servings = max(recipe.servings or 1, 1)
    return Nutrition(
        calories=round(totals["calories"] / servings),
        protein_g=round(totals["protein_g"] / servings, 1),
        carbs_g=round(totals["carbs_g"] / servings, 1),
        fat_g=round(totals["fat_g"] / servings, 1),
        source="estimated",
        note=SOURCE,
        missing=missing,
    )


def has_entered_macros(recipe: Recipe) -> bool:
    return any(
        value is not None
        for value in (recipe.calories, recipe.protein_g, recipe.carbs_g, recipe.fat_g)
    )


def recipe_nutrition(recipe: Recipe) -> Nutrition:
    """Per-serving macros: the user's own numbers if they entered any, else an estimate.

    A blank field next to entered ones is filled from the estimate, so a user who only
    knows the calories still sees protein, carbs and fat.
    """
    estimated = estimate(recipe)
    if not has_entered_macros(recipe):
        return estimated

    def pick(entered: float | None, fallback: float) -> float:
        return fallback if entered is None else entered

    return Nutrition(
        calories=round(pick(recipe.calories, estimated.calories)),
        protein_g=round(pick(recipe.protein_g, estimated.protein_g), 1),
        carbs_g=round(pick(recipe.carbs_g, estimated.carbs_g), 1),
        fat_g=round(pick(recipe.fat_g, estimated.fat_g), 1),
        source="entered",
        note="Entered by you",
        missing=[],
    )


def add(totals: Nutrition | None, item: Nutrition, times: float = 1) -> Nutrition:
    """totals + item x times, unrounded (for daily and weekly totals)."""
    base = totals or Nutrition()
    return Nutrition(
        calories=base.calories + item.calories * times,
        protein_g=base.protein_g + item.protein_g * times,
        carbs_g=base.carbs_g + item.carbs_g * times,
        fat_g=base.fat_g + item.fat_g * times,
        missing=sorted({*base.missing, *item.missing}),
    )
