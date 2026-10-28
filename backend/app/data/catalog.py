"""Built-in recipes the meal plan generator chooses from.

Ingredient tuples are (name, quantity, unit); names line up with data/prices.py so
costs can be estimated. Diet suitability (vegan, vegetarian...) isn't stored here;
it's worked out from the ingredients by services/matching.py.
"""

from dataclasses import dataclass

from ..models import Ingredient, Recipe


@dataclass(frozen=True)
class CatalogRecipe:
    name: str
    description: str
    meal_types: tuple[str, ...]
    prep_minutes: int
    servings: int
    ingredients: tuple[tuple[str, float | None, str], ...]
    instructions: str

    def to_model(self) -> Recipe:
        """A transient (unsaved) Recipe, so catalog and library recipes share code paths."""
        return Recipe(
            name=self.name,
            description=self.description,
            instructions=self.instructions,
            servings=self.servings,
            prep_minutes=self.prep_minutes,
            ingredients=[
                Ingredient(name=name, quantity=quantity, unit=unit, position=position)
                for position, (name, quantity, unit) in enumerate(self.ingredients)
            ],
        )


B, L, D = "breakfast", "lunch", "dinner"

CATALOG: tuple[CatalogRecipe, ...] = (
    # ---------- Breakfast ----------
    CatalogRecipe(
        "Overnight Oats",
        "No-cook breakfast you prep the night before.",
        (B,),
        5,
        1,
        (
            ("rolled oats", 0.5, "cup"),
            ("milk", 0.5, "cup"),
            ("greek yogurt", 0.25, "cup"),
            ("honey", 1, "tbsp"),
            ("blueberries", 0.5, "cup"),
        ),
        "Combine everything in a jar, stir, and refrigerate overnight.",
    ),
    CatalogRecipe(
        "Peanut Butter Banana Toast",
        "Two-minute breakfast with staying power.",
        (B,),
        5,
        1,
        (("bread", 2, "slice"), ("peanut butter", 2, "tbsp"), ("banana", 1, "")),
        "Toast the bread, spread with peanut butter and top with sliced banana.",
    ),
    CatalogRecipe(
        "Veggie Scrambled Eggs",
        "Soft eggs with spinach, peppers and cheddar.",
        (B,),
        10,
        2,
        (
            ("eggs", 4, ""),
            ("spinach", 1, "cup"),
            ("bell pepper", 1, ""),
            ("cheddar cheese", 0.25, "cup"),
            ("butter", 1, "tbsp"),
        ),
        "Saute the pepper and spinach in butter, add beaten eggs and stir gently. "
        "Finish with cheese.",
    ),
    CatalogRecipe(
        "Yogurt Parfait",
        "Layers of yogurt, granola and berries.",
        (B,),
        5,
        1,
        (
            ("greek yogurt", 1, "cup"),
            ("granola", 0.5, "cup"),
            ("blueberries", 0.5, "cup"),
            ("honey", 1, "tbsp"),
        ),
        "Layer yogurt, granola and berries in a glass. Drizzle with honey.",
    ),
    CatalogRecipe(
        "Banana Oat Pancakes",
        "Fluffy pancakes made with oats instead of flour.",
        (B,),
        20,
        2,
        (
            ("rolled oats", 1, "cup"),
            ("banana", 2, ""),
            ("eggs", 2, ""),
            ("milk", 0.5, "cup"),
            ("cinnamon", None, ""),
            ("butter", 1, "tbsp"),
        ),
        "Blend everything except the butter. Cook spoonfuls in a buttered pan, "
        "2 minutes per side.",
    ),
    CatalogRecipe(
        "Breakfast Burritos",
        "Make a batch and reheat all week.",
        (B, L),
        25,
        4,
        (
            ("flour tortillas", 4, ""),
            ("eggs", 6, ""),
            ("black beans", 1, "can"),
            ("cheddar cheese", 0.5, "cup"),
            ("salsa", 0.5, "cup"),
            ("potatoes", 2, ""),
        ),
        "Dice and pan-fry the potatoes, scramble in the eggs, then fill tortillas with "
        "eggs, beans, cheese and salsa.",
    ),
    CatalogRecipe(
        "Tofu Scramble Toast",
        "Plant-based scramble with spinach and cumin.",
        (B,),
        15,
        2,
        (
            ("firm tofu", 14, "oz"),
            ("spinach", 1, "cup"),
            ("onion", 0.5, ""),
            ("cumin", None, ""),
            ("olive oil", 1, "tbsp"),
            ("bread", 2, "slice"),
        ),
        "Crumble the tofu into a pan with oil and onion, season with cumin, stir in "
        "spinach. Serve on toast.",
    ),
    # ---------- Lunch ----------
    CatalogRecipe(
        "Chicken Caesar Wrap",
        "Quick, filling lunch.",
        (L,),
        15,
        2,
        (
            ("chicken breast", 1, "lb"),
            ("romaine lettuce", 1, "head"),
            ("caesar dressing", 0.25, "cup"),
            ("flour tortillas", 2, ""),
            ("parmesan", 0.25, "cup"),
        ),
        "Cook and slice the chicken, toss with lettuce and dressing, and roll in tortillas.",
    ),
    CatalogRecipe(
        "Smashed Chickpea Sandwich",
        "Creamy, lemony chickpeas on toast.",
        (L,),
        10,
        2,
        (
            ("chickpeas", 1, "can"),
            ("hummus", 0.25, "cup"),
            ("lemon", 1, ""),
            ("cucumber", 1, ""),
            ("bread", 4, "slice"),
        ),
        "Mash chickpeas with hummus and lemon juice. Spread on bread with sliced cucumber.",
    ),
    CatalogRecipe(
        "Black Bean Quesadillas",
        "Crispy, cheesy and ready in 15 minutes.",
        (L, D),
        15,
        2,
        (
            ("flour tortillas", 4, ""),
            ("black beans", 1, "can"),
            ("cheddar cheese", 1, "cup"),
            ("salsa", 0.5, "cup"),
            ("bell pepper", 1, ""),
        ),
        "Fill tortillas with beans, pepper and cheese. Toast in a dry pan until golden. "
        "Serve with salsa.",
    ),
    CatalogRecipe(
        "Tuna Salad Wraps",
        "Bright, crunchy tuna salad.",
        (L,),
        10,
        2,
        (
            ("tuna", 2, "can"),
            ("greek yogurt", 0.25, "cup"),
            ("cucumber", 1, ""),
            ("lemon", 1, ""),
            ("flour tortillas", 2, ""),
        ),
        "Mix tuna with yogurt, lemon and diced cucumber. Wrap in tortillas.",
    ),
    CatalogRecipe(
        "Hummus Veggie Pita",
        "No-cook pita stuffed with fresh vegetables.",
        (L,),
        10,
        2,
        (
            ("pita", 2, ""),
            ("hummus", 0.5, "cup"),
            ("cucumber", 1, ""),
            ("tomato", 1, ""),
            ("spinach", 1, "cup"),
        ),
        "Spread hummus inside the pitas and stuff with sliced vegetables.",
    ),
    CatalogRecipe(
        "Greek Quinoa Bowl",
        "Quinoa, chickpeas, feta and crunchy vegetables.",
        (L, D),
        25,
        3,
        (
            ("quinoa", 1, "cup"),
            ("chickpeas", 1, "can"),
            ("cucumber", 1, ""),
            ("tomato", 2, ""),
            ("feta", 0.5, "cup"),
            ("lemon", 1, ""),
            ("olive oil", 2, "tbsp"),
        ),
        "Cook the quinoa. Toss with chickpeas, chopped vegetables, feta, lemon and oil.",
    ),
    CatalogRecipe(
        "Red Lentil Soup",
        "Cozy, cheap and freezes well.",
        (L, D),
        45,
        6,
        (
            ("lentils", 1.5, "cup"),
            ("carrots", 3, ""),
            ("onion", 1, ""),
            ("garlic", 3, "clove"),
            ("crushed tomatoes", 28, "oz"),
            ("vegetable broth", 4, "cup"),
            ("cumin", None, ""),
        ),
        "Soften the onion, carrot and garlic, add everything else and simmer 30 minutes.",
    ),
    # ---------- Dinner ----------
    CatalogRecipe(
        "Spaghetti Bolognese",
        "Classic weeknight pasta with meat sauce.",
        (D,),
        40,
        4,
        (
            ("spaghetti", 1, "lb"),
            ("ground beef", 1, "lb"),
            ("onion", 1, ""),
            ("garlic", 3, "clove"),
            ("crushed tomatoes", 28, "oz"),
        ),
        "Brown the beef with onion and garlic. Add crushed tomatoes and simmer 20 minutes. "
        "Serve over cooked spaghetti.",
    ),
    CatalogRecipe(
        "Veggie Stir Fry",
        "Colorful vegetables and tofu over rice.",
        (D,),
        25,
        3,
        (
            ("firm tofu", 14, "oz"),
            ("broccoli", 2, "cup"),
            ("bell pepper", 2, ""),
            ("soy sauce", 3, "tbsp"),
            ("garlic", 2, "clove"),
            ("rice", 1.5, "cup"),
        ),
        "Press and cube the tofu. Stir fry with the vegetables and soy sauce. Serve over rice.",
    ),
    CatalogRecipe(
        "Chickpea Coconut Curry",
        "Creamy one-pot curry with spinach.",
        (L, D),
        30,
        4,
        (
            ("chickpeas", 2, "can"),
            ("coconut milk", 1, "can"),
            ("onion", 1, ""),
            ("garlic", 3, "clove"),
            ("curry powder", None, ""),
            ("spinach", 2, "cup"),
            ("rice", 1.5, "cup"),
        ),
        "Soften onion and garlic, add curry powder, chickpeas and coconut milk. Simmer 15 "
        "minutes, stir in spinach and serve over rice.",
    ),
    CatalogRecipe(
        "Black Bean Tacos",
        "Smoky beans, avocado and lime.",
        (D,),
        20,
        4,
        (
            ("corn tortillas", 8, ""),
            ("black beans", 2, "can"),
            ("avocado", 1, ""),
            ("salsa", 0.5, "cup"),
            ("lime", 1, ""),
            ("onion", 0.5, ""),
        ),
        "Warm the beans with diced onion. Fill warm tortillas with beans, avocado and salsa. "
        "Squeeze over lime.",
    ),
    CatalogRecipe(
        "Garlic Butter Salmon",
        "Pan-seared salmon with rice and broccoli.",
        (D,),
        25,
        2,
        (
            ("salmon fillet", 1, "lb"),
            ("butter", 2, "tbsp"),
            ("garlic", 3, "clove"),
            ("lemon", 1, ""),
            ("rice", 1, "cup"),
            ("broccoli", 2, "cup"),
        ),
        "Sear the salmon, then baste with garlic butter and lemon. Serve with rice and "
        "steamed broccoli.",
    ),
    CatalogRecipe(
        "Pasta Primavera",
        "One-pot pasta loaded with vegetables.",
        (D,),
        25,
        4,
        (
            ("pasta", 1, "lb"),
            ("broccoli", 2, "cup"),
            ("bell pepper", 1, ""),
            ("frozen peas", 1, "cup"),
            ("garlic", 3, "clove"),
            ("olive oil", 2, "tbsp"),
            ("parmesan", 0.5, "cup"),
        ),
        "Cook the pasta, adding the vegetables for the last 3 minutes. Toss with garlic oil "
        "and parmesan.",
    ),
    CatalogRecipe(
        "Shrimp Fried Rice",
        "Better than takeout in 20 minutes.",
        (D,),
        20,
        3,
        (
            ("shrimp", 0.75, "lb"),
            ("rice", 1.5, "cup"),
            ("eggs", 2, ""),
            ("frozen peas", 1, "cup"),
            ("carrots", 2, ""),
            ("soy sauce", 3, "tbsp"),
            ("green onion", 1, "bunch"),
        ),
        "Cook the rice ahead. Stir fry shrimp and vegetables, push aside to scramble the "
        "eggs, then toss everything with rice and soy sauce.",
    ),
    CatalogRecipe(
        "Sheet Pan Chicken & Veggies",
        "Everything roasts together on one tray.",
        (D,),
        45,
        4,
        (
            ("chicken thighs", 2, "lb"),
            ("potatoes", 4, ""),
            ("carrots", 4, ""),
            ("broccoli", 2, "cup"),
            ("olive oil", 3, "tbsp"),
            ("garlic", 4, "clove"),
            ("paprika", None, ""),
        ),
        "Toss everything with oil and spices on a sheet pan. Roast at 425°F for 35 minutes.",
    ),
    CatalogRecipe(
        "Stuffed Sweet Potatoes",
        "Baked sweet potatoes with beans and avocado.",
        (L, D),
        50,
        2,
        (
            ("sweet potatoes", 2, ""),
            ("black beans", 1, "can"),
            ("salsa", 0.25, "cup"),
            ("avocado", 1, ""),
            ("lime", 1, ""),
        ),
        "Bake the sweet potatoes for 45 minutes. Split and fill with warm beans, salsa and "
        "avocado.",
    ),
    CatalogRecipe(
        "Turkey Chili",
        "Hearty chili that tastes better the next day.",
        (L, D),
        60,
        6,
        (
            ("ground turkey", 1, "lb"),
            ("black beans", 2, "can"),
            ("crushed tomatoes", 28, "oz"),
            ("onion", 1, ""),
            ("bell pepper", 1, ""),
            ("chili powder", None, ""),
        ),
        "Brown the turkey with onion and pepper, add the rest and simmer 45 minutes.",
    ),
    CatalogRecipe(
        "Slow-Braised Beef Stew",
        "A weekend project: tender beef and vegetables.",
        (D,),
        150,
        6,
        (
            ("beef chuck", 2, "lb"),
            ("potatoes", 4, ""),
            ("carrots", 4, ""),
            ("onion", 1, ""),
            ("beef broth", 4, "cup"),
            ("crushed tomatoes", 14, "oz"),
        ),
        "Brown the beef, add vegetables, broth and tomatoes, and braise covered for " "2 hours.",
    ),
    CatalogRecipe(
        "Homemade Margherita Pizza",
        "Fresh pizza from scratch.",
        (D,),
        90,
        4,
        (
            ("pizza dough", 1, "lb"),
            ("crushed tomatoes", 14, "oz"),
            ("mozzarella", 2, "cup"),
            ("tomato", 2, ""),
            ("olive oil", 2, "tbsp"),
        ),
        "Let the dough rest, stretch it out, top with sauce, cheese and tomato slices. "
        "Bake at 500°F for 12 minutes.",
    ),
)

CATALOG_BY_NAME = {recipe.name.lower(): recipe for recipe in CATALOG}
