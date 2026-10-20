# 🥗 Elevate Plate

![CI](https://github.com/joudiheilani/elevate-plate/actions/workflows/ci.yml/badge.svg)

A web app for planning a week of meals. Keep a library of recipes, track what's already in your pantry, set allergies and dislikes, and get a shopping list with only what you actually need to buy.

**Live demo:** https://elevate-plate.vercel.app

## Features

- **Recipe library**: create, edit, search and delete recipes with ingredients, servings, prep time and instructions.
- **Weekly planner**: assign a recipe to any breakfast, lunch or dinner slot and move between weeks.
- **Pantry & fridge**: record what you already have. The shopping list subtracts it: fully stocked items move to an "Already in your pantry" section, and partly stocked items show only the shortfall. One click adds a bought item to the pantry.
- **What can I make?**: recipes ranked by how many of their ingredients are already in your pantry.
- **Allergies & dislikes**: recipes containing them are left out of meal ideas and the planner, and flagged with a badge in the recipe library (with a toggle to hide them). Groups such as *Dairy*, *Gluten*, *Nuts*, *Eggs*, *Shellfish*, *Fish*, *Soy* and *Meat* expand to their common ingredients (Dairy covers milk, cheese, butter, yogurt…), with exceptions such as peanut butter and coconut milk.
- **Shopping list**: ingredients from the week's meals are combined automatically (same name and unit are summed), and you can tick items off as you shop.
- Sample recipes are added the first time the app runs, so a new deployment isn't empty.

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
│   │   │                     #   PantryItem, FoodRestriction
│   │   ├── schemas.py        # Pydantic request/response models + validation
│   │   ├── seed.py           # Sample recipes for a fresh database
│   │   ├── routers/
│   │   │   ├── recipes.py    # /api/recipes CRUD and meal ideas
│   │   │   ├── plan.py       # /api/plan and /api/shopping-list
│   │   │   ├── pantry.py     # /api/pantry CRUD
│   │   │   └── restrictions.py  # /api/restrictions (allergies & dislikes)
│   │   └── services/
│   │       ├── matching.py   # Name normalisation, allergy groups, pantry matching
│   │       └── shopping.py   # Ingredient aggregation and pantry subtraction
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
| GET    | `/api/recipes?q=&safe_only=`           | List recipes with any allergy/dislike conflicts; `safe_only=true` hides them |
| GET    | `/api/recipes/ideas`                   | Safe recipes ranked by pantry coverage        |
| POST   | `/api/recipes`                         | Create a recipe                               |
| GET    | `/api/recipes/{id}`                    | Get one recipe                                |
| PUT    | `/api/recipes/{id}`                    | Update a recipe (replaces its ingredients)    |
| DELETE | `/api/recipes/{id}`                    | Delete a recipe (and its planned meals)       |
| GET    | `/api/plan?start=YYYY-MM-DD`           | Meals planned for the 7 days from `start`     |
| PUT    | `/api/plan`                            | Set a slot: `{day, meal_type, recipe_id}`     |
| DELETE | `/api/plan/{id}`                       | Clear a planned meal                          |
| GET    | `/api/shopping-list?start=YYYY-MM-DD`  | Combined ingredients for that week, minus the pantry |
| GET    | `/api/pantry`                          | List pantry items                             |
| POST   | `/api/pantry`                          | Add an item (merges with an existing one)     |
| PUT    | `/api/pantry/{id}`                     | Update an item's name, quantity or unit       |
| DELETE | `/api/pantry/{id}`                     | Remove an item                                |
| GET    | `/api/restrictions`                    | List allergies and dislikes                   |
| POST   | `/api/restrictions`                    | Add one: `{name, kind: "allergy" \| "dislike"}` |
| DELETE | `/api/restrictions/{id}`               | Remove one                                    |

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
