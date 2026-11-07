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
  dining: [], // meal slots marked as eating out this week
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
const grams = (value) => `${Math.round(value)}g`;
const MACRO_SOURCE = "Estimated from the ingredients using USDA FoodData Central nutrition data";

/** Hover text with all four macros and where the numbers came from. */
function macroTitle(n, label = "Per serving") {
  const lines = [`${label}: ${Math.round(n.calories)} kcal · ${grams(n.protein_g)} protein · ${grams(n.carbs_g)} carbs · ${grams(n.fat_g)} fat`];
  if (n.source === "entered") lines.push("Entered by you (blank fields estimated)");
  else if (n.source) lines.push(MACRO_SOURCE);
  if (n.missing?.length) lines.push(`Not counted: ${n.missing.join(", ")}`);
  return lines.join("\n");
}

/** Calorie and protein pills for a recipe card (hover for carbs, fat and the source). */
function macroPills(n, prefix = "") {
  if (!n || (!n.calories && !n.protein_g)) return "";
  const title = escapeHtml(macroTitle(n));
  const cls = `pill macro${n.source === "entered" ? " entered" : ""}`;
  return `<span class="${cls}" title="${title}">${icon("flame")}${prefix}${Math.round(n.calories)} kcal</span>
    <span class="${cls}" title="${title}">${icon("dumbbell")}${prefix}${grams(n.protein_g)} protein</span>`;
}

/** A planned meal's macros per person, at its portion size. */
function scaledNutrition(entry) {
  const n = entry.recipe.nutrition;
  if (!n) return null;
  const k = entry.portions || 1;
  return { ...n, calories: n.calories * k, protein_g: n.protein_g * k, carbs_g: n.carbs_g * k, fat_g: n.fat_g * k };
}

const diningTotal = () => state.dining.reduce((sum, d) => sum + (d.cost || 0), 0);

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

// The iPhone app bundles these files and calls the live API; the website uses its own origin.
const NATIVE = window.Capacitor?.isNativePlatform?.() === true;
const Native = window.Capacitor?.Plugins ?? {};
const API_BASE = NATIVE ? "https://elevate-plate.vercel.app" : "";
const TOKEN_KEY = "ep-token";
let authToken = readSetting(TOKEN_KEY, null);

/** Thrown when the session is missing or expired; the sign-in screen is already showing. */
class SignedOutError extends Error {}

function cacheKey(path) {
  return `ep-cache:${state.user?.id ?? "me"}:${path}`;
}

function setOffline(offline) {
  $("#offline-banner").hidden = !offline;
}

async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  let response;
  try {
    response = await fetch(API_BASE + path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    // No connection: reads fall back to the last copy saved on this device.
    setOffline(true);
    const cached = method === "GET" ? readSetting(cacheKey(path), undefined) : undefined;
    if (cached !== undefined) return cached;
    throw new Error("You're offline. Connect to the internet and try again.");
  }
  setOffline(false);
  if (response.status === 401 && !path.startsWith("/api/auth/login")) {
    signedOut();
    throw new SignedOutError("Please sign in.");
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d) => d.msg).join(", ");
    } catch { /* non-JSON error body */ }
    throw new Error(message);
  }
  const data = response.status === 204 ? null : await response.json();
  if (method === "GET") writeSetting(cacheKey(path), data);
  return data;
}

async function run(action, successMessage) {
  try {
    await action();
    if (successMessage) toast(successMessage);
  } catch (err) {
    if (!(err instanceof SignedOutError)) toast(err.message, true);
  }
}

/** A light tap on iPhone; a short buzz where the web supports it. */
function haptic() {
  if (NATIVE) Native.Haptics?.impact({ style: "LIGHT" }).catch(() => {});
  else navigator.vibrate?.(12);
}

// =====================================================================
// Data loading
// =====================================================================

