"""Grocery prices (USD) per package, used for budget estimates.

Each entry is the package you'd actually buy: rice comes in a 2 lb bag (about 4.5 cups),
so a recipe needing 1.5 cups still means buying one bag.

Sources
-------
* Entries marked BLS use the U.S. Bureau of Labor Statistics "Average Price Data"
  (U.S. city average, September 2026; series IDs noted). BLS data is public domain:
  https://www.bls.gov/cpi/factsheets/average-prices.htm
  Per-pound prices were turned into package prices with typical package sizes and
  weights (e.g. a banana is about 0.4 lb, a white loaf is 20 oz / 20 slices).
* Everything else is a hand-written estimate of a typical US supermarket price.
  These are ballpark figures, not live store prices.
"""

from dataclasses import dataclass

BLS_PERIOD = "Sept 2026"
ESTIMATE = "Estimate"


@dataclass(frozen=True)
class Price:
    size: float  # how much one package holds, in `unit`
    unit: str  # "" means a count (eggs, bananas...)
    cost: float  # price of one package
    source: str = ESTIMATE
    # Optional food facts so recipe units can be converted to the package unit:
    g_per_cup: float | None = None  # density, for "1 cup" of something sold by weight
    g_each: float | None = None  # weight of one piece, for "3 carrots" sold by the pound


def _bls(series: str) -> str:
    return f"BLS average price, {BLS_PERIOD} ({series})"


