"""Builds a week of meals that fits a budget, time limit, diet and allergies.

Approach:
1. Keep catalog recipes that fit the time limit and don't conflict with any restriction.
2. Meals the user already planned (in "mix" mode) are locked in: they count toward the
   grocery list and budget, but are never swapped out. Only the open slots get filled.
3. Fill each open slot (day x meal) greedily. A recipe is scored on its *extra* grocery
   cost given what's already on the list (so a bag of rice bought for Monday makes rice
   dishes later in the week nearly free), how much of it the pantry covers, how often
   it's been used, and a little randomness so "shuffle" gives a different week.
4. Price the grocery list in whole packages. While it's over budget, swap generated
   meals for alternatives that lower the total until it fits (or no swap helps).
"""

import datetime as dt
import math
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from ..data.catalog import CATALOG
from ..models import FoodRestriction, PantryItem, Recipe
from ..schemas import (
    GeneratedMeal,
    GeneratedPlan,
    GenerateRequest,
    IngredientIn,
    PlanRecipe,
    ShoppingItem,
)
from .matching import find_conflicts, normalize, pantry_coverage
from .pricing import cost_per_serving, purchase_cost
from .shopping import (
    Portion,
    aggregate_ingredients,
    apply_pantry,
    portion,
    price_items,
    round_up_counts,
    staple_items,
)

MEAL_ORDER = ("breakfast", "lunch", "dinner")
MAX_SWAPS = 30


@dataclass(frozen=True)
class _Candidate:
    name: str
    meal_types: tuple[str, ...]
    prep_minutes: int | None
    per_serving: float
    pantry_share: float  # fraction of ingredients already in the pantry
    scaled: Portion  # ingredients scaled to the number of people
    recipe: PlanRecipe  # what's sent back to the client


@dataclass(frozen=True)
class _Slot:
    day: dt.date
    meal: str
    pick: _Candidate
    locked: bool = False  # planned by the user; never swapped


def _candidate(
    model: Recipe, meal_types: tuple[str, ...], people: int, pantry_names: set[str]
) -> _Candidate:
    have, _ = pantry_coverage(model, pantry_names)
    per_serving = cost_per_serving(model)
    return _Candidate(
        name=model.name,
        meal_types=meal_types,
        prep_minutes=model.prep_minutes,
        per_serving=per_serving,
        pantry_share=len(have) / max(len(model.ingredients), 1),
        scaled=portion(model, people),
        recipe=PlanRecipe(
            name=model.name,
            description=model.description or "",
            instructions=model.instructions or "",
            servings=model.servings,
            prep_minutes=model.prep_minutes,
            ingredients=[
                IngredientIn(name=i.name, quantity=i.quantity, unit=i.unit)
                for i in model.ingredients
            ],
            cost_per_serving=per_serving,
        ),
    )


def _catalog_candidates(
    req: GenerateRequest, restrictions: Sequence[FoodRestriction], pantry_names: set[str]
) -> list[_Candidate]:
    candidates = []
    for entry in CATALOG:
        if req.max_minutes is not None and entry.prep_minutes > req.max_minutes:
            continue
        model = entry.to_model()
        if find_conflicts(model, restrictions):
            continue
        candidates.append(_candidate(model, entry.meal_types, req.people, pantry_names))
    return candidates


def _groceries(
    slots: list[_Slot], pantry: Sequence[PantryItem]
) -> tuple[list[ShoppingItem], float]:
    items = round_up_counts(aggregate_ingredients(slot.pick.scaled for slot in slots))
    apply_pantry(items, pantry)
    return items, price_items(items)


class _Basket:
    """Running totals of what's been added to the list, to price the next recipe."""

    def __init__(self, owned: set[str]):
        self.owned = owned
        self.amounts: dict[tuple[str, str], float | None] = {}

    def extra_cost(self, recipe: Portion) -> float:
        extra = 0.0
        for line in recipe.ingredients:
            name = normalize(line.name)
            if name in self.owned:
                continue
            key = (name, normalize(line.unit))
            if key not in self.amounts:
                extra += purchase_cost(line.name, line.quantity, line.unit)[0]
            elif line.quantity is not None and self.amounts[key] is not None:
                before = self.amounts[key]
                extra += (
                    purchase_cost(line.name, before + line.quantity, line.unit)[0]
                    - purchase_cost(line.name, before, line.unit)[0]
                )
        return extra

    def add(self, recipe: Portion) -> None:
        for line in recipe.ingredients:
            key = (normalize(line.name), normalize(line.unit))
            if key not in self.amounts:
                self.amounts[key] = line.quantity
            elif line.quantity is not None and self.amounts[key] is not None:
                self.amounts[key] += line.quantity


