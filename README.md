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
- Every recipe, planned meal and generated meal shows its **macros per serving** (calories, protein, carbs, fat), and each planner day shows a per-person total. They're estimated from the ingredients using public-domain [USDA FoodData Central](https://fdc.nal.usda.gov) values ([`data/nutrition.py`](backend/app/data/nutrition.py)), or you can type in your own numbers when adding a recipe (blank ones are still estimated).
- **Daily macro goals** (optional, per person) for generated plans: calories, protein, carbs and/or fat. Each meal is scored on how close it gets to its share of the day (breakfast 25%, lunch 35%, dinner 40%), and the generator can pick 1.5 or 2 servings when one isn't enough. The shopping list buys for those portions.
- **Dining out:** mark any breakfast, lunch or dinner as eating out, with where and what you expect to spend. The generator leaves those slots open in every mode, and the spend counts toward your weekly budget.
- The shopping list shows the week's **estimated total against your budget** with a live meter, and a budget chip in the header follows you everywhere.
- Recipes are scaled to your household size, and basics (oil, spices, soy sauce) can be treated as already at home.

### Everything else

- **Discover recipes**: search [TheMealDB](https://www.themealdb.com/), a free public recipe database, from the Recipes tab. Each result shows an estimated cost per serving and any diet/allergy conflicts, and can be added to your library in one click (credited, with links to TheMealDB and the original source).
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

The generator ([`services/generator.py`](backend/app/services/generator.py)) is rule-based. It picks from a built-in catalog of 112 recipes ([`data/catalog.py`](backend/app/data/catalog.py)) with cooking times, plus your own saved recipes (unless you turn that off), and prices them with a grocery price table ([`data/prices.py`](backend/app/data/prices.py)). A saved recipe is offered for the meals you've planned it for before; otherwise breakfast-sounding names ("pancakes", "oatmeal") go to breakfast and everything else to lunch and dinner. Saved recipes without a cooking time are skipped when a time limit is set.

1. **Filter**: keep recipes within the time limit that don't conflict with the diet, allergies or dislikes.
2. **Keep your meals (mix mode)**: meals already planned that week are locked in. They're added to the grocery list first and never swapped.
3. **Fill the open slots greedily**: each slot gets the recipe with the lowest *extra* grocery cost given what's already on the list, so ingredients get reused (a bag of rice bought for Monday makes later rice dishes nearly free). Pantry coverage, variety and a little randomness (for "Shuffle") also count.
4. **Fix the budget**: price the list in whole packages; while it's over budget, swap generated meals (or every generated occurrence of a recipe) for alternatives that lower the total. If the budget can't be met, the plan says so and suggests what to change.

A whole week is generated in well under a second, for free, and the same inputs and seed always give the same plan, which keeps it testable.

### Where the recipes come from

- **Built-in catalog (112 recipes)**, in [`data/catalog.py`](backend/app/data/catalog.py): original write-ups of common home dishes (overnight oats, black bean tacos, minestrone...). Ingredient lists of everyday dishes aren't copyrightable, and the descriptions and instructions are written for this project, so they're free to use.
- **TheMealDB** (on demand, via Discover): fetched live from TheMealDB's free API using its test key, which TheMealDB allows "during development of your app or for educational use". Results are credited as "Recipe data and imagery: TheMealDB", and imported recipes keep links to TheMealDB and to the original source. Recipes are only copied into your library when you choose to add one. Publishing an app on an app store would need a TheMealDB supporter key.
- **Your own recipes**: whatever you add.

### Where the prices come from

Prices live in [`data/prices.py`](backend/app/data/prices.py), and every recipe shows a per-ingredient breakdown (hover over its cost) naming each price's source:

- **U.S. Bureau of Labor Statistics "Average Price Data"** (U.S. city average, **September 2026**) for about 20 staples: eggs, milk, bread, ground beef, chicken breast, rice, pasta, bananas, tomatoes, potatoes, cheddar, lettuce, flour, butter, lemons, bacon, sugar, coffee, ice cream and oranges. BLS data is public domain. Per-pound prices are turned into package prices with typical sizes (a banana is about 0.4 lb, a white loaf is 20 oz).
- **Estimates** for everything else: hand-written typical US supermarket prices. These are ballpark figures, not live store prices.
- **Unknown ingredients** get a small flat guess (never multiplied by quantity) and are marked "guessed" in the app.

How a cost is worked out: amounts are converted to the package's unit (grams to pounds, tablespoons to cups, and with typical densities and piece weights, cups of oats to ounces or carrots to pounds). A recipe pays for the share of each package it uses, divided by its servings. The shopping list instead prices whole packages, since that's what you pay at the register.

**Why not GroceryChop?** GroceryChop has live store prices, but its [Terms of Service](https://grocerychop.com/terms) prohibit automated collection ("any robot, spider, scraper or other automated means") and building "a database or competing product from the prices". Its openly licensed Price Index (CC BY 4.0) only has category-level index numbers, not item prices. So it isn't used.

Other ways to make prices more accurate later:

- **Kroger Products API** (free developer account): live prices from Kroger-family stores near a ZIP code, within Kroger's API terms.
- **Let users correct prices**: save the price you actually paid per ingredient and prefer it over the estimate.

### Would an LLM make it better?

An LLM API (such as Claude) could add new recipes beyond the catalog, take preferences in plain language ("high protein, nothing spicy") and suggest substitutions. The trade-offs are a paid API key stored as a secret, a cost for every plan, 5–20 seconds per generation, results that differ each time (harder to test), and unreliable prices. A good next step would be an optional "AI chef" that proposes extra recipes, while this engine keeps doing the budgeting.

## Accounts, iPhone app and installable web app

- **Accounts:** sign up with an email and password. Each account only sees its own
  recipes, plans, pantry, shopping list and preferences. Passwords are hashed with scrypt;
  sessions are random tokens stored only as SHA-256 hashes. Accounts can be deleted from
  the account menu, which permanently removes all their data (an App Store requirement).
- **One codebase, two apps:** the website (this class project's deliverable) and the
  iPhone app share the same frontend, API, database and accounts.
  - **Web:** https://elevate-plate.vercel.app, deployed by Vercel on every push. It's also
    an installable web app (manifest + service worker): in Safari, Share → Add to Home
    Screen.
  - **iPhone:** [`mobile/`](mobile) packages `frontend/` with [Capacitor](https://capacitorjs.com)
    and calls the live API. A GitHub Actions workflow ([`ios.yml`](.github/workflows/ios.yml))
    builds it on a GitHub-hosted Mac, so no Mac is needed, and can upload it to App Store
    Connect. The phone app adds the iOS share sheet, weekly shopping-reminder
    notifications and haptics.
- **Offline:** the app's own files (icons and fonts included, nothing loaded from other
  sites) are cached, and the last data you viewed is saved on the device, so your shopping
  list still opens in a store with no signal.
- **Publishing:** see [docs/app-store/CHECKLIST.md](docs/app-store/CHECKLIST.md) for the
  steps only the developer can do, and [LISTING.md](docs/app-store/LISTING.md) for the
  store text and privacy answers. Privacy policy:
  [`frontend/privacy.html`](frontend/privacy.html).

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
│   │   ├── main.py           # FastAPI app, CORS, health check, startup
│   │   ├── deps.py           # DB session + signed-in user dependencies
│   │   ├── migrations.py     # Idempotent schema upgrades (adds per-user ownership)
│   │   ├── database.py       # Engine/session setup (DATABASE_URL)
│   │   ├── models.py         # SQLAlchemy models: Recipe, Ingredient, MealPlanEntry,
│   │   │                     #   PantryItem, FoodRestriction, GroceryItem, Profile
│   │   ├── schemas.py        # Pydantic request/response models + validation
│   │   ├── seed.py           # Sample recipes for a fresh database
│   │   ├── data/
│   │   │   ├── catalog.py    # 112 built-in recipes for the generator
│   │   │   ├── nutrition.py  # Macros per 100 g (USDA FoodData Central)
│   │   │   └── prices.py     # Grocery prices (BLS averages + estimates), staples
│   │   ├── routers/
│   │   │   ├── auth.py       # /api/auth (sign up, log in, log out, delete account)
│   │   │   ├── recipes.py    # /api/recipes CRUD and meal ideas
│   │   │   ├── plan.py       # /api/plan and /api/shopping-list
│   │   │   ├── dining_out.py # /api/dining-out (meals eaten out)
│   │   │   ├── pantry.py     # /api/pantry CRUD
│   │   │   ├── restrictions.py  # /api/restrictions (allergies & dislikes)
│   │   │   ├── profile.py    # /api/profile (budget, household, diet, mode)
│   │   │   ├── groceries.py  # /api/groceries (your own shopping-list items)
│   │   │   ├── generator.py  # /api/generator (generate & apply a week)
│   │   │   └── discover.py   # /api/discover (search & import from TheMealDB)
│   │   └── services/
│   │       ├── auth.py       # Password hashing and session tokens
│   │       ├── matching.py   # Name normalisation, allergy & diet groups, pantry matching
│   │       ├── pricing.py    # Cost estimates and per-ingredient breakdowns
│   │       ├── nutrition.py  # Macro estimates per serving
│   │       ├── units.py      # Unit conversion (weight, volume, density, piece weight)
│   │       ├── mealdb.py     # TheMealDB client and measure parser
│   │       ├── shopping.py   # Scaling, aggregation, pantry subtraction, pricing
│   │       └── generator.py  # Budget-aware meal plan generator
│   └── tests/                # pytest suite
├── frontend/
│   ├── index.html, styles.css, app.js
│   ├── privacy.html, support.html, legal.css
│   ├── manifest.webmanifest, sw.js   # Installable web app
│   ├── icons/                # App icons
│   └── vendor/               # Lucide icons + fonts, self-hosted
├── mobile/                   # iPhone app (Capacitor config, icon and launch screen)
├── docs/app-store/           # Publishing checklist and App Store listing
├── .github/workflows/ci.yml  # Continuous integration
├── .github/workflows/ios.yml # iPhone build / App Store upload (manual)
├── vercel.json               # Vercel routing/build config
├── requirements.txt          # Runtime dependencies
└── requirements-dev.txt      # + test & lint tools
```

## API

Every endpoint except `/api/health` and sign-up/login needs an
`Authorization: Bearer <token>` header and only returns the signed-in user's data.

Interactive docs are served at `/docs` when running locally.

| Method | Endpoint                               | Description                                   |
| ------ | -------------------------------------- | --------------------------------------------- |
| GET    | `/api/health`                          | Health check (also checks the DB connection)  |
| POST   | `/api/auth/signup`                     | Create an account: `{email, password, name}` → `{token, user}` |
| POST   | `/api/auth/login`                      | Log in → `{token, user}`                      |
| GET    | `/api/auth/me`                         | The signed-in user                            |
| POST   | `/api/auth/logout`                     | End this session                              |
| DELETE | `/api/auth/account`                    | Delete the account and all its data: `{password}` |
| GET    | `/api/recipes?q=&safe_only=`           | List recipes with cost per serving, a per-ingredient cost breakdown and any diet/allergy/dislike conflicts; `safe_only=true` hides them |
| GET    | `/api/recipes/ideas`                   | Safe recipes ranked by pantry coverage        |
| POST   | `/api/recipes`                         | Create a recipe                               |
| GET    | `/api/recipes/{id}`                    | Get one recipe                                |
| PUT    | `/api/recipes/{id}`                    | Update a recipe (replaces its ingredients)    |
| DELETE | `/api/recipes/{id}`                    | Delete a recipe (and its planned meals)       |
| GET    | `/api/plan?start=YYYY-MM-DD`           | Meals planned for the 7 days from `start`     |
| PUT    | `/api/plan`                            | Set a slot: `{day, meal_type, recipe_id}`     |
| DELETE | `/api/plan/{id}`                       | Clear a planned meal                          |
| GET    | `/api/dining-out?start=YYYY-MM-DD`     | Meals eaten out in the 7 days from `start`    |
| PUT    | `/api/dining-out`                      | Mark a slot as eating out: `{day, meal_type, note, cost}` (replaces any recipe there) |
| DELETE | `/api/dining-out/{id}`                 | Un-mark a meal out                            |
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
| GET    | `/api/discover?q=`                     | Search TheMealDB; results include estimated cost and conflicts |
| POST   | `/api/discover/{id}/import`            | Add a TheMealDB recipe to the library (credited) |

## Running locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn backend.app.main:app --reload
```

Open http://localhost:8000 and create an account. With no `DATABASE_URL` set, data is stored in a local SQLite file (`mealplanner.db`). To use Postgres locally, copy `.env.example` to `.env` and set `DATABASE_URL`.

### Settings (environment variables)

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | local SQLite file | Postgres connection string (set automatically by Vercel's Neon integration) |
| `SEED_SAMPLE_DATA` | `true` | Give new accounts 4 sample recipes |
| `MEALDB_API_KEY` | `1` (free test key) | TheMealDB key; a supporter key is required for App Store release |
| `CORS_ORIGINS` | none | Extra allowed origins (the iPhone app's `capacitor://localhost` is always allowed) |

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