PRICES: dict[str, Price] = {
    # ---------- Prices from BLS Average Price Data ----------
    "egg": Price(12, "", 2.27, _bls("APU0000708111")),  # $2.272 / dozen
    "milk": Price(1, "gallon", 4.11, _bls("APU0000709112")),  # $4.106 / gallon
    "bread": Price(20, "slice", 2.29, _bls("APU0000702111")),  # $1.830/lb x 20 oz loaf
    "ground beef": Price(1, "lb", 6.79, _bls("APU0000703112"), g_per_cup=225),
    "chicken breast": Price(
        2, "lb", 8.41, _bls("APU0000FF1101"), g_per_cup=140, g_each=200
    ),  # $4.203/lb, 2 lb pack
    "rice": Price(2, "lb", 2.24, _bls("APU0000701312"), g_per_cup=185),  # $1.118/lb, 2 lb bag
    "spaghetti": Price(1, "lb", 1.38, _bls("APU0000701322")),
    "pasta": Price(1, "lb", 1.38, _bls("APU0000701322"), g_per_cup=100),
    "banana": Price(1, "", 0.26, _bls("APU0000711211")),  # $0.656/lb x 0.4 lb
    "tomato": Price(1, "", 0.80, _bls("APU0000712311")),  # $1.992/lb x 0.4 lb
    "potato": Price(
        5, "lb", 4.95, _bls("APU0000712112"), g_per_cup=150, g_each=225
    ),  # $0.989/lb, 5 lb bag
    "cheddar cheese": Price(8, "oz", 3.07, _bls("APU0000710212"), g_per_cup=113),  # $6.133/lb
    "romaine lettuce": Price(1, "head", 2.05, _bls("APU0000712211")),  # lettuce, 1.25 lb
    "lettuce": Price(1, "head", 2.05, _bls("APU0000712211")),
    "flour": Price(5, "lb", 2.73, _bls("APU0000701111"), g_per_cup=125),  # $0.545/lb
    "butter": Price(1, "lb", 3.96, _bls("APU0000FS1101"), g_per_cup=227),
    "lemon": Price(1, "", 0.53, _bls("APU0000711412")),  # $2.128/lb x 0.25 lb
    "bacon": Price(1, "lb", 6.76, _bls("APU0000704111"), g_each=28),
    "sugar": Price(4, "lb", 4.08, _bls("APU0000715211"), g_per_cup=200),
    "coffee": Price(1, "lb", 9.33, _bls("APU0000717311"), g_per_cup=85),
    "ice cream": Price(0.5, "gallon", 5.93, _bls("APU0000710411")),
    "orange": Price(1, "", 0.86, _bls("APU0000711311")),  # $1.723/lb x 0.5 lb
    # ---------- Estimates: grains, bread & pasta ----------
    "rolled oat": Price(42, "oz", 4.50, g_per_cup=90),
    "granola": Price(12, "oz", 4.50, g_per_cup=120),
    "quinoa": Price(1, "lb", 5.00, g_per_cup=170),
    "flour tortilla": Price(8, "", 3.00),
    "corn tortilla": Price(30, "", 3.00),
    "tortilla": Price(8, "", 3.00),
    "pita": Price(6, "", 3.00),
    "pizza dough": Price(1, "lb", 3.50),
    "bagel": Price(6, "", 3.50),
    "english muffin": Price(6, "", 3.00),
    "noodle": Price(1, "lb", 2.50, g_per_cup=100),
    "breadcrumb": Price(15, "oz", 2.50, g_per_cup=108),
    # ---------- Estimates: dairy & eggs ----------
    "greek yogurt": Price(32, "oz", 5.50, g_per_cup=245),
    "yogurt": Price(32, "oz", 4.00, g_per_cup=245),
    "mozzarella": Price(8, "oz", 3.50, g_per_cup=113),
    "parmesan": Price(8, "oz", 5.00, g_per_cup=100),
    "feta": Price(6, "oz", 4.00, g_per_cup=150),
    "cheese slice": Price(16, "", 3.50),
    "cheese": Price(8, "oz", 3.50, g_per_cup=113),
    "cream cheese": Price(8, "oz", 2.50, g_per_cup=232),
    "sour cream": Price(16, "oz", 2.50, g_per_cup=230),
    "heavy cream": Price(1, "pint", 4.00),
    "cream": Price(1, "pint", 4.00),
    # ---------- Estimates: plant milks & proteins ----------
    "almond milk": Price(0.5, "gallon", 3.50),
    "oat milk": Price(0.5, "gallon", 4.00),
    "coconut milk": Price(1, "can", 2.50),
    "firm tofu": Price(14, "oz", 2.50),
    "tofu": Price(14, "oz", 2.50),
    "black bean": Price(1, "can", 1.10),
    "kidney bean": Price(1, "can", 1.10),
    "chickpea": Price(1, "can", 1.20),
    "lentil": Price(1, "lb", 2.00, g_per_cup=190),
    "hummus": Price(10, "oz", 3.50, g_per_cup=246),
    "peanut butter": Price(16, "oz", 3.50, g_per_cup=258),
    # ---------- Estimates: meat & seafood ----------
    "chicken thigh": Price(2, "lb", 6.50, g_per_cup=140, g_each=110),
    "chicken": Price(2, "lb", 6.50, g_per_cup=140),
    "beef chuck": Price(2, "lb", 14.00),
    "beef": Price(1, "lb", 7.50),
    "ground turkey": Price(1, "lb", 5.00, g_per_cup=225),
    "pork": Price(1, "lb", 4.50),
    "sausage": Price(1, "lb", 5.00, g_each=75),
    "ham": Price(1, "lb", 6.00),
    "salmon": Price(1, "lb", 10.00, g_each=170),
    "shrimp": Price(1, "lb", 9.00, g_per_cup=145),
    "tuna": Price(1, "can", 1.50),
    "white fish": Price(1, "lb", 8.00, g_each=150),
    # ---------- Estimates: produce ----------
    "apple": Price(1, "", 0.80),
    "blueberry": Price(1, "pint", 4.00),
    "strawberry": Price(1, "lb", 3.50, g_per_cup=150),
    "berry": Price(1, "pint", 4.00),
    "lime": Price(1, "", 0.40),
    "avocado": Price(1, "", 1.50),
    "spinach": Price(10, "oz", 3.50, g_per_cup=30),
    "kale": Price(1, "bunch", 2.50),
    "broccoli": Price(1, "lb", 2.50, g_per_cup=90),
    "cauliflower": Price(1, "head", 3.00),
    "bell pepper": Price(1, "", 1.25),
    "onion": Price(1, "", 0.70),
    "green onion": Price(1, "bunch", 1.00),
    "garlic": Price(10, "clove", 0.75),
    "ginger": Price(1, "", 0.75),
    "carrot": Price(2, "lb", 1.80, g_per_cup=128, g_each=61),
    "celery": Price(1, "bunch", 2.00),
    "cucumber": Price(1, "", 0.90),
    "zucchini": Price(1, "", 1.00),
    "mushroom": Price(8, "oz", 2.50, g_per_cup=70, g_each=18),
    "sweet potato": Price(1, "", 1.25),
    "corn": Price(1, "can", 1.10),
    "cabbage": Price(1, "head", 2.50),
    "cilantro": Price(1, "bunch", 1.00),
    "parsley": Price(1, "bunch", 1.00),
    "basil": Price(1, "bunch", 2.50),
    "frozen pea": Price(1, "lb", 2.00, g_per_cup=145),
    "pea": Price(1, "lb", 2.00, g_per_cup=145),
    "frozen mixed vegetable": Price(1, "lb", 2.00, g_per_cup=140),
    "tater tot": Price(32, "oz", 3.50, g_each=11),
    # ---------- Estimates: canned, sauces & condiments ----------
    "crushed tomato": Price(28, "oz", 2.50, g_per_cup=245),
    "canned tomato": Price(28, "oz", 2.50, g_per_cup=245),
    "tomato paste": Price(6, "oz", 1.00, g_per_cup=262),
    "tomato sauce": Price(15, "oz", 1.20, g_per_cup=245),
    "marinara sauce": Price(24, "oz", 3.00, g_per_cup=250),
    "vegetable broth": Price(4, "cup", 2.50),
    "chicken broth": Price(4, "cup", 2.50),
    "chicken stock": Price(4, "cup", 2.50),
    "beef broth": Price(4, "cup", 2.50),
    "salsa": Price(16, "oz", 3.50, g_per_cup=260),
    "soy sauce": Price(15, "fl oz", 3.00),
    "caesar dressing": Price(12, "fl oz", 3.50),
    "mayonnaise": Price(30, "fl oz", 4.50),
    "ketchup": Price(20, "oz", 2.50, g_per_cup=240),
    "mustard": Price(8, "oz", 1.50),
    "honey": Price(12, "oz", 4.50, g_per_cup=340),
    "maple syrup": Price(12, "fl oz", 7.00),
    "olive oil": Price(500, "ml", 7.00),
    "vegetable oil": Price(48, "fl oz", 4.00),
    "sunflower oil": Price(48, "fl oz", 4.50),
    "oil": Price(48, "fl oz", 4.00),
    "vinegar": Price(16, "fl oz", 2.00),
    # ---------- Estimates: spices & baking ----------
    "salt": Price(1, "", 1.00),
    "black pepper": Price(1, "", 3.00),
    "cinnamon": Price(1, "", 2.50),
    "cumin": Price(1, "", 2.50),
    "paprika": Price(1, "", 2.50),
    "chili powder": Price(1, "", 2.50),
    "curry powder": Price(1, "", 3.00),
    "oregano": Price(1, "", 2.50),
    "baking powder": Price(1, "", 2.50),
    "vanilla": Price(1, "", 5.00),
    # ---------- Estimates: ingredients common in TheMealDB recipes ----------
    "water": Price(1, "", 0.0, "Free (tap water)"),
    "pepper": Price(1, "", 3.00),  # ground black pepper
    "red pepper": Price(1, "", 1.25),  # UK name for a bell pepper
    "green pepper": Price(1, "", 1.25),
    "yellow pepper": Price(1, "", 1.25),
    "roasted pepper": Price(12, "oz", 3.50),
    "chilli": Price(1, "", 0.25),
    "chili": Price(1, "", 0.25),
    "scotch bonnet": Price(1, "", 0.30),
    "chilli powder": Price(1, "", 2.50),
    "cayenne pepper": Price(1, "", 2.50),
    "thyme": Price(1, "bunch", 2.00),
    "rosemary": Price(1, "bunch", 2.00),
    "mint": Price(1, "bunch", 2.00),
    "dill": Price(1, "bunch", 2.00),
    "chive": Price(1, "bunch", 2.00),
    "coriander": Price(1, "bunch", 1.00),  # UK name for cilantro
    "lemongrass": Price(1, "", 0.75),
    "bay leaf": Price(1, "", 3.00),
    "bay leave": Price(1, "", 3.00),
    "allspice": Price(1, "", 3.00),
    "garam masala": Price(1, "", 3.50),
    "clove": Price(1, "", 4.00),  # the spice; garlic is priced separately
    "cardamom": Price(1, "", 5.00),
    "nutmeg": Price(1, "", 3.50),
    "star anise": Price(1, "", 3.50),
    "turmeric": Price(1, "", 3.00),
    "saffron": Price(1, "", 8.00),
    "harissa": Price(1, "", 4.00),
    "sesame seed": Price(1, "", 3.00),
    "fish sauce": Price(7, "fl oz", 3.00),
    "oyster sauce": Price(9, "oz", 3.00),
    "worcestershire sauce": Price(10, "fl oz", 3.00),
    "hot sauce": Price(5, "fl oz", 2.50),
    "hotsauce": Price(5, "fl oz", 2.50),
    "curry paste": Price(4, "oz", 3.50),
    "vegetable stock": Price(4, "cup", 2.50),
    "fish stock": Price(4, "cup", 3.00),
    "beef stock": Price(4, "cup", 2.50),
    "stock": Price(4, "cup", 2.50),
    "cornstarch": Price(16, "oz", 2.00, g_per_cup=128),
    "starch": Price(16, "oz", 2.00, g_per_cup=128),
    "yeast": Price(3, "", 1.80),
    "shortcrust pastry": Price(1, "lb", 4.50),
    "puff pastry": Price(1, "lb", 5.00),
    "pastry": Price(1, "lb", 4.50),
    "white wine": Price(750, "ml", 9.00),
    "red wine": Price(750, "ml", 9.00),
    "creme fraiche": Price(8, "oz", 4.00, g_per_cup=240),
    "chorizo": Price(9, "oz", 5.00),
    "lamb": Price(1, "lb", 9.00, g_per_cup=225),
    "prawn": Price(1, "lb", 10.00, g_per_cup=145),
    "fish fillet": Price(1, "lb", 8.00, g_each=150),
    "steak": Price(1, "lb", 10.00, g_each=280),
    "shallot": Price(1, "", 0.50),
    "challot": Price(1, "", 0.50),
    "leek": Price(1, "", 1.25),
    "green bean": Price(1, "lb", 2.50, g_per_cup=110),
    "scallion": Price(1, "bunch", 1.00),
    "sweetcorn": Price(1, "can", 1.10),
    "bean sprout": Price(12, "oz", 2.50),
    "pumpkin": Price(1, "lb", 1.50),
    "olive": Price(6, "oz", 3.50),
    "peanut": Price(16, "oz", 3.50, g_per_cup=146),
    "cannellini bean": Price(1, "can", 1.20),
}

# Long-lasting basics most kitchens already have. The generator assumes these are at
# home unless told otherwise, since buying a full bottle for one recipe skews a budget.
STAPLES = frozenset(
    {
        "olive oil",
        "vegetable oil",
        "oil",
        "soy sauce",
        "salt",
        "black pepper",
        "cinnamon",
        "cumin",
        "paprika",
        "chili powder",
        "curry powder",
        "oregano",
        "water",
    }
)

# Ingredients that aren't in the table get one modest flat guess per recipe line,
# never multiplied by the quantity (8 "tater tots" must not mean 8 packages).
UNKNOWN_PACKAGE_COST = 3.00  # buying one of something we don't know
UNKNOWN_USAGE_COST = 0.75  # a recipe's share of something we don't know
