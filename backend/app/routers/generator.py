import datetime as dt

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from ..data.catalog import CATALOG_BY_NAME
from ..deps import CurrentUser, DbSession
from ..models import DiningOut, FoodRestriction, MealPlanEntry, PantryItem, Recipe
from ..schemas import ApplyPlanIn, ApplyPlanOut, GeneratedPlan, GenerateRequest
from ..services.generator import generate_plan
from ..services.matching import diet_restrictions

router = APIRouter(prefix="/api/generator", tags=["meal plan generator"])


@router.post("", response_model=GeneratedPlan)
def generate(payload: GenerateRequest, db: DbSession, user: CurrentUser):
    """Preview a generated week. Nothing is saved until the plan is applied.

    With `fill_gaps`, meals already planned that week are kept and only empty slots
    are filled ("mix" mode). Slots marked as dining out are never filled, and their
    expected cost comes out of the grocery budget.
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
    return generate_plan(payload, restrictions, pantry, planned, dining)


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
