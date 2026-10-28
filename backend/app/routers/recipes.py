from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import FoodRestriction, Ingredient, PantryItem, Recipe
from ..schemas import IngredientIn, MealIdea, RecipeIn, RecipeOut
from ..services.matching import diet_restrictions, find_conflicts, normalize, pantry_coverage
from ..services.pricing import cost_breakdown, cost_per_serving
from .profile import get_profile

router = APIRouter(prefix="/api/recipes", tags=["recipes"])
DbSession = Annotated[Session, Depends(get_db)]


def get_recipe_or_404(db: Session, recipe_id: int) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


def build_ingredients(items: list[IngredientIn]) -> list[Ingredient]:
    return [
        Ingredient(name=item.name, quantity=item.quantity, unit=item.unit, position=position)
        for position, item in enumerate(items)
    ]


def to_recipe_out(recipe: Recipe, restrictions: Sequence[FoodRestriction]) -> RecipeOut:
    out = RecipeOut.model_validate(recipe)
    out.conflicts = find_conflicts(recipe, restrictions)
    out.cost_per_serving = cost_per_serving(recipe)
    out.cost_breakdown = cost_breakdown(recipe)
    return out


def all_restrictions(db: Session) -> list[FoodRestriction]:
    """The user's allergies and dislikes, plus whatever their diet rules out."""
    return [*db.scalars(select(FoodRestriction)), *diet_restrictions(get_profile(db).diet)]


def all_recipes(db: Session) -> Sequence[Recipe]:
    return db.scalars(
        select(Recipe).options(selectinload(Recipe.ingredients)).order_by(Recipe.name)
    ).all()


@router.get("", response_model=list[RecipeOut])
def list_recipes(db: DbSession, q: str | None = None, safe_only: bool = False):
    """List recipes, each flagged with any allergies/dislikes it conflicts with.

    `safe_only=true` leaves out recipes that have conflicts.
    """
    restrictions = all_restrictions(db)
    query = (q or "").strip().lower()
    recipes = [
        to_recipe_out(recipe, restrictions)
        for recipe in all_recipes(db)
        if query in recipe.name.lower()
    ]
    return [r for r in recipes if not r.conflicts] if safe_only else recipes


@router.get("/ideas", response_model=list[MealIdea])
def meal_ideas(db: DbSession):
    """Recipes free of allergies/dislikes, best pantry match first."""
    restrictions = all_restrictions(db)
    pantry_names = {normalize(item.name) for item in db.scalars(select(PantryItem))}
    ideas = []
    for recipe in all_recipes(db):
        out = to_recipe_out(recipe, restrictions)
        if out.conflicts:
            continue
        have, missing = pantry_coverage(recipe, pantry_names)
        ideas.append(MealIdea(recipe=out, have=have, missing=missing))
    ideas.sort(
        key=lambda idea: (
            -len(idea.have) / max(len(idea.recipe.ingredients), 1),
            len(idea.missing),
            idea.recipe.name.lower(),
        )
    )
    return ideas


@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(payload: RecipeIn, db: DbSession):
    recipe = Recipe(
        **payload.model_dump(exclude={"ingredients"}),
        ingredients=build_ingredients(payload.ingredients),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return to_recipe_out(recipe, all_restrictions(db))


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int, db: DbSession):
    return to_recipe_out(get_recipe_or_404(db, recipe_id), all_restrictions(db))


@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(recipe_id: int, payload: RecipeIn, db: DbSession):
    recipe = get_recipe_or_404(db, recipe_id)
    for field, value in payload.model_dump(exclude={"ingredients"}).items():
        setattr(recipe, field, value)
    recipe.ingredients = build_ingredients(payload.ingredients)
    db.commit()
    db.refresh(recipe)
    return to_recipe_out(recipe, all_restrictions(db))


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: DbSession):
    db.delete(get_recipe_or_404(db, recipe_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
