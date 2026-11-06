"""Builds a week of meals that fits a budget, time limit, diet and allergies.

Approach:
1. Keep catalog recipes that fit the time limit and don't conflict with any restriction.
2. Meals the user already planned (in "mix" mode) are locked in: they count toward the
   grocery list and budget, but are never swapped out. Only the open slots get filled.
3. Fill each open slot (day x meal) greedily. A recipe is scored on its *extra* grocery
   cost given what's already on the list (so a bag of rice bought for Monday makes rice
   dishes later in the week nearly free), how much of it the pantry covers, how often
   it's been used, and a little randomness so "shuffle" gives a different week.
   With macro goals, it's also scored on how close its macros come to what's left of
   that day's goal (each meal gets a share: breakfast 25%, lunch 35%, dinner 40%).
   One serving of a recipe is often too little for a high goal, so with goals each
   recipe can also be picked at 1.5 or 2 servings per person (bought for accordingly).
   Slots the user marked as dining out are skipped, and what they expect to spend
   eating out comes out of the grocery budget.
4. Price the grocery list in whole packages. While it's over budget, swap generated
   meals for alternatives that lower the total until it fits (or no swap helps).
"""

import datetime as dt
import math
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from ..data.catalog import CATALOG
from ..models import DiningOut, FoodRestriction, PantryItem, Recipe
from ..schemas import (
    DiningOutOut,
    GeneratedMeal,
    GeneratedPlan,
    GenerateRequest,
    IngredientIn,
    Nutrition,
    PlanRecipe,
    ShoppingItem,
)
from .matching import find_conflicts, normalize, pantry_coverage
from .nutrition import add, recipe_nutrition
from .pricing import cost_per_serving, purchase_cost
from .shopping import (
    Line,
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
# Each meal's share of a day's macro goals.
MEAL_SHARE = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.40}
# How much each goal counts when scoring a recipe against it, and how much macro fit
# counts against cost and variety overall.
GOAL_WEIGHTS = {"calories": 1.0, "protein_g": 1.0, "carbs_g": 0.5, "fat_g": 0.5}
MACRO_STRENGTH = 2.0
# Portion sizes (servings per person) the generator may pick when there are goals.
GOAL_PORTIONS = (1.0, 1.5, 2.0)
# A plan this far off a goal (on average) gets a note saying so.
GOAL_TOLERANCE = 0.15


@dataclass(frozen=True)
class _Candidate:
    name: str
    meal_types: tuple[str, ...]
    prep_minutes: int | None
    per_serving: float  # cost per person at this portion size
    pantry_share: float  # fraction of ingredients already in the pantry
    scaled: Portion  # ingredients scaled to the number of people and portions
    recipe: PlanRecipe  # what's sent back to the client
    portions: float = 1.0  # servings per person
    nutrition: Nutrition = field(default_factory=Nutrition)  # per person, this portion


@dataclass(frozen=True)
class _Slot:
    day: dt.date
    meal: str
    pick: _Candidate
    locked: bool = False  # planned by the user; never swapped


def _candidate(
    model: Recipe,
    meal_types: tuple[str, ...],
    people: int,
    pantry_names: set[str],
    portions: float = 1.0,
) -> _Candidate:
    have, _ = pantry_coverage(model, pantry_names)
    per_serving = cost_per_serving(model)
    nutrition = recipe_nutrition(model)
    return _Candidate(
        name=model.name,
        meal_types=meal_types,
        prep_minutes=model.prep_minutes,
        per_serving=per_serving * portions,
        pantry_share=len(have) / max(len(model.ingredients), 1),
        scaled=portion(model, people * portions),
        portions=portions,
        nutrition=add(None, nutrition, portions),
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
            nutrition=nutrition,
        ),
    )


