import os

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select

from ..deps import CurrentUser, DbSession
from ..migrations import claim_unowned_rows
from ..models import (
    AuthToken,
    FoodRestriction,
    GroceryItem,
    Ingredient,
    MealPlanEntry,
    PantryItem,
    Profile,
    Recipe,
    User,
)
from ..schemas import AuthOut, DeleteAccountIn, LoginIn, SignupIn, UserOut
from ..seed import seed_for_user
from ..services.auth import hash_password, new_token, token_expiry, verify_password

router = APIRouter(prefix="/api/auth", tags=["accounts"])


def _start_session(db, user: User) -> AuthOut:
    token, token_hash = new_token()
    db.add(AuthToken(user_id=user.id, token_hash=token_hash, expires_at=token_expiry()))
    db.commit()
    return AuthOut(token=token, user=UserOut.model_validate(user))


@router.post("/signup", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: DbSession):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    is_first_user = not db.scalar(select(func.count()).select_from(User))
    user = User(email=email, name=payload.name, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    if is_first_user:
        # Data created before accounts existed belongs to whoever set up the app.
        claim_unowned_rows(db, user.id)
    if os.getenv("SEED_SAMPLE_DATA", "true").lower() == "true":
        seed_for_user(db, user.id)
    return _start_session(db, user)


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, db: DbSession):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return _start_session(db, user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: DbSession, user: CurrentUser):
    db.execute(delete(AuthToken).where(AuthToken.id == request.state.auth_token_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(payload: DeleteAccountIn, db: DbSession, user: CurrentUser):
    """Permanently delete the account and everything in it (required by the App Store)."""
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=403, detail="That password isn't right.")
    recipe_ids = select(Recipe.id).where(Recipe.user_id == user.id)
    # Explicit deletes, children first, so this works even where foreign-key cascades
    # aren't enforced (SQLite).
    db.execute(delete(MealPlanEntry).where(MealPlanEntry.user_id == user.id))
    db.execute(delete(MealPlanEntry).where(MealPlanEntry.recipe_id.in_(recipe_ids)))
    db.execute(delete(Ingredient).where(Ingredient.recipe_id.in_(recipe_ids)))
    for model in (Recipe, PantryItem, GroceryItem, Profile, FoodRestriction):
        db.execute(delete(model).where(model.user_id == user.id))
    db.execute(delete(AuthToken).where(AuthToken.user_id == user.id))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
