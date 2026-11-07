import datetime as dt
import re

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from ..data.catalog import CATALOG_BY_NAME
from ..deps import CurrentUser, DbSession
from ..models import DiningOut, FoodRestriction, MealPlanEntry, PantryItem, Recipe
from ..schemas import ApplyPlanIn, ApplyPlanOut, GeneratedPlan, GenerateRequest
from ..services.generator import MEAL_ORDER, generate_plan
from ..services.matching import diet_restrictions

router = APIRouter(prefix="/api/generator", tags=["meal plan generator"])

# Recipe names that suggest breakfast, for saved recipes never planned before.
_BREAKFAST_WORDS = re.compile(
    r"\b(breakfast|oats|oatmeal|porridge|pancakes?|waffles?|french toast|omelett?e|"
    r"scrambl\w*|frittata|smoothie|parfait|granola|muffins?|bagels?|cereal|crepes?|chia)\b"
)


def _meal_types(recipe: Recipe, history: dict[int, set[str]]) -> tuple[str, ...]:
    """Which meals a saved recipe suits: where you've planned it before, else where the
    catalog uses it, else a guess from its name (breakfast-y names) or lunch and dinner."""
    if recipe.id in history:
        return tuple(m for m in MEAL_ORDER if m in history[recipe.id])
    catalog = CATALOG_BY_NAME.get(recipe.name.lower())
    if catalog is not None:
        return catalog.meal_types
    if _BREAKFAST_WORDS.search(recipe.name.lower()):
        return ("breakfast",)
    return ("lunch", "dinner")


def _library(db, user) -> list[tuple[Recipe, tuple[str, ...]]]:
    recipes = db.scalars(
        select(Recipe).where(Recipe.user_id == user.id).options(selectinload(Recipe.ingredients))
    ).all()
    history: dict[int, set[str]] = {}
    for recipe_id, meal_type in db.execute(
        select(MealPlanEntry.recipe_id, MealPlanEntry.meal_type)
        .where(MealPlanEntry.user_id == user.id)
        .distinct()
    ):
        history.setdefault(recipe_id, set()).add(meal_type)
    return [(recipe, _meal_types(recipe, history)) for recipe in recipes]


@router.post("", response_model=GeneratedPlan)
def generate(payload: GenerateRequest, db: DbSession, user: CurrentUser):
    """Preview a generated week. Nothing is saved until the plan is applied.

    With `fill_gaps`, meals already planned that week are kept and only empty slots
    are filled ("mix" mode). Slots marked as dining out are never filled; their
    expected cost is reported separately and isn't part of the grocery budget.
    """
    saved = db.scalars(select(FoodRestriction).where(FoodRestriction.user_id == user.id))
    restrictions = [*saved, *diet_restrictions(payload.diet)]
    pantry = db.scalars(select(PantryItem).where(PantryItem.user_id == user.id)).all()
    end = payload.start + dt.timedelta(days=payload.days - 1)
    # Meals eaten out are always left open, in every planning mode.
    dining = db.scalars(
        select(DiningOut)
        .where(DiningOut.user_id == user.id, DiningOut.day.between(payload.start, end))
        .order_by(DiningOut.day)
    ).all()
    planned = []
    if payload.fill_gaps:
        entries = db.scalars(
            select(MealPlanEntry)
            .where(MealPlanEntry.user_id == user.id, MealPlanEntry.day.between(payload.start, end))
            .options(selectinload(MealPlanEntry.recipe).selectinload(Recipe.ingredients))
        ).all()
        planned = [
            (entry.day, entry.meal_type, entry.recipe, entry.portions or 1) for entry in entries
        ]
    library = _library(db, user) if payload.use_library else []
    return generate_plan(payload, restrictions, pantry, planned, dining, library)


@router.post("/apply", response_model=ApplyPlanOut)
def apply_plan(payload: ApplyPlanIn, db: DbSession, user: CurrentUser):
    """Save a generated week: add its recipes to the library and fill the planner slots."""
    recipes: dict[str, Recipe] = {}
    added = 0
    for name in {meal.recipe_name.lower() for meal in payload.meals}:
        recipe = db.scalar(
            select(Recipe).where(Recipe.user_id == user.id, func.lower(Recipe.name) == name)
        )
        if recipe is None:
            entry = CATALOG_BY_NAME.get(name)
            if entry is None:
                raise HTTPException(status_code=404, detail=f'Unknown recipe "{name}"')
            recipe = entry.to_model()
            recipe.user_id = user.id
            db.add(recipe)
            added += 1
        recipes[name] = recipe
    db.flush()

    for meal in payload.meals:
        entry = db.scalar(
            select(MealPlanEntry).where(
                MealPlanEntry.user_id == user.id,
                MealPlanEntry.day == meal.day,
                MealPlanEntry.meal_type == meal.meal_type,
            )
        )
        if entry is None:
            entry = MealPlanEntry(user_id=user.id, day=meal.day, meal_type=meal.meal_type)
            db.add(entry)
        entry.recipe = recipes[meal.recipe_name.lower()]
        entry.portions = meal.portions
        db.execute(
            delete(DiningOut).where(
                DiningOut.user_id == user.id,
                DiningOut.day == meal.day,
                DiningOut.meal_type == meal.meal_type,
            )
        )
    db.commit()
    return ApplyPlanOut(recipes_added=added, meals_planned=len(payload.meals))
