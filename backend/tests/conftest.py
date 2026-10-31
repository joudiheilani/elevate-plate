import os

# New accounts normally get sample recipes; tests start from an empty library.
os.environ.setdefault("SEED_SAMPLE_DATA", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.app.database import Base, get_db, make_engine  # noqa: E402
from backend.app.main import app  # noqa: E402

# CI points this at a real Postgres service; locally it defaults to in-memory SQLite.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def db_engine():
    engine = make_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield engine
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def anon(db_engine):
    """A client that isn't signed in."""
    # Not used as a context manager, so the app's startup (create tables) is skipped.
    return TestClient(app)


@pytest.fixture
def sign_up(db_engine):
    """Create an account and return a client signed in as it."""

    def _sign_up(email="alice@example.com", password="correct horse battery", name=""):
        user_client = TestClient(app)
        response = user_client.post(
            "/api/auth/signup", json={"email": email, "password": password, "name": name}
        )
        assert response.status_code == 201, response.text
        user_client.headers["Authorization"] = f"Bearer {response.json()['token']}"
        return user_client

    return _sign_up


@pytest.fixture
def client(sign_up):
    """A client signed in as a fresh user (most tests just need "a user")."""
    return sign_up()


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