def _with_portions(candidate: _Candidate, portions: float) -> _Candidate:
    """The same recipe at a different portion size (servings per person)."""
    factor = portions / candidate.portions
    return replace(
        candidate,
        portions=portions,
        per_serving=candidate.per_serving * factor,
        scaled=Portion(
            candidate.scaled.name,
            tuple(
                Line(i.name, None if i.quantity is None else i.quantity * factor, i.unit)
                for i in candidate.scaled.ingredients
            ),
        ),
        nutrition=add(None, candidate.nutrition, factor),
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
        candidate = _candidate(model, entry.meal_types, req.people, pantry_names)
        candidates.append(candidate)
        if req.macro_goals and req.macro_goals.targets():
            candidates += [_with_portions(candidate, p) for p in GOAL_PORTIONS if p != 1.0]
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
    planned: Sequence[tuple[dt.date, str, Recipe, float]] = (),
    dining_out: Sequence[DiningOut] = (),
) -> GeneratedPlan:
    """Generate a week. `planned` are the user's own meals to keep (mix mode), and
    `dining_out` the slots they're eating out for (left empty)."""
    rng = random.Random(req.seed)
    goals = req.macro_goals.targets() if req.macro_goals else {}
    pantry = list(pantry) if req.use_pantry else []
    if req.assume_staples:
        pantry += staple_items()
    pantry_names = {normalize(item.name) for item in pantry}
    candidates = _catalog_candidates(req, restrictions, pantry_names)

    locked = [
        _Slot(
            day,
            meal,
            _candidate(recipe, (meal,), req.people, pantry_names, portions or 1.0),
            locked=True,
        )
        for day, meal, recipe, portions in planned
    ]
    taken = {(slot.day, slot.meal) for slot in locked}
    taken |= {(d.day, d.meal_type) for d in dining_out}
    dining_total = round(sum(d.cost or 0 for d in dining_out), 2)
    # What's left for groceries once meals out are paid for.
    budget = max(req.weekly_budget - dining_total, 0)

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
    slot_budget = max(budget, 1) / max(len(wanted) + len(locked), 1)
    uses: Counter[str] = Counter(slot.pick.name for slot in locked)
    basket = _Basket(pantry_names)
    for slot in locked:
        basket.add(slot.pick.scaled)

    # Macros already eaten each day (planned meals), and meals eaten somewhere else
    # (dining out, or not planned at all), which use up their usual share of the goal.
    eaten: dict[dt.date, dict[str, float]] = {}
    for slot in locked:
        day_totals = eaten.setdefault(slot.day, dict.fromkeys(goals, 0.0))
        for name in goals:
            day_totals[name] += getattr(slot.pick.nutrition, name)
    dining_slots = {(d.day, d.meal_type) for d in dining_out}
    locked_slots = {(slot.day, slot.meal) for slot in locked}
    open_share = Counter()
    for day, meal in wanted:
        open_share[day] += MEAL_SHARE[meal]

    def slot_target(day: dt.date, meal: str) -> dict[str, float]:
        """What this meal should provide: the rest of the day's goal, split by share."""
        elsewhere = sum(
            MEAL_SHARE[m]
            for m in MEAL_ORDER
            if (day, m) not in locked_slots
            and (m not in req.meals or (day, m) in dining_slots or not pools[m])
        )
        share = MEAL_SHARE[meal] / max(open_share[day], 1e-9)
        day_totals = eaten.get(day, {})
        return {
            name: max(goal * (1 - elsewhere) - day_totals.get(name, 0.0), 0.0) * share
            for name, goal in goals.items()
        }

    def macro_penalty(candidate: _Candidate, target: dict[str, float], meal: str) -> float:
        nutrition = candidate.nutrition
        misses = [
            GOAL_WEIGHTS[name]
            * abs(getattr(nutrition, name) - wanted_amount)
            / max(goals[name] * MEAL_SHARE[meal], 1)
            for name, wanted_amount in target.items()
        ]
        return MACRO_STRENGTH * sum(misses) / sum(GOAL_WEIGHTS[name] for name in target)

    slots: list[_Slot] = list(locked)
    for day, meal in wanted:
        target = slot_target(day, meal) if goals else {}
        pool = pools[meal]
        # Allow repeats only as often as the pool size forces.
        cap = max(2, math.ceil(sum(1 for _, m in wanted if m == meal) / len(pool)))
        options = [c for c in pool if uses[c.name] < cap] or pool

        def score(candidate: _Candidate, target=target, meal=meal) -> float:
            return (
                basket.extra_cost(candidate.scaled) / slot_budget
                + uses[candidate.name] * 0.6
                - candidate.pantry_share * 0.5
                + rng.random() * 0.9
                + (macro_penalty(candidate, target, meal) if target else 0)
            )

        pick = min(options, key=score)
        if goals:
            day_totals = eaten.setdefault(day, dict.fromkeys(goals, 0.0))
            for name in goals:
                day_totals[name] += getattr(pick.nutrition, name)
            open_share[day] -= MEAL_SHARE[meal]
        basket.add(pick.scaled)
        uses[pick.name] += 1
        slots.append(_Slot(day, meal, pick))

    groceries, total = _groceries(slots, pantry)
    # Over budget, repeating cheap meals (batch cooking) beats overspending.
    max_uses = max(4, math.ceil(len(slots) / max(len(candidates), 1)) + 1)
    for _ in range(MAX_SWAPS):
        if total <= budget:
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
    if dining_out:
        count = len(dining_out)
        spend = f" (about ${dining_total:.2f}, taken out of your budget)" if dining_total else ""
        notes.append(
            f"Left {count} meal{'s' if count != 1 else ''} open because you're eating out"
            f"{spend}."
        )
    within_budget = total <= budget
    if slots and not within_budget:
        groceries_budget = (
            f"${budget:.2f} left for groceries after eating out"
            if dining_total
            else f"${req.weekly_budget:.2f} budget"
        )
        notes.append(
            f"The cheapest plan we could build costs about ${total:.2f}, above your "
            f"{groceries_budget}. Try fewer meals, a longer cooking time "
            "or adding what you already have to your pantry."
        )

    slots.sort(key=lambda slot: (slot.day, MEAL_ORDER.index(slot.meal)))
    daily = None
    for slot in slots:
        daily = add(daily, slot.pick.nutrition, 1 / req.days)
    if daily is not None:
        daily = _rounded(daily, whole=True)
    target = _daily_target(req, goals, slots, dining_slots) if goals else None
    if target is not None and daily is not None:
        notes.extend(_goal_notes(daily, target, goals))
    timed = [slot.pick.prep_minutes for slot in slots if slot.pick.prep_minutes is not None]
    return GeneratedPlan(
        meals=[
            GeneratedMeal(
                day=slot.day,
                meal_type=slot.meal,
                recipe=slot.pick.recipe,
                cost=round(slot.pick.per_serving * req.people, 2),
                locked=slot.locked,
                portions=slot.pick.portions,
                nutrition=_rounded(slot.pick.nutrition),
            )
            for slot in slots
        ],
        groceries=groceries,
        estimated_total=total,
        budget=req.weekly_budget,
        within_budget=within_budget,
        average_minutes=round(sum(timed) / len(timed)) if timed else None,
        notes=notes,
        dining_out=[DiningOutOut.model_validate(d) for d in dining_out],
        dining_out_total=dining_total,
        daily_nutrition=daily,
        daily_target=target,
    )


