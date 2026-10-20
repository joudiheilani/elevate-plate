import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MealType = Literal["breakfast", "lunch", "dinner"]
RestrictionKind = Literal["allergy", "dislike"]
ShoppingStatus = Literal["buy", "partial", "have", "check"]


class IngredientIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    quantity: float | None = Field(default=None, ge=0)
    unit: str = Field(default="", max_length=30)


class IngredientOut(IngredientIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class RecipeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    instructions: str = ""
    servings: int = Field(default=2, ge=1, le=100)
    prep_minutes: int | None = Field(default=None, ge=0, le=1440)
    ingredients: list[IngredientIn] = []


class Conflict(BaseModel):
    """An ingredient that clashes with one of the user's allergies or dislikes."""

    restriction: str
    kind: RestrictionKind
    ingredient: str


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    instructions: str
    servings: int
    prep_minutes: int | None
    ingredients: list[IngredientOut]
    conflicts: list[Conflict] = []


class MealIdea(BaseModel):
    recipe: RecipeOut
    have: list[str]
    missing: list[str]


class RecipeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    servings: int
    prep_minutes: int | None


class PlanEntryIn(BaseModel):
    day: dt.date
    meal_type: MealType
    recipe_id: int


class PlanEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    day: dt.date
    meal_type: MealType
    recipe: RecipeSummary


class ShoppingItem(BaseModel):
    name: str
    quantity: float | None
    unit: str
    recipes: list[str]
    # How the pantry affects this item:
    #   buy     - not in the pantry
    #   partial - in the pantry, but not enough (to_buy is the shortfall)
    #   have    - the pantry covers it
    #   check   - in the pantry in a different unit, so the amount can't be compared
    status: ShoppingStatus = "buy"
    to_buy: float | None = None
    pantry_quantity: float | None = None
    pantry_unit: str | None = None


class PantryItemIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    quantity: float | None = Field(default=None, ge=0)
    unit: str = Field(default="", max_length=30)


class PantryItemOut(PantryItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class RestrictionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)
    kind: RestrictionKind = "allergy"


class RestrictionOut(RestrictionIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ShoppingList(BaseModel):
    start: dt.date
    end: dt.date
    items: list[ShoppingItem]
