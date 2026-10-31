import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _owner() -> Mapped[int | None]:
    """The user a row belongs to.

    Nullable only so databases created before accounts existed can be migrated (their
    rows are claimed by the first account; see migrations.py). Every query filters on it.
    """
    return mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuthToken(Base):
    """A login session. Only a SHA-256 hash of the token is stored."""

    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = _owner()
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    servings: Mapped[int] = mapped_column(default=2)
    prep_minutes: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ingredients: Mapped[list["Ingredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="Ingredient.position",
    )
    plan_entries: Mapped[list["MealPlanEntry"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[float | None] = mapped_column(Float, default=None)
    unit: Mapped[str] = mapped_column(String(30), default="")
    position: Mapped[int] = mapped_column(default=0)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")


class MealPlanEntry(Base):
    """One recipe assigned to one meal slot (e.g. Tuesday dinner)."""

    __tablename__ = "meal_plan_entries"
    __table_args__ = (UniqueConstraint("user_id", "day", "meal_type", name="uq_user_meal_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = _owner()
    day: Mapped[dt.date] = mapped_column(index=True)
    meal_type: Mapped[str] = mapped_column(String(20))
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))

    recipe: Mapped[Recipe] = relationship(back_populates="plan_entries")


class PantryItem(Base):
    """Something already in the fridge or pantry. A missing quantity means "have some"."""

    __tablename__ = "pantry_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = _owner()
    name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[float | None] = mapped_column(Float, default=None)
    unit: Mapped[str] = mapped_column(String(30), default="")


class GroceryItem(Base):
    """An item the user added to their shopping list by hand (not from a planned meal)."""

    __tablename__ = "grocery_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = _owner()
    name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[float | None] = mapped_column(Float, default=None)
    unit: Mapped[str] = mapped_column(String(30), default="")
    price: Mapped[float | None] = mapped_column(Float, default=None)


class Profile(Base):
    """Budget and planning preferences, one row per user."""

    __tablename__ = "profile"
    __table_args__ = (UniqueConstraint("user_id", name="uq_profile_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    weekly_budget: Mapped[float] = mapped_column(Float, default=75.0)
    people: Mapped[int] = mapped_column(default=2)
    max_minutes: Mapped[int | None] = mapped_column(default=30)
    diet: Mapped[str] = mapped_column(String(20), default="any")
    meals: Mapped[str] = mapped_column(String(40), default="breakfast,lunch,dinner")
    mode: Mapped[str] = mapped_column(String(10), default="auto")
    assume_staples: Mapped[bool] = mapped_column(default=True)


class FoodRestriction(Base):
    """An allergy or dislike. Recipes containing it are kept out of suggestions."""

    __tablename__ = "food_restrictions"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_restriction"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = _owner()
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(10))


# Tables whose rows belong to a user (used by migrations and account deletion).
OWNED_MODELS = (Recipe, MealPlanEntry, PantryItem, GroceryItem, Profile, FoodRestriction)
