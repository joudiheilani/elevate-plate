from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..deps import CurrentUser, DbSession
from ..models import FoodRestriction, Ingredient, PantryItem, Recipe, User
from ..schemas import IngredientIn, MealIdea, RecipeIn, RecipeOut
from ..services.matching import diet_restrictions, find_conflicts, normalize, pantry_coverage
from ..services.nutrition import recipe_nutrition
from ..services.pricing import cost_breakdown, cost_per_serving
from .profile import get_profile

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


def get_recipe_or_404(db: Session, user: User, recipe_id: int) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None or recipe.user_id != user.id:
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
    out.nutrition = recipe_nutrition(recipe)
    return out


def all_restrictions(db: Session, user: User) -> list[FoodRestriction]:
    """The user's allergies and dislikes, plus whatever their diet rules out."""
    saved = db.scalars(select(FoodRestriction).where(FoodRestriction.user_id == user.id))
    return [*saved, *diet_restrictions(get_profile(db, user).diet)]


def all_recipes(db: Session, user: User) -> Sequence[Recipe]:
    return db.scalars(
        select(Recipe)
        .where(Recipe.user_id == user.id)
        .options(selectinload(Recipe.ingredients))
        .order_by(Recipe.name)
    ).all()


@router.get("", response_model=list[RecipeOut])
def list_recipes(db: DbSession, user: CurrentUser, q: str | None = None, safe_only: bool = False):
    """List recipes, each flagged with any allergies/dislikes it conflicts with.

    `safe_only=true` leaves out recipes that have conflicts.
    """
    restrictions = all_restrictions(db, user)
    query = (q or "").strip().lower()
    recipes = [
        to_recipe_out(recipe, restrictions)
        for recipe in all_recipes(db, user)
        if query in recipe.name.lower()
    ]
    return [r for r in recipes if not r.conflicts] if safe_only else recipes


@router.get("/ideas", response_model=list[MealIdea])
def meal_ideas(db: DbSession, user: CurrentUser):
    """Recipes free of allergies/dislikes, best pantry match first."""
    restrictions = all_restrictions(db, user)
    pantry = db.scalars(select(PantryItem).where(PantryItem.user_id == user.id))
    pantry_names = {normalize(item.name) for item in pantry}
    ideas = []
    for recipe in all_recipes(db, user):
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
def create_recipe(payload: RecipeIn, db: DbSession, user: CurrentUser):
    recipe = Recipe(
        **payload.model_dump(exclude={"ingredients"}),
        user_id=user.id,
        ingredients=build_ingredients(payload.ingredients),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return to_recipe_out(recipe, all_restrictions(db, user))


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int, db: DbSession, user: CurrentUser):
    return to_recipe_out(get_recipe_or_404(db, user, recipe_id), all_restrictions(db, user))


@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(recipe_id: int, payload: RecipeIn, db: DbSession, user: CurrentUser):
    recipe = get_recipe_or_404(db, user, recipe_id)
    for field, value in payload.model_dump(exclude={"ingredients"}).items():
        setattr(recipe, field, value)
    recipe.ingredients = build_ingredients(payload.ingredients)
    db.commit()
    db.refresh(recipe)
    return to_recipe_out(recipe, all_restrictions(db, user))


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: DbSession, user: CurrentUser):
    db.delete(get_recipe_or_404(db, user, recipe_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
