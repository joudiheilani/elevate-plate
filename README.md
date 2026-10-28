# Elevate Plate

![CI](https://github.com/joudiheilani/elevate-plate/actions/workflows/ci.yml/badge.svg)

A budget-aware meal planner. Plan your week yourself, or have Elevate Plate generate a personalized week of meals and a priced grocery list from your budget, diet, allergies and how much time you have to cook.

**Live demo:** https://elevate-plate.vercel.app

## Features

### Three ways to plan

- **"I'll plan it myself"**: pick your own recipes and meals, and add your own grocery items with prices. Everything is tracked against your weekly budget.
- **"Mix it up"**: plan the meals you already have in mind, and the generator fills every empty slot. Your meals are kept exactly as they are (even if they break the time limit) and count toward the budget and grocery list, so the meals it adds fit what's left.
- **"Plan it for me"**: enter a weekly budget, the number of people, the time you can spend per meal (15 minutes to no limit), your diet and which meals to plan. The generator builds a full week and a priced grocery list that fits, respecting your allergies and dislikes and using what's already in your pantry. Shuffle for a different week, then apply it to your planner in one click.

### Budget

- Every recipe shows an estimated **cost per serving**, and every shopping-list item an estimated price, based on typical US supermarket prices for the package you'd actually buy (one bag of rice, not 1.5 cups). See [Where the prices come from](#where-the-prices-come-from).
- The shopping list shows the week's **estimated total against your budget** with a live meter, and a budget chip in the header follows you everywhere.
- Recipes are scaled to your household size, and basics (oil, spices, soy sauce) can be treated as already at home.

### Everything else

- **Recipe library**: create, edit, search and delete recipes with ingredients, servings, prep time and instructions.
- **Weekly planner**: assign a recipe to any breakfast, lunch or dinner slot and move between weeks.
- **Pantry & fridge**: record what you already have. The shopping list subtracts it: fully stocked items move to an "Already in your pantry" section, and partly stocked items show only the shortfall. One click adds a bought item to the pantry.
- **What can I make?**: recipes ranked by how many of their ingredients are already in your pantry.
- **Allergies & dislikes**: recipes containing them are left out of meal ideas and the planner, and flagged with a badge in the recipe library (with a toggle to hide them). Groups such as *Dairy*, *Gluten*, *Nuts*, *Eggs*, *Shellfish*, *Fish*, *Soy* and *Meat* expand to their common ingredients (Dairy covers milk, cheese, butter, yogurt…), with exceptions such as peanut butter and coconut milk.
- **Shopping list**: ingredients from the week's meals are combined automatically (same name and unit are summed), and you can tick items off as you shop.
- **Diets**: Vegetarian, Vegan and Pescatarian apply everywhere, on top of allergies and dislikes.
- **Soft neobrutalist UI**: ink borders, hard offset shadows, flat bold colors and sticker-style labels, with soft neumorphic wells for inputs, rings and meters. Lucide icons throughout, and motion: drifting background shapes, a sliding tab indicator, staggered card entrances, an animated striped budget meter, counting numbers, buttons that press in, and a confetti burst when you apply a plan or finish shopping. Motion is turned off for users who prefer reduced motion.
- Sample recipes are added the first time the app runs, so a new deployment isn't empty.

## How the meal plan generator works

The generator ([`services/generator.py`](backend/app/services/generator.py)) is rule-based and uses a built-in catalog of 26 recipes ([`data/catalog.py`](backend/app/data/catalog.py)) with cooking times, and a grocery price table ([`data/prices.py`](backend/app/data/prices.py)).

1. **Filter**: keep recipes within the time limit that don't conflict with the diet, allergies or dislikes.
2. **Keep your meals (mix mode)**: meals already planned that week are locked in. They're added to the grocery list first and never swapped.
3. **Fill the open slots greedily**: each slot gets the recipe with the lowest *extra* grocery cost given what's already on the list, so ingredients get reused (a bag of rice bought for Monday makes later rice dishes nearly free). Pantry coverage, variety and a little randomness (for "Shuffle") also count.
4. **Fix the budget**: price the list in whole packages; while it's over budget, swap generated meals (or every generated occurrence of a recipe) for alternatives that lower the total. If the budget can't be met, the plan says so and suggests what to change.

A whole week is generated in well under a second, for free, and the same inputs and seed always give the same plan, which keeps it testable.

### Where the prices come from

The prices in [`data/prices.py`](backend/app/data/prices.py) are **hand-written estimates** of typical US supermarket package prices (around 2024–25), based on general knowledge. They are not pulled from a store, an API or a dataset, and real prices vary by store, region and season. Treat them as ballpark figures for comparing meals and staying roughly on budget.

How a "cost per serving" is worked out: each ingredient costs the share of its package the recipe uses (1 cup of rice is 1/20 of a $5.00, 20-cup bag, so $0.25). Those shares are added up and divided by the recipe's servings. Shopping-list prices are different on purpose: they're for whole packages, since that's what you pay at the register. Items you add yourself can carry your own real price, which is used instead of the estimate.

Ways to make prices real, if needed later:

- **Kroger Products API** (free developer account): live prices from Kroger-family stores near a ZIP code.
- **U.S. Bureau of Labor Statistics "Average Price Data"**: official national average prices for staples (eggs, milk, bread, ground beef...), updated monthly. Good for calibrating the table.
- **Let users correct prices**: save the price you actually paid per ingredient and prefer it over the estimate next time.

### Would an LLM make it better?

An LLM API (such as Claude) could add new recipes beyond the catalog, take preferences in plain language ("high protein, nothing spicy") and suggest substitutions. The trade-offs are a paid API key stored as a secret, a cost for every plan, 5–20 seconds per generation, results that differ each time (harder to test), and unreliable prices. A good next step would be an optional "AI chef" that proposes extra recipes, while this engine keeps doing the budgeting.

## Tech stack

| Layer      | Technology                                                        |
| ---------- | ----------------------------------------------------------------- |
| Frontend   | HTML, CSS, vanilla JavaScript (no build step), [Lucide](https://lucide.dev) icons |
| Backend    | Python 3.12, [FastAPI](https://fastapi.tiangolo.com/) REST API    |
| Database   | PostgreSQL ([Neon](https://neon.tech)) via SQLAlchemy 2.0; SQLite for local dev |
| Hosting    | [Vercel](https://vercel.com): static frontend + Python serverless function |
| CI         | GitHub Actions: Ruff lint/format checks and pytest against a real Postgres |

## Architecture

```
Browser ──► Vercel
             ├── /            → frontend/ (static HTML/CSS/JS)
             └── /api/*       → api/index.py (FastAPI, serverless) ──► Neon Postgres
```

## Project structure

```
elevate-plate/
├── api/
│   └── index.py              # Vercel serverless entry point
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, health check, startup
│   │   ├── database.py       # Engine/session setup (DATABASE_URL)
│   │   ├── models.py         # SQLAlchemy models: Recipe, Ingredient, MealPlanEntry,
│   │   │                     #   PantryItem, FoodRestriction, GroceryItem, Profile
│   │   ├── schemas.py        # Pydantic request/response models + validation
│   │   ├── seed.py           # Sample recipes for a fresh database
│   │   ├── data/
│   │   │   ├── catalog.py    # Built-in recipes for the generator
│   │   │   └── prices.py     # Grocery package prices and kitchen staples
│   │   ├── routers/
│   │   │   ├── recipes.py    # /api/recipes CRUD and meal ideas
│   │   │   ├── plan.py       # /api/plan and /api/shopping-list
│   │   │   ├── pantry.py     # /api/pantry CRUD
│   │   │   ├── restrictions.py  # /api/restrictions (allergies & dislikes)
│   │   │   ├── profile.py    # /api/profile (budget, household, diet, mode)
│   │   │   ├── groceries.py  # /api/groceries (your own shopping-list items)
│   │   │   └── generator.py  # /api/generator (generate & apply a week)
│   │   └── services/
│   │       ├── matching.py   # Name normalisation, allergy & diet groups, pantry matching
│   │       ├── pricing.py    # Cost estimates for ingredients and recipes
│   │       ├── shopping.py   # Scaling, aggregation, pantry subtraction, pricing
│   │       └── generator.py  # Budget-aware meal plan generator
│   └── tests/                # pytest suite
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── .github/workflows/ci.yml  # Continuous integration
├── vercel.json               # Vercel routing/build config
├── requirements.txt          # Runtime dependencies
└── requirements-dev.txt      # + test & lint tools
```

## API

Interactive docs are served at `/docs` when running locally.

| Method | Endpoint                               | Description                                   |
| ------ | -------------------------------------- | --------------------------------------------- |
| GET    | `/api/health`                          | Health check (also checks the DB connection)  |
| GET    | `/api/recipes?q=&safe_only=`           | List recipes with cost per serving and any diet/allergy/dislike conflicts; `safe_only=true` hides them |
| GET    | `/api/recipes/ideas`                   | Safe recipes ranked by pantry coverage        |
| POST   | `/api/recipes`                         | Create a recipe                               |
| GET    | `/api/recipes/{id}`                    | Get one recipe                                |
| PUT    | `/api/recipes/{id}`                    | Update a recipe (replaces its ingredients)    |
| DELETE | `/api/recipes/{id}`                    | Delete a recipe (and its planned meals)       |
| GET    | `/api/plan?start=YYYY-MM-DD`           | Meals planned for the 7 days from `start`     |
| PUT    | `/api/plan`                            | Set a slot: `{day, meal_type, recipe_id}`     |
| DELETE | `/api/plan/{id}`                       | Clear a planned meal                          |
| GET    | `/api/shopping-list?start=YYYY-MM-DD`  | That week's ingredients (scaled to your household, minus the pantry) plus your own items, with prices, total and budget |
| GET    | `/api/pantry`                          | List pantry items                             |
| POST   | `/api/pantry`                          | Add an item (merges with an existing one)     |
| PUT    | `/api/pantry/{id}`                     | Update an item's name, quantity or unit       |
| DELETE | `/api/pantry/{id}`                     | Remove an item                                |
| GET    | `/api/restrictions`                    | List allergies and dislikes                   |
| POST   | `/api/restrictions`                    | Add one: `{name, kind: "allergy" \| "dislike"}` |
| DELETE | `/api/restrictions/{id}`               | Remove one                                    |
| GET    | `/api/profile`                         | Budget, household size, cooking time, diet, meals, planning mode (`manual`, `hybrid`, `auto`) |
| PUT    | `/api/profile`                         | Update the profile                            |
| GET    | `/api/groceries`                       | Your own shopping-list items                  |
| POST   | `/api/groceries`                       | Add one: `{name, quantity, unit, price}` (price optional) |
| DELETE | `/api/groceries/{id}`                  | Remove one                                    |
| POST   | `/api/generator`                       | Preview a generated week (nothing is saved); `fill_gaps: true` keeps meals already planned |
| POST   | `/api/generator/apply`                 | Save a generated week to the library and planner |

## Running locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn backend.app.main:app --reload
```

Open http://localhost:8000. With no `DATABASE_URL` set, data is stored in a local SQLite file (`mealplanner.db`). To use Postgres locally, copy `.env.example` to `.env` and set `DATABASE_URL`.

### Tests and linting

```bash
pytest
ruff check .
ruff format --check .
```

Tests use in-memory SQLite by default. Set `TEST_DATABASE_URL` to run them against Postgres, which is what CI does.

## Continuous integration

Every push and pull request to `main` runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

1. Starts a PostgreSQL 16 service container
2. Installs dependencies
3. Lints with `ruff check` and checks formatting with `ruff format --check`
4. Runs the pytest suite against Postgres

Vercel's GitHub integration deploys every push to `main` to production and every pull request to a preview URL.

## Deploying to Vercel (free)

1. **Push to GitHub.** Create a public repo named `elevate-plate` and push this project.
2. **Import into Vercel.** At [vercel.com/new](https://vercel.com/new), import the repo. Leave the framework preset as **Other** and keep the default settings. `vercel.json` handles the build.
3. **Add a database.** In the Vercel project, open **Storage → Create Database → Neon (Serverless Postgres)**, choose the free plan, and connect it to the project. This sets `DATABASE_URL` automatically.
4. **Redeploy.** Go to **Deployments → ⋯ → Redeploy** so the function picks up `DATABASE_URL`. Tables and sample recipes are created on first request.
5. **Check it.** `https://<your-project>.vercel.app/api/health` should return `{"status":"ok","database":"ok"}`.

> Vercel functions have no persistent disk, so `DATABASE_URL` must point to Postgres. SQLite is only for local development.