def _cheaper_plan(
    slots: list[_Slot], pools: dict[str, list[_Candidate]], total: float, pantry, max_uses: int
) -> tuple[list[_Slot], float] | None:
    """Find one swap of generated meals that lowers the grocery total.

    First tries replacing *every* generated occurrence of a recipe (dropping a pricey
    ingredient only saves money once nothing else needs it), then single meals,
    priciest first. Locked (user-planned) meals are never touched.
    """
    uses = Counter(slot.pick.name for slot in slots)
    free = [i for i, slot in enumerate(slots) if not slot.locked]
    per_serving = {slots[i].pick.name: slots[i].pick.per_serving for i in free}

    for name in sorted(per_serving, key=lambda n: -per_serving[n]):
        indexes = {i for i in free if slots[i].pick.name == name}
        meals_needed = {slots[i].meal for i in indexes}
        alternatives = {
            c.name: c
            for meal in meals_needed
            for c in pools[meal]
            if c.name != name
            and meals_needed <= set(c.meal_types)
            and uses[c.name] + len(indexes) <= max_uses + 1
        }
        for alt in sorted(alternatives.values(), key=lambda c: c.per_serving):
            trial = [
                _Slot(slot.day, slot.meal, alt) if i in indexes else slot
                for i, slot in enumerate(slots)
            ]
            _, trial_total = _groceries(trial, pantry)
            if trial_total < total:
                return trial, trial_total

    for index in sorted(free, key=lambda i: -slots[i].pick.per_serving):
        slot = slots[index]
        for alt in sorted(pools[slot.meal], key=lambda c: c.per_serving):
            if alt.name == slot.pick.name or uses[alt.name] >= max_uses:
                continue
            trial = [*slots[:index], _Slot(slot.day, slot.meal, alt), *slots[index + 1 :]]
            _, trial_total = _groceries(trial, pantry)
            if trial_total < total:
                return trial, trial_total
    return None


def generate_plan(
    req: GenerateRequest,
    restrictions: Sequence[FoodRestriction],
    pantry: Sequence[PantryItem],
    planned: Sequence[tuple[dt.date, str, Recipe]] = (),
) -> GeneratedPlan:
    """Generate a week. `planned` are the user's own meals to keep (mix mode)."""
    rng = random.Random(req.seed)
    pantry = list(pantry) if req.use_pantry else []
    if req.assume_staples:
        pantry += staple_items()
    pantry_names = {normalize(item.name) for item in pantry}
    candidates = _catalog_candidates(req, restrictions, pantry_names)

    locked = [
        _Slot(day, meal, _candidate(recipe, (meal,), req.people, pantry_names), locked=True)
        for day, meal, recipe in planned
    ]
    taken = {(slot.day, slot.meal) for slot in locked}

    meals = [meal for meal in MEAL_ORDER if meal in req.meals]
    pools = {meal: [c for c in candidates if meal in c.meal_types] for meal in MEAL_ORDER}
    notes = [
        f"No {meal} recipes fit your time limit, diet and allergies, so {meal} was left open."
        for meal in meals
        if not pools[meal]
    ]

    wanted = []
    for offset in range(req.days):
        day = req.start + dt.timedelta(days=offset)
        wanted += [(day, meal) for meal in meals if pools[meal] and (day, meal) not in taken]
    slot_budget = req.weekly_budget / max(len(wanted) + len(locked), 1)
    uses: Counter[str] = Counter(slot.pick.name for slot in locked)
    basket = _Basket(pantry_names)
    for slot in locked:
        basket.add(slot.pick.scaled)

    slots: list[_Slot] = list(locked)
    for day, meal in wanted:
        pool = pools[meal]
        # Allow repeats only as often as the pool size forces.
        cap = max(2, math.ceil(sum(1 for _, m in wanted if m == meal) / len(pool)))
        options = [c for c in pool if uses[c.name] < cap] or pool

        def score(candidate: _Candidate) -> float:
            return (
                basket.extra_cost(candidate.scaled) / slot_budget
                + uses[candidate.name] * 0.6
                - candidate.pantry_share * 0.5
                + rng.random() * 0.9
            )

        pick = min(options, key=score)
        basket.add(pick.scaled)
        uses[pick.name] += 1
        slots.append(_Slot(day, meal, pick))

    groceries, total = _groceries(slots, pantry)
    # Over budget, repeating cheap meals (batch cooking) beats overspending.
    max_uses = max(4, math.ceil(len(slots) / max(len(candidates), 1)) + 1)
    for _ in range(MAX_SWAPS):
        if total <= req.weekly_budget:
            break
        cheaper = _cheaper_plan(slots, pools, total, pantry, max_uses)
        if cheaper is None:
            break
        slots, total = cheaper
        groceries, total = _groceries(slots, pantry)

    if locked:
        generated = len(slots) - len(locked)
        notes.insert(
            0,
            f"Kept your {len(locked)} planned meal{'s' if len(locked) != 1 else ''} and "
            f"filled {generated} open slot{'s' if generated != 1 else ''}."
            if generated
            else f"Your {len(locked)} planned meals already fill every slot you asked for.",
        )
    within_budget = total <= req.weekly_budget
    if slots and not within_budget:
        notes.append(
            f"The cheapest plan we could build costs about ${total:.2f}, above your "
            f"${req.weekly_budget:.2f} budget. Try fewer meals, a longer cooking time "
            "or adding what you already have to your pantry."
        )

    slots.sort(key=lambda slot: (slot.day, MEAL_ORDER.index(slot.meal)))
    timed = [slot.pick.prep_minutes for slot in slots if slot.pick.prep_minutes is not None]
    return GeneratedPlan(
        meals=[
            GeneratedMeal(
                day=slot.day,
                meal_type=slot.meal,
                recipe=slot.pick.recipe,
                cost=round(slot.pick.per_serving * req.people, 2),
                locked=slot.locked,
            )
            for slot in slots
        ],
        groceries=groceries,
        estimated_total=total,
        budget=req.weekly_budget,
        within_budget=within_budget,
        average_minutes=round(sum(timed) / len(timed)) if timed else None,
        notes=notes,
    )
