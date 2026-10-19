from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Ingredient, Recipe
from ..schemas import IngredientIn, RecipeIn, RecipeOut

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


@router.get("", response_model=list[RecipeOut])
def list_recipes(db: DbSession, q: str | None = None):
    stmt = select(Recipe).options(selectinload(Recipe.ingredients)).order_by(Recipe.name)
    if q:
        stmt = stmt.where(Recipe.name.ilike(f"%{q.strip()}%"))
    return db.scalars(stmt).all()


@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(payload: RecipeIn, db: DbSession):
    recipe = Recipe(
        **payload.model_dump(exclude={"ingredients"}),
        ingredients=build_ingredients(payload.ingredients),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int, db: DbSession):
    return get_recipe_or_404(db, recipe_id)


@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(recipe_id: int, payload: RecipeIn, db: DbSession):
    recipe = get_recipe_or_404(db, recipe_id)
    for field, value in payload.model_dump(exclude={"ingredients"}).items():
        setattr(recipe, field, value)
    recipe.ingredients = build_ingredients(payload.ingredients)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: DbSession):
    db.delete(get_recipe_or_404(db, recipe_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
