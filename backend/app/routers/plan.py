import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from ..database import get_db
from ..models import GroceryItem, MealPlanEntry, PantryItem, Recipe
from ..schemas import PlanEntryIn, PlanEntryOut, ShoppingItem, ShoppingList
from ..services.pricing import purchase_cost
from ..services.shopping import (
    aggregate_ingredients,
    apply_pantry,
    portion,
    price_items,
    round_up_counts,
    staple_items,
)
from .profile import get_profile
from .recipes import get_recipe_or_404

router = APIRouter(prefix="/api", tags=["meal plan"])
DbSession = Annotated[Session, Depends(get_db)]

WEEK_SPAN = dt.timedelta(days=6)


def week_entries_stmt(start: dt.date):
    return (
        select(MealPlanEntry)
        .where(MealPlanEntry.day.between(start, start + WEEK_SPAN))
        .order_by(MealPlanEntry.day, MealPlanEntry.meal_type)
    )


@router.get("/plan", response_model=list[PlanEntryOut])
def get_week_plan(start: dt.date, db: DbSession):
    """Return the meal plan for the 7 days beginning at `start`."""
    return db.scalars(week_entries_stmt(start).options(joinedload(MealPlanEntry.recipe))).all()


@router.put("/plan", response_model=PlanEntryOut)
def set_meal(payload: PlanEntryIn, db: DbSession):
    """Assign a recipe to a meal slot, replacing whatever was planned there."""
    recipe = get_recipe_or_404(db, payload.recipe_id)
    entry = db.scalar(
        select(MealPlanEntry).where(
            MealPlanEntry.day == payload.day, MealPlanEntry.meal_type == payload.meal_type
        )
    )
    if entry is None:
        entry = MealPlanEntry(day=payload.day, meal_type=payload.meal_type)
        db.add(entry)
    entry.recipe = recipe
    db.commit()
    return entry


@router.delete("/plan/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_meal(entry_id: int, db: DbSession):
    entry = db.get(MealPlanEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Plan entry not found")
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/shopping-list", response_model=ShoppingList, tags=["shopping list"])
def get_shopping_list(start: dt.date, db: DbSession):
    """Ingredients for the week beginning at `start`, minus the pantry, plus custom items.

    Each planned meal is scaled to the household size, and basics (oil, spices) count as
    owned when the profile says so, matching how generated plans are priced. Each item
    gets an estimated cost in whole packages, to compare with the weekly budget.
    """
    profile = get_profile(db)
    entries = db.scalars(
        week_entries_stmt(start).options(
            selectinload(MealPlanEntry.recipe).selectinload(Recipe.ingredients)
        )
    ).all()
    staples = staple_items() if profile.assume_staples else []
    items = apply_pantry(
        round_up_counts(
            aggregate_ingredients(portion(entry.recipe, profile.people) for entry in entries)
        ),
        [*db.scalars(select(PantryItem)), *staples],
    )
    price_items(items)

    for custom in db.scalars(select(GroceryItem).order_by(GroceryItem.id)):
        estimate, known = purchase_cost(custom.name, custom.quantity, custom.unit)
        items.append(
            ShoppingItem(
                name=custom.name,
                quantity=custom.quantity,
                unit=custom.unit,
                recipes=[],
                to_buy=custom.quantity,
                source="custom",
                custom_id=custom.id,
                est_cost=custom.price if custom.price is not None else estimate,
                price_known=custom.price is not None or known,
            )
        )

    return ShoppingList(
        start=start,
        end=start + WEEK_SPAN,
        items=items,
        estimated_total=round(sum(item.est_cost for item in items), 2),
        budget=profile.weekly_budget,
    )
