"""Recipe search and import from TheMealDB (https://www.themealdb.com).

Uses TheMealDB's free test API key "1", which they allow "during development of your
app or for educational use". Per their guidance, results are credited as:
"Recipe data and imagery: TheMealDB". Imported recipes keep a link back to TheMealDB
and to the original source when one is listed.
"""

import json
import re
import urllib.parse
import urllib.request
from fractions import Fraction

from ..schemas import IngredientIn
from .units import VOLUME_ML, WEIGHT_GRAMS, canonical_unit

API_BASE = "https://www.themealdb.com/api/json/v1/1"
MEAL_PAGE = "https://www.themealdb.com/meal/{id}"
TIMEOUT_SECONDS = 8
DEFAULT_SERVINGS = 4  # TheMealDB doesn't list servings

# Units that are counted rather than measured.
DISCRETE_UNITS = {"clove", "can", "slice", "bunch", "head", "stick", "jar", "packet", "sprig"}
_UNIT_ALIASES = {"tin": "can", "tins": "can", "fillet": "", "fillets": ""}
_UNICODE_FRACTIONS = {"½": " 1/2", "¼": " 1/4", "¾": " 3/4", "⅓": " 1/3", "⅔": " 2/3", "⅛": " 1/8"}
_AMOUNT = re.compile(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*([a-z][a-z .]*)?")


class MealDBError(Exception):
    """TheMealDB couldn't be reached or returned something unexpected."""


def fetch(path: str, params: dict) -> dict:
    """GET a TheMealDB endpoint. Tests replace this function to avoid network calls."""
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "ElevatePlate/1.0 (class project)"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except (OSError, ValueError) as exc:
        raise MealDBError("Couldn't reach TheMealDB right now. Please try again.") from exc


def search(query: str) -> list[dict]:
    return fetch("search.php", {"s": query}).get("meals") or []


def lookup(meal_id: str) -> dict | None:
    meals = fetch("lookup.php", {"i": meal_id}).get("meals") or []
    return meals[0] if meals else None


def parse_measure(text: str | None) -> tuple[float | None, str]:
    """Turn TheMealDB's free-text measures into (quantity, unit).

    "1 1/2 cups" -> (1.5, "cup"), "100g" -> (100, "g"), "2 large" -> (2, ""),
    "to serve" -> (None, "").
    """
    cleaned = (text or "").lower()
    for symbol, fraction in _UNICODE_FRACTIONS.items():
        cleaned = cleaned.replace(symbol, fraction)
    match = _AMOUNT.match(cleaned)
    if not match:
        return None, ""
    quantity = float(sum(Fraction(part) for part in match.group(1).split()))
    words = (match.group(2) or "").split()
    for candidate in (" ".join(words[:2]), " ".join(words[:1])):
        unit = canonical_unit(_UNIT_ALIASES.get(candidate, candidate))
        if unit in WEIGHT_GRAMS or unit in VOLUME_ML or unit in DISCRETE_UNITS:
            return quantity, unit
    return quantity, ""  # "2 large", "1 chopped": a count


def ingredients(meal: dict) -> list[IngredientIn]:
    items = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        if not name:
            continue
        quantity, unit = parse_measure(meal.get(f"strMeasure{i}"))
        items.append(IngredientIn(name=name.lower()[:120], quantity=quantity, unit=unit))
    return items


def description(meal: dict) -> str:
    kind = " · ".join(part for part in (meal.get("strCategory"), meal.get("strArea")) if part)
    credit = f"From TheMealDB: {MEAL_PAGE.format(id=meal['idMeal'])}"
    source = meal.get("strSource")
    original = f" (original recipe: {source})" if source else ""
    return f"{kind}. {credit}{original}" if kind else f"{credit}{original}"


def instructions(meal: dict) -> str:
    text = (meal.get("strInstructions") or "").replace("\r\n", "\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()
