from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ingredient, Recipe
from ..schemas import DiscoveredRecipe, RecipeOut
from ..services import mealdb
from ..services.matching import find_conflicts
from ..services.pricing import cost_per_serving
from .recipes import all_restrictions, build_ingredients, to_recipe_out

router = APIRouter(prefix="/api/discover", tags=["discover recipes (TheMealDB)"])
DbSession = Annotated[Session, Depends(get_db)]
MAX_RESULTS = 12


def _upstream(call, *args):
    try:
        return call(*args)
    except mealdb.MealDBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("", response_model=list[DiscoveredRecipe])
def discover(db: DbSession, q: Annotated[str, Query(min_length=2, max_length=60)]):
    """Search TheMealDB. Each result gets an estimated cost and diet/allergy check."""
    restrictions = all_restrictions(db)
    library = {name.lower() for name in db.scalars(select(Recipe.name))}
    results = []
    for meal in _upstream(mealdb.search, q.strip())[:MAX_RESULTS]:
        items = mealdb.ingredients(meal)
        preview = Recipe(
            name=meal["strMeal"],
            servings=mealdb.DEFAULT_SERVINGS,
            ingredients=[Ingredient(name=i.name, quantity=i.quantity, unit=i.unit) for i in items],
        )
        results.append(
            DiscoveredRecipe(
                id=meal["idMeal"],
                name=meal["strMeal"],
                category=meal.get("strCategory") or "",
                area=meal.get("strArea") or "",
                thumbnail=meal.get("strMealThumb") or "",
                mealdb_url=mealdb.MEAL_PAGE.format(id=meal["idMeal"]),
                source_url=meal.get("strSource") or None,
                ingredients=items,
                servings=mealdb.DEFAULT_SERVINGS,
                cost_per_serving=cost_per_serving(preview),
                conflicts=find_conflicts(preview, restrictions),
                in_library=meal["strMeal"].lower() in library,
            )
        )
    return results


@router.post("/{meal_id}/import", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def import_meal(meal_id: str, db: DbSession):
    """Copy a TheMealDB recipe into the library, credited to TheMealDB and its source."""
    if not meal_id.isdigit() or len(meal_id) > 10:
        raise HTTPException(status_code=422, detail="Invalid recipe id")
    meal = _upstream(mealdb.lookup, meal_id)
    if meal is None:
        raise HTTPException(status_code=404, detail="Recipe not found on TheMealDB")
    name = meal["strMeal"][:200]
    if db.scalar(select(Recipe).where(func.lower(Recipe.name) == name.lower())):
        raise HTTPException(status_code=409, detail=f'"{name}" is already in your recipes')
    recipe = Recipe(
        name=name,
        description=mealdb.description(meal),
        instructions=mealdb.instructions(meal),
        servings=mealdb.DEFAULT_SERVINGS,
        prep_minutes=None,
        ingredients=build_ingredients(mealdb.ingredients(meal)),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return to_recipe_out(recipe, all_restrictions(db))
