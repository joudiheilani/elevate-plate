"use strict";

const MEAL_TYPES = ["breakfast", "lunch", "dinner"];
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const state = {
  recipes: [],
  plan: [],
  weekStart: mondayOf(new Date()),
  editingRecipeId: null,
};

const $ = (selector) => document.querySelector(selector);

// ---------- Helpers ----------

function mondayOf(date) {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const offset = (d.getDay() + 6) % 7; // Monday = 0
  d.setDate(d.getDate() - offset);
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

async function loadRecipes() {
  state.recipes = await api("/api/recipes");
}

async function loadPlan() {
  state.plan = await api(`/api/plan?start=${isoDate(state.weekStart)}`);
}

// ---------- Planner view ----------

function renderPlanner() {
  $("#week-label").textContent = weekLabel();
  const today = isoDate(new Date());
  const recipeOptions = state.recipes
    .map((r) => `<option value="${r.id}">${escapeHtml(r.name)}</option>`)
    .join("");

  $("#week-grid").innerHTML = DAY_NAMES.map((dayName, i) => {
    const day = isoDate(addDays(state.weekStart, i));
    const slots = MEAL_TYPES.map((meal) => {
      const entry = state.plan.find((e) => e.day === day && e.meal_type === meal);
      const content = entry
        ? `<div class="meal"><span>${escapeHtml(entry.recipe.name)}</span>
             <button class="icon-btn" data-clear="${entry.id}" title="Remove">×</button></div>`
        : `<select data-day="${day}" data-meal="${meal}">
             <option value="">+ Add</option>${recipeOptions}</select>`;
      return `<div class="slot"><div class="slot-label">${meal}</div>${content}</div>`;
    }).join("");
    return `<div class="day ${day === today ? "today" : ""}">
      <div class="day-head"><span class="day-name">${dayName}</span>
      <span class="day-date">${formatShort(addDays(state.weekStart, i))}</span></div>${slots}</div>`;
  }).join("");
}

$("#week-grid").addEventListener("change", (event) => {
  const select = event.target.closest("select[data-day]");
  if (!select || !select.value) return;
  run(async () => {
    await api("/api/plan", {
      method: "PUT",
      body: { day: select.dataset.day, meal_type: select.dataset.meal, recipe_id: Number(select.value) },
    });
    await loadPlan();
    renderPlanner();
  }, "Meal planned");
});

$("#week-grid").addEventListener("click", (event) => {
  const button = event.target.closest("[data-clear]");
  if (!button) return;
  run(async () => {
    await api(`/api/plan/${button.dataset.clear}`, { method: "DELETE" });
    await loadPlan();
    renderPlanner();
  });
});

function changeWeek(newStart) {
  state.weekStart = newStart;
  run(async () => {
    await loadPlan();
    renderCurrentView();
  });
}

$("#prev-week").addEventListener("click", () => changeWeek(addDays(state.weekStart, -7)));
$("#next-week").addEventListener("click", () => changeWeek(addDays(state.weekStart, 7)));
$("#this-week").addEventListener("click", () => changeWeek(mondayOf(new Date())));

// ---------- Recipes view ----------

function renderRecipes() {
  const query = $("#recipe-search").value.trim().toLowerCase();
  const recipes = state.recipes.filter((r) => r.name.toLowerCase().includes(query));
  const list = $("#recipe-list");

  if (!recipes.length) {
    list.innerHTML = `<p class="empty">${state.recipes.length ? "No recipes match your search." : "No recipes yet — add your first one!"}</p>`;
    return;
  }

  list.innerHTML = recipes.map((r) => {
    const meta = [`${r.servings} serving${r.servings === 1 ? "" : "s"}`];
    if (r.prep_minutes != null) meta.push(`${r.prep_minutes} min`);
    const ingredients = r.ingredients
      .map((i) => `<li>${escapeHtml(formatQuantity(i.quantity, i.unit))} ${escapeHtml(i.name)}</li>`)
      .join("");
    return `<article class="recipe-card">
      <h3>${escapeHtml(r.name)}</h3>
      <div class="recipe-meta">${meta.join(" · ")}</div>
      ${r.description ? `<p>${escapeHtml(r.description)}</p>` : ""}
      ${ingredients ? `<ul>${ingredients}</ul>` : ""}
      <div class="card-actions">
        <button class="btn ghost small" data-edit="${r.id}">Edit</button>
        <button class="btn danger small" data-delete="${r.id}">Delete</button>
      </div>
    </article>`;
  }).join("");
}

$("#recipe-search").addEventListener("input", renderRecipes);

$("#recipe-list").addEventListener("click", (event) => {
  const editId = event.target.closest("[data-edit]")?.dataset.edit;
  const deleteId = event.target.closest("[data-delete]")?.dataset.delete;
  if (editId) openRecipeDialog(state.recipes.find((r) => r.id === Number(editId)));
  if (deleteId) {
    const recipe = state.recipes.find((r) => r.id === Number(deleteId));
    if (!confirm(`Delete "${recipe.name}"? It will also be removed from your meal plan.`)) return;
    run(async () => {
      await api(`/api/recipes/${deleteId}`, { method: "DELETE" });
      await Promise.all([loadRecipes(), loadPlan()]);
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
    <input name="unit" placeholder="Unit" maxlength="30" value="${escapeHtml(ingredient.unit)}" />
    <input name="ingredient" placeholder="Ingredient" maxlength="120" value="${escapeHtml(ingredient.name)}" />
    <button type="button" class="icon-btn" title="Remove">×</button>`;
  row.querySelector("button").addEventListener("click", () => row.remove());
  $("#ingredient-rows").appendChild(row);
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
    .map((row) => ({
      name: row.querySelector("[name=ingredient]").value.trim(),
      unit: row.querySelector("[name=unit]").value.trim(),
      quantity: row.querySelector("[name=qty]").value === "" ? null : Number(row.querySelector("[name=qty]").value),
    }))
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
    await api(id ? `/api/recipes/${id}` : "/api/recipes", {
      method: id ? "PUT" : "POST",
      body: readRecipeForm(),
    });
    dialog.close();
    await Promise.all([loadRecipes(), loadPlan()]);
    renderRecipes();
  }, id ? "Recipe updated" : "Recipe added");
});

// ---------- Shopping list view ----------

function checkedKey() {
  return `shopping-checked:${isoDate(state.weekStart)}`;
}

function readChecked() {
  try {
    return new Set(JSON.parse(localStorage.getItem(checkedKey()) || "[]"));
  } catch {
    return new Set();
  }
}

function writeChecked(checked) {
  try {
    localStorage.setItem(checkedKey(), JSON.stringify([...checked]));
  } catch { /* storage unavailable: checkmarks just won't persist */ }
}

async function renderShopping() {
  $("#shopping-label").textContent = `Shopping list · ${weekLabel()}`;
  const data = await api(`/api/shopping-list?start=${isoDate(state.weekStart)}`);
  const list = $("#shopping-list");
  if (!data.items.length) {
    list.innerHTML = `<li class="empty">Nothing planned this week. Add meals in the Week plan tab.</li>`;
    return;
  }
  const checked = readChecked();
  list.innerHTML = data.items.map((item) => {
    const key = `${item.name}|${item.unit}`.toLowerCase();
    const isChecked = checked.has(key);
    return `<li class="${isChecked ? "checked" : ""}">
      <label>
        <input type="checkbox" data-key="${escapeHtml(key)}" ${isChecked ? "checked" : ""} />
        <span class="item-text"><span class="qty">${escapeHtml(formatQuantity(item.quantity, item.unit))}</span>
        ${escapeHtml(item.name)}</span>
        <span class="from">${escapeHtml(item.recipes.join(", "))}</span>
      </label></li>`;
  }).join("");
}

$("#shopping-list").addEventListener("change", (event) => {
  const box = event.target.closest("input[data-key]");
  if (!box) return;
  const checked = readChecked();
  box.checked ? checked.add(box.dataset.key) : checked.delete(box.dataset.key);
  writeChecked(checked);
  box.closest("li").classList.toggle("checked", box.checked);
});

$("#clear-checked").addEventListener("click", () => {
  writeChecked(new Set());
  run(renderShopping);
});

// ---------- Tabs ----------

let currentView = "planner";

function renderCurrentView() {
  if (currentView === "planner") renderPlanner();
  if (currentView === "recipes") renderRecipes();
  if (currentView === "shopping") return run(renderShopping);
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

run(async () => {
  await Promise.all([loadRecipes(), loadPlan()]);
  renderCurrentView();
});
