"use strict";

const MEALS = [
  { key: "breakfast", label: "Breakfast", icon: "sunrise" },
  { key: "lunch", label: "Lunch", icon: "sun" },
  { key: "dinner", label: "Dinner", icon: "moon" },
];
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const COMMON_RESTRICTIONS = ["Dairy", "Gluten", "Nuts", "Peanuts", "Eggs", "Shellfish", "Fish", "Soy", "Meat"];
const COMMON_UNITS = ["cup", "tbsp", "tsp", "g", "kg", "oz", "lb", "ml", "l", "clove", "slice", "can", "jar", "bag"];
const AVATAR_COLORS = ["#fde8d7", "#e2f3e8", "#e5edfb", "#fbe6ef", "#fff3c4", "#ece8fb", "#dff3f1"];

// First matching pattern wins, so put specific words before general ones.
const RECIPE_EMOJI = [
  [/oat|porridge|granola|cereal/, "🥣"], [/pancake|waffle|crepe/, "🥞"], [/omelet|egg|frittata|shakshuka/, "🍳"],
  [/taco/, "🌮"], [/wrap|burrito|quesadilla/, "🌯"], [/salad/, "🥗"], [/spaghetti|pasta|bolognese|lasagna|mac/, "🍝"],
  [/stir.?fry|wok/, "🥘"], [/soup|stew|chili/, "🍲"], [/curry/, "🍛"], [/pizza/, "🍕"], [/burger/, "🍔"],
  [/sandwich|toast|panini/, "🥪"], [/smoothie|shake/, "🥤"], [/sushi/, "🍣"], [/salmon|fish|tuna|cod/, "🐟"],
  [/shrimp|prawn/, "🍤"], [/chicken/, "🍗"], [/steak|beef/, "🥩"], [/rice|bowl/, "🍚"], [/noodle|ramen|pho/, "🍜"],
  [/cake|cookie|muffin|brownie/, "🧁"],
];
const FOOD_EMOJI = [
  [/peanut|almond|walnut|cashew|nut\b|nuts/, "🥜"], [/milk|cream/, "🥛"], [/cheese|parmesan|mozzarella|cheddar|feta/, "🧀"],
  [/egg/, "🥚"], [/butter/, "🧈"], [/yogurt/, "🥣"], [/bread|toast|bun|bagel/, "🍞"], [/tortilla|wrap/, "🫓"],
  [/spaghetti|pasta|noodle|macaroni/, "🍝"], [/rice/, "🍚"], [/oat|flour|cereal|grain|quinoa/, "🌾"],
  [/chicken|turkey/, "🍗"], [/beef|steak|pork|lamb|bacon|ham|sausage/, "🥩"], [/salmon|fish|tuna|cod/, "🐟"],
  [/shrimp|prawn/, "🦐"], [/tofu|bean|lentil|chickpea/, "🫘"], [/garlic/, "🧄"], [/onion|shallot|scallion/, "🧅"],
  [/tomato/, "🍅"], [/broccoli/, "🥦"], [/lettuce|romaine|spinach|kale|greens|cabbage/, "🥬"], [/bell pepper|capsicum/, "🫑"],
  [/chili|jalape/, "🌶️"], [/carrot/, "🥕"], [/potato/, "🥔"], [/corn/, "🌽"], [/mushroom/, "🍄"], [/avocado/, "🥑"],
  [/cucumber/, "🥒"], [/lemon|lime/, "🍋"], [/apple/, "🍎"], [/banana/, "🍌"], [/strawberr/, "🍓"], [/berr/, "🫐"],
  [/grape/, "🍇"], [/orange/, "🍊"], [/honey|syrup/, "🍯"], [/oil|olive/, "🫒"], [/chocolate|cocoa/, "🍫"],
  [/coffee/, "☕"], [/tea\b/, "🍵"], [/sauce|ketchup|dressing|vinegar|paste/, "🥫"], [/salt|pepper|spice|cinnamon|cumin|paprika/, "🧂"],
];

