"""Typical US supermarket prices (USD), per package, used for budget estimates.

Each entry is the package you'd actually buy: e.g. rice comes in a bag of about
20 cups for $5.00, so a recipe needing 1.5 cups still means buying one bag.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Price:
    size: float  # how much one package holds, in `unit`
    unit: str  # "" means a count (eggs, bananas...)
    cost: float  # price of one package


PRICES: dict[str, Price] = {
    # Grains, bread & pasta
    "rolled oat": Price(10, "cup", 4.50),
    "granola": Price(4, "cup", 4.50),
    "rice": Price(20, "cup", 5.00),
    "quinoa": Price(3, "cup", 5.00),
    "spaghetti": Price(1, "lb", 1.50),
    "pasta": Price(1, "lb", 1.50),
    "bread": Price(20, "slice", 3.50),
    "flour tortilla": Price(8, "", 3.00),
    "corn tortilla": Price(30, "", 3.00),
    "pita": Price(6, "", 3.00),
    "flour": Price(15, "cup", 4.00),
    "pizza dough": Price(1, "lb", 3.50),
    # Dairy & eggs
    "milk": Price(16, "cup", 4.00),
    "greek yogurt": Price(4, "cup", 5.50),
    "butter": Price(32, "tbsp", 5.00),
    "cheddar cheese": Price(2, "cup", 3.50),
    "mozzarella": Price(2, "cup", 3.50),
    "parmesan": Price(1.5, "cup", 5.00),
    "feta": Price(1, "cup", 4.00),
    "egg": Price(12, "", 3.50),
    # Plant milks & proteins
    "almond milk": Price(8, "cup", 3.50),
    "coconut milk": Price(1, "can", 2.50),
    "firm tofu": Price(14, "oz", 2.50),
    "black bean": Price(1, "can", 1.10),
    "chickpea": Price(1, "can", 1.20),
    "lentil": Price(2.5, "cup", 2.00),
    "hummus": Price(1.25, "cup", 3.50),
    "peanut butter": Price(28, "tbsp", 3.50),
    # Meat & seafood
    "chicken breast": Price(2, "lb", 9.00),
    "chicken thigh": Price(2, "lb", 6.50),
    "ground beef": Price(1, "lb", 5.50),
    "beef chuck": Price(2, "lb", 14.00),
    "ground turkey": Price(1, "lb", 5.00),
    "salmon fillet": Price(1, "lb", 10.00),
    "shrimp": Price(1, "lb", 9.00),
    "tuna": Price(1, "can", 1.50),
    # Produce
    "banana": Price(6, "", 1.80),
    "apple": Price(6, "", 4.50),
    "blueberry": Price(2, "cup", 4.00),
    "lemon": Price(1, "", 0.60),
    "lime": Price(1, "", 0.40),
    "avocado": Price(1, "", 1.50),
    "spinach": Price(6, "cup", 3.50),
    "romaine lettuce": Price(1, "head", 2.50),
    "broccoli": Price(4, "cup", 2.50),
    "bell pepper": Price(1, "", 1.25),
    "onion": Price(3, "", 2.00),
    "green onion": Price(1, "bunch", 1.00),
    "garlic": Price(10, "clove", 0.75),
    "ginger": Price(1, "", 0.75),
    "carrot": Price(8, "", 1.50),
    "potato": Price(8, "", 4.00),
    "sweet potato": Price(1, "", 1.25),
    "tomato": Price(1, "", 0.80),
    "cucumber": Price(1, "", 0.90),
    "frozen pea": Price(4, "cup", 2.00),
    # Canned, sauces & condiments
    "crushed tomato": Price(28, "oz", 2.50),
    "vegetable broth": Price(4, "cup", 2.50),
    "beef broth": Price(4, "cup", 2.50),
    "salsa": Price(2, "cup", 3.50),
    "soy sauce": Price(32, "tbsp", 3.00),
    "caesar dressing": Price(1.5, "cup", 3.50),
    "honey": Price(16, "tbsp", 4.50),
    "olive oil": Price(34, "tbsp", 7.00),
    # Spices
    "cinnamon": Price(1, "", 2.50),
    "cumin": Price(1, "", 2.50),
    "paprika": Price(1, "", 2.50),
    "chili powder": Price(1, "", 2.50),
    "curry powder": Price(1, "", 3.00),
}

# Long-lasting basics most kitchens already have. The generator assumes these are at
# home unless told otherwise, since buying a full bottle for one recipe skews a budget.
STAPLES = frozenset(
    {"olive oil", "soy sauce", "cinnamon", "cumin", "paprika", "chili powder", "curry powder"}
)

# Used when an ingredient isn't in the table.
DEFAULT_PRICE = Price(1, "", 3.00)
