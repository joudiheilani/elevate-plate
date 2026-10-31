"""Upgrading a database created before user accounts existed (like the live one)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db, make_engine
from backend.app.main import app
from backend.app.migrations import migrate

from .conftest import TEST_DATABASE_URL

LEGACY_SCHEMA = [
    "CREATE TABLE recipes (id {pk}, name VARCHAR(200), description TEXT, "
    "instructions TEXT, servings INTEGER, prep_minutes INTEGER, created_at TIMESTAMP)",
    "CREATE TABLE ingredients (id {pk}, recipe_id INTEGER REFERENCES recipes(id), "
    "name VARCHAR(120), quantity FLOAT, unit VARCHAR(30), position INTEGER)",
    "CREATE TABLE meal_plan_entries (id {pk}, day DATE, meal_type VARCHAR(20), "
    "recipe_id INTEGER REFERENCES recipes(id), CONSTRAINT uq_meal_slot UNIQUE (day, meal_type))",
    "CREATE TABLE pantry_items (id {pk}, name VARCHAR(120), quantity FLOAT, unit VARCHAR(30))",
    "CREATE TABLE grocery_items (id {pk}, name VARCHAR(120), quantity FLOAT, "
    "unit VARCHAR(30), price FLOAT)",
    "CREATE TABLE food_restrictions (id {pk}, name VARCHAR(80) UNIQUE, kind VARCHAR(10))",
    "CREATE TABLE profile (id {pk}, weekly_budget FLOAT, people INTEGER, max_minutes INTEGER, "
    "diet VARCHAR(20), meals VARCHAR(40), mode VARCHAR(10), assume_staples BOOLEAN)",
]
LEGACY_ROWS = [
    "INSERT INTO recipes (id, name, description, instructions, servings) "
    "VALUES (1, 'Breakfast Burrito', '', '', 1)",
    "INSERT INTO ingredients (id, recipe_id, name, quantity, unit, position) "
    "VALUES (1, 1, 'eggs', 2, '', 0)",
    "INSERT INTO meal_plan_entries (id, day, meal_type, recipe_id) "
    "VALUES (1, '2026-10-12', 'breakfast', 1)",
    "INSERT INTO pantry_items (id, name, quantity, unit) VALUES (1, 'rice', NULL, '')",
    "INSERT INTO food_restrictions (id, name, kind) VALUES (1, 'Dairy', 'allergy')",
    "INSERT INTO profile (id, weekly_budget, people, max_minutes, diet, meals, mode, "
    "assume_staples) VALUES (1, 90, 3, 30, 'any', 'breakfast,lunch,dinner', 'auto', TRUE)",
]


@pytest.fixture
def legacy_engine():
    engine = make_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    pk = "SERIAL PRIMARY KEY" if engine.dialect.name == "postgresql" else "INTEGER PRIMARY KEY"
    with engine.begin() as conn:
        for statement in LEGACY_SCHEMA:
            conn.execute(text(statement.format(pk=pk)))
        for statement in LEGACY_ROWS:
            conn.execute(text(statement))
    Base.metadata.create_all(engine)  # adds users / auth_tokens, leaves old tables alone
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_migration_adds_owner_columns_and_is_idempotent(legacy_engine):
    applied = migrate(legacy_engine)
    assert "added recipes.user_id" in applied
    for table in ("recipes", "meal_plan_entries", "pantry_items", "food_restrictions", "profile"):
        columns = {c["name"] for c in inspect(legacy_engine).get_columns(table)}
        assert "user_id" in columns, table
    assert migrate(legacy_engine) == []  # nothing left to do


def test_first_account_claims_existing_data(legacy_engine):
    migrate(legacy_engine)
    TestingSession = sessionmaker(bind=legacy_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        owner, other = TestClient(app), TestClient(app)
        for client, email in ((owner, "owner@example.com"), (other, "other@example.com")):
            response = client.post(
                "/api/auth/signup", json={"email": email, "password": "long enough pw"}
            )
            client.headers["Authorization"] = f"Bearer {response.json()['token']}"

        assert [r["name"] for r in owner.get("/api/recipes").json()] == ["Breakfast Burrito"]
        assert owner.get("/api/profile").json()["weekly_budget"] == 90
        assert (
            owner.get("/api/plan", params={"start": "2026-10-12"}).json()[0]["recipe"]["name"]
            == "Breakfast Burrito"
        )

        assert other.get("/api/recipes").json() == []
        assert other.get("/api/profile").json()["weekly_budget"] == 75  # a fresh profile row
        # Per-user uniqueness: both can plan the same slot and name the same allergy.
        # (Only checked on Postgres, which the live site uses: SQLite can't drop the old
        # app-wide constraints, and is only used for local development.)
        if legacy_engine.dialect.name == "postgresql":
            recipe = other.post("/api/recipes", json={"name": "Toast", "ingredients": []}).json()
            slot = {"day": "2026-10-12", "meal_type": "breakfast", "recipe_id": recipe["id"]}
            assert other.put("/api/plan", json=slot).status_code == 200
            assert other.post("/api/restrictions", json={"name": "Dairy"}).status_code == 201
    finally:
        app.dependency_overrides.clear()