def _rounded(nutrition: Nutrition, whole: bool = False) -> Nutrition:
    grams = ("protein_g", "carbs_g", "fat_g")
    update = {name: round(getattr(nutrition, name), None if whole else 1) for name in grams}
    return nutrition.model_copy(update={"calories": round(nutrition.calories), **update})


_GOAL_LABELS = {"calories": "calories", "protein_g": "protein", "carbs_g": "carbs", "fat_g": "fat"}


def _daily_target(
    req: GenerateRequest,
    goals: dict[str, float],
    slots: list[_Slot],
    dining_slots: set[tuple[dt.date, str]],
) -> Nutrition:
    """The part of the daily goals that the planned home meals should cover, on average.

    A day with breakfast, lunch and dinner at home covers 100% of the goal; skipping
    breakfast or eating dinner out lowers it by that meal's share.
    """
    share = sum(MEAL_SHARE[slot.meal] for slot in slots) / req.days
    values = {name: round(goal * share) for name, goal in goals.items()}
    return Nutrition(**values, note=f"{round(share * 100)}% of your daily goals")


def _goal_notes(daily: Nutrition, target: Nutrition, goals: dict[str, float]) -> list[str]:
    """Say which goals the plan misses by more than GOAL_TOLERANCE."""
    misses = []
    for name in goals:
        wanted = getattr(target, name)
        actual = getattr(daily, name)
        if wanted and abs(actual - wanted) / wanted > GOAL_TOLERANCE:
            unit = "" if name == "calories" else "g"
            direction = "under" if actual < wanted else "over"
            misses.append(
                f"{_GOAL_LABELS[name]} {direction} ({actual:.0f}{unit} vs {wanted:.0f}{unit})"
            )
    if not misses:
        return []
    return [
        "Closest we could get to your daily goals with recipes that fit your budget, time "
        f"and diet: {', '.join(misses)}, per person per day. A bigger budget or more "
        "cooking time gives the planner more recipes to choose from."
    ]
