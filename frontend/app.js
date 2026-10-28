"use strict";

// =====================================================================
// Constants
// =====================================================================

const MEALS = [
  { key: "breakfast", label: "Breakfast", icon: "sunrise" },
  { key: "lunch", label: "Lunch", icon: "sun" },
  { key: "dinner", label: "Dinner", icon: "moon" },
];
const MEAL_BY_KEY = Object.fromEntries(MEALS.map((m) => [m.key, m]));
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const COMMON_RESTRICTIONS = ["Dairy", "Gluten", "Nuts", "Peanuts", "Eggs", "Shellfish", "Fish", "Soy", "Meat"];
const COMMON_UNITS = ["cup", "tbsp", "tsp", "g", "kg", "oz", "lb", "ml", "l", "clove", "slice", "can", "jar", "bag", "head", "bunch"];
const AVATAR_COLORS = ["#ffd43b", "#63e6be", "#b197fc", "#ffa94d", "#74c0fc", "#ff8787", "#c0eb75"];
const CONFETTI_COLORS = ["#ffd43b", "#63e6be", "#b197fc", "#ff8787", "#74c0fc", "#ffa94d"];

// First match wins, so put specific patterns before general ones.
const RECIPE_ICONS = [
  [/egg|omelet|scramble|frittata/, "egg"], [/salmon|fish|tuna|shrimp|prawn/, "fish"], [/pizza/, "pizza"],
  [/soup|stew|chili|curry/, "soup"], [/salad|bowl|primavera/, "salad"], [/chicken|turkey/, "drumstick"],
  [/beef|bolognese|burger|steak/, "beef"], [/oat|parfait|granola|yogurt|smoothie/, "milk"],
  [/pancake|waffle|toast|sandwich|pita|wrap|burrito|quesadilla|taco/, "sandwich"],
  [/rice|stir fry|fried|noodle/, "cooking-pot"], [/sweet potato|potato|veggie/, "carrot"],
  [/pasta|spaghetti/, "utensils-crossed"],
];
const FOOD_ICONS = [
  [/peanut|almond|walnut|cashew|pecan|\bnuts?\b/, "nut", "legume"],
  [/egg/, "egg", "dairy"],
  [/milk|yogurt|cream|cheese|parmesan|mozzarella|cheddar|feta|butter/, "milk", "dairy"],
  [/chicken|turkey/, "drumstick", "protein"],
  [/beef|steak|pork|lamb|bacon|ham|sausage/, "beef", "protein"],
  [/salmon|fish|tuna|cod/, "fish", "protein"],
  [/shrimp|prawn|crab|lobster|clam|mussel/, "shell", "protein"],
  [/bean|chickpea|lentil|tofu|hummus|\bpeas?\b|edamame/, "bean", "legume"],
  [/bread|toast|bun|bagel|pita|tortilla|croissant|dough/, "croissant", "grain"],
  [/rice|oat|flour|grain|quinoa|granola|cereal|pasta|spaghetti|noodle/, "wheat", "grain"],
  [/carrot/, "carrot", "produce"], [/apple/, "apple", "produce"], [/banana/, "banana", "produce"],
  [/berr|cherr/, "cherry", "produce"], [/lemon|lime|orange/, "citrus", "produce"], [/grape/, "grape", "produce"],
  [/spinach|lettuce|romaine|kale|green|broccoli|cabbage|herb|cilantro|basil/, "leafy-green", "produce"],
  [/onion|garlic|pepper|tomato|cucumber|avocado|potato|corn|mushroom|ginger|squash|zucchini/, "sprout", "produce"],
  [/cinnamon|cumin|paprika|chili|curry|spice|salt|seasoning/, "flame", "spice"],
  [/oil|honey|syrup|sauce|salsa|dressing|broth|paste|vinegar|ketchup/, "droplet", "pantry"],
  [/coffee/, "coffee", "pantry"],
];

// =====================================================================
// State
// =====================================================================

const state = {
  recipes: [],
  plan: [],
  pantry: [],
  restrictions: [],
  profile: null,
  shopping: null, // last shopping-list response (drives the budget chip & ring)
  weekStart: mondayOf(new Date()),
  editingRecipeId: null,
  hideConflicts: readSetting("hideConflicts", true),
  recipeMaxMinutes: "",
  generated: null,
  generatorSeed: Math.floor(Math.random() * 1e6),
  generatorStart: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// =====================================================================
// Helpers
// =====================================================================

function readSetting(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : JSON.parse(value);
  } catch {
    return fallback;
  }
}

function writeSetting(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch { /* storage unavailable: the setting just won't persist */ }
}

function mondayOf(date) {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); // Monday = 0
  return d;
}

function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

