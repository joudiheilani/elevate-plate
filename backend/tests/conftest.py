import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db, make_engine
from backend.app.main import app

# CI points this at a real Postgres service; locally it defaults to in-memory SQLite.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def client():
    engine = make_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    # Not used as a context manager, so the app's startup (create tables + seed) is skipped.
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def make_recipe(client):
    def _make_recipe(name="Pancakes", ingredients=None, **fields):
        payload = {
            "name": name,
            "servings": 2,
            "ingredients": ingredients
            if ingredients is not None
            else [{"name": "flour", "quantity": 2, "unit": "cup"}],
            **fields,
        }
        response = client.post("/api/recipes", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_recipe