const state = {
  recipes: [],
  plan: [],
  pantry: [],
  restrictions: [],
  weekStart: mondayOf(new Date()),
  editingRecipeId: null,
  hideConflicts: readSetting("hideConflicts", true),
};

const $ = (selector) => document.querySelector(selector);

// ---------- Helpers ----------

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

function formatShort(date) {
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function weekLabel() {
  return `${formatShort(state.weekStart)} – ${formatShort(addDays(state.weekStart, 6))}`;
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

function pickEmoji(table, name, fallback) {
  const lower = String(name).toLowerCase();
  return table.find(([pattern]) => pattern.test(lower))?.[1] ?? fallback;
}
const recipeEmoji = (name) => pickEmoji(RECIPE_EMOJI, name, "🍽️");
const foodEmoji = (name) => pickEmoji(FOOD_EMOJI, name, "🥫");

function avatarColor(name) {
  let hash = 0;
  for (const ch of String(name)) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

const icon = (name) => `<i data-lucide="${name}"></i>`;

function refreshIcons() {
  window.lucide?.createIcons();
}

function pantryNames() {
  return new Set(state.pantry.map((item) => normalizeName(item.name)));
}

/** One badge per restriction, even if several ingredients trigger it. */
function conflictBadges(recipe) {
  const seen = new Map();
  for (const c of recipe.conflicts) if (!seen.has(c.restriction)) seen.set(c.restriction, c);
  return [...seen.values()]
    .map((c) => `<span class="badge ${c.kind}" title="Contains ${escapeHtml(c.ingredient)}">
        ${icon(c.kind === "allergy" ? "shield-alert" : "thumbs-down")}${escapeHtml(c.restriction)}</span>`)
    .join("");
}

let toastTimer;
function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2500);
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

// ---------- Data loading ----------

const loaders = {
  recipes: async () => { state.recipes = await api("/api/recipes"); },
  plan: async () => { state.plan = await api(`/api/plan?start=${isoDate(state.weekStart)}`); },
  pantry: async () => { state.pantry = await api("/api/pantry"); },
  restrictions: async () => { state.restrictions = await api("/api/restrictions"); },
};

async function reload(...names) {
  await Promise.all(names.map((name) => loaders[name]()));
}

// ---------- Planner ----------

function renderPlanner() {
  $("#week-label").textContent = weekLabel();
  const today = isoDate(new Date());
  const recipesById = new Map(state.recipes.map((r) => [r.id, r]));
  const safeRecipes = state.recipes.filter((r) => !r.conflicts.length);
  const options = safeRecipes.length
    ? safeRecipes.map((r) => `<option value="${r.id}">${recipeEmoji(r.name)} ${escapeHtml(r.name)}</option>`).join("")
    : `<option disabled>No recipes available</option>`;

  const planned = state.plan.length;
  const total = DAY_NAMES.length * MEALS.length;
  $("#plan-progress").textContent = `${planned} of ${total} meals planned this week`;
  $("#plan-progress-bar").style.width = `${(planned / total) * 100}%`;

  $("#week-grid").innerHTML = DAY_NAMES.map((dayName, i) => {
    const date = addDays(state.weekStart, i);
    const day = isoDate(date);
    const slots = MEALS.map((meal) => {
      const entry = state.plan.find((e) => e.day === day && e.meal_type === meal.key);
      let content;
      if (entry) {
        const conflicts = recipesById.get(entry.recipe.id)?.conflicts ?? [];
        const warn = conflicts.length
          ? `<span class="warn" title="Contains ${escapeHtml(conflicts.map((c) => c.restriction).join(", "))}">${icon("triangle-alert")}</span>`
          : "";
        content = `<div class="meal">
            <span class="meal-name">${escapeHtml(entry.recipe.name)}</span>${warn}
            <button class="icon-btn" data-clear="${entry.id}" title="Remove" aria-label="Remove ${escapeHtml(entry.recipe.name)}">${icon("x")}</button>
          </div>`;
      } else {
        content = `<select data-day="${day}" data-meal="${meal.key}" aria-label="${dayName} ${meal.label}">
            <option value="">+ Add ${meal.label.toLowerCase()}</option>${options}</select>`;
      }
      return `<div class="slot slot-${meal.key}"><div class="slot-label">${icon(meal.icon)}${meal.label}</div>${content}</div>`;
    }).join("");
    return `<div class="day ${day === today ? "today" : ""}">
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

// ---------- Recipes ----------

function renderRecipes() {
  $("#hide-conflicts").checked = state.hideConflicts;
  const query = $("#recipe-search").value.trim().toLowerCase();
  const matching = state.recipes.filter((r) => r.name.toLowerCase().includes(query));
  const recipes = state.hideConflicts ? matching.filter((r) => !r.conflicts.length) : matching;
  const hiddenCount = matching.length - recipes.length;
  const inPantry = pantryNames();

  const note = $("#hidden-note");
  note.hidden = hiddenCount === 0;
  note.innerHTML = `${icon("eye-off")} ${hiddenCount} recipe${hiddenCount === 1 ? "" : "s"} hidden because of your allergies or dislikes.
    <button class="link-btn" id="show-hidden">Show them</button>`;

  const list = $("#recipe-list");
  if (!recipes.length) {
    list.innerHTML = `<p class="empty"><span class="big">📖</span>${
      state.recipes.length ? "No recipes match." : "No recipes yet. Add your first one!"}</p>`;
    refreshIcons();
    return;
  }

  list.innerHTML = recipes.map((r) => {
    const meta = [`<span>${icon("users")}${r.servings} serving${r.servings === 1 ? "" : "s"}</span>`];
    if (r.prep_minutes != null) meta.push(`<span>${icon("clock")}${r.prep_minutes} min</span>`);
    const ingredients = r.ingredients.map((i) => {
      const have = inPantry.has(normalizeName(i.name));
      return `<li class="${have ? "in-pantry" : ""}">${have ? icon("check") : ""}
        ${escapeHtml(formatQuantity(i.quantity, i.unit))} ${escapeHtml(i.name)}</li>`;
    }).join("");
    return `<article class="recipe-card ${r.conflicts.length ? "has-conflict" : ""}">
      <div class="recipe-head">
        <div class="avatar" style="background:${avatarColor(r.name)}">${recipeEmoji(r.name)}</div>
        <div><h3>${escapeHtml(r.name)}</h3><div class="recipe-meta">${meta.join("")}</div></div>
      </div>
      ${r.conflicts.length ? `<div class="badges">${conflictBadges(r)}</div>` : ""}
      ${r.description ? `<p>${escapeHtml(r.description)}</p>` : ""}
      ${ingredients ? `<ul class="ingredients">${ingredients}</ul>` : ""}
      <div class="card-actions">
        <button class="btn ghost small" data-edit="${r.id}">${icon("pencil")}Edit</button>
        <button class="btn danger small" data-delete="${r.id}">${icon("trash-2")}Delete</button>
      </div>
    </article>`;
  }).join("");
  refreshIcons();
}

$("#recipe-search").addEventListener("input", renderRecipes);

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
  const ingredients = [...document.querySelectorAll(".ingredient-row")]
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

// ---------- Pantry ----------

function renderSuggestions() {
  const names = new Set();
  state.recipes.forEach((r) => r.ingredients.forEach((i) => names.add(i.name.toLowerCase())));
  $("#ingredient-suggestions").innerHTML = [...names].sort().map((n) => `<option value="${escapeHtml(n)}"></option>`).join("");
  $("#unit-suggestions").innerHTML = COMMON_UNITS.map((u) => `<option value="${u}"></option>`).join("");
}

async function renderPantry() {
  renderSuggestions();
  const list = $("#pantry-list");
  list.innerHTML = state.pantry.length
    ? state.pantry.map((item) => `<li class="pantry-row">
        <span class="food-emoji">${foodEmoji(item.name)}</span>
        <span class="pantry-name">${escapeHtml(item.name)}</span>
        <span class="qty-edit">
          <input type="number" min="0" step="any" placeholder="some" value="${item.quantity ?? ""}"
            data-qty="${item.id}" aria-label="Quantity of ${escapeHtml(item.name)}" />
          ${escapeHtml(item.unit)}
        </span>
        <button class="icon-btn" data-remove="${item.id}" title="Remove" aria-label="Remove ${escapeHtml(item.name)}">${icon("trash-2")}</button>
      </li>`).join("")
    : `<li class="empty"><span class="big">🧺</span>Your pantry is empty. Add what you already have at home.</li>`;
  refreshIcons();

  const ideas = await api("/api/recipes/ideas");
  $("#ideas-list").innerHTML = ideas.length
    ? ideas.map(({ recipe, have, missing }) => {
        const total = have.length + missing.length;
        const pct = total ? Math.round((have.length / total) * 100) : 0;
        const status = missing.length === 0
          ? `<b>You have everything!</b>`
          : `<b>${have.length} of ${total}</b> in pantry · need ${escapeHtml(missing.join(", "))}`;
        return `<div class="idea ${missing.length === 0 ? "ready" : ""}">
          <div class="avatar" style="background:${avatarColor(recipe.name)}">${recipeEmoji(recipe.name)}</div>
          <div class="idea-body">
            <div class="idea-title">${escapeHtml(recipe.name)}</div>
            <div class="idea-bar"><div style="width:${pct}%"></div></div>
            <div class="idea-meta">${status}</div>
          </div>
        </div>`;
      }).join("")
    : `<p class="empty"><span class="big">🍽️</span>No recipes fit your allergies and dislikes yet.</p>`;
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
    await renderPantry();
  }, "Pantry updated");
});

$("#pantry-list").addEventListener("click", (event) => {
  const id = event.target.closest("[data-remove]")?.dataset.remove;
  if (!id) return;
  run(async () => {
    await api(`/api/pantry/${id}`, { method: "DELETE" });
    await reload("pantry");
    await renderPantry();
  });
});

// ---------- Shopping list ----------

function checkedKey() {
  return `shopping-checked:${isoDate(state.weekStart)}`;
}

let shoppingItems = [];

async function renderShopping() {
  $("#shopping-label").textContent = `For ${weekLabel()} · items in your pantry are taken off automatically`;
  shoppingItems = (await api(`/api/shopping-list?start=${isoDate(state.weekStart)}`)).items;
  const toBuy = shoppingItems.filter((item) => item.status !== "have");
  const have = shoppingItems.filter((item) => item.status === "have");
  const checked = new Set(readSetting(checkedKey(), []));

  $("#to-buy-count").textContent = toBuy.length;
  $("#have-count").textContent = have.length;
  $("#have-card").hidden = have.length === 0;

  $("#shopping-list").innerHTML = toBuy.length
    ? toBuy.map((item) => {
        const index = shoppingItems.indexOf(item);
        const key = `${item.name}|${item.unit}`.toLowerCase();
        const isChecked = checked.has(key);
        let sub = escapeHtml(item.recipes.join(", "));
        if (item.status === "partial") {
          sub = `<span class="item-sub partial">You have ${escapeHtml(formatQuantity(item.pantry_quantity, item.pantry_unit))}, need ${escapeHtml(formatQuantity(item.quantity, item.unit))} total</span>`;
        } else if (item.status === "check") {
          sub = `<span class="item-sub partial">Pantry has ${escapeHtml(formatQuantity(item.pantry_quantity, item.pantry_unit) || "some")}. Check if it's enough</span>`;
        } else {
          sub = `<span class="item-sub">${sub}</span>`;
        }
        return `<li class="${isChecked ? "checked" : ""}"><div class="shop-row">
          <label>
            <input type="checkbox" data-key="${escapeHtml(key)}" ${isChecked ? "checked" : ""} />
            <span class="food-emoji">${foodEmoji(item.name)}</span>
            <span class="item-text">
              <span class="qty">${escapeHtml(formatQuantity(item.to_buy, item.unit))}</span><span class="item-name">${escapeHtml(item.name)}</span>
              ${sub}
            </span>
          </label>
          <button class="icon-btn positive" data-stock="${index}" title="Bought it: add to pantry" aria-label="Add ${escapeHtml(item.name)} to pantry">${icon("package-plus")}</button>
        </div></li>`;
      }).join("")
    : `<li class="empty"><span class="big">🛒</span>${
        shoppingItems.length ? "Nothing to buy. Your pantry has it all!" : "Nothing planned this week. Add meals in the Plan tab."}</li>`;

  $("#have-list").innerHTML = have.map((item) => `<li><div class="shop-row">
      <span class="food-emoji">${foodEmoji(item.name)}</span>
      <span class="item-text">
        <span class="item-name">${escapeHtml(item.name)}</span>
        <span class="item-sub">Need ${escapeHtml(formatQuantity(item.quantity, item.unit) || "some")} · have ${escapeHtml(formatQuantity(item.pantry_quantity, item.pantry_unit) || "some")}</span>
      </span>
      <span class="have-icon">${icon("circle-check")}</span>
    </div></li>`).join("");
  refreshIcons();
}

$("#shopping-list").addEventListener("change", (event) => {
  const box = event.target.closest("input[data-key]");
  if (!box) return;
  const checked = new Set(readSetting(checkedKey(), []));
  box.checked ? checked.add(box.dataset.key) : checked.delete(box.dataset.key);
  writeSetting(checkedKey(), [...checked]);
  box.closest("li").classList.toggle("checked", box.checked);
});

$("#shopping-list").addEventListener("click", (event) => {
  const index = event.target.closest("[data-stock]")?.dataset.stock;
  if (index === undefined) return;
  const item = shoppingItems[Number(index)];
  run(async () => {
    await api("/api/pantry", { method: "POST", body: { name: item.name, quantity: item.to_buy, unit: item.unit } });
    await reload("pantry");
    await renderShopping();
  }, `${item.name} added to pantry`);
});

$("#clear-checked").addEventListener("click", () => {
  writeSetting(checkedKey(), []);
  run(renderShopping);
});

// ---------- Allergies & dislikes ----------

function renderPreferences() {
  const chip = (r) => `<span class="chip ${r.kind}">${escapeHtml(r.name)}
      <button class="icon-btn" data-unrestrict="${r.id}" title="Remove" aria-label="Remove ${escapeHtml(r.name)}">${icon("x")}</button></span>`;
  const allergies = state.restrictions.filter((r) => r.kind === "allergy");
  const dislikes = state.restrictions.filter((r) => r.kind === "dislike");
  $("#allergy-list").innerHTML = allergies.map(chip).join("") || `<p class="subtle">No allergies added.</p>`;
  $("#dislike-list").innerHTML = dislikes.map(chip).join("") || `<p class="subtle">No dislikes added.</p>`;

  const existing = new Set(state.restrictions.map((r) => r.name.toLowerCase()));
  const suggestions = COMMON_RESTRICTIONS.filter((name) => !existing.has(name.toLowerCase()));
  $("#quick-chips").innerHTML = suggestions.length
    ? suggestions.map((name) => `<button class="chip suggest" data-quick="${name}">+ ${name}</button>`).join("")
    : `<span class="subtle">All added</span>`;
  refreshIcons();
}

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

document.querySelector("#view-preferences").addEventListener("click", (event) => {
  const id = event.target.closest("[data-unrestrict]")?.dataset.unrestrict;
  if (!id) return;
  run(async () => {
    await api(`/api/restrictions/${id}`, { method: "DELETE" });
    await reload("restrictions", "recipes");
    renderPreferences();
  });
});

// ---------- Tabs ----------

let currentView = "planner";

const renderers = {
  planner: renderPlanner,
  recipes: renderRecipes,
  pantry: renderPantry,
  shopping: renderShopping,
  preferences: renderPreferences,
};

function renderCurrentView() {
  return run(async () => renderers[currentView]());
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    currentView = tab.dataset.view;
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${currentView}`));
    renderCurrentView();
  });
});

// ---------- Start ----------

window.addEventListener("load", refreshIcons); // lucide loads with `defer`
run(async () => {
  await reload("recipes", "plan", "pantry", "restrictions");
  await renderCurrentView();
});
