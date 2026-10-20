import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
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
    __table_args__ = (UniqueConstraint("day", "meal_type", name="uq_meal_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[dt.date] = mapped_column(index=True)
    meal_type: Mapped[str] = mapped_column(String(20))
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))

    recipe: Mapped[Recipe] = relationship(back_populates="plan_entries")


class PantryItem(Base):
    """Something already in the fridge or pantry. A missing quantity means "have some"."""

    __tablename__ = "pantry_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[float | None] = mapped_column(Float, default=None)
    unit: Mapped[str] = mapped_column(String(30), default="")


class FoodRestriction(Base):
    """An allergy or dislike. Recipes containing it are kept out of suggestions."""

    __tablename__ = "food_restrictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(10))