/** YYYY-MM-DD in local time (toISOString would shift to UTC). */
function isoDate(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function parseIsoDate(text) {
  const [y, m, d] = text.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function formatShort(date) {
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function weekLabel(start = state.weekStart) {
  return `${formatShort(start)} – ${formatShort(addDays(start, 6))}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

function formatQuantity(quantity, unit) {
  if (quantity == null) return unit || "";
  const qty = Number.isInteger(quantity) ? quantity : Number(quantity.toFixed(2));
  return unit ? `${qty} ${unit}` : String(qty);
}

const money = (value, decimals = 2) => `$${Number(value || 0).toFixed(decimals)}`;

/** Mirrors backend normalize(): lowercase, collapse spaces, singularize the last word. */
function normalizeName(text) {
  const words = String(text).toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return "";
  let last = words[words.length - 1];
  if (last.length > 4 && last.endsWith("ies")) last = last.slice(0, -3) + "y";
  else if (last.length > 4 && /(oes|ches|shes|xes)$/.test(last)) last = last.slice(0, -2);
  else if (last.length > 3 && last.endsWith("s") && !/(ss|us)$/.test(last)) last = last.slice(0, -1);
  words[words.length - 1] = last;
  return words.join(" ");
}

const icon = (name, extra = "") => `<i data-lucide="${name}"${extra ? ` class="${extra}"` : ""}></i>`;

function refreshIcons() {
  window.lucide?.createIcons();
}

function hashIndex(text, size) {
  let hash = 0;
  for (const ch of String(text)) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return hash % size;
}

function recipeAvatar(name, size = "") {
  const lower = String(name).toLowerCase();
  const iconName = RECIPE_ICONS.find(([pattern]) => pattern.test(lower))?.[1] ?? "chef-hat";
  const color = AVATAR_COLORS[hashIndex(name, AVATAR_COLORS.length)];
  return `<div class="avatar ${size}" style="--avatar:${color}">${icon(iconName)}</div>`;
}

function foodIcon(name, size = "") {
  const lower = String(name).toLowerCase();
  const [, iconName, tone] = FOOD_ICONS.find(([pattern]) => pattern.test(lower)) ?? [null, "package", "pantry"];
  return `<span class="food-icon ${size} tone-${tone}">${icon(iconName)}</span>`;
}

function pantryNames() {
  return new Set(state.pantry.map((item) => normalizeName(item.name)));
}

const CONFLICT_ICONS = { allergy: "shield-alert", dislike: "thumbs-down", diet: "leaf" };

/** One badge per restriction, even if several ingredients trigger it. */
function conflictBadges(recipe) {
  const seen = new Map();
  for (const c of recipe.conflicts) {
    const key = c.kind === "diet" ? "diet" : c.restriction; // one badge for the whole diet
    if (!seen.has(key)) seen.set(key, c);
  }
  return [...seen.values()]
    .map((c) => `<span class="badge ${c.kind}" title="Contains ${escapeHtml(c.ingredient)}">
        ${icon(CONFLICT_ICONS[c.kind])}${escapeHtml(c.kind === "diet" ? `Not ${state.profile?.diet}` : c.restriction)}</span>`)
    .join("");
}

// ---------- Motion helpers ----------

/** Smoothly count a number up/down inside an element. */
function animateNumber(el, to, format) {
  const from = Number(el.dataset.value ?? 0);
  el.dataset.value = to;
  if (reduceMotion || from === to) {
    el.textContent = format(to);
    return;
  }
  const start = performance.now();
  const duration = 900;
  const step = (now) => {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = format(from + (to - from) * eased);
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function setRing(circle, ratio) {
  const circumference = 2 * Math.PI * 50;
  const clamped = Math.max(0, Math.min(ratio, 1));
  circle.style.strokeDashoffset = String(circumference * (1 - clamped));
  circle.classList.toggle("over", ratio > 1);
  circle.style.opacity = ratio > 0 ? "1" : "0"; // a zero-length round cap still draws a dot
}

function confetti(fromEl) {
  if (reduceMotion) return;
  const rect = fromEl.getBoundingClientRect();
  for (let i = 0; i < 26; i++) {
    const piece = document.createElement("span");
    piece.className = "confetti";
    const angle = Math.random() * Math.PI * 2;
    const distance = 80 + Math.random() * 140;
    piece.style.left = `${rect.left + rect.width / 2}px`;
    piece.style.top = `${rect.top + rect.height / 2}px`;
    piece.style.background = CONFETTI_COLORS[i % CONFETTI_COLORS.length];
    piece.style.borderRadius = i % 3 === 0 ? "50%" : "3px";
    piece.style.setProperty("--dx", `${Math.cos(angle) * distance}px`);
    piece.style.setProperty("--dy", `${Math.sin(angle) * distance - 60}px`);
    piece.style.setProperty("--rot", `${Math.random() * 720 - 360}deg`);
    document.body.appendChild(piece);
    setTimeout(() => piece.remove(), 1100);
  }
}

// Ripple on every button press.
document.addEventListener("pointerdown", (event) => {
  const button = event.target.closest(".btn");
  if (!button || reduceMotion) return;
  const rect = button.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  ripple.style.width = ripple.style.height = `${size}px`;
  ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
  ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
  button.appendChild(ripple);
  setTimeout(() => ripple.remove(), 650);
});

// Subtle 3D tilt on the planning-mode cards.
$$(".mode-card").forEach((card) => {
  card.addEventListener("pointermove", (event) => {
    if (reduceMotion || card.getAttribute("aria-checked") === "true") return;
    const rect = card.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    card.style.transform = `translateY(-4px) rotateX(${-y * 6}deg) rotateY(${x * 8}deg)`;
  });
  card.addEventListener("pointerleave", () => { card.style.transform = ""; });
});

let toastTimer;
function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d) => d.msg).join(", ");
    } catch { /* non-JSON error body */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

async function run(action, successMessage) {
  try {
    await action();
    if (successMessage) toast(successMessage);
  } catch (err) {
    toast(err.message, true);
  }
}

// =====================================================================
// Data loading
// =====================================================================

const loaders = {
  recipes: async () => { state.recipes = await api("/api/recipes"); },
  plan: async () => { state.plan = await api(`/api/plan?start=${isoDate(state.weekStart)}`); },
  pantry: async () => { state.pantry = await api("/api/pantry"); },
  restrictions: async () => { state.restrictions = await api("/api/restrictions"); },
  profile: async () => { state.profile = await api("/api/profile"); },
  shopping: async () => { state.shopping = await api(`/api/shopping-list?start=${isoDate(state.weekStart)}`); },
};

async function reload(...names) {
  await Promise.all(names.map((name) => loaders[name]()));
  if (!names.includes("shopping") && names.some((n) => ["plan", "pantry", "recipes", "profile"].includes(n))) {
    await loaders.shopping();
  }
  renderBudgetChip();
}

async function saveProfile(changes) {
  state.profile = await api("/api/profile", { method: "PUT", body: { ...state.profile, ...changes } });
}

// =====================================================================
// Budget chip & home ring
// =====================================================================

function renderBudgetChip() {
  if (!state.shopping || !state.profile) return;
  const total = state.shopping.estimated_total;
  const budget = state.profile.weekly_budget;
  $("#budget-chip-text").textContent = `${money(total, 0)} / ${money(budget, 0)}`;
  $(".budget-chip").classList.toggle("over", budget > 0 && total > budget);

  const ratio = budget > 0 ? total / budget : 0;
  setRing($("#home-ring"), ratio);
  animateNumber($("#home-ring-value"), total, (v) => money(v, 0));
  $("#home-ring-sub").textContent = budget > 0 ? `of ${money(budget, 0)} this week` : "this week";
}

// =====================================================================
// Home: planning modes & generator
// =====================================================================

function renderHome() {
  const mode = state.profile.mode;
  $$(".mode-card").forEach((card) => card.setAttribute("aria-checked", String(card.dataset.mode === mode)));
  $("#manual-panel").hidden = mode !== "manual";
  $("#auto-panel").hidden = mode === "manual"; // auto and hybrid both use the generator
  $("#hybrid-info").hidden = mode !== "hybrid";
  $("#hybrid-count").innerHTML = `${state.plan.length}<small>/21</small>`;
  $("#hybrid-week").textContent = weekLabel();
  if (!$("#generate-btn").disabled) $("#generate-btn span").textContent = generateLabel();
  $("#manual-budget").value = state.profile.weekly_budget;
  $("#manual-people").value = state.profile.people;
  renderGeneratorForm();
  renderBudgetChip();
  refreshIcons();
}

$$(".mode-card").forEach((card) => {
  card.addEventListener("click", () => {
    card.style.transform = "";
    run(async () => {
      await saveProfile({ mode: card.dataset.mode });
      renderHome();
    });
  });
});

$("#manual-people").addEventListener("change", (event) => {
  const people = Math.round(Number(event.target.value));
  if (!(people >= 1 && people <= 12)) return toast("People must be between 1 and 12", true);
  draft.people = people;
  run(async () => {
    await saveProfile({ people });
    await reload("shopping");
  }, "Household size saved");
});

$("#manual-budget").addEventListener("change", (event) => {
  const value = Number(event.target.value);
  if (!(value >= 0)) return;
  run(async () => {
    await saveProfile({ weekly_budget: value });
    await reload("shopping");
  }, "Budget saved");
});

// ---------- Generator form ----------

/** The form keeps its own draft; it's saved to the profile when you generate. */
const draft = {};

function renderGeneratorForm() {
  if (!draft.loaded) {
    Object.assign(draft, {
      loaded: true,
      weekly_budget: state.profile.weekly_budget || 75,
      people: state.profile.people,
      max_minutes: state.profile.max_minutes,
      diet: state.profile.diet,
      meals: [...state.profile.meals],
      assume_staples: state.profile.assume_staples,
    });
  }
  $("#gen-staples").checked = draft.assume_staples;
  setBudgetInputs(draft.weekly_budget);
  $("#gen-people").textContent = draft.people;
  $$("#gen-time .chip").forEach((chip) =>
    chip.setAttribute("aria-pressed", String(chip.dataset.minutes === String(draft.max_minutes ?? ""))));
  $$("#gen-diet .chip").forEach((chip) => chip.setAttribute("aria-pressed", String(chip.dataset.diet === draft.diet)));
  $$("#gen-meals .chip").forEach((chip) => chip.setAttribute("aria-pressed", String(draft.meals.includes(chip.dataset.meal))));

  const count = state.restrictions.length;
  $("#gen-restrictions-note").innerHTML = count
    ? `${icon("shield-check")} Your ${count} allerg${count === 1 ? "y/dislike is" : "ies & dislikes are"} always respected.
       <button type="button" class="link-btn" data-goto="preferences">Edit</button>`
    : `No allergies or dislikes set. <button type="button" class="link-btn" data-goto="preferences">Add some</button>`;
}

function generateLabel(again = false) {
  if (state.profile.mode === "hybrid") return again ? "Fill the gaps again" : "Fill the gaps";
  return again ? "Regenerate my week" : "Generate my week";
}

function setBudgetInputs(value) {
  const range = $("#gen-budget-range");
  $("#gen-budget").value = value;
  range.value = Math.min(Math.max(value, Number(range.min)), Number(range.max));
  const pct = ((range.value - range.min) / (range.max - range.min)) * 100;
  range.style.setProperty("--fill", `${pct}%`);
}

$("#gen-budget-range").addEventListener("input", (event) => {
  draft.weekly_budget = Number(event.target.value);
  setBudgetInputs(draft.weekly_budget);
});

$("#gen-budget").addEventListener("input", (event) => {
  const value = Number(event.target.value);
  if (value > 0) {
    draft.weekly_budget = value;
    setBudgetInputs(value);
    $("#gen-budget").value = event.target.value; // keep what the user is typing
  }
});

$("#gen-staples").addEventListener("change", (event) => { draft.assume_staples = event.target.checked; });

$$("[data-people-step]").forEach((button) => {
  button.addEventListener("click", () => {
    draft.people = Math.min(12, Math.max(1, draft.people + Number(button.dataset.peopleStep)));
    const output = $("#gen-people");
    output.textContent = draft.people;
    output.classList.remove("bump");
    void output.offsetWidth; // restart the animation
    output.classList.add("bump");
  });
});

$("#gen-time").addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  draft.max_minutes = chip.dataset.minutes === "" ? null : Number(chip.dataset.minutes);
  renderGeneratorForm();
});

$("#gen-diet").addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  draft.diet = chip.dataset.diet;
  renderGeneratorForm();
});

$("#gen-meals").addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  const meal = chip.dataset.meal;
  if (draft.meals.includes(meal)) {
    if (draft.meals.length === 1) return toast("Pick at least one meal", true);
    draft.meals = draft.meals.filter((m) => m !== meal);
  } else {
    draft.meals = MEALS.map((m) => m.key).filter((m) => m === meal || draft.meals.includes(m));
  }
  renderGeneratorForm();
});

function setGenerating(button, busy, label) {
  button.disabled = busy;
  const iconEl = button.querySelector("svg, i");
  iconEl?.classList.toggle("spin", busy);
  if (label) button.querySelector("span").textContent = label;
}

async function generate({ reshuffle = false } = {}) {
  if (reshuffle) state.generatorSeed = Math.floor(Math.random() * 1e6);
  await saveProfile({
    weekly_budget: draft.weekly_budget,
    people: draft.people,
    max_minutes: draft.max_minutes,
    diet: draft.diet,
    meals: draft.meals,
    assume_staples: draft.assume_staples,
  });
  // Plan the week currently shown in the planner (this week by default).
  state.generatorStart = isoDate(state.weekStart);
  state.generated = await api("/api/generator", {
    method: "POST",
    body: {
      start: state.generatorStart,
      weekly_budget: draft.weekly_budget,
      people: draft.people,
      max_minutes: draft.max_minutes,
      diet: draft.diet,
      meals: draft.meals,
      use_pantry: $("#gen-use-pantry").checked,
      assume_staples: draft.assume_staples,
      fill_gaps: state.profile.mode === "hybrid",
      seed: state.generatorSeed,
    },
  });
  await reload("recipes"); // the diet may have changed what's flagged
  renderGenerated();
}

$("#generator-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const button = $("#generate-btn");
  setGenerating(button, true, "Building your week...");
  run(async () => {
    await generate();
    // Wait a frame so the results are laid out before scrolling to them.
    requestAnimationFrame(() =>
      $("#gen-result").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" }));
  }).finally(() => setGenerating(button, false, generateLabel(true)));
});

$("#shuffle-btn").addEventListener("click", () => {
  const button = $("#shuffle-btn");
  $$("#gen-week .meal-card").forEach((card) => card.classList.add("shuffling"));
  setGenerating(button, true);
  run(() => generate({ reshuffle: true })).finally(() => setGenerating(button, false));
});

$("#apply-btn").addEventListener("click", () => {
  const plan = state.generated;
  // Locked meals were planned by the user (mix mode) and are already saved.
  const newMeals = (plan?.meals ?? []).filter((m) => !m.locked);
  if (!newMeals.length) return toast("Nothing new to add. Your planned meals already fill the week.");
  const button = $("#apply-btn");
  run(async () => {
    const result = await api("/api/generator/apply", {
      method: "POST",
      body: {
        meals: newMeals.map((m) => ({ day: m.day, meal_type: m.meal_type, recipe_name: m.recipe.name })),
      },
    });
    confetti(button);
    state.weekStart = parseIsoDate(state.generatorStart);
    await reload("recipes", "plan");
    toast(`Added ${result.meals_planned} meals${result.recipes_added ? ` and ${result.recipes_added} new recipes` : ""}`);
    setTimeout(() => switchView("planner"), reduceMotion ? 0 : 650);
  });
});

function renderGenerated() {
  const plan = state.generated;
  $("#gen-result").hidden = false;
  if (!plan) return;

  const ratio = plan.budget > 0 ? plan.estimated_total / plan.budget : 0;
  setRing($("#gen-ring"), ratio);
  animateNumber($("#gen-ring-pct"), Math.round(ratio * 100), (v) => `${Math.round(v)}%`);
  animateNumber($("#stat-total"), plan.estimated_total, (v) => money(v));
  animateNumber($("#stat-meals"), plan.meals.length, (v) => String(Math.round(v)));
  animateNumber($("#stat-minutes"), plan.average_minutes ?? 0, (v) => String(Math.round(v)));
  const servings = plan.meals.length * draft.people;
  animateNumber($("#stat-per-meal"), servings ? plan.estimated_total / servings : 0, (v) => money(v));

  const notes = plan.within_budget && plan.meals.length
    ? [`<p class="notice good">${icon("circle-check")} This week fits your budget with ${money(plan.budget - plan.estimated_total)} to spare.</p>`]
    : [];
  notes.push(...plan.notes.map((note) => `<p class="notice">${icon("triangle-alert")} ${escapeHtml(note)}</p>`));
  $("#gen-notes").innerHTML = notes.join("");

  const start = parseIsoDate(state.generatorStart);
  let index = 0;
  $("#gen-week").innerHTML = DAY_NAMES.map((dayName, offset) => {
    const day = isoDate(addDays(start, offset));
    const meals = plan.meals.filter((m) => m.day === day);
    if (!meals.length) return "";
    const cards = meals.map((m) => {
      const meal = MEAL_BY_KEY[m.meal_type];
      const mine = m.locked ? `<span class="mine" title="You planned this">${icon("pin")}Yours</span>` : "";
      const time = m.recipe.prep_minutes != null ? `<span>${icon("clock")}${m.recipe.prep_minutes}m</span>` : "";
      return `<div class="meal-card ${meal.key} ${m.locked ? "locked" : ""} reveal" style="--i:${index++}" title="${escapeHtml(m.recipe.description)}">
          <div class="meal-type">${icon(meal.icon)}${meal.label}${mine}</div>
          <div class="meal-title">${escapeHtml(m.recipe.name)}</div>
          <div class="meal-meta">${time}<span>${icon("wallet")}${money(m.cost)}</span></div>
        </div>`;
    }).join("");
    return `<div class="gen-day"><div class="gen-day-head">${dayName}<span>${formatShort(addDays(start, offset))}</span></div>${cards}</div>`;
  }).join("");

  const newCount = plan.meals.filter((m) => !m.locked).length;
  $("#apply-btn").disabled = newCount === 0;
  $("#apply-btn span").textContent = plan.meals.some((m) => m.locked)
    ? `Add ${newCount} meal${newCount === 1 ? "" : "s"} to my plan`
    : "Use this plan";

  const toBuy = plan.groceries.filter((g) => g.status !== "have");
  $("#gen-groceries-title").textContent = `Grocery list · ${toBuy.length} items · ${money(plan.estimated_total)}`;
  $("#gen-groceries").innerHTML = plan.groceries.map((g) => `<li>
      ${foodIcon(g.name, "sm")}
      <span><span class="item-name">${escapeHtml(g.name)}</span>
        <span class="item-sub">${escapeHtml(formatQuantity(g.status === "have" ? g.quantity : g.to_buy, g.unit) || "some")}</span></span>
      ${g.status === "have" ? `<span class="price owned">At home</span>` : `<span class="price">${money(g.est_cost)}</span>`}
    </li>`).join("");
  refreshIcons();
}

// =====================================================================
// Planner
// =====================================================================

function renderPlanner() {
  $("#week-label").textContent = weekLabel();
  const today = isoDate(new Date());
  const recipesById = new Map(state.recipes.map((r) => [r.id, r]));
  const safeRecipes = state.recipes.filter((r) => !r.conflicts.length);
  const options = safeRecipes.length
    ? safeRecipes.map((r) => `<option value="${r.id}">${escapeHtml(r.name)}</option>`).join("")
    : `<option disabled>No recipes available</option>`;

  const planned = state.plan.length;
  const total = DAY_NAMES.length * MEALS.length;
  const cost = state.shopping?.estimated_total ?? 0;
  $("#plan-progress").textContent = `${planned} of ${total} meals planned · about ${money(cost)} in groceries`;
  requestAnimationFrame(() => { $("#plan-progress-bar").style.width = `${(planned / total) * 100}%`; });

  $("#week-grid").innerHTML = DAY_NAMES.map((dayName, i) => {
    const date = addDays(state.weekStart, i);
    const day = isoDate(date);
    const slots = MEALS.map((meal) => {
      const entry = state.plan.find((e) => e.day === day && e.meal_type === meal.key);
      let content;
      if (entry) {
        const conflicts = recipesById.get(entry.recipe.id)?.conflicts ?? [];
        const warn = conflicts.length
          ? `<span class="warn" title="Contains ${escapeHtml(conflicts.map((c) => c.ingredient).join(", "))}">${icon("triangle-alert")}</span>`
          : "";
        // A filled slot is still a dropdown, so switching recipes is one pick (no delete first).
        // Keep the current recipe selectable even if it's now flagged by an allergy or diet.
        const current = safeRecipes.some((r) => r.id === entry.recipe.id)
          ? ""
          : `<option value="${entry.recipe.id}">${escapeHtml(entry.recipe.name)}</option>`;
        const choices = (current + options).replace(
          `<option value="${entry.recipe.id}">`, `<option value="${entry.recipe.id}" selected>`);
        content = `<div class="meal">
            <select class="meal-select" data-day="${day}" data-meal="${meal.key}"
              aria-label="${dayName} ${meal.label}: ${escapeHtml(entry.recipe.name)}. Choose a different recipe" title="Switch recipe">${choices}</select>${warn}
            <button class="icon-btn" data-clear="${entry.id}" title="Remove" aria-label="Remove ${escapeHtml(entry.recipe.name)}">${icon("x")}</button>
          </div>`;
      } else {
        content = `<select data-day="${day}" data-meal="${meal.key}" aria-label="${dayName} ${meal.label}">
            <option value="">+ Add ${meal.label.toLowerCase()}</option>${options}</select>`;
      }
      return `<div class="slot ${meal.key}"><div class="slot-label">${icon(meal.icon)}${meal.label}</div>${content}</div>`;
    }).join("");
    return `<div class="day reveal ${day === today ? "today" : ""}" style="--i:${i}">
        <div class="day-head"><span class="day-name">${dayName}</span><span class="day-date">${formatShort(date)}</span></div>
        ${slots}
      </div>`;
  }).join("");
  refreshIcons();
}

$("#week-grid").addEventListener("change", (event) => {
  const select = event.target.closest("select[data-day]");
  if (!select?.value) return;
  run(async () => {
    await api("/api/plan", {
      method: "PUT",
      body: { day: select.dataset.day, meal_type: select.dataset.meal, recipe_id: Number(select.value) },
    });
    await reload("plan");
    renderPlanner();
  }, "Meal planned");
});

$("#week-grid").addEventListener("click", (event) => {
  const button = event.target.closest("[data-clear]");
  if (!button) return;
  run(async () => {
    await api(`/api/plan/${button.dataset.clear}`, { method: "DELETE" });
    await reload("plan");
    renderPlanner();
  });
});

function changeWeek(newStart) {
  state.weekStart = newStart;
  run(async () => {
    await reload("plan");
    renderCurrentView();
  });
}

$("#prev-week").addEventListener("click", () => changeWeek(addDays(state.weekStart, -7)));
$("#next-week").addEventListener("click", () => changeWeek(addDays(state.weekStart, 7)));
$("#this-week").addEventListener("click", () => changeWeek(mondayOf(new Date())));

// =====================================================================
// Recipes
// =====================================================================

/** Escape text, then turn bare URLs into links (used for imported recipes' credits). */
function linkify(text) {
  return escapeHtml(text).replace(/https?:\/\/[^\s)<]+/g, (url) =>
    `<a href="${url}" target="_blank" rel="noopener noreferrer">${url.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]}</a>`);
}

/** Hover text listing each ingredient's estimated cost and where its price came from. */
function costTooltip(recipe) {
  const lines = recipe.cost_breakdown.map((line) =>
    `${line.ingredient}: ${money(line.cost)} (${line.priced ? line.source : "not in our price list, guessed"})`);
  return [`Estimated whole-recipe cost, ${recipe.servings} servings:`, ...lines].join("\n");
}

function renderRecipes() {
  $("#hide-conflicts").checked = state.hideConflicts;
  $$("#recipe-time .chip").forEach((chip) =>
    chip.setAttribute("aria-pressed", String(chip.dataset.max === state.recipeMaxMinutes)));

  const query = $("#recipe-search").value.trim().toLowerCase();
  const maxMinutes = state.recipeMaxMinutes === "" ? Infinity : Number(state.recipeMaxMinutes);
  const matching = state.recipes.filter((r) =>
    r.name.toLowerCase().includes(query) && (r.prep_minutes ?? 0) <= maxMinutes);
  const recipes = state.hideConflicts ? matching.filter((r) => !r.conflicts.length) : matching;
  const hiddenCount = matching.length - recipes.length;
  const inPantry = pantryNames();

  const note = $("#hidden-note");
  note.hidden = hiddenCount === 0;
  note.innerHTML = `${icon("eye-off")} ${hiddenCount} recipe${hiddenCount === 1 ? "" : "s"} hidden because of your diet, allergies or dislikes.
    <button class="link-btn" id="show-hidden">Show them</button>`;

  const list = $("#recipe-list");
  if (!recipes.length) {
    list.innerHTML = `<p class="empty">${icon("book-open")}${
      state.recipes.length ? "No recipes match these filters." : "No recipes yet. Add your first one!"}</p>`;
    refreshIcons();
    return;
  }

  list.innerHTML = recipes.map((r, i) => {
    const meta = [`<span class="pill">${icon("users")}${r.servings}</span>`];
    if (r.prep_minutes != null) meta.push(`<span class="pill">${icon("clock")}${r.prep_minutes} min</span>`);
    const guessed = r.cost_breakdown.filter((line) => !line.priced).length;
    meta.push(`<span class="pill money" title="${escapeHtml(costTooltip(r))}">${icon("wallet")}${money(r.cost_per_serving)}/serving</span>`);
    if (guessed) meta.push(`<span class="pill guess" title="${escapeHtml(costTooltip(r))}">${icon("circle-help")}${guessed} guessed</span>`);
    const ingredients = r.ingredients.map((ing) => {
      const have = inPantry.has(normalizeName(ing.name));
      return `<li class="${have ? "in-pantry" : ""}" title="${have ? "In your pantry" : ""}">${have ? icon("check") : ""}
        ${escapeHtml(formatQuantity(ing.quantity, ing.unit))} ${escapeHtml(ing.name)}</li>`;
    }).join("");
    return `<article class="recipe-card reveal ${r.conflicts.length ? "has-conflict" : ""}" style="--i:${i}">
      <div class="recipe-head">
        ${recipeAvatar(r.name)}
        <div><h3>${escapeHtml(r.name)}</h3><div class="recipe-meta">${meta.join("")}</div></div>
      </div>
      ${r.conflicts.length ? `<div class="badges">${conflictBadges(r)}</div>` : ""}
      ${r.description ? `<p>${linkify(r.description)}</p>` : ""}
      ${ingredients ? `<ul class="ingredients">${ingredients}</ul>` : ""}
      <div class="card-actions">
        <button class="btn small" data-edit="${r.id}">${icon("pencil")}Edit</button>
        <button class="btn small danger" data-delete="${r.id}">${icon("trash-2")}Delete</button>
      </div>
    </article>`;
  }).join("");
  refreshIcons();
}

$("#recipe-search").addEventListener("input", renderRecipes);

$("#recipe-time").addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  state.recipeMaxMinutes = chip.dataset.max;
  renderRecipes();
});

function setHideConflicts(value) {
  state.hideConflicts = value;
  writeSetting("hideConflicts", value);
  renderRecipes();
}

$("#hide-conflicts").addEventListener("change", (event) => setHideConflicts(event.target.checked));
$("#hidden-note").addEventListener("click", (event) => {
  if (event.target.closest("#show-hidden")) setHideConflicts(false);
});

$("#recipe-list").addEventListener("click", (event) => {
  const editId = event.target.closest("[data-edit]")?.dataset.edit;
  const deleteId = event.target.closest("[data-delete]")?.dataset.delete;
  if (editId) openRecipeDialog(state.recipes.find((r) => r.id === Number(editId)));
  if (deleteId) {
    const recipe = state.recipes.find((r) => r.id === Number(deleteId));
    if (!confirm(`Delete "${recipe.name}"? It will also be removed from your meal plan.`)) return;
    run(async () => {
      await api(`/api/recipes/${deleteId}`, { method: "DELETE" });
      await reload("recipes", "plan");
      renderRecipes();
    }, "Recipe deleted");
  }
});

// ---------- Recipe dialog ----------

const dialog = $("#recipe-dialog");
const form = $("#recipe-form");
const fields = form.elements;

function addIngredientRow(ingredient = {}) {
  const row = document.createElement("div");
  row.className = "ingredient-row";
  row.innerHTML = `
    <input name="qty" type="number" min="0" step="any" placeholder="Qty" value="${ingredient.quantity ?? ""}" />
    <input name="unit" placeholder="Unit" maxlength="30" list="unit-suggestions" value="${escapeHtml(ingredient.unit)}" />
    <input name="ingredient" placeholder="Ingredient" maxlength="120" value="${escapeHtml(ingredient.name)}" />
    <button type="button" class="icon-btn" title="Remove" aria-label="Remove ingredient">${icon("x")}</button>`;
  row.querySelector("button").addEventListener("click", () => row.remove());
  $("#ingredient-rows").appendChild(row);
  refreshIcons();
}

function openRecipeDialog(recipe = null) {
  state.editingRecipeId = recipe?.id ?? null;
  $("#recipe-dialog-title").textContent = recipe ? "Edit recipe" : "New recipe";
  form.reset();
  fields.name.value = recipe?.name ?? "";
  fields.description.value = recipe?.description ?? "";
  fields.servings.value = recipe?.servings ?? 2;
  fields.prep_minutes.value = recipe?.prep_minutes ?? "";
  fields.instructions.value = recipe?.instructions ?? "";
  $("#ingredient-rows").innerHTML = "";
  (recipe?.ingredients.length ? recipe.ingredients : [{}, {}, {}]).forEach(addIngredientRow);
  dialog.showModal();
}

function readRecipeForm() {
  const ingredients = $$(".ingredient-row")
    .map((row) => {
      const qty = row.querySelector("[name=qty]").value;
      return {
        name: row.querySelector("[name=ingredient]").value.trim(),
        unit: row.querySelector("[name=unit]").value.trim(),
        quantity: qty === "" ? null : Number(qty),
      };
    })
    .filter((i) => i.name);
  return {
    name: fields.name.value.trim(),
    description: fields.description.value.trim(),
    servings: Number(fields.servings.value),
    prep_minutes: fields.prep_minutes.value === "" ? null : Number(fields.prep_minutes.value),
    instructions: fields.instructions.value.trim(),
    ingredients,
  };
}

$("#new-recipe").addEventListener("click", () => openRecipeDialog());
$("#add-ingredient").addEventListener("click", () => addIngredientRow());
$("#cancel-recipe").addEventListener("click", () => dialog.close());

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const id = state.editingRecipeId;
  run(async () => {
    await api(id ? `/api/recipes/${id}` : "/api/recipes", { method: id ? "PUT" : "POST", body: readRecipeForm() });
    dialog.close();
    await reload("recipes", "plan");
    renderRecipes();
  }, id ? "Recipe updated" : "Recipe added");
});

// ---------- Discover (TheMealDB) ----------

let discovered = [];

function renderDiscover() {
  const grid = $("#discover-results");
  if (!discovered.length) {
    grid.innerHTML = "";
    return;
  }
  grid.innerHTML = discovered.map((r, i) => {
    const badges = r.conflicts.length ? `<div class="badges">${conflictBadges({ conflicts: r.conflicts })}</div>` : "";
    const kind = [r.category, r.area].filter(Boolean).join(" · ");
    return `<article class="discover-card reveal" style="--i:${i}">
      <img src="${escapeHtml(r.thumbnail)}/preview" alt="" loading="lazy" onerror="this.onerror=null;this.src='${escapeHtml(r.thumbnail)}'" />
      <div class="discover-body">
        <h3>${escapeHtml(r.name)}</h3>
        <div class="recipe-meta">
          ${kind ? `<span class="pill">${escapeHtml(kind)}</span>` : ""}
          <span class="pill money" title="Estimated, assuming ${r.servings} servings">${icon("wallet")}~${money(r.cost_per_serving)}/serving</span>
          <span class="pill">${icon("list")}${r.ingredients.length} ingredients</span>
        </div>
        ${badges}
        <div class="card-actions">
          ${r.in_library
            ? `<button class="btn small" disabled>${icon("check")}In your recipes</button>`
            : `<button class="btn small go" data-import="${escapeHtml(r.id)}">${icon("plus")}Add to my recipes</button>`}
          <a class="btn small" href="${escapeHtml(r.mealdb_url)}" target="_blank" rel="noopener">${icon("external-link")}View</a>
        </div>
      </div>
    </article>`;
  }).join("");
  refreshIcons();
}

$("#discover-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const query = event.target.elements.q.value.trim();
  const button = event.target.querySelector("button");
  setGenerating(button, true, "Searching...");
  run(async () => {
    discovered = await api(`/api/discover?q=${encodeURIComponent(query)}`);
    renderDiscover();
    if (!discovered.length) {
      $("#discover-results").innerHTML = `<p class="empty">${icon("search-x")}No recipes found for "${escapeHtml(query)}". Try a single word like "chicken".</p>`;
      refreshIcons();
    }
  }).finally(() => setGenerating(button, false, "Search"));
});

$("#discover-results").addEventListener("click", (event) => {
  const button = event.target.closest("[data-import]");
  if (!button) return;
  button.disabled = true;
  run(async () => {
    const recipe = await api(`/api/discover/${button.dataset.import}/import`, { method: "POST" });
    confetti(button);
    discovered = discovered.map((r) => (r.id === button.dataset.import ? { ...r, in_library: true } : r));
    await reload("recipes");
    renderRecipes();
    renderDiscover();
    toast(`${recipe.name} added to your recipes`);
  }).finally(() => { button.disabled = false; });
});

// =====================================================================
// Pantry
// =====================================================================

function renderSuggestions() {
  const names = new Set();
  state.recipes.forEach((r) => r.ingredients.forEach((i) => names.add(i.name.toLowerCase())));
  $("#ingredient-suggestions").innerHTML = [...names].sort().map((n) => `<option value="${escapeHtml(n)}"></option>`).join("");
  $("#unit-suggestions").innerHTML = COMMON_UNITS.map((u) => `<option value="${u}"></option>`).join("");
}

async function renderPantry() {
  renderSuggestions();
  $("#pantry-list").innerHTML = state.pantry.length
    ? state.pantry.map((item, i) => `<li class="item-row reveal" style="--i:${i}">
        ${foodIcon(item.name)}
        <span class="item-main item-name">${escapeHtml(item.name)}</span>
        <span class="qty-edit">
          <input type="number" min="0" step="any" placeholder="some" value="${item.quantity ?? ""}"
            data-qty="${item.id}" aria-label="Quantity of ${escapeHtml(item.name)}" />
          ${escapeHtml(item.unit)}
        </span>
        <button class="icon-btn" data-remove="${item.id}" title="Remove" aria-label="Remove ${escapeHtml(item.name)}">${icon("trash-2")}</button>
      </li>`).join("")
    : `<li class="empty">${icon("refrigerator")}Your pantry is empty. Add what you already have at home.</li>`;
  refreshIcons();

  const ideas = await api("/api/recipes/ideas");
  $("#ideas-list").innerHTML = ideas.length
    ? ideas.map(({ recipe, have, missing }, i) => {
        const total = have.length + missing.length;
        const pct = total ? Math.round((have.length / total) * 100) : 0;
        const status = missing.length === 0
          ? `<b>You have everything!</b>`
          : `<b>${have.length} of ${total}</b> at home · need ${escapeHtml(missing.join(", "))}`;
        return `<div class="idea reveal ${missing.length === 0 ? "ready" : ""}" style="--i:${i}">
          ${recipeAvatar(recipe.name, "sm")}
          <div class="idea-body">
            <div class="idea-title">${escapeHtml(recipe.name)}</div>
            <div class="idea-bar"><div data-pct="${pct}" style="width:0"></div></div>
            <div class="idea-meta">${status}</div>
          </div>
        </div>`;
      }).join("")
    : `<p class="empty">${icon("utensils")}No recipes fit your diet and allergies yet.</p>`;
  refreshIcons();
  requestAnimationFrame(() => $$("#ideas-list [data-pct]").forEach((bar) => { bar.style.width = `${bar.dataset.pct}%`; }));
}

$("#pantry-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const pantryFields = event.target.elements;
  const quantity = pantryFields.quantity.value;
  run(async () => {
    await api("/api/pantry", {
      method: "POST",
      body: { name: pantryFields.name.value.trim(), quantity: quantity === "" ? null : Number(quantity), unit: pantryFields.unit.value.trim() },
    });
    event.target.reset();
    pantryFields.name.focus();
    await reload("pantry");
    await renderPantry();
  }, "Added to pantry");
});

$("#pantry-list").addEventListener("change", (event) => {
  const input = event.target.closest("[data-qty]");
  if (!input) return;
  const item = state.pantry.find((p) => p.id === Number(input.dataset.qty));
  run(async () => {
    await api(`/api/pantry/${item.id}`, {
      method: "PUT",
      body: { name: item.name, unit: item.unit, quantity: input.value === "" ? null : Number(input.value) },
    });
    await reload("pantry");
  }, "Pantry updated");
});

$("#pantry-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove]");
  if (!button) return;
  button.closest("li").classList.add("leaving");
  run(async () => {
    await api(`/api/pantry/${button.dataset.remove}`, { method: "DELETE" });
    await reload("pantry");
    await renderPantry();
  });
});

// =====================================================================
// Shopping list
// =====================================================================

function checkedKey() {
  return `shopping-checked:${isoDate(state.weekStart)}`;
}

async function renderShopping() {
  await reload("shopping");
  const data = state.shopping;
  const items = data.items;
  $("#shopping-label").textContent = `For ${weekLabel()} · pantry items are taken off automatically`;

  // Budget meter
  const budget = state.profile.weekly_budget;
  const ratio = budget > 0 ? data.estimated_total / budget : 0;
  animateNumber($("#shop-total"), data.estimated_total, (v) => money(v));
  $("#shop-budget").textContent = money(budget, 0);
  const meter = $("#shop-meter");
  requestAnimationFrame(() => { meter.style.width = `${Math.min(ratio, 1) * 100}%`; });
  meter.classList.toggle("over", ratio > 1);
  $("#shop-meter-note").textContent = budget <= 0
    ? "Set a weekly budget on the Home tab to track spending."
    : ratio > 1
      ? `${money(data.estimated_total - budget)} over budget. Try swapping a pricey meal or using what's in your pantry.`
      : `${money(budget - data.estimated_total)} left in your budget this week.`;

  const toBuy = items.filter((item) => item.status !== "have");
  const have = items.filter((item) => item.status === "have");
  const checked = new Set(readSetting(checkedKey(), []));
  $("#to-buy-count").textContent = toBuy.length;
  $("#have-count").textContent = have.length;
  $("#have-card").hidden = have.length === 0;

  $("#shopping-list").innerHTML = toBuy.length
    ? toBuy.map((item, i) => {
        const index = items.indexOf(item);
        const key = `${item.source}|${item.name}|${item.unit}`.toLowerCase();
        const isChecked = checked.has(key);
        let sub;
        if (item.source === "custom") sub = `<span class="item-sub">Added by you</span>`;
        else if (item.status === "partial") sub = `<span class="item-sub warn">You have ${escapeHtml(formatQuantity(item.pantry_quantity, item.pantry_unit))}, need ${escapeHtml(formatQuantity(item.quantity, item.unit))}</span>`;
        else if (item.status === "check") sub = `<span class="item-sub warn">Pantry has ${escapeHtml(formatQuantity(item.pantry_quantity, item.pantry_unit) || "some")}. Check if it's enough</span>`;
        else sub = `<span class="item-sub">${escapeHtml(item.recipes.join(", "))}</span>`;
        const action = item.source === "custom"
          ? `<button class="icon-btn" data-remove-grocery="${item.custom_id}" title="Remove" aria-label="Remove ${escapeHtml(item.name)}">${icon("trash-2")}</button>`
          : `<button class="icon-btn positive" data-stock="${index}" title="Bought it: add to pantry" aria-label="Add ${escapeHtml(item.name)} to pantry">${icon("package-plus")}</button>`;
        return `<li class="item-row reveal ${isChecked ? "checked" : ""}" style="--i:${i}">
          <label class="check"><input type="checkbox" data-key="${escapeHtml(key)}" ${isChecked ? "checked" : ""} aria-label="Got ${escapeHtml(item.name)}" /><span>${icon("check")}</span></label>
          ${foodIcon(item.name)}
          <span class="item-main">
            <span class="qty">${escapeHtml(formatQuantity(item.to_buy, item.unit))}</span><span class="item-name">${escapeHtml(item.name)}</span>
            ${item.source === "custom" ? `<span class="custom-tag">yours</span>` : ""}
            ${sub}
          </span>
          <span class="price-tag ${item.price_known ? "" : "estimate"}">${money(item.est_cost)}</span>
          ${action}
        </li>`;
      }).join("")
    : `<li class="empty">${icon("shopping-cart")}${
        items.length ? "Nothing to buy. Your pantry has it all!" : "Nothing planned yet. Plan some meals or add your own items above."}</li>`;

  $("#have-list").innerHTML = have.map((item) => `<li class="item-row">
      ${foodIcon(item.name)}
      <span class="item-main">
        <span class="item-name">${escapeHtml(item.name)}</span>
        <span class="item-sub">Need ${escapeHtml(formatQuantity(item.quantity, item.unit) || "some")} · have ${escapeHtml(formatQuantity(item.pantry_quantity, item.pantry_unit) || "some")}</span>
      </span>
      <span class="have-icon">${icon("circle-check")}</span>
    </li>`).join("");
  refreshIcons();
}

$("#shopping-list").addEventListener("change", (event) => {
  const box = event.target.closest("input[data-key]");
  if (!box) return;
  const checked = new Set(readSetting(checkedKey(), []));
  box.checked ? checked.add(box.dataset.key) : checked.delete(box.dataset.key);
  writeSetting(checkedKey(), [...checked]);
  box.closest("li").classList.toggle("checked", box.checked);
  const remaining = $$("#shopping-list input[data-key]").filter((b) => !b.checked).length;
  if (box.checked && remaining === 0) {
    confetti(box);
    toast("All done. Happy cooking!");
  }
});

$("#shopping-list").addEventListener("click", (event) => {
  const stock = event.target.closest("[data-stock]")?.dataset.stock;
  const removeId = event.target.closest("[data-remove-grocery]")?.dataset.removeGrocery;
  if (stock !== undefined) {
    const item = state.shopping.items[Number(stock)];
    run(async () => {
      await api("/api/pantry", { method: "POST", body: { name: item.name, quantity: item.to_buy, unit: item.unit } });
      await reload("pantry");
      await renderShopping();
    }, `${item.name} added to pantry`);
  }
  if (removeId) {
    event.target.closest("li").classList.add("leaving");
    run(async () => {
      await api(`/api/groceries/${removeId}`, { method: "DELETE" });
      await renderShopping();
    });
  }
});

$("#grocery-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const f = event.target.elements;
  run(async () => {
    await api("/api/groceries", {
      method: "POST",
      body: {
        name: f.name.value.trim(),
        quantity: f.quantity.value === "" ? null : Number(f.quantity.value),
        unit: f.unit.value.trim(),
        price: f.price.value === "" ? null : Number(f.price.value),
      },
    });
    event.target.reset();
    f.name.focus();
    await renderShopping();
  }, "Added to your list");
});

$("#clear-checked").addEventListener("click", () => {
  writeSetting(checkedKey(), []);
  run(renderShopping);
});

// =====================================================================
// Diet & allergies
// =====================================================================

function renderPreferences() {
  $$("#pref-diet .chip").forEach((chip) => chip.setAttribute("aria-pressed", String(chip.dataset.diet === state.profile.diet)));

  const chip = (r) => `<span class="tag-chip ${r.kind}">${escapeHtml(r.name)}
      <button class="icon-btn" data-unrestrict="${r.id}" title="Remove" aria-label="Remove ${escapeHtml(r.name)}">${icon("x")}</button></span>`;
  const allergies = state.restrictions.filter((r) => r.kind === "allergy");
  const dislikes = state.restrictions.filter((r) => r.kind === "dislike");
  $("#allergy-list").innerHTML = allergies.map(chip).join("") || `<p class="subtle">No allergies added.</p>`;
  $("#dislike-list").innerHTML = dislikes.map(chip).join("") || `<p class="subtle">No dislikes added.</p>`;

  const existing = new Set(state.restrictions.map((r) => r.name.toLowerCase()));
  const suggestions = COMMON_RESTRICTIONS.filter((name) => !existing.has(name.toLowerCase()));
  $("#quick-chips").innerHTML = suggestions.length
    ? suggestions.map((name) => `<button type="button" class="chip" data-quick="${name}">${icon("plus")}${name}</button>`).join("")
    : `<span class="subtle">All added</span>`;
  refreshIcons();
}

$("#pref-diet").addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  run(async () => {
    await saveProfile({ diet: chip.dataset.diet });
    draft.diet = chip.dataset.diet;
    await reload("recipes");
    renderPreferences();
  }, "Diet saved");
});

