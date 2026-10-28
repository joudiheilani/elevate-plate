import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..data.catalog import CATALOG_BY_NAME
from ..database import get_db
from ..models import FoodRestriction, MealPlanEntry, PantryItem, Recipe
from ..schemas import ApplyPlanIn, ApplyPlanOut, GeneratedPlan, GenerateRequest
from ..services.generator import generate_plan
from ..services.matching import diet_restrictions

router = APIRouter(prefix="/api/generator", tags=["meal plan generator"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=GeneratedPlan)
def generate(payload: GenerateRequest, db: DbSession):
    """Preview a generated week. Nothing is saved until the plan is applied.

    With `fill_gaps`, meals already planned that week are kept and only empty slots
    are filled ("mix" mode).
    """
    restrictions = [*db.scalars(select(FoodRestriction)), *diet_restrictions(payload.diet)]
    pantry = db.scalars(select(PantryItem)).all()
    planned = []
    if payload.fill_gaps:
        end = payload.start + dt.timedelta(days=payload.days - 1)
        entries = db.scalars(
            select(MealPlanEntry)
            .where(MealPlanEntry.day.between(payload.start, end))
            .options(selectinload(MealPlanEntry.recipe).selectinload(Recipe.ingredients))
        ).all()
        planned = [(entry.day, entry.meal_type, entry.recipe) for entry in entries]
    return generate_plan(payload, restrictions, pantry, planned)


@router.post("/apply", response_model=ApplyPlanOut)
def apply_plan(payload: ApplyPlanIn, db: DbSession):
    """Save a generated week: add its recipes to the library and fill the planner slots."""
    recipes: dict[str, Recipe] = {}
    added = 0
    for name in {meal.recipe_name.lower() for meal in payload.meals}:
        recipe = db.scalar(select(Recipe).where(func.lower(Recipe.name) == name))
        if recipe is None:
            entry = CATALOG_BY_NAME.get(name)
            if entry is None:
                raise HTTPException(status_code=404, detail=f'Unknown recipe "{name}"')
            recipe = entry.to_model()
            db.add(recipe)
            added += 1
        recipes[name] = recipe
    db.flush()

    for meal in payload.meals:
        entry = db.scalar(
            select(MealPlanEntry).where(
                MealPlanEntry.day == meal.day, MealPlanEntry.meal_type == meal.meal_type
            )
        )
        if entry is None:
            entry = MealPlanEntry(day=meal.day, meal_type=meal.meal_type)
            db.add(entry)
        entry.recipe = recipes[meal.recipe_name.lower()]
    db.commit()
    return ApplyPlanOut(recipes_added=added, meals_planned=len(payload.meals))