const loaders = {
  recipes: async () => { state.recipes = await api("/api/recipes"); },
  plan: async () => {
    const start = isoDate(state.weekStart);
    [state.plan, state.dining] = await Promise.all([
      api(`/api/plan?start=${start}`),
      api(`/api/dining-out?start=${start}`),
    ]);
  },
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
  // Groceries plus what you expect to spend eating out.
  const total = state.shopping.estimated_total + (state.shopping.dining_out_total || 0);
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
  $("#hybrid-count").innerHTML = `${state.plan.length + state.dining.length}<small>/21</small>`;
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
      macro_goals: { ...state.profile.macro_goals },
    });
  }
  for (const field of MACRO_FIELDS) {
    const input = $(`#gen-goals [name=${field}]`);
    if (document.activeElement !== input) input.value = draft.macro_goals[field] ?? "";
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

$("#gen-goals").addEventListener("input", (event) => {
  const input = event.target.closest("input");
  if (!input) return;
  draft.macro_goals[input.name] = input.value === "" ? null : Number(input.value);
});

/** The goals to send, or null when none are filled in. */
function macroGoals() {
  return Object.values(draft.macro_goals).some((v) => v != null) ? draft.macro_goals : null;
}

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
    macro_goals: draft.macro_goals,
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
      macro_goals: macroGoals(),
      use_library: $("#gen-use-library").checked,
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
        meals: newMeals.map((m) => ({ day: m.day, meal_type: m.meal_type, recipe_name: m.recipe.name, portions: m.portions })),
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

  const spent = plan.estimated_total + plan.dining_out_total;
  const ratio = plan.budget > 0 ? spent / plan.budget : 0;
  setRing($("#gen-ring"), ratio);
  animateNumber($("#gen-ring-pct"), Math.round(ratio * 100), (v) => `${Math.round(v)}%`);
  animateNumber($("#stat-total"), plan.estimated_total, (v) => money(v));
  animateNumber($("#stat-meals"), plan.meals.length, (v) => String(Math.round(v)));
  animateNumber($("#stat-minutes"), plan.average_minutes ?? 0, (v) => String(Math.round(v)));
  const servings = plan.meals.length * draft.people;
  animateNumber($("#stat-per-meal"), servings ? plan.estimated_total / servings : 0, (v) => money(v));
  const daily = plan.daily_nutrition;
  $("#stat-kcal-wrap").hidden = $("#stat-protein-wrap").hidden = !daily;
  if (daily) {
    const target = plan.daily_target;
    const ofGoal = (value) => (value ? ` / ${Math.round(value).toLocaleString()}` : "");
    animateNumber($("#stat-kcal"), daily.calories, (v) => `${Math.round(v).toLocaleString()}${ofGoal(target?.calories)}`);
    animateNumber($("#stat-protein"), daily.protein_g, (v) => `${grams(v)}${ofGoal(target?.protein_g)}`);
    $("#stat-kcal-wrap .stat-label").textContent = target?.calories ? "kcal / goal, per person, per day" : "kcal per person, per day";
    $("#stat-protein-wrap .stat-label").textContent = target?.protein_g ? "protein / goal, per person, per day" : "protein per person, per day";
    $("#stat-kcal-wrap").title = $("#stat-protein-wrap").title =
      `${macroTitle({ ...daily, source: "" }, "Average per person, per day")}\n`
      + "Only counts the meals in this plan, not meals out or snacks. Estimated from USDA FoodData Central data."
      + (target ? `\nGoal for these meals: ${target.note}` : "");
  }

  const notes = plan.within_budget && plan.meals.length
    ? [`<p class="notice good">${icon("circle-check")} This week fits your budget with ${money(plan.budget - spent)} to spare${plan.dining_out_total ? " after eating out" : ""}.</p>`]
    : [];
  notes.push(...plan.notes.map((note) => `<p class="notice">${icon("triangle-alert")} ${escapeHtml(note)}</p>`));
  $("#gen-notes").innerHTML = notes.join("");

  const start = parseIsoDate(state.generatorStart);
  let index = 0;
  $("#gen-week").innerHTML = DAY_NAMES.map((dayName, offset) => {
    const day = isoDate(addDays(start, offset));
    const mealIndex = (slot) => MEALS.findIndex((m) => m.key === slot.meal_type);
    const slots = [
      ...plan.meals.filter((m) => m.day === day),
      ...plan.dining_out.filter((d) => d.day === day).map((d) => ({ ...d, out: true })),
    ].sort((a, b) => mealIndex(a) - mealIndex(b));
    if (!slots.length) return "";
    const cards = slots.map((m) => {
      const meal = MEAL_BY_KEY[m.meal_type];
      if (m.out) {
        return `<div class="meal-card out reveal" style="--i:${index++}" title="You're eating out, so this meal is left open">
            <div class="meal-type">${icon(meal.icon)}${meal.label}<span class="mine">${icon("utensils")}Out</span></div>
            <div class="meal-title">${escapeHtml(m.note || "Dining out")}</div>
            <div class="meal-meta">${m.cost != null ? `<span>${icon("wallet")}${money(m.cost)}</span>` : ""}</div>
          </div>`;
      }
      const mine = m.locked
        ? `<span class="mine" title="You planned this">${icon("pin")}Yours</span>`
        : m.recipe.source === "library"
          ? `<span class="mine" title="One of your saved recipes">${icon("bookmark")}Saved</span>`
          : "";
      const time = m.recipe.prep_minutes != null ? `<span>${icon("clock")}${m.recipe.prep_minutes}m</span>` : "";
      const n = m.nutrition?.calories ? m.nutrition : m.recipe.nutrition;
      const kcal = n?.calories ? `<span>${icon("flame")}${Math.round(n.calories)} kcal</span>` : "";
      const size = m.portions !== 1 ? `<span class="portion-badge" title="${m.portions} servings per person, to help meet your goals">${m.portions}x</span>` : "";
      const macros = n?.calories
        ? `<div class="meal-macros" title="${escapeHtml(macroTitle(n, "Per person"))}">${grams(n.protein_g)} protein · ${grams(n.carbs_g)} carbs · ${grams(n.fat_g)} fat</div>`
        : "";
      return `<div class="meal-card ${meal.key} ${m.locked ? "locked" : ""} reveal" style="--i:${index++}" title="${escapeHtml(m.recipe.description)}">
          <div class="meal-type">${icon(meal.icon)}${meal.label}${mine}</div>
          <div class="meal-title">${escapeHtml(m.recipe.name)} ${size}</div>
          <div class="meal-meta">${time}<span>${icon("wallet")}${money(m.cost)}</span>${kcal}</div>
          ${macros}
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

function renderPlannerProgress() {
  const outCount = state.dining.length;
  const planned = state.plan.length + outCount;
  const total = DAY_NAMES.length * MEALS.length;
  const cost = state.shopping?.estimated_total ?? 0;
  const eatingOut = diningTotal();
  $("#plan-progress").textContent = `${planned} of ${total} meals planned${outCount ? ` (${outCount} eating out)` : ""}`
    + ` · about ${money(cost)} in groceries${eatingOut ? ` + ${money(eatingOut)} eating out` : ""}`;
  requestAnimationFrame(() => { $("#plan-progress-bar").style.width = `${(planned / total) * 100}%`; });
}

function renderPlanner() {
  $("#week-label").textContent = weekLabel();
  const today = isoDate(new Date());
  const recipesById = new Map(state.recipes.map((r) => [r.id, r]));
  const safeRecipes = state.recipes.filter((r) => !r.conflicts.length);
  const recipeOptions = safeRecipes.length
    ? safeRecipes.map((r) => `<option value="${r.id}">${escapeHtml(r.name)}</option>`).join("")
    : `<option disabled>No recipes available</option>`;
  const options = `<option value="out">Dining out</option>${recipeOptions}`;
  renderPlannerProgress();

  $("#week-grid").innerHTML = DAY_NAMES.map((dayName, i) => {
    const date = addDays(state.weekStart, i);
    const day = isoDate(date);
    const dayEntries = state.plan.filter((e) => e.day === day);
    const slots = MEALS.map((meal) => {
      const entry = dayEntries.find((e) => e.meal_type === meal.key);
      const out = state.dining.find((d) => d.day === day && d.meal_type === meal.key);
      let content;
      if (out) {
        content = `<div class="meal out">
            <select class="meal-select" data-day="${day}" data-meal="${meal.key}"
              aria-label="${dayName} ${meal.label}: dining out. Choose a recipe instead" title="Switch to a recipe">
              <option value="out" selected>Dining out</option>${recipeOptions}</select>
            <button class="icon-btn" data-clear-out="${out.id}" title="Remove" aria-label="Remove dining out for ${dayName} ${meal.label}">${icon("x")}</button>
          </div>
          <div class="out-details" data-day="${day}" data-meal="${meal.key}">
            <input data-out-note maxlength="120" placeholder="Where? (optional)" value="${escapeHtml(out.note)}" aria-label="Where you're eating, ${dayName} ${meal.label}" />
            <input data-out-cost type="number" min="0" max="2000" step="any" inputmode="decimal" placeholder="$ cost" value="${out.cost ?? ""}"
              aria-label="Expected cost for everyone, ${dayName} ${meal.label}" title="What you expect to spend, for everyone. Counts toward your weekly budget." />
          </div>`;
      } else if (entry) {
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
        const n = scaledNutrition(entry);
        if (n?.calories) {
          const size = entry.portions !== 1 ? ` · ${entry.portions}x portion` : "";
          content += `<div class="slot-macros" title="${escapeHtml(macroTitle(n, `Per person${size ? `, ${entry.portions} servings` : ""}`))}">${Math.round(n.calories)} kcal · ${grams(n.protein_g)} protein${size}</div>`;
        }
      } else {
        content = `<select data-day="${day}" data-meal="${meal.key}" aria-label="${dayName} ${meal.label}">
            <option value="">+ Add ${meal.label.toLowerCase()}</option>${options}</select>`;
      }
      return `<div class="slot ${meal.key}"><div class="slot-label">${icon(meal.icon)}${meal.label}</div>${content}</div>`;
    }).join("");
    // Day total per person, for the meals cooked at home.
    const totals = { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 };
    for (const e of dayEntries) {
      const n = scaledNutrition(e);
      for (const key of Object.keys(totals)) totals[key] += n?.[key] || 0;
    }
    const outToday = state.dining.some((d) => d.day === day);
    const note = `Counts the ${dayEntries.length} meal${dayEntries.length === 1 ? "" : "s"} planned at home${outToday ? ", not meals out" : ""}.`;
    const dayMacros = totals.calories
      ? `<div class="day-macros" title="${escapeHtml(`${macroTitle(totals, "Per person")}\n${note}`)}">
          ${Math.round(totals.calories).toLocaleString()} kcal <span>· ${grams(totals.protein_g)} protein</span></div>`
      : "";
    return `<div class="day reveal ${day === today ? "today" : ""}" style="--i:${i}">
        <div class="day-head"><span class="day-name">${dayName}</span><span class="day-date">${formatShort(date)}</span></div>
        ${dayMacros}
        ${slots}
      </div>`;
  }).join("");
  refreshIcons();
}

/** Save the "where" and "cost" of a dining-out slot. */
function saveDiningDetails(details) {
  const costText = details.querySelector("[data-out-cost]").value;
  const cost = costText === "" ? null : Number(costText);
  if (cost != null && !(cost >= 0 && cost <= 2000)) return toast("Enter a cost between $0 and $2000", true);
  run(async () => {
    await api("/api/dining-out", {
      method: "PUT",
      body: {
        day: details.dataset.day,
        meal_type: details.dataset.meal,
        note: details.querySelector("[data-out-note]").value.trim(),
        cost,
      },
    });
    await reload("plan");
    renderPlannerProgress(); // no full re-render, so focus stays where you tabbed to
  }, "Saved");
}

$("#week-grid").addEventListener("change", (event) => {
  const details = event.target.closest(".out-details");
  if (details) return saveDiningDetails(details);
  const select = event.target.closest("select[data-day]");
  if (!select?.value) return;
  if (select.value === "out") {
    return run(async () => {
      await api("/api/dining-out", { method: "PUT", body: { day: select.dataset.day, meal_type: select.dataset.meal } });
      await reload("plan");
      renderPlanner();
    }, "Marked as dining out");
  }
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
  const outButton = event.target.closest("[data-clear-out]");
  if (outButton) {
    return run(async () => {
      await api(`/api/dining-out/${outButton.dataset.clearOut}`, { method: "DELETE" });
      await reload("plan");
      renderPlanner();
    });
  }
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
    meta.push(macroPills(r.nutrition));
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

// Units for recipe ingredients: [stored value, label]. "" means a count (2 eggs).
const RECIPE_UNITS = [
  ["", "whole / each"],
  ["cup", "cups"], ["tbsp", "tablespoons"], ["tsp", "teaspoons"],
  ["oz", "ounces"], ["lb", "pounds"], ["g", "grams"], ["kg", "kilograms"],
  ["fl oz", "fluid ounces"], ["ml", "milliliters"], ["l", "liters"],
  ["slice", "slices"], ["clove", "cloves"], ["can", "cans"], ["jar", "jars"],
  ["bunch", "bunches"], ["head", "heads"], ["stalk", "stalks"], ["bag", "bags"],
  ["pinch", "pinch"],
];

/** <option>s for the unit dropdown. A unit not in the list (from an older or imported
 *  recipe) is kept as an extra option so saving doesn't change it. */
function unitOptions(current = "") {
  const value = (current ?? "").trim();
  const known = RECIPE_UNITS.some(([unit]) => unit === value);
  const options = known ? RECIPE_UNITS : [...RECIPE_UNITS, [value, value]];
  return options.map(([unit, label]) =>
    `<option value="${escapeHtml(unit)}"${unit === value ? " selected" : ""}>${escapeHtml(label)}</option>`).join("");
}

function addIngredientRow(ingredient = {}) {
  const row = document.createElement("div");
  row.className = "ingredient-row";
  row.innerHTML = `
    <input name="qty" type="number" min="0" step="any" inputmode="decimal" placeholder="3" aria-label="Amount" value="${ingredient.quantity ?? ""}" />
    <select name="unit" aria-label="Unit">${unitOptions(ingredient.unit)}</select>
    <input name="ingredient" placeholder="bread" aria-label="Ingredient" maxlength="120" value="${escapeHtml(ingredient.name)}" />
    <button type="button" class="icon-btn" title="Remove" aria-label="Remove ingredient">${icon("x")}</button>`;
  row.querySelector("button").addEventListener("click", () => row.remove());
  $("#ingredient-rows").appendChild(row);
  refreshIcons();
}

const MACRO_FIELDS = ["calories", "protein_g", "carbs_g", "fat_g"];

function openRecipeDialog(recipe = null) {
  state.editingRecipeId = recipe?.id ?? null;
  $("#recipe-dialog-title").textContent = recipe ? "Edit recipe" : "New recipe";
  form.reset();
  fields.name.value = recipe?.name ?? "";
  fields.description.value = recipe?.description ?? "";
  fields.servings.value = recipe?.servings ?? 2;
  fields.prep_minutes.value = recipe?.prep_minutes ?? "";
  // Blank macro fields show the current estimate as a faded placeholder.
  const estimate = recipe && recipe.nutrition?.source !== "entered" ? recipe.nutrition : null;
  for (const field of MACRO_FIELDS) {
    fields[field].value = recipe?.[field] ?? "";
    fields[field].placeholder = estimate?.calories ? `~${Math.round(estimate[field])}` : "";
  }
  $("#macro-hint").textContent = estimate?.calories
    ? "The faded numbers are our estimate from the ingredients. Type your own to replace them."
    : "Know the numbers (from a label or app)? Add them here. Anything left blank is estimated from the ingredients.";
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
    ...Object.fromEntries(MACRO_FIELDS.map((field) =>
      [field, fields[field].value === "" ? null : Number(fields[field].value)])),
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


// =====================================================================
// Pantry
// =====================================================================

function renderSuggestions() {
  const names = new Set();
  state.recipes.forEach((r) => r.ingredients.forEach((i) => names.add(i.name.toLowerCase())));
  $("#ingredient-suggestions").innerHTML = [...names].sort().map((n) => `<option value="${escapeHtml(n)}"></option>`).join("");
  $("#unit-suggestions").innerHTML = COMMON_UNITS.map((u) => `<option value="${u}"></option>`).join("");
  const pantryUnit = $("#pantry-form [name=unit]");
  if (!pantryUnit.options.length) pantryUnit.innerHTML = unitOptions("");
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
    pantryFields.quantity.focus();
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
  return `shopping-checked:${state.user?.id}:${isoDate(state.weekStart)}`;
}

async function renderShopping() {
  await reload("shopping");
  const data = state.shopping;
  const items = data.items;
  $("#shopping-label").textContent = `For ${weekLabel()} · pantry items are taken off automatically`;

  // Budget meter
  const budget = state.profile.weekly_budget;
  const eatingOut = data.dining_out_total || 0;
  const spent = data.estimated_total + eatingOut;
  const ratio = budget > 0 ? spent / budget : 0;
  animateNumber($("#shop-total"), data.estimated_total, (v) => money(v));
  const diningNote = $("#shop-dining-note");
  diningNote.hidden = !eatingOut;
  diningNote.innerHTML = `${icon("utensils")}Plus about ${money(eatingOut)} you expect to spend eating out this week, included in the budget meter above.`;
  $("#shop-budget").textContent = money(budget, 0);
  const meter = $("#shop-meter");
  requestAnimationFrame(() => { meter.style.width = `${Math.min(ratio, 1) * 100}%`; });
  meter.classList.toggle("over", ratio > 1);
  $("#shop-meter-note").textContent = budget <= 0
    ? "Set a weekly budget on the Home tab to track spending."
    : ratio > 1
      ? `${money(spent - budget)} over budget. Try swapping a pricey meal or using what's in your pantry.`
      : `${money(budget - spent)} left in your budget this week.`;

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
  haptic();
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

// =====================================================================
// Accounts
// =====================================================================

function authMode() {
  return document.querySelector('input[name="auth-mode"]:checked').value;
}

function renderAuthMode() {
  const signup = authMode() === "signup";
  $("#auth-title").textContent = signup ? "Create your account" : "Welcome back";
  $("#auth-subtitle").textContent = signup
    ? "Save your recipes, plans and shopping lists, on the web and on your phone."
    : "Sign in to see your recipes, meal plan and shopping list.";
  $("#auth-name-field").hidden = !signup;
  $("#auth-submit span").textContent = signup ? "Create account" : "Sign in";
  $("#auth-form").elements.password.autocomplete = signup ? "new-password" : "current-password";
  $("#auth-error").hidden = true;
}

function showAuth() {
  document.body.classList.add("signed-out");
  $("#auth-screen").hidden = false;
  renderAuthMode();
  refreshIcons();
}

function signedOut() {
  authToken = null;
  writeSetting(TOKEN_KEY, null);
  Object.assign(state, { user: null, recipes: [], plan: [], pantry: [], restrictions: [], profile: null, shopping: null, generated: null });
  draft.loaded = false;
  $("#account-dialog").open && $("#account-dialog").close();
  showAuth();
}

function renderAccount() {
  const { name, email } = state.user;
  const initial = (name || email || "?").trim()[0].toUpperCase();
  $("#account-initial").textContent = initial;
  $("#account-avatar").textContent = initial;
  $("#account-name").textContent = name || "Your account";
  $("#account-email").textContent = email;
  renderReminder();
}

async function boot() {
  state.user = await api("/api/auth/me");
  document.body.classList.remove("signed-out");
  $("#auth-screen").hidden = true;
  renderAccount();
  await reload("profile", "recipes", "plan", "pantry", "restrictions", "shopping");
  switchView("home");
}

$$('input[name="auth-mode"]').forEach((radio) => radio.addEventListener("change", renderAuthMode));

$("#auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const f = event.target.elements;
  const mode = authMode();
  const email = f.email.value.trim();
  const password = f.password.value;
  const error = $("#auth-error");
  const fail = (message) => { error.textContent = message; error.hidden = false; };
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fail("Enter a valid email address.");
  if (mode === "signup" && password.length < 8) return fail("Use at least 8 characters for your password.");
  if (!password) return fail("Enter your password.");

  const button = $("#auth-submit");
  setGenerating(button, true, mode === "signup" ? "Creating account..." : "Signing in...");
  try {
    const result = await api(`/api/auth/${mode}`, {
      method: "POST",
      body: mode === "signup" ? { email, password, name: f.name.value.trim() } : { email, password },
    });
    authToken = result.token;
    writeSetting(TOKEN_KEY, authToken);
    f.password.value = "";
    await boot();
    toast(mode === "signup" ? "Welcome to Elevate Plate!" : `Welcome back${result.user.name ? `, ${result.user.name}` : ""}!`);
  } catch (err) {
    if (!(err instanceof SignedOutError)) fail(err.message);
  } finally {
    setGenerating(button, false, mode === "signup" ? "Create account" : "Sign in");
  }
});

$("#account-btn").addEventListener("click", () => {
  renderAccount();
  $("#account-dialog").showModal();
  refreshIcons();
});
$("#close-account").addEventListener("click", () => $("#account-dialog").close());

$("#sign-out").addEventListener("click", async () => {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch { /* signing out locally is what matters */ }
  signedOut();
  toast("Signed out");
});

$("#delete-account-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const password = event.target.elements.password.value;
  if (!confirm("Delete your account and all your data permanently? This can't be undone.")) return;
  const userId = state.user.id;
  run(async () => {
    await api("/api/auth/account", { method: "DELETE", body: { password } });
    event.target.reset();
    // Forget anything cached on this device for this account.
    try {
      Object.keys(localStorage)
        .filter((key) => key.startsWith(`ep-cache:${userId}:`) || key.startsWith(`shopping-checked:${userId}:`))
        .forEach((key) => localStorage.removeItem(key));
    } catch { /* storage unavailable */ }
    signedOut();
    toast("Your account and data were deleted.");
  });
});

// =====================================================================
// Sharing & reminders (phone features)
// =====================================================================

function shoppingListText() {
  const toBuy = (state.shopping?.items ?? []).filter((item) => item.status !== "have");
  const lines = toBuy.map((item) => {
    const qty = formatQuantity(item.to_buy, item.unit);
    return `- ${qty ? `${qty} ` : ""}${item.name}`;
  });
  return [
    `Shopping list for ${weekLabel()}`,
    "",
    ...(lines.length ? lines : ["(nothing to buy)"]),
    "",
    `Estimated total: ${money(state.shopping?.estimated_total ?? 0)}`,
    "Made with Elevate Plate",
  ].join("\n");
}

$("#share-list").addEventListener("click", async () => {
  const text = shoppingListText();
  try {
    if (NATIVE && Native.Share) {
      await Native.Share.share({ title: "Shopping list", text, dialogTitle: "Share your shopping list" });
    } else if (navigator.share) {
      await navigator.share({ title: "Shopping list", text });
    } else {
      await navigator.clipboard.writeText(text);
      toast("Shopping list copied. Paste it anywhere.");
    }
  } catch (err) {
    if (err?.name !== "AbortError" && !/cancel/i.test(err?.message ?? "")) toast("Couldn't share the list.", true);
  }
});

const REMINDER_ID = 1001;
const REMINDER_KEY = "ep-reminder";

function renderReminder() {
  const supported = NATIVE && Boolean(Native.LocalNotifications);
  $("#reminder-section").hidden = !supported;
  if (!supported) return;
  const settings = readSetting(REMINDER_KEY, { on: false, day: "7", time: "10:00" });
  $("#reminder-on").checked = settings.on;
  $("#reminder-day").value = settings.day;
  $("#reminder-time").value = settings.time;
}

async function saveReminder() {
  const settings = { on: $("#reminder-on").checked, day: $("#reminder-day").value, time: $("#reminder-time").value || "10:00" };
  const notifications = Native.LocalNotifications;
  await notifications.cancel({ notifications: [{ id: REMINDER_ID }] }).catch(() => {});
  if (settings.on) {
    const permission = await notifications.requestPermissions();
    if (permission.display !== "granted") {
      $("#reminder-on").checked = false;
      settings.on = false;
      toast("Notifications are off for Elevate Plate. Turn them on in Settings to get reminders.", true);
    } else {
      const [hour, minute] = settings.time.split(":").map(Number);
      await notifications.schedule({
        notifications: [{
          id: REMINDER_ID,
          title: "Time to shop",
          body: "Your Elevate Plate shopping list is ready for this week.",
          schedule: { on: { weekday: Number(settings.day), hour, minute }, allowWhileIdle: true },
        }],
      });
      toast("Weekly reminder set");
    }
  }
  writeSetting(REMINDER_KEY, settings);
}

["#reminder-on", "#reminder-day", "#reminder-time"].forEach((selector) =>
  $(selector).addEventListener("change", () => run(saveReminder)));

// =====================================================================
// Start
// =====================================================================

window.addEventListener("load", () => { refreshIcons(); moveTabIndicator(); }); // lucide loads with `defer`
document.fonts?.ready.then(moveTabIndicator);
window.addEventListener("online", () => { if (state.user) run(() => reload("recipes", "plan", "pantry", "shopping")); });

// The website works offline as an installable app; the iPhone app already has its files.
if (!NATIVE && "serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

if (authToken) run(boot);
else showAuth();
