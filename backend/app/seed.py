from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Ingredient, Recipe

SAMPLE_RECIPES = [
    {
        "name": "Overnight Oats",
        "description": "No-cook breakfast you prep the night before.",
        "servings": 1,
        "prep_minutes": 5,
        "instructions": "Combine everything in a jar, stir, and refrigerate overnight.",
        "ingredients": [
            ("rolled oats", 0.5, "cup"),
            ("milk", 0.5, "cup"),
            ("greek yogurt", 0.25, "cup"),
            ("honey", 1, "tbsp"),
            ("blueberries", 0.5, "cup"),
        ],
    },
    {
        "name": "Chicken Caesar Wrap",
        "description": "Quick, filling lunch.",
        "servings": 2,
        "prep_minutes": 15,
        "instructions": "Slice the chicken, toss with lettuce and dressing, and roll in tortillas.",
        "ingredients": [
            ("chicken breast", 1, "lb"),
            ("romaine lettuce", 1, "head"),
            ("caesar dressing", 0.25, "cup"),
            ("flour tortillas", 2, ""),
            ("parmesan", 0.25, "cup"),
        ],
    },
    {
        "name": "Spaghetti Bolognese",
        "description": "Classic weeknight pasta with meat sauce.",
        "servings": 4,
        "prep_minutes": 40,
        "instructions": (
            "Brown the beef with onion and garlic. Add crushed tomatoes and simmer 20 minutes. "
            "Serve over cooked spaghetti."
        ),
        "ingredients": [
            ("spaghetti", 1, "lb"),
            ("ground beef", 1, "lb"),
            ("onion", 1, ""),
            ("garlic", 3, "clove"),
            ("crushed tomatoes", 28, "oz"),
        ],
    },
    {
        "name": "Veggie Stir Fry",
        "description": "Colorful vegetables and tofu over rice.",
        "servings": 3,
        "prep_minutes": 25,
        "instructions": "Press and cube the tofu. Stir fry with the vegetables and soy sauce. "
        "Serve over rice.",
        "ingredients": [
            ("firm tofu", 14, "oz"),
            ("broccoli", 2, "cup"),
            ("bell pepper", 2, ""),
            ("soy sauce", 3, "tbsp"),
            ("garlic", 2, "clove"),
            ("rice", 1.5, "cup"),
        ],
    },
]


def seed_if_empty(db: Session) -> None:
    """Insert a few sample recipes so a fresh deployment isn't empty."""
    if db.scalar(select(func.count()).select_from(Recipe)):
        return
    for data in SAMPLE_RECIPES:
        ingredients = [
            Ingredient(name=name, quantity=quantity, unit=unit, position=position)
            for position, (name, quantity, unit) in enumerate(data["ingredients"])
        ]
        db.add(Recipe(**{**data, "ingredients": ingredients}))
    db.commit()
