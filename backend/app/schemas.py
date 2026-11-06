import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MealType = Literal["breakfast", "lunch", "dinner"]
RestrictionKind = Literal["allergy", "dislike"]
ConflictKind = Literal["allergy", "dislike", "diet"]
ShoppingStatus = Literal["buy", "partial", "have", "check"]
Diet = Literal["any", "vegetarian", "vegan", "pescatarian"]
# manual: plan it yourself · auto: generate everything · hybrid: you plan, we fill the gaps
PlanningMode = Literal["manual", "auto", "hybrid"]


class SignupIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=80)


class LoginIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class DeleteAccountIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str


class AuthOut(BaseModel):
    token: str
    user: UserOut


class IngredientIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    quantity: float | None = Field(default=None, ge=0)
    unit: str = Field(default="", max_length=30)


class IngredientOut(IngredientIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class Nutrition(BaseModel):
    """Macros for one serving (or a total, for daily and weekly sums)."""

    calories: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    # entered: typed in by the user · estimated: worked out from the ingredients
    source: Literal["estimated", "entered"] = "estimated"
    note: str = ""
    missing: list[str] = []  # ingredients left out of the estimate


class RecipeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    instructions: str = ""
    servings: int = Field(default=2, ge=1, le=100)
    prep_minutes: int | None = Field(default=None, ge=0, le=1440)
    ingredients: list[IngredientIn] = []
    # Optional macros per serving. Blank ones are estimated from the ingredients.
    calories: float | None = Field(default=None, ge=0, le=10000)
    protein_g: float | None = Field(default=None, ge=0, le=1000)
    carbs_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=1000)


class Conflict(BaseModel):
    """An ingredient that clashes with the user's allergies, dislikes or diet."""

    restriction: str
    kind: ConflictKind
    ingredient: str


class CostLine(BaseModel):
    """One ingredient's share of a recipe's estimated cost, and where its price came from."""

    ingredient: str
    cost: float
    priced: bool  # False = not in the price table, so the cost is a flat guess
    source: str


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    instructions: str
    servings: int
    prep_minutes: int | None
    ingredients: list[IngredientOut]
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    conflicts: list[Conflict] = []
    cost_per_serving: float = 0
    cost_breakdown: list[CostLine] = []
    nutrition: Nutrition = Nutrition()  # per serving


class DiscoveredRecipe(BaseModel):
    """A recipe found on TheMealDB, previewed before importing."""

    id: str
    name: str
    category: str
    area: str
    thumbnail: str
    mealdb_url: str
    source_url: str | None
    ingredients: list[IngredientIn]
    servings: int
    cost_per_serving: float
    nutrition: Nutrition
    conflicts: list[Conflict]
    in_library: bool


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
    nutrition: Nutrition = Nutrition()  # per serving


class PlanEntryIn(BaseModel):
    day: dt.date
    meal_type: MealType
    recipe_id: int
    portions: float = Field(default=1, ge=0.5, le=4)  # servings per person


class PlanEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    day: dt.date
    meal_type: MealType
    recipe: RecipeSummary
    portions: float = 1


class DiningOutIn(BaseModel):
    """A meal eaten out, so the planner and generator leave that slot alone."""

    model_config = ConfigDict(str_strip_whitespace=True)

    day: dt.date
    meal_type: MealType
    note: str = Field(default="", max_length=120)  # e.g. "Pizza with friends"
    cost: float | None = Field(default=None, ge=0, le=2000)  # expected spend, all people


class DiningOutOut(DiningOutIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


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
    # "custom" items were added by hand; custom_id identifies them for deletion.
    source: Literal["plan", "custom"] = "plan"
    custom_id: int | None = None
    est_cost: float = 0
    price_known: bool = True


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
    estimated_total: float = 0
    budget: float | None = None
    dining_out_total: float = 0  # expected spend on meals out that week


class GroceryItemIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    quantity: float | None = Field(default=None, ge=0)
    unit: str = Field(default="", max_length=30)
    price: float | None = Field(default=None, ge=0, le=10000)


class GroceryItemOut(GroceryItemIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class MacroGoals(BaseModel):
    """Daily targets per person. Any can be left out."""

    calories: float | None = Field(default=None, ge=500, le=10000)
    protein_g: float | None = Field(default=None, ge=0, le=500)
    carbs_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=500)

    def targets(self) -> dict[str, float]:
        return {name: value for name, value in self.model_dump().items() if value is not None}


class ProfileData(BaseModel):
    weekly_budget: float = Field(default=75, ge=0, le=5000)
    people: int = Field(default=2, ge=1, le=12)
    max_minutes: int | None = Field(default=30, ge=5, le=600)  # None = no limit
    diet: Diet = "any"
    meals: list[MealType] = Field(default=["breakfast", "lunch", "dinner"], min_length=1)
    mode: PlanningMode = "auto"
    assume_staples: bool = True  # oil, spices etc. count as already at home
    macro_goals: MacroGoals = MacroGoals()


class GenerateRequest(BaseModel):
    start: dt.date
    weekly_budget: float = Field(ge=10, le=5000)
    people: int = Field(default=2, ge=1, le=12)
    max_minutes: int | None = Field(default=None, ge=5, le=600)
    diet: Diet = "any"
    meals: list[MealType] = Field(min_length=1)
    days: int = Field(default=7, ge=1, le=7)
    use_pantry: bool = True
    assume_staples: bool = True  # oil and spices are already at home
    fill_gaps: bool = False  # keep meals already planned that week; only fill empty slots
    macro_goals: MacroGoals | None = None  # daily targets per person to plan around
    seed: int | None = None  # same seed + same inputs = same plan; change it to reshuffle


class PlanRecipe(BaseModel):
    name: str
    description: str
    instructions: str
    servings: int
    prep_minutes: int | None
    ingredients: list[IngredientIn]
    cost_per_serving: float
    nutrition: Nutrition = Nutrition()  # per serving


class GeneratedMeal(BaseModel):
    day: dt.date
    meal_type: MealType
    recipe: PlanRecipe
    cost: float  # for everyone eating this meal
    locked: bool = False  # already planned by the user (mix mode); kept as-is
    portions: float = 1  # servings per person (bigger portions help meet macro goals)
    nutrition: Nutrition = Nutrition()  # per person, at this portion size


class GeneratedPlan(BaseModel):
    meals: list[GeneratedMeal]
    groceries: list[ShoppingItem]
    estimated_total: float
    budget: float
    within_budget: bool
    average_minutes: int | None
    notes: list[str]
    dining_out: list[DiningOutOut] = []  # slots skipped because you're eating out
    dining_out_total: float = 0
    # Average per person per day, counting only the meals cooked at home.
    daily_nutrition: Nutrition | None = None
    # The share of the daily macro goals those home-cooked meals should cover
    # (e.g. without breakfast, lunch and dinner aim for 75% of the day).
    daily_target: Nutrition | None = None


class ApplyMeal(BaseModel):
    day: dt.date
    meal_type: MealType
    recipe_name: str = Field(min_length=1, max_length=200)
    portions: float = Field(default=1, ge=0.5, le=4)


class ApplyPlanIn(BaseModel):
    meals: list[ApplyMeal] = Field(min_length=1, max_length=50)


class ApplyPlanOut(BaseModel):
    recipes_added: int
    meals_planned: int