function addRestriction(name) {
  const kind = $("#restriction-form").elements.kind.value;
  return run(async () => {
    await api("/api/restrictions", { method: "POST", body: { name, kind } });
    await reload("restrictions", "recipes");
    renderPreferences();
  }, `${name} added to ${kind === "allergy" ? "allergies" : "dislikes"}`);
}

$("#restriction-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = event.target.elements.name;
  await addRestriction(input.value.trim());
  input.value = "";
});

$("#quick-chips").addEventListener("click", (event) => {
  const name = event.target.closest("[data-quick]")?.dataset.quick;
  if (name) addRestriction(name);
});

$("#view-preferences").addEventListener("click", (event) => {
  const id = event.target.closest("[data-unrestrict]")?.dataset.unrestrict;
  if (!id) return;
  run(async () => {
    await api(`/api/restrictions/${id}`, { method: "DELETE" });
    await reload("restrictions", "recipes");
    renderPreferences();
  });
});

// =====================================================================
// Navigation
// =====================================================================

let currentView = "home";

const renderers = {
  home: renderHome,
  planner: renderPlanner,
  recipes: renderRecipes,
  pantry: renderPantry,
  shopping: renderShopping,
  preferences: renderPreferences,
};

function moveTabIndicator() {
  const active = $(".tab.active");
  const indicator = $(".tab-indicator");
  if (!active) return;
  indicator.style.left = `${active.offsetLeft}px`;
  indicator.style.width = `${active.offsetWidth}px`;
}

function renderCurrentView() {
  return run(async () => renderers[currentView]());
}

function switchView(view) {
  currentView = view;
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  moveTabIndicator();
  window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
  renderCurrentView();
}

$$(".tab").forEach((tab) => tab.addEventListener("click", () => switchView(tab.dataset.view)));

// Any element with data-goto="<view>" acts as a link to that tab.
document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-goto]");
  if (target) switchView(target.dataset.goto);
});

window.addEventListener("resize", moveTabIndicator);

// =====================================================================
// Start
// =====================================================================

window.addEventListener("load", () => { refreshIcons(); moveTabIndicator(); }); // lucide loads with `defer`
document.fonts?.ready.then(moveTabIndicator);
moveTabIndicator();
run(async () => {
  await reload("profile", "recipes", "plan", "pantry", "restrictions", "shopping");
  await renderCurrentView();
});
