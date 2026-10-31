from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import CurrentUser, DbSession
from ..models import Profile, User
from ..schemas import ProfileData

router = APIRouter(prefix="/api/profile", tags=["profile & budget"])


def get_profile(db: Session, user: User) -> Profile:
    """The user's profile row, created with defaults on first use."""
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(user_id=user.id, **_to_columns(ProfileData()))
        db.add(profile)
        db.commit()
    return profile


def _to_columns(data: ProfileData) -> dict:
    return {**data.model_dump(exclude={"meals"}), "meals": ",".join(data.meals)}


def to_profile_data(profile: Profile) -> ProfileData:
    return ProfileData(
        weekly_budget=profile.weekly_budget,
        people=profile.people,
        max_minutes=profile.max_minutes,
        diet=profile.diet,
        meals=[meal for meal in profile.meals.split(",") if meal],
        mode=profile.mode,
        assume_staples=profile.assume_staples,
    )


@router.get("", response_model=ProfileData)
def read_profile(db: DbSession, user: CurrentUser):
    return to_profile_data(get_profile(db, user))


@router.put("", response_model=ProfileData)
def update_profile(payload: ProfileData, db: DbSession, user: CurrentUser):
    profile = get_profile(db, user)
    for field, value in _to_columns(payload).items():
        setattr(profile, field, value)
    db.commit()
    return to_profile_data(profile)
