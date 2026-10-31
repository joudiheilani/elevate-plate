import datetime as dt

from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.app.models import AuthToken
from backend.app.services.auth import hash_password, verify_password

PASSWORD = "correct horse battery"


def test_password_hashing():
    stored = hash_password("s3cret-pass")
    assert stored.startswith("scrypt$") and "s3cret-pass" not in stored
    assert verify_password("s3cret-pass", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("s3cret-pass", "garbage")
    assert hash_password("same") != hash_password("same")  # random salt


def test_signup_login_me_logout(anon, sign_up):
    user = sign_up("Bob@Example.com", PASSWORD, "Bob")
    assert user.get("/api/auth/me").json()["email"] == "bob@example.com"

    login = anon.post("/api/auth/login", json={"email": "BOB@example.com", "password": PASSWORD})
    assert login.status_code == 200
    assert login.json()["user"]["name"] == "Bob"

    assert user.post("/api/auth/logout").status_code == 204
    assert user.get("/api/auth/me").status_code == 401


def test_signup_validation(anon, sign_up):
    sign_up("taken@example.com")
    duplicate = anon.post(
        "/api/auth/signup", json={"email": "TAKEN@example.com", "password": PASSWORD}
    )
    assert duplicate.status_code == 409
    short = anon.post("/api/auth/signup", json={"email": "a@b.co", "password": "short"})
    assert short.status_code == 422
    bad_email = anon.post("/api/auth/signup", json={"email": "not-an-email", "password": PASSWORD})
    assert bad_email.status_code == 422


def test_login_failures_are_generic(anon, sign_up):
    sign_up("carol@example.com")
    wrong = anon.post("/api/auth/login", json={"email": "carol@example.com", "password": "nope"})
    missing = anon.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


def test_data_endpoints_require_sign_in(anon):
    for path in ("/api/recipes", "/api/pantry", "/api/profile", "/api/restrictions"):
        assert anon.get(path).status_code == 401
    anon.headers["Authorization"] = "Bearer not-a-real-token"
    assert anon.get("/api/recipes").status_code == 401
    assert anon.get("/api/health").status_code == 200  # still public


def test_expired_session(db_engine, client):
    with Session(db_engine) as db:
        db.execute(update(AuthToken).values(expires_at=dt.datetime(2000, 1, 1, tzinfo=dt.UTC)))
        db.commit()
    response = client.get("/api/recipes")
    assert response.status_code == 401
    assert "sign in again" in response.json()["detail"]


def test_users_cannot_see_or_touch_each_others_data(sign_up):
    alice = sign_up("alice@example.com")
    bob = sign_up("bob@example.com")

    recipe = alice.post("/api/recipes", json={"name": "Alice's Soup", "ingredients": []}).json()
    pantry = alice.post("/api/pantry", json={"name": "rice"}).json()
    allergy = alice.post("/api/restrictions", json={"name": "Peanuts"}).json()
    grocery = alice.post("/api/groceries", json={"name": "coffee"}).json()
    plan = alice.put(
        "/api/plan", json={"day": "2026-10-12", "meal_type": "dinner", "recipe_id": recipe["id"]}
    ).json()
    alice.put("/api/profile", json={**alice.get("/api/profile").json(), "weekly_budget": 200})

    assert bob.get("/api/recipes").json() == []
    assert bob.get("/api/pantry").json() == []
    assert bob.get("/api/restrictions").json() == []
    assert bob.get("/api/groceries").json() == []
    assert bob.get("/api/plan", params={"start": "2026-10-12"}).json() == []
    assert bob.get("/api/profile").json()["weekly_budget"] == 75
    assert bob.get("/api/shopping-list", params={"start": "2026-10-12"}).json()["items"] == []

    assert bob.get(f"/api/recipes/{recipe['id']}").status_code == 404
    assert bob.delete(f"/api/recipes/{recipe['id']}").status_code == 404
    assert bob.delete(f"/api/pantry/{pantry['id']}").status_code == 404
    assert bob.delete(f"/api/restrictions/{allergy['id']}").status_code == 404
    assert bob.delete(f"/api/groceries/{grocery['id']}").status_code == 404
    assert bob.delete(f"/api/plan/{plan['id']}").status_code == 404
    stolen = {"day": "2026-10-12", "meal_type": "lunch", "recipe_id": recipe["id"]}
    assert bob.put("/api/plan", json=stolen).status_code == 404

    # Same names are fine across users.
    assert bob.post("/api/restrictions", json={"name": "Peanuts"}).status_code == 201
    assert alice.get(f"/api/recipes/{recipe['id']}").status_code == 200


def test_delete_account_removes_everything(anon, sign_up):
    user = sign_up("dave@example.com")
    recipe = user.post("/api/recipes", json={"name": "Stew", "ingredients": [{"name": "beef"}]})
    user.put(
        "/api/plan",
        json={"day": "2026-10-12", "meal_type": "dinner", "recipe_id": recipe.json()["id"]},
    )
    user.post("/api/pantry", json={"name": "salt"})
    user.get("/api/profile")

    wrong = user.request("DELETE", "/api/auth/account", json={"password": "nope"})
    assert wrong.status_code == 403
    assert (
        user.request("DELETE", "/api/auth/account", json={"password": PASSWORD}).status_code == 204
    )

    assert user.get("/api/auth/me").status_code == 401
    login = anon.post("/api/auth/login", json={"email": "dave@example.com", "password": PASSWORD})
    assert login.status_code == 401
    # The email can be used again, and the new account starts empty.
    fresh = sign_up("dave@example.com")
    assert fresh.get("/api/recipes").json() == []
    assert fresh.get("/api/pantry").json() == []


def test_new_accounts_get_sample_recipes_when_enabled(sign_up, monkeypatch):
    monkeypatch.setenv("SEED_SAMPLE_DATA", "true")
    user = sign_up("erin@example.com")
    names = [r["name"] for r in user.get("/api/recipes").json()]
    assert "Overnight Oats" in names and len(names) == 4
